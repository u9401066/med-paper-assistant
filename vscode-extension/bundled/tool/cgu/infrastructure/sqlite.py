"""SQLite archive: WAL, user_version migrations, one locked connection used off the event loop."""

from __future__ import annotations

import asyncio
import contextlib
import functools
import json
import sqlite3
import threading
from collections.abc import Callable, Coroutine, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Concatenate, ParamSpec, TypeVar

import numpy as np

from cgu.domain.capture import DEFAULT_THEME_MIN_SIZE, SETTING_THEMES_MIN_SIZE
from cgu.domain.common import CGUError, Session
from cgu.domain.frame import Frame
from cgu.domain.idea import Fragment, Idea
from cgu.domain.inquiry import Inquiry, SourceRecord, ThemeRecord
from cgu.domain.inquiry_material import InquiryMaterial, InquiryReview, text_sha256
from cgu.domain.judge import Matchup, Verdict
from cgu.infrastructure import inquiry_sql
from cgu.infrastructure.schema import MIGRATIONS as MIGRATIONS
from cgu.infrastructure.schema import migrate

TABLES = (
    "frames",
    "ideas",
    "fragments",
    "matchups",
    "verdicts",
    "niches",
    "questions",
    "feedback",
)

P = ParamSpec("P")
R = TypeVar("R")


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def threaded(
    fn: Callable[Concatenate[SQLiteArchive, P], R],
) -> Callable[Concatenate[SQLiteArchive, P], Coroutine[Any, Any, R]]:
    """Run a synchronous archive method on a worker thread under the connection lock."""

    @functools.wraps(fn)
    async def wrapper(self: SQLiteArchive, *args: P.args, **kwargs: P.kwargs) -> R:
        return await asyncio.to_thread(lambda: self._locked(fn, *args, **kwargs))

    return wrapper  # type: ignore[return-value]


