from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import sqlite3
import time
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from assess import coach, rubric, standards_for, state_meta, states

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = Path(os.environ.get("COACH_DB", os.environ.get("SQUAD_DB", ROOT / "backend" / "coach.db")))
SECRET = os.environ.get("COACH_SECRET", os.environ.get("SQUAD_SECRET", "dev-only-change-me"))
COOKIE = "ewc_session"
MAX_AGE = 60 * 60 * 24 * 30

app = FastAPI(title="Early Writing Coach", version="0.5.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def db() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    with db() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              email TEXT UNIQUE NOT NULL,
              password_hash TEXT NOT NULL,
              name TEXT NOT NULL,
              plan TEXT NOT NULL DEFAULT 'free',
              state TEXT DEFAULT 'CA',
              grade TEXT DEFAULT '3',
              writer_name TEXT DEFAULT '',
              created_at INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS recommendations (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              user_id INTEGER,
              state TEXT NOT NULL,
              grade TEXT NOT NULL,
              assignment_label TEXT,
              focus_json TEXT NOT NULL,
              created_at INTEGER NOT NULL,
              saved_on_device_at INTEGER,
              FOREIGN KEY(user_id) REFERENCES users(id)
            );
            """
        )


def hash_password(password: str, salt: Optional[str] = None) -> str:
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 120_000).hex()
    return f"{salt}${digest}"


def verify_password(password: str, stored: str) -> bool:
    salt, _digest = stored.split("$", 1)
    return hmac.compare_digest(stored, hash_password(password, salt))


def sign_session(user_id: int) -> str:
    payload = f"{user_id}:{int(time.time())}"
    sig = hmac.new(SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return f"{payload}:{sig}"


def read_session(token: str) -> Optional[int]:
    try:
        user_id, ts, sig = token.split(":")
        expected = hmac.new(SECRET.encode(), f"{user_id}:{ts}".encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected):
            return None
        return int(user_id)
    except (ValueError, TypeError):
        return None


def current_user(request: Request) -> Optional[sqlite3.Row]:
    token = request.cookies.get(COOKIE)
    if not token:
        return None
    uid = read_session(token)
    if not uid:
        return None
    with db() as conn:
        return conn.execute("SELECT * FROM users WHERE id = ?", (uid,)).fetchone()


def require_user(request: Request) -> sqlite3.Row:
    user = current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Sign in to continue.")
    return user


def set_session(response: Response, user_id: int) -> None:
    response.set_cookie(COOKIE, sign_session(user_id), httponly=True, samesite="lax", max_age=MAX_AGE)


def remaining_notes(user: sqlite3.Row) -> Optional[int]:
    if user["plan"] in {"family", "classroom"}:
        return None
    limit = rubric()["plans"]["free"]["notes"]
    with db() as conn:
        used = conn.execute(
            "SELECT COUNT(*) AS n FROM recommendations WHERE user_id = ?", (user["id"],)
        ).fetchone()["n"]
    return max(0, limit - used)


class RegisterIn(BaseModel):
    email: str = Field(min_length=3)
    password: str = Field(min_length=6)
    name: str = Field(min_length=1)
    writer_name: str = ""
    state: str = "CA"
    grade: str = "3"


class LoginIn(BaseModel):
    email: str
    password: str


class ProfileIn(BaseModel):
    writer_name: Optional[str] = None
    state: Optional[str] = None
    grade: Optional[str] = None


class SubscribeIn(BaseModel):
    plan: str = "family"


class CoachIn(BaseModel):
    text: str = Field(min_length=1)
    state: str = "CA"
    grade: str = "3"
    assignment_label: str = ""
    genre: str = "any"


def current_user_by_id(uid: int) -> sqlite3.Row:
    with db() as conn:
        return conn.execute("SELECT * FROM users WHERE id = ?", (uid,)).fetchone()


def user_payload(user: sqlite3.Row) -> dict:
    return {
        "id": user["id"],
        "email": user["email"],
        "name": user["name"],
        "plan": user["plan"],
        "state": user["state"],
        "grade": user["grade"],
        "writer_name": user["writer_name"],
        "remaining_notes": remaining_notes(user),
    }


def public_note(row: sqlite3.Row) -> dict:
    payload = json.loads(row["focus_json"])
    payload["id"] = row["id"]
    payload["created_at"] = row["created_at"]
    payload["saved_on_device"] = bool(row["saved_on_device_at"])
    payload["writing_stored"] = False
    return payload


@app.on_event("startup")
def _startup() -> None:
    init_db()


@app.get("/api/health")
def health():
    return {"ok": True, "product": "earlywritingcoach", "jurisdictions": len(states()), "stores_writing": False}


@app.get("/api/states")
def list_states():
    return {"jurisdictions": states()}


@app.get("/api/standards")
def get_standards(state: str = "CA", grade: str = "3"):
    try:
        meta = state_meta(state)
        items = standards_for(state, grade)
    except KeyError as exc:
        raise HTTPException(404, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(400, str(exc)) from exc
    return {"state": meta, "grade": str(grade).upper(), "standards": items}


@app.get("/api/plans")
def plans():
    return rubric()["plans"]


@app.post("/api/auth/register")
def register(body: RegisterIn, response: Response):
    try:
        state_meta(body.state)
    except KeyError:
        raise HTTPException(400, "Pick a US state or DC.")
    with db() as conn:
        try:
            cur = conn.execute(
                "INSERT INTO users (email, password_hash, name, state, grade, writer_name, created_at) VALUES (?,?,?,?,?,?,?)",
                (
                    body.email.lower(),
                    hash_password(body.password),
                    body.name.strip(),
                    body.state.upper(),
                    str(body.grade).upper(),
                    body.writer_name.strip(),
                    int(time.time()),
                ),
            )
            uid = cur.lastrowid
        except sqlite3.IntegrityError:
            raise HTTPException(409, "That email already has an account.")
    set_session(response, uid)
    return user_payload(current_user_by_id(uid))


@app.post("/api/auth/login")
def login(body: LoginIn, response: Response):
    with db() as conn:
        user = conn.execute("SELECT * FROM users WHERE email = ?", (body.email.lower(),)).fetchone()
    if not user or not verify_password(body.password, user["password_hash"]):
        raise HTTPException(401, "Email or password is not right.")
    set_session(response, user["id"])
    return user_payload(user)


@app.post("/api/auth/logout")
def logout(response: Response):
    response.delete_cookie(COOKIE)
    return {"ok": True}


@app.get("/api/me")
def me(request: Request):
    user = current_user(request)
    if not user:
        return JSONResponse({"user": None})
    return {"user": user_payload(user)}


@app.post("/api/me")
def update_me(body: ProfileIn, request: Request):
    user = require_user(request)
    state = (body.state or user["state"]).upper()
    grade = str(body.grade or user["grade"]).upper()
    try:
        state_meta(state)
    except KeyError:
        raise HTTPException(400, "Unknown state")
    writer = body.writer_name if body.writer_name is not None else user["writer_name"]
    with db() as conn:
        conn.execute(
            "UPDATE users SET state=?, grade=?, writer_name=? WHERE id=?",
            (state, grade, writer, user["id"]),
        )
    return user_payload(current_user_by_id(user["id"]))


@app.post("/api/subscribe")
def subscribe(body: SubscribeIn, request: Request):
    user = require_user(request)
    if body.plan not in {"family", "classroom"}:
        raise HTTPException(400, "Choose family or classroom.")
    with db() as conn:
        conn.execute("UPDATE users SET plan=? WHERE id=?", (body.plan, user["id"]))
    return {"ok": True, "plan": body.plan, "mode": "demo", "user": user_payload(current_user_by_id(user["id"]))}


@app.post("/api/coach")
def run_coach(body: CoachIn, request: Request):
    user = current_user(request)
    if user:
        left = remaining_notes(user)
        if left == 0:
            raise HTTPException(402, "Free plan includes three coaching notes. Open a family plan to keep going.")
    try:
        result = coach(body.text, body.state, body.grade, body.assignment_label, body.genre)
    except (KeyError, ValueError) as exc:
        raise HTTPException(400, str(exc)) from exc
    # Never persist body.text. Only skill notes are stored for signed-in parents.
    uid = user["id"] if user else None
    note_id = None
    if uid:
        with db() as conn:
            cur = conn.execute(
                "INSERT INTO recommendations (user_id, state, grade, assignment_label, focus_json, created_at) VALUES (?,?,?,?,?,?)",
                (
                    uid,
                    result["state"],
                    result["grade"],
                    result["assignment_label"],
                    json.dumps(result),
                    int(time.time()),
                ),
            )
            note_id = cur.lastrowid
        result["remaining_notes"] = remaining_notes(current_user_by_id(uid))
    result["id"] = note_id
    result["account_kept_writing"] = False
    return result


@app.get("/api/notes")
def list_notes(request: Request):
    user = require_user(request)
    with db() as conn:
        rows = conn.execute(
            "SELECT id, state, grade, assignment_label, created_at, saved_on_device_at, focus_json FROM recommendations WHERE user_id=? ORDER BY id DESC LIMIT 50",
            (user["id"],),
        ).fetchall()
    notes = []
    for row in rows:
        payload = json.loads(row["focus_json"])
        notes.append(
            {
                "id": row["id"],
                "state": row["state"],
                "grade": row["grade"],
                "assignment_label": row["assignment_label"],
                "created_at": row["created_at"],
                "saved_on_device": bool(row["saved_on_device_at"]),
                "titles": [f["title"] for f in payload.get("focuses", [])],
            }
        )
    return {"notes": notes, "stores_writing": False}


@app.get("/api/notes/{note_id}")
def get_note(note_id: int, request: Request):
    user = require_user(request)
    with db() as conn:
        row = conn.execute(
            "SELECT * FROM recommendations WHERE id=? AND user_id=?", (note_id, user["id"])
        ).fetchone()
    if not row:
        raise HTTPException(404, "Not found")
    return public_note(row)


@app.post("/api/notes/{note_id}/saved")
def mark_saved(note_id: int, request: Request):
    user = require_user(request)
    with db() as conn:
        cur = conn.execute(
            "UPDATE recommendations SET saved_on_device_at=? WHERE id=? AND user_id=?",
            (int(time.time()), note_id, user["id"]),
        )
        if cur.rowcount == 0:
            raise HTTPException(404, "Not found")
    return {
        "ok": True,
        "cue": "This coaching note is marked as saved on your device. Keep the downloaded file or the printout — the writing sample is still not stored here.",
    }


@app.get("/")
def home():
    return FileResponse(ROOT / "index.html")


app.mount("/assets", StaticFiles(directory=ROOT / "assets"), name="assets")
app.mount("/data", StaticFiles(directory=ROOT / "data"), name="data")


@app.get("/{page}.html")
def html_page(page: str):
    path = ROOT / f"{page}.html"
    if not path.exists():
        raise HTTPException(404)
    return FileResponse(path)
