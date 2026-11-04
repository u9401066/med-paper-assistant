"""Helpers shared by the use cases."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from cgu.application.ports import ArchivePort
from cgu.domain.common import CGUError, Engine, Provenance, Session, iter_stray_floats
from cgu.domain.frame import Frame


def now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def provenance(
    engine: Engine,
    *,
    seed: int | None = None,
    warnings: list[str] | None = None,
    degraded: bool = False,
    model: str | None = None,
    sources: list[dict[str, Any]] | None = None,
) -> Provenance:
    return Provenance(
        engine=engine,
        degraded=degraded,
        warnings=list(warnings or []),
        seed=seed,
        model=model,
        sources=list(sources or []),
    )


async def require_session(archive: ArchivePort, session_id: str) -> Session:
    session = await archive.get_session(session_id)
    if session is None:
        known = [s.id for s in await archive.list_sessions()][:5]
        hint = (
            'Open one with cgu_session(action="open", topic="...") or list them with action="list".'
        )
        if known:
            hint += f" Use the id that open returned, not a made-up name. Existing ids: {known}."
        raise CGUError("not_found", f"session {session_id!r} does not exist", hint)
    return session


async def require_frame(archive: ArchivePort, session_id: str, frame_id: str) -> Frame:
    frame = await archive.get_frame(frame_id)
    if frame is None or frame.session_id != session_id:
        raise CGUError(
            "not_found",
            f"frame {frame_id!r} does not exist in this session",
            'Create one with cgu_frame(action="create", problem="...").',
        )
    return frame


def reject_floats(value: Any, label: str) -> None:
    stray = list(iter_stray_floats(value, label))
    if stray:
        raise CGUError(
            "invalid_input",
            f"{label} must not contain floating-point numbers ({stray[0]})",
            "Uncalibrated scores must not enter the archive; use strings or integers.",
        )


def pick(items: list[Any], index: int) -> Any:
    return items[index % len(items)]


def frame_summary(frame: Frame, limit: int = 6) -> str:
    parts = [f"problem={frame.problem}"]
    if frame.goal:
        parts.append(f"goal={frame.goal}")
    if frame.unit:
        parts.append(f"unit={frame.unit}")
    if frame.assumptions:
        listed = "; ".join(f"{a.id}:{a.text}" for a in frame.assumptions[:limit])
        parts.append(f"assumptions=[{listed}]")
    if frame.metaphors:
        parts.append("metaphors=[" + "; ".join(m.text for m in frame.metaphors[:limit]) + "]")
    if frame.criteria:
        parts.append("criteria=[" + "; ".join(c.text for c in frame.criteria[:limit]) + "]")
    return " | ".join(parts)