class SQLiteArchive:
    def __init__(self, path: Path | str) -> None:
        if str(path) != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(str(path), check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._conn.execute("PRAGMA secure_delete=ON")
        self._conn.execute("PRAGMA busy_timeout=5000")
        self.schema_version = migrate(self._conn)

    def _locked(self, fn: Callable[..., R], *args: Any, **kwargs: Any) -> R:
        with self._lock:
            return fn(self, *args, **kwargs)

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    @threaded
    def inquiry_maintenance_counts(self, project: str | None = None) -> dict[str, int]:
        scope = " AND i.project = ?" if project is not None else ""
        args = (project,) if project is not None else ()
        pending = self._conn.execute(
            "SELECT COUNT(*) FROM inquiries i LEFT JOIN inquiry_reviews r ON r.inquiry_id = i.id"
            " WHERE r.inquiry_id IS NULL" + scope,
            args,
        ).fetchone()[0]
        material_scope = (
            " WHERE EXISTS (SELECT 1 FROM inquiry_material_links l JOIN inquiries i"
            " ON i.id = l.inquiry_id WHERE l.material_id = m.id AND i.project = ?)"
            if project is not None
            else ""
        )
        materials = self._conn.execute(
            "SELECT COUNT(*) FROM inquiry_materials m" + material_scope,
            args,
        ).fetchone()[0]
        return {"pending": int(pending), "materials": int(materials)}

    @threaded
    def pending_inquiries(self, limit: int, project: str | None = None) -> list[Inquiry]:
        scope = " AND project = ?" if project is not None else ""
        args = (*((project,) if project is not None else ()), limit)
        rows = self._all(
            f"SELECT {inquiry_sql.INQUIRY_COLUMNS} FROM inquiries"
            " WHERE id NOT IN (SELECT inquiry_id FROM inquiry_reviews)"
            + scope
            + " ORDER BY captured_at, rowid LIMIT ?",
            args,
        )
        return [self._inquiry(row) for row in rows]

    @threaded
    def save_inquiry_materials(
        self, materials: Sequence[InquiryMaterial], reviewed: Sequence[InquiryReview], now: str
    ) -> None:
        # Validate inside the same write transaction: a hook or another client may delete evidence.
        with self._conn:
            self._conn.execute("BEGIN IMMEDIATE")
            for ref in reviewed:
                row = self._conn.execute(
                    "SELECT text FROM inquiries WHERE id = ?", (ref.inquiry_id,)
                ).fetchone()
                if row is None or text_sha256(str(row[0])) != ref.text_sha256:
                    raise CGUError(
                        "invalid_input", f"missing or stale inquiry evidence: {ref.inquiry_id}"
                    )
            allowed = {r.inquiry_id: r.text_sha256 for r in reviewed}
            for material in materials:
                if not material.evidence or any(
                    allowed.get(e.inquiry_id) != e.text_sha256 for e in material.evidence
                ):
                    raise CGUError(
                        "invalid_input", "material evidence must belong to the reviewed batch"
                    )
                self._conn.execute(
                    "INSERT INTO inquiry_materials (id, json, created_at) VALUES (?, ?, ?)"
                    " ON CONFLICT(id) DO NOTHING",
                    (material.id, material.model_dump_json(), material.created_at),
                )
                self._conn.executemany(
                    "INSERT OR IGNORE INTO inquiry_material_links (material_id, inquiry_id) VALUES (?, ?)",
                    [(material.id, e.inquiry_id) for e in material.evidence],
                )
            self._conn.executemany(
                "INSERT INTO inquiry_reviews (inquiry_id, text_sha256, reviewed_at) VALUES (?, ?, ?)"
                " ON CONFLICT(inquiry_id) DO UPDATE SET text_sha256=excluded.text_sha256, reviewed_at=excluded.reviewed_at",
                [(r.inquiry_id, r.text_sha256, now) for r in reviewed],
            )

    @threaded
    def list_inquiry_materials(
        self,
        project: str | None = None,
        query: str | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[InquiryMaterial]:
        clauses: list[str] = []
        args: list[Any] = []
        if project is not None:
            clauses.append(
                "EXISTS (SELECT 1 FROM inquiry_material_links l JOIN inquiries i ON i.id=l.inquiry_id"
                " WHERE l.material_id=m.id AND i.project=?)"
            )
            args.append(project)
        if query:
            clauses.append("instr(lower(json_extract(m.json, '$.text')), lower(?)) > 0")
            args.append(query)
        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        rows = self._all(
            "SELECT m.json FROM inquiry_materials m"
            + where
            + " ORDER BY m.created_at DESC, m.rowid DESC LIMIT ? OFFSET ?",
            [*args, -1 if limit is None else limit, offset],
        )
        return [InquiryMaterial.model_validate_json(row[0]) for row in rows]

    def _all(self, sql: str, params: Sequence[Any] = ()) -> list[sqlite3.Row | tuple[Any, ...]]:
        return list(self._conn.execute(sql, params).fetchall())

    @threaded
    def create_session(self, session: Session) -> None:
        with self._conn:
            self._conn.execute(
                "INSERT INTO sessions (id, topic, domain, language, seed, created_at, meta)"
                " VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    session.id,
                    session.topic,
                    session.domain,
                    session.language,
                    session.seed,
                    session.created_at,
                    json.dumps(session.meta),
                ),
            )

    @staticmethod
    def _session(row: Sequence[Any]) -> Session:
        return Session(
            id=row[0],
            topic=row[1],
            domain=row[2],
            language=row[3],
            seed=row[4],
            created_at=row[5],
            meta=json.loads(row[6]),
        )

    @threaded
    def get_session(self, session_id: str) -> Session | None:
        rows = self._all(
            "SELECT id, topic, domain, language, seed, created_at, meta FROM sessions WHERE id = ?",
            (session_id,),
        )
        return self._session(rows[0]) if rows else None

    @threaded
    def list_sessions(self) -> list[Session]:
        rows = self._all(
            "SELECT id, topic, domain, language, seed, created_at, meta FROM sessions"
            " ORDER BY created_at DESC, rowid DESC"
        )
        return [self._session(row) for row in rows]

    @threaded
    def delete_session(self, session_id: str) -> bool:
        with self._conn:
            cursor = self._conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
            if cursor.rowcount > 0:
                self._prune_inquiry_state()
        return cursor.rowcount > 0

    @threaded
    def counts(self, session_id: str) -> dict[str, int]:
        return {
            table: int(
                self._conn.execute(
                    f"SELECT COUNT(*) FROM {table} WHERE session_id = ?", (session_id,)
                ).fetchone()[0]
            )
            for table in TABLES
        }

    @threaded
    def bump_counter(self, session_id: str, name: str) -> int:
        with self._conn:
            row = self._conn.execute(
                "SELECT meta FROM sessions WHERE id = ?", (session_id,)
            ).fetchone()
            meta = json.loads(row[0])
            meta[name] = int(meta.get(name, 0)) + 1
            self._conn.execute(
                "UPDATE sessions SET meta = ? WHERE id = ?", (json.dumps(meta), session_id)
            )
        return int(meta[name])

    @threaded
    def save_frame(self, frame: Frame) -> None:
        with self._conn:
            self._conn.execute(
                "INSERT INTO frames (id, session_id, parent_id, operator, json, created_at)"
                " VALUES (?, ?, ?, ?, ?, ?)",
                (
                    frame.frame_id,
                    frame.session_id,
                    frame.parent_id,
                    frame.operator,
                    frame.model_dump_json(),
                    frame.created_at or _now(),
                ),
            )

    @threaded
    def get_frame(self, frame_id: str) -> Frame | None:
        rows = self._all("SELECT json FROM frames WHERE id = ?", (frame_id,))
        return Frame.model_validate_json(rows[0][0]) if rows else None

    @threaded
    def list_frames(self, session_id: str) -> list[Frame]:
        rows = self._all(
            "SELECT json FROM frames WHERE session_id = ? ORDER BY rowid", (session_id,)
        )
        return [Frame.model_validate_json(row[0]) for row in rows]

    @threaded
    def save_ideas(self, ideas: Sequence[Idea]) -> None:
        with self._conn:
            self._conn.executemany(
                "INSERT INTO ideas (id, session_id, kind, json, created_at) VALUES (?, ?, ?, ?, ?)",
                [
                    (i.id, i.session_id, i.kind, i.model_dump_json(), i.created_at or _now())
                    for i in ideas
                ],
            )

    @threaded
    def update_idea(self, idea: Idea) -> None:
        with self._conn:
            self._conn.execute(
                "UPDATE ideas SET kind = ?, json = ? WHERE id = ?",
                (idea.kind, idea.model_dump_json(), idea.id),
            )

    @threaded
    def list_ideas(self, session_id: str, kind: str | None = None) -> list[Idea]:
        if kind is None:
            rows = self._all(
                "SELECT json FROM ideas WHERE session_id = ? ORDER BY rowid", (session_id,)
            )
        else:
            rows = self._all(
                "SELECT json FROM ideas WHERE session_id = ? AND kind = ? ORDER BY rowid",
                (session_id, kind),
            )
        return [Idea.model_validate_json(row[0]) for row in rows]

    @threaded
    def save_fragments(self, fragments: Sequence[Fragment]) -> None:
        with self._conn:
            self._conn.executemany(
                "INSERT INTO fragments (id, session_id, source_type, json, created_at)"
                " VALUES (?, ?, ?, ?, ?)",
                [
                    (f.id, f.session_id, f.source_type, f.model_dump_json(), f.created_at or _now())
                    for f in fragments
                ],
            )

    @threaded
    def list_fragments(self, session_id: str) -> list[Fragment]:
        rows = self._all(
            "SELECT json FROM fragments WHERE session_id = ? ORDER BY rowid", (session_id,)
        )
        return [Fragment.model_validate_json(row[0]) for row in rows]

    @threaded
    def save_matchups(self, matchups: Sequence[Matchup]) -> None:
        with self._conn:
            self._conn.executemany(
                "INSERT INTO matchups (id, session_id, json, created_at) VALUES (?, ?, ?, ?)",
                [
                    (m.id, m.session_id, m.model_dump_json(), m.created_at or _now())
                    for m in matchups
                ],
            )

    @threaded
    def list_matchups(self, session_id: str) -> list[Matchup]:
        rows = self._all(
            "SELECT json FROM matchups WHERE session_id = ? ORDER BY rowid", (session_id,)
        )
        return [Matchup.model_validate_json(row[0]) for row in rows]

    @threaded
    def save_verdicts(self, session_id: str, verdicts: Sequence[Verdict]) -> None:
        with self._conn:
            self._conn.executemany(
                "INSERT INTO verdicts (session_id, matchup_id, ord, judge, json, created_at)"
                " VALUES (?, ?, ?, ?, ?, ?)",
                [
                    (
                        session_id,
                        v.matchup_id,
                        v.order,
                        v.judge_model or "unknown",
                        v.model_dump_json(),
                        _now(),
                    )
                    for v in verdicts
                ],
            )

    @threaded
    def list_verdicts(self, session_id: str) -> list[Verdict]:
        rows = self._all(
            "SELECT json FROM verdicts WHERE session_id = ? ORDER BY id", (session_id,)
        )
        return [Verdict.model_validate_json(row[0]) for row in rows]

    @threaded
    def get_niches(self, session_id: str) -> dict[str, dict[str, Any]]:
        rows = self._all(
            "SELECT niche, json FROM niches WHERE session_id = ? ORDER BY niche", (session_id,)
        )
        return {row[0]: json.loads(row[1]) for row in rows}

    @threaded
    def put_niche(self, session_id: str, niche: str, state: dict[str, Any]) -> None:
        with self._conn:
            self._conn.execute(
                "INSERT INTO niches (session_id, niche, json, updated_at) VALUES (?, ?, ?, ?)"
                " ON CONFLICT(session_id, niche) DO UPDATE SET"
                " json = excluded.json, updated_at = excluded.updated_at",
                (session_id, niche, json.dumps(state), _now()),
            )

    @threaded
    def save_question(self, session_id: str, record: dict[str, Any]) -> None:
        with self._conn:
            self._conn.execute(
                "INSERT INTO questions (session_id, passed, json, created_at) VALUES (?, ?, ?, ?)",
                (session_id, int(bool(record.get("passed"))), json.dumps(record), _now()),
            )

    @threaded
    def list_questions(self, session_id: str) -> list[dict[str, Any]]:
        rows = self._all(
            "SELECT json FROM questions WHERE session_id = ? ORDER BY id", (session_id,)
        )
        return [json.loads(row[0]) for row in rows]

    @threaded
    def save_feedback(self, session_id: str, record: dict[str, Any]) -> None:
        with self._conn:
            self._conn.execute(
                "INSERT INTO feedback (session_id, idea_id, decision, json, created_at)"
                " VALUES (?, ?, ?, ?, ?)",
                (session_id, record["idea_id"], record["decision"], json.dumps(record), _now()),
            )

    @threaded
    def list_feedback(self, session_id: str) -> list[dict[str, Any]]:
        rows = self._all(
            "SELECT json FROM feedback WHERE session_id = ? ORDER BY id", (session_id,)
        )
        return [json.loads(row[0]) for row in rows]

    @threaded
    def delete_feedback(self, session_id: str) -> int:
        with self._conn:
            cursor = self._conn.execute("DELETE FROM feedback WHERE session_id = ?", (session_id,))
        return int(cursor.rowcount)

    @threaded
    def export_session(self, session_id: str) -> dict[str, Any]:
        session = self._session(
            self._conn.execute(
                "SELECT id, topic, domain, language, seed, created_at, meta FROM sessions"
                " WHERE id = ?",
                (session_id,),
            ).fetchone()
        )

        def rows(table: str, order: str = "rowid") -> list[Any]:
            sql = f"SELECT json FROM {table} WHERE session_id = ? ORDER BY {order}"
            return [json.loads(row[0]) for row in self._conn.execute(sql, (session_id,))]

        niches = {
            row[0]: json.loads(row[1])
            for row in self._conn.execute(
                "SELECT niche, json FROM niches WHERE session_id = ? ORDER BY niche", (session_id,)
            )
        }
        linked = [
            self._inquiry(row).model_dump()
            for row in self._conn.execute(
                f"SELECT {inquiry_sql.INQUIRY_COLUMNS} FROM inquiries WHERE session_id = ?"
                " ORDER BY occurred_at, rowid",
                (session_id,),
            )
        ]
        return {
            "session": session.model_dump(mode="json"),
            "frames": rows("frames"),
            "ideas": rows("ideas"),
            "fragments": rows("fragments"),
            "matchups": rows("matchups"),
            "verdicts": rows("verdicts", "id"),
            "niches": niches,
            "questions": rows("questions", "id"),
            "feedback": rows("feedback", "id"),
            "inquiries": linked,
        }

    # --- inquiry memory: cross-session, opt-in -------------------------------------------------

    @staticmethod
    def _inquiry(row: Sequence[Any]) -> Inquiry:
        return Inquiry(
            id=row[0],
            session_id=row[1],
            text=row[2],
            gist=row[3],
            source=row[4],
            project=row[5],
            occurred_at=row[6],
            captured_at=row[7],
            redactions=json.loads(row[8]),
            truncated=bool(row[9]),
            family_id=row[10],
            meta=json.loads(row[11]),
        )

    @staticmethod
    def _inquiry_filter(
        project: str | None, since: str | None, ids: Sequence[str] | None
    ) -> tuple[str, list[Any]]:
        clauses: list[str] = []
        params: list[Any] = []
        if project is not None:
            clauses.append("project = ?")
            params.append(project)
        if since is not None:
            clauses.append("occurred_at >= ?")
            params.append(since)
        if ids is not None:
            clauses.append(f"id IN ({','.join('?' * len(ids))})" if ids else "0")
            params.extend(ids)
        return (" WHERE " + " AND ".join(clauses)) if clauses else "", params

    @threaded
    def get_inquiry_settings(self) -> dict[str, str]:
        rows = self._all("SELECT key, value FROM inquiry_settings")
        return {str(row[0]): str(row[1]) for row in rows}

    @threaded
    def set_inquiry_settings(self, values: dict[str, str]) -> None:
        now = _now()
        with self._conn:
            for key, value in values.items():
                inquiry_sql.set_setting(self._conn, key, value, now)

    @threaded
    def insert_inquiries(self, inquiries: Sequence[Inquiry]) -> None:
        with self._conn:
            for inquiry in inquiries:
                inquiry_sql.insert_inquiry(self._conn, inquiry.model_dump())

    @threaded
    def inquiry_family_rows(self) -> list[tuple[str, str, str, str]]:
        rows = self._all(
            "SELECT id, family_id, text, occurred_at FROM inquiries ORDER BY occurred_at, rowid"
        )
        return [(str(r[0]), str(r[1]), str(r[2]), str(r[3])) for r in rows]

    @threaded
    def list_inquiries(
        self,
        *,
        project: str | None = None,
        since: str | None = None,
        ids: Sequence[str] | None = None,
        newest_first: bool = False,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[Inquiry]:
        where, params = self._inquiry_filter(project, since, ids)
        direction = "DESC" if newest_first else "ASC"
        sql = (
            f"SELECT {inquiry_sql.INQUIRY_COLUMNS} FROM inquiries{where}"
            f" ORDER BY occurred_at {direction}, rowid {direction}"
        )
        if limit is not None:
            sql += " LIMIT ? OFFSET ?"
            params = [*params, limit, offset]
        return [self._inquiry(row) for row in self._all(sql, params)]

    @threaded
    def count_inquiries(
        self,
        *,
        project: str | None = None,
        since: str | None = None,
        ids: Sequence[str] | None = None,
    ) -> int:
        where, params = self._inquiry_filter(project, since, ids)
        return int(
            self._conn.execute(f"SELECT COUNT(*) FROM inquiries{where}", params).fetchone()[0]
        )

    def _prune_inquiry_state(self) -> tuple[int, int]:
        """Drop deleted questions from themes and drop themes and sources that lose their basis."""
        family = {
            str(r[0]): str(r[1]) for r in self._conn.execute("SELECT id, family_id FROM inquiries")
        }
        min_size = int(
            inquiry_sql.get_setting(self._conn, SETTING_THEMES_MIN_SIZE) or DEFAULT_THEME_MIN_SIZE
        )
        themes_removed = 0
        for theme_id, raw in self._conn.execute(
            "SELECT id, member_ids FROM inquiry_themes"
        ).fetchall():
            members = json.loads(raw)
            kept = [m for m in members if m in family]
            if len({family[m] for m in kept}) < min_size:
                self._conn.execute("DELETE FROM inquiry_themes WHERE id = ?", (theme_id,))
                themes_removed += 1
            elif len(kept) != len(members):
                self._conn.execute(
                    "UPDATE inquiry_themes SET member_ids = ? WHERE id = ?",
                    (json.dumps(kept), theme_id),
                )
        sources_removed = 0
        for source_id, raw in self._conn.execute("SELECT id, json FROM inquiry_sources").fetchall():
            evidence = json.loads(raw).get("evidence_ids", [])
            if any(e not in family for e in evidence):
                self._conn.execute("DELETE FROM inquiry_sources WHERE id = ?", (source_id,))
                sources_removed += 1
        return themes_removed, sources_removed

    @threaded
    def delete_inquiries(
        self,
        *,
        ids: Sequence[str] | None = None,
        project: str | None = None,
        before: str | None = None,
        everything: bool = False,
    ) -> tuple[int, int, int]:
        where = ""
        params: list[Any] = []
        if not everything:
            clauses: list[str] = []
            if ids is not None:
                clauses.append(f"id IN ({','.join('?' * len(ids))})" if ids else "0")
                params.extend(ids)
            if project is not None:
                clauses.append("project = ?")
                params.append(project)
            if before is not None:
                clauses.append("occurred_at < ?")
                params.append(before)
            if not clauses:
                return 0, 0, 0
            where = " WHERE " + " AND ".join(clauses)
        with self._conn:
            cursor = self._conn.execute(f"DELETE FROM inquiries{where}", params)
            themes, sources = self._prune_inquiry_state()
        with contextlib.suppress(sqlite3.Error):
            self._conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        return int(cursor.rowcount), themes, sources

    @threaded
    def save_inquiry_vectors(self, backend: str, items: Sequence[tuple[str, np.ndarray]]) -> None:
        with self._conn:
            self._conn.executemany(
                "INSERT OR REPLACE INTO inquiry_vectors (inquiry_id, backend, dim, vec)"
                " SELECT ?, ?, ?, ? WHERE EXISTS (SELECT 1 FROM inquiries WHERE id = ?)",
                [
                    (
                        inquiry_id,
                        backend,
                        int(vector.shape[0]),
                        np.asarray(vector, dtype=np.float32).tobytes(),
                        inquiry_id,
                    )
                    for inquiry_id, vector in items
                ],
            )

    @threaded
    def load_inquiry_vectors(
        self, backend: str, ids: Sequence[str]
    ) -> tuple[list[str], np.ndarray]:
        found: list[tuple[str, int, bytes]] = []
        for start in range(0, len(ids), 500):
            chunk = list(ids[start : start + 500])
            marks = ",".join("?" * len(chunk))
            rows = self._conn.execute(
                "SELECT inquiry_id, dim, vec FROM inquiry_vectors"
                f" WHERE backend = ? AND inquiry_id IN ({marks})",
                [backend, *chunk],
            ).fetchall()
            found.extend((str(r[0]), int(r[1]), bytes(r[2])) for r in rows)
        if not found:
            return [], np.zeros((0, 0), dtype=np.float32)
        dims: dict[int, int] = {}
        for _id, dim, _blob in found:
            dims[dim] = dims.get(dim, 0) + 1
        dim = max(dims, key=lambda d: dims[d])
        kept = [(i, blob) for i, d, blob in found if d == dim]
        matrix = np.stack([np.frombuffer(blob, dtype=np.float32, count=dim) for _i, blob in kept])
        return [i for i, _blob in kept], matrix

    @threaded
    def list_themes(self) -> list[ThemeRecord]:
        rows = self._all(
            "SELECT id, label, labeled_by, member_ids, backend, updated_at FROM inquiry_themes"
            " ORDER BY rowid"
        )
        return [
            ThemeRecord(
                id=r[0],
                label=r[1],
                labeled_by=r[2],
                member_ids=json.loads(r[3]),
                backend=r[4],
                updated_at=r[5],
            )
            for r in rows
        ]

    @threaded
    def replace_themes(self, themes: Sequence[ThemeRecord], min_size: int) -> None:
        now = _now()
        with self._conn:
            self._conn.execute("DELETE FROM inquiry_themes")
            self._conn.executemany(
                "INSERT INTO inquiry_themes (id, label, labeled_by, member_ids, backend, updated_at)"
                " VALUES (?, ?, ?, ?, ?, ?)",
                [
                    (t.id, t.label, t.labeled_by, json.dumps(t.member_ids), t.backend, now)
                    for t in themes
                ],
            )
            inquiry_sql.set_setting(self._conn, SETTING_THEMES_MIN_SIZE, str(min_size), now)

    @threaded
    def label_themes(self, labels: dict[str, str], by: str) -> list[str]:
        updated: list[str] = []
        now = _now()
        with self._conn:
            for theme_id, label in labels.items():
                cursor = self._conn.execute(
                    "UPDATE inquiry_themes SET label = ?, labeled_by = ?, updated_at = ?"
                    " WHERE id = ?",
                    (label, by, now, theme_id),
                )
                if cursor.rowcount > 0:
                    updated.append(theme_id)
        return updated

    @threaded
    def upsert_sources(self, records: Sequence[tuple[str, str, dict[str, Any]]], now: str) -> None:
        with self._conn:
            for source_id, kind, data in records:
                self._conn.execute(
                    "INSERT INTO inquiry_sources"
                    " (id, kind, json, first_surfaced_at, last_surfaced_at, times_surfaced)"
                    " VALUES (?, ?, ?, ?, ?, 1)"
                    " ON CONFLICT(id) DO UPDATE SET json = excluded.json,"
                    " last_surfaced_at = excluded.last_surfaced_at,"
                    " times_surfaced = times_surfaced + 1",
                    (source_id, kind, json.dumps(data, ensure_ascii=False), now, now),
                )

    @threaded
    def list_sources(self) -> list[SourceRecord]:
        rows = self._all(
            "SELECT id, kind, json, first_surfaced_at, last_surfaced_at, times_surfaced"
            " FROM inquiry_sources ORDER BY rowid"
        )
        return [
            SourceRecord(
                id=r[0],
                kind=r[1],
                data=json.loads(r[2]),
                first_surfaced_at=r[3],
                last_surfaced_at=r[4],
                times_surfaced=int(r[5]),
            )
            for r in rows
        ]

    @threaded
    def list_feedback_with_ideas(self) -> list[dict[str, Any]]:
        rows = self._all(
            "SELECT f.idea_id, f.session_id, f.decision, f.created_at, s.topic, i.json"
            " FROM feedback f JOIN sessions s ON s.id = f.session_id"
            " LEFT JOIN ideas i ON i.id = f.idea_id ORDER BY f.id"
        )
        result: list[dict[str, Any]] = []
        for row in rows:
            idea = json.loads(row[5]) if row[5] else {}
            result.append(
                {
                    "idea_id": row[0],
                    "session_id": row[1],
                    "decision": row[2],
                    "at": row[3],
                    "session_topic": row[4],
                    "text": idea.get("text"),
                    "kind": idea.get("kind"),
                }
            )
        return result

    @threaded
    def list_ideas_from_sources(self) -> list[tuple[str, str, str]]:
        rows = self._all(
            "SELECT id, session_id, json FROM ideas WHERE json LIKE '%from_source%' ORDER BY rowid"
        )
        found: list[tuple[str, str, str]] = []
        for row in rows:
            source_id = json.loads(row[2]).get("meta", {}).get("from_source")
            if isinstance(source_id, str) and source_id:
                found.append((str(row[0]), str(row[1]), source_id))
        return found
