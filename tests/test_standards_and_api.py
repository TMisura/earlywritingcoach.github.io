from __future__ import annotations

import json
import os
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "tools"))

import build_standards

build_standards.main()


class StandardsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.states = json.loads((ROOT / "data/standards/states.json").read_text())["jurisdictions"]
        cls.by_state = json.loads((ROOT / "data/standards/by_state.json").read_text())
        cls.ccss = json.loads((ROOT / "data/standards/ccss_writing_language_k8.json").read_text())["grades"]

    def test_fifty_one_jurisdictions(self):
        abbrs = {row["abbr"] for row in self.states}
        self.assertEqual(len(abbrs), 51)
        self.assertIn("DC", abbrs)

    def test_every_grade_has_writing_constructs(self):
        needed = {"opinion", "informative", "narrative", "conventions"}
        for row in self.states:
            for grade in ["K", "1", "2", "3", "4", "5", "6", "7", "8"]:
                constructs = {item["construct"] for item in self.by_state[row["abbr"]][grade]}
                missing = needed - constructs
                self.assertFalse(missing, f"{row['abbr']} grade {grade} missing {missing}")

    def test_ccss_grade3_opinion_present(self):
        codes = [i["code"] for i in self.ccss["3"]]
        self.assertIn("W.3.1", codes)
        self.assertIn("L.3.1", codes)


class CoachTests(unittest.TestCase):
    def test_returns_one_or_two_focuses_and_no_writing(self):
        from assess import coach

        text = "i like dogs they run they are fun my dog is named spot"
        result = coach(text, "CA", "3", "journal")
        self.assertEqual(result["writing_stored"], False)
        self.assertTrue(1 <= len(result["focuses"]) <= 2)
        self.assertNotIn("overall", result)
        dumped = json.dumps(result)
        self.assertNotIn("named spot", dumped)
        self.assertIn("save_filename", result)
        self.assertTrue(result["focuses"][0]["teacher_share"])
        self.assertTrue(result["focuses"][0]["home_practice"])

    def test_texas_codes_on_letter(self):
        from assess import coach

        text = "Dear Grandma thank you for the book please write back Love Sam"
        result = coach(text, "TX", "3", "letter home", "letter")
        codes = [s["code"] for f in result["focuses"] for s in f["standards"]]
        self.assertTrue(codes)


class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db = Path(tempfile.gettempdir()) / "coach-test.db"
        cls.db.unlink(missing_ok=True)
        os.environ["COACH_DB"] = str(cls.db)
        from fastapi.testclient import TestClient
        import server

        server.DB_PATH = cls.db
        server.init_db()
        cls.client = TestClient(server.app)
        cls.server = server

    def test_health_does_not_claim_to_store_writing(self):
        health = self.client.get("/api/health").json()
        self.assertTrue(health["ok"])
        self.assertEqual(health["jurisdictions"], 51)
        self.assertFalse(health["stores_writing"])

    def test_coach_does_not_persist_writing_and_caps_free_plan(self):
        sample = "i went to the park we played then we went home it was fun"
        r = self.client.post(
            "/api/auth/register",
            json={"email": "parent@example.com", "password": "secret1", "name": "Parent", "state": "VA", "grade": "3"},
        )
        self.assertEqual(r.status_code, 200, r.text)
        for i in range(3):
            a = self.client.post(
                "/api/coach",
                json={"text": sample, "state": "VA", "grade": "3", "assignment_label": f"hw {i}"},
            )
            self.assertEqual(a.status_code, 200, a.text)
            self.assertFalse(a.json()["writing_stored"])
            self.assertTrue(1 <= len(a.json()["focuses"]) <= 2)
            self.assertNotIn(sample, json.dumps(a.json()))
        blocked = self.client.post("/api/coach", json={"text": sample, "state": "VA", "grade": "3"})
        self.assertEqual(blocked.status_code, 402)
        self.client.post("/api/subscribe", json={"plan": "family"})
        after = self.client.post("/api/coach", json={"text": sample, "state": "VA", "grade": "3"})
        self.assertEqual(after.status_code, 200, after.text)
        conn = sqlite3.connect(self.db)
        row = conn.execute("SELECT focus_json, assignment_label FROM recommendations LIMIT 1").fetchone()
        conn.close()
        self.assertIsNotNone(row)
        self.assertNotIn(sample, row[0])
        notes = self.client.get("/api/notes").json()
        self.assertFalse(notes["stores_writing"])
        self.assertGreaterEqual(len(notes["notes"]), 3)


if __name__ == "__main__":
    unittest.main()
