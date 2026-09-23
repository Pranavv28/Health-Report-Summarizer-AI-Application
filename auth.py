"""
auth.py — Authentication & Memory System for Health Report Summarizer.

Provides:
  - SQLite-backed user accounts and report history (no external DB required)
  - bcrypt password hashing
  - JWT token creation / verification (HS256, 7-day expiry)
  - CRUD helpers for per-user report memory
"""

import os
import json
import sqlite3
import secrets
import datetime
from datetime import timezone
from pathlib import Path
from typing import Optional
from contextlib import contextmanager

import bcrypt
import jwt

# ─── Config ───────────────────────────────────────────────────────────────────
# DB is stored next to this file (or wherever the process cwd is)
DB_PATH = Path(__file__).parent / "users.db"

# Read JWT secret from environment; fall back to a stable file-based secret so
# tokens survive process restarts during development.
_SECRET_FILE = Path(__file__).parent / ".jwt_secret"


def _load_or_create_secret() -> str:
    env_secret = os.environ.get("JWT_SECRET")
    if env_secret:
        return env_secret
    if _SECRET_FILE.exists():
        return _SECRET_FILE.read_text().strip()
    new_secret = secrets.token_hex(32)
    _SECRET_FILE.write_text(new_secret)
    return new_secret


JWT_SECRET = _load_or_create_secret()
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_DAYS = 7
MAX_HISTORY_PER_USER = 50  # oldest entries pruned automatically


# ─── Connection Management ───────────────────────────────────────────────────

@contextmanager
def get_db():
    """Context manager providing an isolated SQLite connection with guaranteed cleanup."""
    con = sqlite3.connect(str(DB_PATH), timeout=15, check_same_thread=False)
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA busy_timeout=10000")
    try:
        yield con
    finally:
        con.close()


# ─── Database Initialisation ──────────────────────────────────────────────────

