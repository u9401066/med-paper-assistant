"""Ports: what the use cases need from the outside world."""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Sequence
from typing import Any, Protocol

import numpy as np
from pydantic import BaseModel, Field

from cgu.domain.common import Session
from cgu.domain.frame import Frame
from cgu.domain.idea import Fragment, Idea
from cgu.domain.inquiry import Inquiry, SourceRecord, ThemeRecord
from cgu.domain.inquiry_material import InquiryMaterial, InquiryReview
from cgu.domain.judge import Matchup, Verdict

ProgressFn = Callable[[float, float | None, str | None], Awaitable[None]]


class EmbeddingUnavailableError(Exception):
    pass


class LLMUnavailableError(Exception):
    pass


class RetrievalUnavailableError(Exception):
    pass


class EmbeddingInfo(BaseModel):
    backend: str
    semantic: bool


class Embedded(BaseModel):
    """Unit-length vectors from a single backend, so one call never mixes spaces."""

    vectors: list[list[float]]
    backend: str
    semantic: bool
    warnings: list[str] = Field(default_factory=list)


class RetrievedDoc(BaseModel):
    title: str
    text: str
    url: str | None = None
    source_id: str | None = None


class EmbeddingPort(Protocol):
    async def describe(self) -> EmbeddingInfo: ...

    async def embed(self, texts: Sequence[str]) -> Embedded: ...


class LLMPort(Protocol):
    model: str

    async def complete(self, prompt: str, *, seed: int | None = None) -> str: ...


class RetrievalPort(Protocol):
    async def search(self, query: str, *, lang: str, limit: int) -> list[RetrievedDoc]: ...


class InquiryArchivePort(Protocol):
    """Cross-session storage of a person's own questions and what was mined from them."""

    async def get_inquiry_settings(self) -> dict[str, str]: ...

    async def inquiry_maintenance_counts(self, project: str | None = None) -> dict[str, int]: ...

    async def pending_inquiries(self, limit: int, project: str | None = None) -> list[Inquiry]: ...

    async def save_inquiry_materials(
        self, materials: Sequence[InquiryMaterial], reviewed: Sequence[InquiryReview], now: str
    ) -> None: ...

    async def list_inquiry_materials(
        self,
        project: str | None = None,
        query: str | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[InquiryMaterial]: ...

    async def set_inquiry_settings(self, values: dict[str, str]) -> None: ...

    async def insert_inquiries(self, inquiries: Sequence[Inquiry]) -> None: ...

    async def inquiry_family_rows(self) -> list[tuple[str, str, str, str]]:
        """(id, family_id, text, occurred_at) of every stored question, oldest first."""
        ...

    async def list_inquiries(
        self,
        *,
        project: str | None = None,
        since: str | None = None,
        ids: Sequence[str] | None = None,
        newest_first: bool = False,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[Inquiry]: ...

    async def count_inquiries(
        self,
        *,
        project: str | None = None,
        since: str | None = None,
        ids: Sequence[str] | None = None,
    ) -> int: ...

    async def delete_inquiries(
        self,
        *,
        ids: Sequence[str] | None = None,
        project: str | None = None,
        before: str | None = None,
        everything: bool = False,
    ) -> tuple[int, int, int]:
        """Delete matching questions; returns (deleted, themes removed, sources removed)."""
        ...

    async def save_inquiry_vectors(
        self, backend: str, items: Sequence[tuple[str, np.ndarray]]
    ) -> None: ...

    async def load_inquiry_vectors(
        self, backend: str, ids: Sequence[str]
    ) -> tuple[list[str], np.ndarray]: ...

    async def list_themes(self) -> list[ThemeRecord]: ...

    async def replace_themes(self, themes: Sequence[ThemeRecord], min_size: int) -> None: ...

    async def label_themes(self, labels: dict[str, str], by: str) -> list[str]: ...

    async def upsert_sources(
        self, records: Sequence[tuple[str, str, dict[str, Any]]], now: str
    ) -> None: ...

    async def list_sources(self) -> list[SourceRecord]: ...

    async def list_feedback_with_ideas(self) -> list[dict[str, Any]]:
        """Every feedback record across sessions, joined with its idea text and session topic."""
        ...

    async def list_ideas_from_sources(self) -> list[tuple[str, str, str]]:
        """(idea_id, session_id, source_id) of ideas whose meta carries from_source."""
        ...


class ArchivePort(InquiryArchivePort, Protocol):
    async def create_session(self, session: Session) -> None: ...

    async def get_session(self, session_id: str) -> Session | None: ...

    async def list_sessions(self) -> list[Session]: ...

    async def delete_session(self, session_id: str) -> bool: ...

    async def export_session(self, session_id: str) -> dict[str, Any]: ...

    async def counts(self, session_id: str) -> dict[str, int]: ...

    async def bump_counter(self, session_id: str, name: str) -> int: ...

    async def save_frame(self, frame: Frame) -> None: ...

    async def get_frame(self, frame_id: str) -> Frame | None: ...

    async def list_frames(self, session_id: str) -> list[Frame]: ...

    async def save_ideas(self, ideas: Sequence[Idea]) -> None: ...

    async def update_idea(self, idea: Idea) -> None: ...

    async def list_ideas(self, session_id: str, kind: str | None = None) -> list[Idea]: ...

    async def save_fragments(self, fragments: Sequence[Fragment]) -> None: ...

    async def list_fragments(self, session_id: str) -> list[Fragment]: ...

    async def save_matchups(self, matchups: Sequence[Matchup]) -> None: ...

    async def list_matchups(self, session_id: str) -> list[Matchup]: ...

    async def save_verdicts(self, session_id: str, verdicts: Sequence[Verdict]) -> None: ...

    async def list_verdicts(self, session_id: str) -> list[Verdict]: ...

    async def get_niches(self, session_id: str) -> dict[str, dict[str, Any]]: ...

    async def put_niche(self, session_id: str, niche: str, state: dict[str, Any]) -> None: ...

    async def save_question(self, session_id: str, record: dict[str, Any]) -> None: ...

    async def list_questions(self, session_id: str) -> list[dict[str, Any]]: ...

    async def save_feedback(self, session_id: str, record: dict[str, Any]) -> None: ...

    async def list_feedback(self, session_id: str) -> list[dict[str, Any]]: ...

    async def delete_feedback(self, session_id: str) -> int: ...
