"""SQL for the inquiry tables. Standard library only: the hook uses it without pydantic or numpy."""

from __future__ import annotations

import json
import sqlite3
from typing import Any

from cgu.domain.capture import SETTING_ENABLED, SETTING_EXCLUDED

INQUIRY_COLUMNS = (
    "id, session_id, text, gist, source, project, occurred_at, captured_at,"
    " redactions, truncated, family_id, meta"
)


def get_setting(conn: sqlite3.Connection, key: str) -> str | None:
    row = conn.execute("SELECT value FROM inquiry_settings WHERE key = ?", (key,)).fetchone()
    return None if row is None else str(row[0])


def set_setting(conn: sqlite3.Connection, key: str, value: str, now: str) -> None:
    conn.execute(
        "INSERT INTO inquiry_settings (key, value, updated_at) VALUES (?, ?, ?)"
        " ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at",
        (key, value, now),
    )


def load_gate(conn: sqlite3.Connection) -> tuple[bool | None, list[str]]:
    """The recorded decision (None = never asked) and the excluded project names."""
    raw = get_setting(conn, SETTING_ENABLED)
    enabled = None if raw is None else raw == "true"
    excluded = json.loads(get_setting(conn, SETTING_EXCLUDED) or "[]")
    return enabled, [str(item) for item in excluded]


def insert_inquiry(conn: sqlite3.Connection, row: dict[str, Any]) -> None:
    conn.execute(
        f"INSERT INTO inquiries ({INQUIRY_COLUMNS}) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            row["id"],
            row.get("session_id"),
            row["text"],
            row.get("gist"),
            row["source"],
            row.get("project"),
            row["occurred_at"],
            row["captured_at"],
            json.dumps(row.get("redactions") or {}),
            int(bool(row.get("truncated"))),
            row["family_id"],
            json.dumps(row.get("meta") or {}, ensure_ascii=False),
        ),
    )


def family_index(conn: sqlite3.Connection) -> list[tuple[str, str, str]]:
    """(id, family_id, text) of every stored question, oldest first."""
    rows = conn.execute(
        "SELECT id, family_id, text FROM inquiries ORDER BY occurred_at, rowid"
    ).fetchall()
    return [(str(r[0]), str(r[1]), str(r[2])) for r in rows]
