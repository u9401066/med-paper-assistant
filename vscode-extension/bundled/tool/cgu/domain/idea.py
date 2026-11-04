"""Ideas and material fragments."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from cgu.domain.common import Measurement

IdeaKind = Literal["typical", "candidate", "human", "prior_art"]
IDEA_KINDS = ("typical", "candidate", "human", "prior_art")
MAX_IDEA_CHARS = 2000


class Idea(BaseModel):
    id: str
    session_id: str
    text: str
    kind: IdeaKind
    frame_id: str | None = None
    operator: str | None = None
    parent_id: str | None = None
    material_ids: list[str] = Field(default_factory=list)
    meta: dict[str, Any] = Field(default_factory=dict)
    duplicate_of: str | None = None
    created_at: str = ""


class Fragment(BaseModel):
    id: str
    session_id: str
    text: str
    fenced_text: str
    source_type: str
    source_id: str | None = None
    url: str | None = None
    title: str | None = None
    trusted: Literal[False] = False
    truncated: bool = False
    stripped: int = 0
    distance_band: Measurement | None = None
    band: Literal["near", "mid", "far"] | None = None
    created_at: str = ""
