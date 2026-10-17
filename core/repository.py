from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from core.schemas import Extraction


def now() -> str:
    return datetime.now(UTC).isoformat()


class Repository:
    def __init__(self, path: Path):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY, identifier TEXT UNIQUE NOT NULL, created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS conversations (
                    id TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id),
                    name TEXT NOT NULL DEFAULT 'New conversation', created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL, metadata TEXT NOT NULL DEFAULT '{}'
                );
                CREATE TABLE IF NOT EXISTS preferences (
                    user_id TEXT NOT NULL REFERENCES users(id), dimension TEXT NOT NULL,
                    subject TEXT NOT NULL, value TEXT NOT NULL, evidence TEXT NOT NULL,
                    updated_at TEXT NOT NULL, PRIMARY KEY(user_id, dimension, subject)
                );
                CREATE TABLE IF NOT EXISTS preference_events (
                    id INTEGER PRIMARY KEY, user_id TEXT NOT NULL, thread_id TEXT NOT NULL,
                    message_id TEXT NOT NULL, dimension TEXT NOT NULL, subject TEXT NOT NULL,
                    old_value TEXT, new_value TEXT, evidence TEXT NOT NULL, created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS preference_batches (
                    user_id TEXT NOT NULL, thread_id TEXT NOT NULL, message_id TEXT NOT NULL,
                    created_at TEXT NOT NULL, PRIMARY KEY(user_id, thread_id, message_id)
                );
                CREATE INDEX IF NOT EXISTS conversations_user ON conversations(user_id, updated_at);
                CREATE INDEX IF NOT EXISTS events_user ON preference_events(user_id, id);
            """)

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=30)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        db.execute("PRAGMA journal_mode=WAL")
        try:
            with db:
                yield db
        finally:
            db.close()

    def user(self, identifier: str) -> dict:
        # Only call with the verified authentication identifier.
        uid = str(uuid5(NAMESPACE_URL, f"restaurant-menu-assistant:user:{identifier}"))
        with self.connect() as db:
            db.execute("INSERT OR IGNORE INTO users VALUES (?,?,?)", (uid, identifier, now()))
            return dict(
                db.execute("SELECT * FROM users WHERE identifier=?", (identifier,)).fetchone()
            )

    def get_user(self, identifier: str) -> dict | None:
        with self.connect() as db:
            row = db.execute("SELECT * FROM users WHERE identifier=?", (identifier,)).fetchone()
            return dict(row) if row else None

    def create_conversation(self, thread_id: str, user_id: str):
        with self.connect() as db:
            db.execute(
                "INSERT OR IGNORE INTO conversations(id,user_id,created_at,updated_at) "
                "VALUES (?,?,?,?)",
                (thread_id, user_id, now(), now()),
            )
        self.owned(thread_id, user_id)

    def owned(self, thread_id: str, user_id: str) -> dict:
        with self.connect() as db:
            row = db.execute(
                "SELECT * FROM conversations WHERE id=? AND user_id=?", (thread_id, user_id)
            ).fetchone()
            if row is None:
                raise PermissionError("Conversation not found for this user")
            return dict(row)

    def profile(self, user_id: str) -> list[dict]:
        with self.connect() as db:
            return [
                dict(r)
                for r in db.execute(
                    "SELECT * FROM preferences WHERE user_id=? ORDER BY dimension,subject",
                    (user_id,),
                )
            ]

    def apply(
        self, user_id: str, thread_id: str, message_id: str, message: str, extraction: Extraction
    ):
        self.owned(thread_id, user_id)
        for change in extraction.changes:
            if change.evidence not in message:
                raise ValueError(
                    "Preference evidence must be an exact quote from the latest user message"
                )
        if extraction.forget_all and (
            not extraction.forget_evidence or extraction.forget_evidence not in message
        ):
            raise ValueError("Forgetting requires evidence in the latest message")
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            inserted = db.execute(
                "INSERT OR IGNORE INTO preference_batches VALUES (?,?,?,?)",
                (user_id, thread_id, message_id, now()),
            ).rowcount
            if not inserted:
                return
            changes = [
                (
                    c.dimension.value,
                    c.subject,
                    c.value if c.operation == "set" else None,
                    c.evidence,
                )
                for c in extraction.changes
            ]
            if extraction.forget_all:
                changes = [
                    (r["dimension"], r["subject"], None, extraction.forget_evidence)
                    for r in db.execute("SELECT * FROM preferences WHERE user_id=?", (user_id,))
                ]
            for dim, subject, value, evidence in changes:
                key = (user_id, dim, subject)
                row = db.execute(
                    "SELECT value FROM preferences WHERE user_id=? AND dimension=? AND subject=?",
                    key,
                ).fetchone()
                old = row["value"] if row else None
                if old == value:
                    continue
                stamp = now()
                db.execute(
                    "INSERT INTO preference_events(user_id,thread_id,message_id,dimension,"
                    "subject,old_value,new_value,evidence,created_at) VALUES(?,?,?,?,?,?,?,?,?)",
                    (user_id, thread_id, message_id, dim, subject, old, value, evidence, stamp),
                )
                if value is None:
                    db.execute(
                        "DELETE FROM preferences WHERE user_id=? AND dimension=? AND subject=?", key
                    )
                else:
                    db.execute(
                        "INSERT INTO preferences VALUES(?,?,?,?,?,?) ON CONFLICT(user_id,"
                        "dimension,subject) DO UPDATE SET value=excluded.value, "
                        "evidence=excluded.evidence,updated_at=excluded.updated_at",
                        (*key, value, evidence, stamp),
                    )

    def events(self, user_id: str) -> list[dict]:
        with self.connect() as db:
            return [
                dict(r)
                for r in db.execute(
                    "SELECT * FROM preference_events WHERE user_id=? ORDER BY id", (user_id,)
                )
            ]

    def list_conversations(self, user_id: str) -> list[dict]:
        with self.connect() as db:
            return [
                dict(r)
                for r in db.execute(
                    "SELECT * FROM conversations WHERE user_id=? ORDER BY updated_at DESC",
                    (user_id,),
                )
            ]

    def update_conversation(self, thread_id: str, user_id: str, name=None, metadata=None):
        self.owned(thread_id, user_id)
        with self.connect() as db:
            db.execute(
                "UPDATE conversations SET name=COALESCE(?,name),metadata=COALESCE(?,metadata),"
                "updated_at=? WHERE id=? AND user_id=?",
                (
                    name,
                    json.dumps(metadata) if metadata is not None else None,
                    now(),
                    thread_id,
                    user_id,
                ),
            )

    def delete_conversation(self, thread_id: str, user_id: str):
        self.owned(thread_id, user_id)
        with self.connect() as db:
            db.execute("DELETE FROM conversations WHERE id=? AND user_id=?", (thread_id, user_id))
