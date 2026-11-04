"""Sessions: the boundary of all state."""

from __future__ import annotations

import secrets

from cgu.application.ports import ArchivePort
from cgu.application.services._common import new_id, now_iso, provenance, require_session
from cgu.domain.common import CGUError, Session, ToolResult


class SessionService:
    def __init__(self, archive: ArchivePort) -> None:
        self._archive = archive

    async def open(
        self, topic: str | None, domain: str | None, language: str | None, seed: int | None
    ) -> ToolResult:
        if not topic or not topic.strip():
            raise CGUError("invalid_input", "topic is required for action=open")
        session = Session(
            id=new_id("s"),
            topic=topic.strip(),
            domain=domain.strip() if domain else None,
            language=language or "zh-TW",
            seed=seed if seed is not None else secrets.randbits(31),
            created_at=now_iso(),
        )
        await self._archive.create_session(session)
        return ToolResult.success(
            provenance("archive", seed=session.seed),
            {"session_id": session.id, "seed": session.seed, "session": session.model_dump()},
        )

    async def get(self, session_id: str) -> ToolResult:
        session = await require_session(self._archive, session_id)
        counts = await self._archive.counts(session_id)
        return ToolResult.success(
            provenance("archive", seed=session.seed),
            {"session": session.model_dump(), "counts": counts},
        )

    async def list_sessions(self) -> ToolResult:
        sessions = await self._archive.list_sessions()
        return ToolResult.success(
            provenance("archive"),
            {"sessions": [s.model_dump() for s in sessions], "count": len(sessions)},
        )

    async def export(self, session_id: str) -> ToolResult:
        session = await require_session(self._archive, session_id)
        return ToolResult.success(
            provenance("archive", seed=session.seed), await self._archive.export_session(session_id)
        )

    async def delete(self, session_id: str, confirm: bool) -> ToolResult:
        await require_session(self._archive, session_id)
        if not confirm:
            raise CGUError(
                "invalid_input",
                "delete removes every record of the session and needs confirm=true",
                'Call again with confirm=true after the user agrees; use action="export" first '
                "to keep a copy.",
            )
        counts = await self._archive.counts(session_id)
        await self._archive.delete_session(session_id)
        return ToolResult.success(
            provenance("archive"), {"deleted": session_id, "removed_counts": counts}
        )
