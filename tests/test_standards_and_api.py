from __future__ import annotations

import json
import os
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
        import build_standards

        build_standards.main()
        cls.states = json.loads((ROOT / "data/standards/states.json").read_text())["jurisdictions"]
        cls.by_state = json.loads((ROOT / "data/standards/by_state.json").read_text())
        cls.ccss = json.loads((ROOT / "data/standards/ccss_writing_language_k8.json").read_text())["grades"]

    def test_fifty_one_jurisdictions(self):
        abbrs = {row["abbr"] for row in self.states}
        self.assertEqual(len(abbrs), 51)
        self.assertIn("DC", abbrs)
        self.assertIn("TX", abbrs)
        self.assertIn("FL", abbrs)
        self.assertIn("VA", abbrs)
        self.assertIn("NE", abbrs)

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
        self.assertIn("L.3.2", codes)

    def test_texas_uses_teks_codes(self):
        codes = [i["code"] for i in self.by_state["TX"]["3"]]
        self.assertTrue(any(c.startswith("3.11") for c in codes))
        self.assertTrue(any(c.startswith("3.12") for c in codes))

    def test_florida_uses_best_codes(self):
        codes = [i["code"] for i in self.by_state["FL"]["3"]]
        self.assertIn("ELA.3.C.1.3", codes)


class AssessTests(unittest.TestCase):
    def test_california_opinion(self):
        from assess import assess

        text = (
            "I think kids should learn history every week. First, because it helps us "
            "understand why rules exist. For example, voting rights changed because people "
            "wrote and spoke up. Another reason is that history is full of odd true stories. "
            "In conclusion, history class should stay."
        )
        result = assess(text, "CA", "3", "opinion")
        self.assertEqual(result["state"], "CA")
        self.assertGreaterEqual(result["overall"], 3)
        codes = [s["code"] for c in result["constructs"] for s in c["standards"]]
        self.assertTrue(any(code.startswith("W.3") for code in codes))

    def test_texas_letter(self):
        from assess import assess

        text = (
            "Dear Grandma,\n\nThank you for the book about Texas. I read it on the porch. "
            "Please write back and tell me about the ranch when you were little.\n\nLove,\nSam"
        )
        result = assess(text, "TX", "3", "letter")
        self.assertEqual(result["genre"], "correspondence")
        codes = [s["code"] for c in result["constructs"] for s in c["standards"]]
        self.assertTrue(any("3.12" in code or "3.11" in code for code in codes))

    def test_emptyish_is_low(self):
        from assess import assess

        result = assess("hi", "NE", "K", "narrative")
        self.assertEqual(result["overall"], 1)


class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ["SQUAD_DB"] = str(Path(tempfile.gettempdir()) / "squad-test.db")
        Path(os.environ["SQUAD_DB"]).unlink(missing_ok=True)
        from fastapi.testclient import TestClient
        import server

        server.init_db()
        cls.client = TestClient(server.app)

    def test_health_and_states(self):
        health = self.client.get("/api/health").json()
        self.assertTrue(health["ok"])
        self.assertEqual(health["jurisdictions"], 51)
        listed = self.client.get("/api/states").json()["jurisdictions"]
        self.assertEqual(len(listed), 51)

    def test_register_assess_and_free_cap(self):
        email = "parent@example.com"
        r = self.client.post(
            "/api/auth/register",
            json={"email": email, "password": "secret1", "name": "Parent", "state": "VA", "grade": "3", "writer_name": "Jo"},
        )
        self.assertEqual(r.status_code, 200, r.text)
        sample = "I think recess should be longer because kids need to move. Another reason is we talk and solve problems. In conclusion, more recess helps writing later."
        for i in range(3):
            a = self.client.post(
                "/api/assess",
                json={"text": sample, "state": "VA", "grade": "3", "genre": "opinion", "prompt_title": f"t{i}"},
            )
            self.assertEqual(a.status_code, 200, a.text)
        blocked = self.client.post(
            "/api/assess",
            json={"text": sample, "state": "VA", "grade": "3", "genre": "opinion"},
        )
        self.assertEqual(blocked.status_code, 402)
        sub = self.client.post("/api/subscribe", json={"plan": "family"})
        self.assertEqual(sub.status_code, 200)
        after = self.client.post(
            "/api/assess",
            json={"text": sample, "state": "VA", "grade": "3", "genre": "opinion"},
        )
        self.assertEqual(after.status_code, 200, after.text)


if __name__ == "__main__":
    unittest.main()
