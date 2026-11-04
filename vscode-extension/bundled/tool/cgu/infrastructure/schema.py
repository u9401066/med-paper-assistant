"""Database schema and migrations. Standard library only, so the hook can use it cheaply."""

from __future__ import annotations

import sqlite3

SCHEMA_V1 = """
CREATE TABLE sessions (
    id TEXT PRIMARY KEY,
    topic TEXT NOT NULL,
    domain TEXT,
    language TEXT NOT NULL,
    seed INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    meta TEXT NOT NULL DEFAULT '{}'
);
CREATE TABLE frames (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    parent_id TEXT REFERENCES frames(id) ON DELETE CASCADE,
    operator TEXT,
    json TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE ideas (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    kind TEXT NOT NULL,
    json TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE fragments (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    source_type TEXT NOT NULL,
    json TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE matchups (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    json TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE verdicts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    matchup_id TEXT NOT NULL,
    ord TEXT NOT NULL,
    judge TEXT NOT NULL,
    json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE (session_id, matchup_id, ord, judge)
);
CREATE TABLE niches (
    session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    niche TEXT NOT NULL,
    json TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (session_id, niche)
);
CREATE TABLE questions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    passed INTEGER NOT NULL,
    json TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    idea_id TEXT NOT NULL,
    decision TEXT NOT NULL,
    json TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX idx_frames_session ON frames(session_id);
CREATE INDEX idx_ideas_session ON ideas(session_id, kind);
CREATE INDEX idx_fragments_session ON fragments(session_id);
CREATE INDEX idx_matchups_session ON matchups(session_id);
CREATE INDEX idx_verdicts_session ON verdicts(session_id);
CREATE INDEX idx_feedback_session ON feedback(session_id);
"""

SCHEMA_V2 = """
CREATE TABLE inquiry_settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE inquiries (
    id TEXT PRIMARY KEY,
    session_id TEXT REFERENCES sessions(id) ON DELETE CASCADE,
    text TEXT NOT NULL,
    gist TEXT,
    source TEXT NOT NULL,
    project TEXT,
    occurred_at TEXT NOT NULL,
    captured_at TEXT NOT NULL,
    redactions TEXT NOT NULL DEFAULT '{}',
    truncated INTEGER NOT NULL DEFAULT 0,
    family_id TEXT NOT NULL,
    meta TEXT NOT NULL DEFAULT '{}'
);
CREATE TABLE inquiry_vectors (
    inquiry_id TEXT NOT NULL REFERENCES inquiries(id) ON DELETE CASCADE,
    backend TEXT NOT NULL,
    dim INTEGER NOT NULL,
    vec BLOB NOT NULL,
    PRIMARY KEY (inquiry_id, backend)
);
CREATE TABLE inquiry_themes (
    id TEXT PRIMARY KEY,
    label TEXT,
    labeled_by TEXT,
    member_ids TEXT NOT NULL,
    backend TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE inquiry_sources (
    id TEXT PRIMARY KEY,
    kind TEXT NOT NULL,
    json TEXT NOT NULL,
    first_surfaced_at TEXT NOT NULL,
    last_surfaced_at TEXT NOT NULL,
    times_surfaced INTEGER NOT NULL DEFAULT 1
);
CREATE INDEX idx_inquiries_family ON inquiries(family_id);
CREATE INDEX idx_inquiries_occurred ON inquiries(occurred_at);
CREATE INDEX idx_inquiries_project ON inquiries(project);
CREATE INDEX idx_inquiries_session ON inquiries(session_id);
"""

SCHEMA_V3 = """
CREATE TABLE inquiry_reviews (
    inquiry_id TEXT PRIMARY KEY REFERENCES inquiries(id) ON DELETE CASCADE,
    text_sha256 TEXT NOT NULL,
    reviewed_at TEXT NOT NULL
);
CREATE TABLE inquiry_materials (
    id TEXT PRIMARY KEY,
    json TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE inquiry_material_links (
    material_id TEXT NOT NULL REFERENCES inquiry_materials(id) ON DELETE CASCADE,
    inquiry_id TEXT NOT NULL REFERENCES inquiries(id) ON DELETE CASCADE,
    PRIMARY KEY (material_id, inquiry_id)
);
CREATE INDEX idx_material_links_inquiry ON inquiry_material_links(inquiry_id);
CREATE TRIGGER delete_inquiry_materials BEFORE DELETE ON inquiries
BEGIN
    DELETE FROM inquiry_materials WHERE id IN (
        SELECT material_id FROM inquiry_material_links WHERE inquiry_id = OLD.id
    );
END;
"""

MIGRATIONS: tuple[str, ...] = (SCHEMA_V1, SCHEMA_V2, SCHEMA_V3)
INQUIRY_TABLES = (
    "inquiry_settings",
    "inquiries",
    "inquiry_vectors",
    "inquiry_themes",
    "inquiry_sources",
    "inquiry_reviews",
    "inquiry_materials",
    "inquiry_material_links",
)


def migrate(conn: sqlite3.Connection) -> int:
    version = int(conn.execute("PRAGMA user_version").fetchone()[0])
    if version > len(MIGRATIONS):
        raise RuntimeError(
            f"database schema v{version} is newer than this CGU (v{len(MIGRATIONS)})"
        )
    for number, script in enumerate(MIGRATIONS[version:], start=version + 1):
        try:
            conn.executescript(
                f"BEGIN IMMEDIATE;\n{script}\nPRAGMA user_version = {number};\nCOMMIT;"
            )
        except sqlite3.OperationalError:
            if conn.in_transaction:
                conn.rollback()
            if int(conn.execute("PRAGMA user_version").fetchone()[0]) < number:
                raise
    return len(MIGRATIONS)
