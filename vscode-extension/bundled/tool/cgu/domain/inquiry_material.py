"""Creative material distilled by the caller, with references to stored inquiry text."""

from __future__ import annotations

import hashlib
from typing import Literal

from pydantic import BaseModel, Field

MaterialKind = Literal["question", "constraint", "assumption", "analogy", "observation", "idea"]


def text_sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class InquiryReview(BaseModel):
    inquiry_id: str = Field(min_length=1)
    text_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class MaterialDraft(BaseModel):
    kind: MaterialKind
    text: str = Field(min_length=1, max_length=2000)
    inquiry_ids: list[str] = Field(min_length=1, max_length=100)


class MaterialEvidence(InquiryReview):
    occurred_at: str
    source: str
    project: str | None = None


class InquiryMaterial(BaseModel):
    id: str
    kind: MaterialKind
    text: str
    evidence: list[MaterialEvidence]
    created_at: str
    created_by: Literal["caller"] = "caller"
    agent_model: str | None = None
