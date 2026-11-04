"""Feedback: what the human did with each idea, as counts. No personalisation, no prediction."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from cgu.application.ports import ArchivePort
from cgu.application.services._common import now_iso, provenance, require_session
from cgu.domain.common import CGUError, ToolResult

DECISIONS = ("adopt", "modify", "abandon")


class FeedbackService:
    def __init__(self, archive: ArchivePort) -> None:
        self._archive = archive

    async def record(
        self,
        session_id: str,
        idea_id: str | None,
        decision: str | None,
        reasons: list[str] | None,
        note: str | None,
    ) -> ToolResult:
        session = await require_session(self._archive, session_id)
        if not idea_id or decision not in DECISIONS:
            raise CGUError(
                "invalid_input",
                f"idea_id and decision in {DECISIONS} are required for action=record",
            )
        ideas = {i.id: i for i in await self._archive.list_ideas(session_id)}
        idea = ideas.get(idea_id)
        if idea is None:
            raise CGUError("not_found", f"idea {idea_id!r} does not exist in this session")
        element = idea.meta.get("frame_element_kind") or idea.meta.get("rewrote")
        record: dict[str, Any] = {
            "idea_id": idea_id,
            "decision": decision,
            "reasons": reasons or [],
            "note": note,
            "operator": idea.operator,
            "frame_element_kind": element if isinstance(element, str) else None,
            "at": now_iso(),
        }
        await self._archive.save_feedback(session_id, record)
        return ToolResult.success(provenance("archive", seed=session.seed), {"recorded": record})

    async def summary(self, session_id: str) -> ToolResult:
        await require_session(self._archive, session_id)
        rows = await self._archive.list_feedback(session_id)

        def tally(key: str) -> dict[str, dict[str, int]]:
            table: dict[str, dict[str, int]] = defaultdict(lambda: dict.fromkeys(DECISIONS, 0))
            for row in rows:
                table[row.get(key) or "unspecified"][row["decision"]] += 1
            return dict(table)

        by_decision = dict.fromkeys(DECISIONS, 0)
        for row in rows:
            by_decision[row["decision"]] += 1
        return ToolResult.success(
            provenance("archive"),
            {
                "total": len(rows),
                "by_decision": by_decision,
                "by_operator": tally("operator"),
                "by_frame_element_kind": tally("frame_element_kind"),
                "note": "counts of what you decided; not a preference model and not a prediction",
            },
        )

    async def export(self, session_id: str) -> ToolResult:
        await require_session(self._archive, session_id)
        rows = await self._archive.list_feedback(session_id)
        return ToolResult.success(provenance("archive"), {"feedback": rows, "count": len(rows)})

    async def delete(self, session_id: str, confirm: bool) -> ToolResult:
        await require_session(self._archive, session_id)
        if not confirm:
            raise CGUError(
                "invalid_input",
                "delete removes this session's feedback records and needs confirm=true",
                'Use action="export" first if you want a copy.',
            )
        removed = await self._archive.delete_feedback(session_id)
        return ToolResult.success(provenance("archive"), {"deleted": removed})