def init_db() -> None:
    """Create tables if they don't exist yet. Safe to call on every startup."""
    with get_db() as con:
        con.execute("PRAGMA foreign_keys=ON")
        con.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                name          TEXT    NOT NULL,
                email         TEXT    NOT NULL UNIQUE COLLATE NOCASE,
                password_hash TEXT    NOT NULL,
                created_at    TEXT    NOT NULL
            )
        """)
        con.execute("""
            CREATE TABLE IF NOT EXISTS report_history (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id        INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                title          TEXT    NOT NULL,
                summary_json   TEXT    NOT NULL,
                findings_count INTEGER NOT NULL DEFAULT 0,
                created_at     TEXT    NOT NULL
            )
        """)
        con.execute("""
            CREATE INDEX IF NOT EXISTS idx_history_user
                ON report_history(user_id, created_at DESC)
        """)
        con.commit()


# ─── Password Helpers ─────────────────────────────────────────────────────────

def hash_password(plain: str) -> str:
    """Return a bcrypt hash of *plain* as a UTF-8 string."""
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    """Return True if *plain* matches *hashed*."""
    try:
        return bcrypt.checkpw(plain.encode(), hashed.encode())
    except Exception:
        return False


# ─── User CRUD ────────────────────────────────────────────────────────────────

def create_user(name: str, email: str, password: str) -> dict:
    """
    Register a new user.

    Returns:
        {"ok": True, "user": {...}}  on success
        {"ok": False, "error": "..."}  on failure (e.g. duplicate email)
    """
    try:
        pw_hash = hash_password(password)
        now = datetime.datetime.now(timezone.utc).isoformat()
        with get_db() as con:
            cur = con.cursor()
            cur.execute(
                "INSERT INTO users (name, email, password_hash, created_at) VALUES (?, ?, ?, ?)",
                (name.strip(), email.strip().lower(), pw_hash, now),
            )
            user_id = cur.lastrowid
            con.commit()
            return {"ok": True, "user": {"id": user_id, "name": name.strip(), "email": email.strip().lower()}}
    except sqlite3.IntegrityError:
        return {"ok": False, "error": "An account with this email already exists."}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def authenticate_user(email: str, password: str) -> Optional[dict]:
    """
    Verify credentials.

    Returns user dict on success, None on failure.
    """
    with get_db() as con:
        con.row_factory = sqlite3.Row
        cur = con.cursor()
        cur.execute(
            "SELECT id, name, email, password_hash FROM users WHERE email = ?",
            (email.strip().lower(),),
        )
        row = cur.fetchone()

    if row is None:
        return None
    if not verify_password(password, row["password_hash"]):
        return None
    return {"id": row["id"], "name": row["name"], "email": row["email"]}


# ─── JWT Helpers ──────────────────────────────────────────────────────────────

def create_jwt(user_id: int, email: str, name: str) -> str:
    """Return a signed JWT token valid for JWT_EXPIRY_DAYS days."""
    payload = {
        "sub": str(user_id),
        "email": email,
        "name": name,
        "exp": datetime.datetime.now(timezone.utc) + datetime.timedelta(days=JWT_EXPIRY_DAYS),
        "iat": datetime.datetime.now(timezone.utc),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def verify_jwt(token: str) -> Optional[dict]:
    """
    Decode and verify a JWT token.

    Returns the payload dict on success, None if expired or invalid.
    """
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


# ─── Report History CRUD ──────────────────────────────────────────────────────

def save_report(user_id: int, title: str, summary_json: str, findings_count: int = 0) -> int:
    """
    Persist an analysis result for *user_id*.

    Automatically prunes oldest entries if the history exceeds MAX_HISTORY_PER_USER.
    Returns the new record id.
    """
    now = datetime.datetime.now(timezone.utc).isoformat()
    with get_db() as con:
        cur = con.cursor()
        cur.execute(
            "INSERT INTO report_history (user_id, title, summary_json, findings_count, created_at) VALUES (?, ?, ?, ?, ?)",
            (user_id, title, summary_json, findings_count, now),
        )
        new_id = cur.lastrowid

        # Prune oldest beyond the cap
        cur.execute(
            """DELETE FROM report_history
               WHERE user_id = ? AND id NOT IN (
                   SELECT id FROM report_history
                   WHERE user_id = ?
                   ORDER BY created_at DESC
                   LIMIT ?
               )""",
            (user_id, user_id, MAX_HISTORY_PER_USER),
        )
        con.commit()
        return new_id


def get_report_history(user_id: int) -> list[dict]:
    """
    Return a list of report history records for *user_id*, newest first.

    Each record: {id, title, findings_count, created_at, summary_json}
    """
    with get_db() as con:
        con.row_factory = sqlite3.Row
        cur = con.cursor()
        cur.execute(
            """SELECT id, title, findings_count, created_at, summary_json
               FROM report_history
               WHERE user_id = ?
               ORDER BY created_at DESC""",
            (user_id,),
        )
        rows = [dict(r) for r in cur.fetchall()]
        return rows


def delete_report(report_id: int, user_id: int) -> bool:
    """
    Delete a report by *report_id*, scoped to *user_id* for safety.

    Returns True if a row was deleted, False otherwise.
    """
    with get_db() as con:
        cur = con.cursor()
        cur.execute(
            "DELETE FROM report_history WHERE id = ? AND user_id = ?",
            (report_id, user_id),
        )
        deleted = cur.rowcount > 0
        con.commit()
        return deleted


def get_report_by_id(report_id: int, user_id: int) -> Optional[dict]:
    """Fetch a single report record (including full summary_json) for the owner."""
    with get_db() as con:
        con.row_factory = sqlite3.Row
        cur = con.cursor()
        cur.execute(
            "SELECT id, title, findings_count, created_at, summary_json FROM report_history WHERE id = ? AND user_id = ?",
            (report_id, user_id),
        )
        row = cur.fetchone()
        return dict(row) if row else None
