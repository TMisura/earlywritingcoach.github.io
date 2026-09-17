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

from assess import assess, rubric, standards_for, state_meta, states

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = Path(os.environ.get("SQUAD_DB", ROOT / "backend" / "squad.db"))
SECRET = os.environ.get("SQUAD_SECRET", "dev-only-change-me")
COOKIE = "squad_session"
MAX_AGE = 60 * 60 * 24 * 30

app = FastAPI(title="Summer Writing Squad", version="0.4.0")
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
            CREATE TABLE IF NOT EXISTS assessments (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              user_id INTEGER,
              state TEXT NOT NULL,
              grade TEXT NOT NULL,
              genre TEXT NOT NULL,
              prompt_title TEXT,
              text TEXT NOT NULL,
              result_json TEXT NOT NULL,
              created_at INTEGER NOT NULL,
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
        payload = f"{user_id}:{ts}"
        expected = hmac.new(SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()
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


def remaining_assessments(user: sqlite3.Row) -> Optional[int]:
    plan = user["plan"]
    if plan in {"family", "classroom"}:
        return None
    limit = rubric()["plans"]["free"]["assessments"]
    with db() as conn:
        used = conn.execute(
            "SELECT COUNT(*) AS n FROM assessments WHERE user_id = ?", (user["id"],)
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


class AssessIn(BaseModel):
    text: str = Field(min_length=1)
    state: str = "CA"
    grade: str = "3"
    genre: str = "informative"
    prompt_title: str = ""


PROMPTS = json.loads((ROOT / "data" / "prompts.json").read_text()) if (ROOT / "data" / "prompts.json").exists() else {}


@app.on_event("startup")
def _startup() -> None:
    init_db()


@app.get("/api/health")
def health():
    return {"ok": True, "jurisdictions": len(states())}


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


@app.get("/api/prompts")
def prompts(destination: str = "history", grade: str = "3"):
    grade = str(grade).upper()
    dest = PROMPTS.get(destination, {})
    items = dest.get(grade) or dest.get("3") or []
    return {"destination": destination, "grade": grade, "prompts": items}


@app.get("/api/plans")
def plans():
    return rubric()["plans"]


def user_payload(user: sqlite3.Row) -> dict:
    return {
        "id": user["id"],
        "email": user["email"],
        "name": user["name"],
        "plan": user["plan"],
        "state": user["state"],
        "grade": user["grade"],
        "writer_name": user["writer_name"],
        "remaining_assessments": remaining_assessments(user),
    }


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
    user = current_user_by_id(uid)
    set_session(response, uid)
    return user_payload(user)


def current_user_by_id(uid: int) -> sqlite3.Row:
    with db() as conn:
        return conn.execute("SELECT * FROM users WHERE id = ?", (uid,)).fetchone()


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
    # Live Stripe checkout is the next backend slice. Demo activation makes the
    # product usable locally and on preview hosts without keys.
    with db() as conn:
        conn.execute("UPDATE users SET plan=? WHERE id=?", (body.plan, user["id"]))
    return {"ok": True, "plan": body.plan, "mode": "demo", "user": user_payload(current_user_by_id(user["id"]))}


@app.post("/api/assess")
def run_assess(body: AssessIn, request: Request):
    user = current_user(request)
    if user:
        left = remaining_assessments(user)
        if left == 0:
            raise HTTPException(402, "Free plan includes three scored pieces. Upgrade to keep going.")
    try:
        result = assess(body.text, body.state, body.grade, body.genre)
    except (KeyError, ValueError) as exc:
        raise HTTPException(400, str(exc)) from exc
    uid = user["id"] if user else None
    with db() as conn:
        cur = conn.execute(
            "INSERT INTO assessments (user_id, state, grade, genre, prompt_title, text, result_json, created_at) VALUES (?,?,?,?,?,?,?,?)",
            (
                uid,
                result["state"],
                result["grade"],
                result["genre"],
                body.prompt_title,
                body.text,
                json.dumps(result),
                int(time.time()),
            ),
        )
        aid = cur.lastrowid
    result["id"] = aid
    result["saved"] = uid is not None
    if user:
        result["remaining_assessments"] = remaining_assessments(current_user_by_id(user["id"]))
    return result


@app.get("/api/assessments")
def list_assessments(request: Request):
    user = require_user(request)
    with db() as conn:
        rows = conn.execute(
            "SELECT id, state, grade, genre, prompt_title, created_at, result_json FROM assessments WHERE user_id=? ORDER BY id DESC LIMIT 50",
            (user["id"],),
        ).fetchall()
    out = []
    for row in rows:
        result = json.loads(row["result_json"])
        out.append(
            {
                "id": row["id"],
                "state": row["state"],
                "grade": row["grade"],
                "genre": row["genre"],
                "prompt_title": row["prompt_title"],
                "created_at": row["created_at"],
                "overall": result.get("overall"),
                "overall_label": result.get("overall_label"),
            }
        )
    return {"assessments": out}


@app.get("/api/assessments/{aid}")
def get_assessment(aid: int, request: Request):
    user = require_user(request)
    with db() as conn:
        row = conn.execute(
            "SELECT * FROM assessments WHERE id=? AND user_id=?", (aid, user["id"])
        ).fetchone()
    if not row:
        raise HTTPException(404, "Not found")
    result = json.loads(row["result_json"])
    result["id"] = row["id"]
    result["text"] = row["text"]
    result["prompt_title"] = row["prompt_title"]
    return result


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
