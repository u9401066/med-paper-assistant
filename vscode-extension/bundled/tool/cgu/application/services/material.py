"""Material: untrusted fragments from retrieval or other tools, fenced before they are stored."""

from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, Field

from cgu.application.ports import (
    ArchivePort,
    EmbeddingPort,
    EmbeddingUnavailableError,
    ProgressFn,
    RetrievalPort,
    RetrievalUnavailableError,
)
from cgu.application.services._common import new_id, now_iso, provenance, require_session
from cgu.domain.common import CGUError, Measurement, ToolResult
from cgu.domain.fence import fence
from cgu.domain.idea import Fragment
from cgu.domain.measure import BAND_NOTE, as_matrix, band_from_distance

MAX_SEARCH_LIMIT = 10
MAX_ADD_BATCH = 50
SUPPORTED_SOURCES = ("wikipedia",)
_URL_RE = re.compile(r"^https?://[^\s<>\"']{1,500}$")


class FragmentInput(BaseModel):
    text: str = Field(min_length=1)
    source_type: str = Field(min_length=1, max_length=40)
    source_id: str | None = Field(default=None, max_length=200)
    url: str | None = Field(default=None, max_length=500)
    title: str | None = Field(default=None, max_length=300)


def fragment_view(fragment: Fragment) -> dict[str, Any]:
    view: dict[str, Any] = fragment.model_dump(mode="json", exclude={"text", "session_id"})
    return view


def _safe_url(url: str | None) -> str | None:
    return url if url and _URL_RE.match(url) else None


class MaterialService:
    def __init__(
        self,
        archive: ArchivePort,
        embedding: EmbeddingPort,
        retrieval: RetrievalPort,
        *,
        network_enabled: bool,
    ) -> None:
        self._archive = archive
        self._embedding = embedding
        self._retrieval = retrieval
        self._network = network_enabled

    async def _distances(
        self, topic: str, texts: list[str]
    ) -> tuple[list[Measurement | None], list[str], bool]:
        """Cosine distance to the topic, only when the backend is semantic."""
        try:
            embedded = await self._embedding.embed([topic, *texts])
        except EmbeddingUnavailableError as exc:
            return [None] * len(texts), [f"distance_band skipped: {exc}"], True
        warnings = list(embedded.warnings)
        if not embedded.semantic:
            warnings.append(
                "distance_band is null: the embedding backend is not semantic, so char n-gram "
                "overlap would be mistaken for meaning"
            )
            return [None] * len(texts), warnings, bool(embedded.warnings)
        matrix = as_matrix(embedded.vectors)
        topic_vec, rest = matrix[0], matrix[1:]
        method = f"cosine distance to the session topic over {embedded.backend}; {BAND_NOTE}"
        return (
            [
                Measurement(
                    value=float(1.0 - float(vec @ topic_vec)),
                    method=method,
                    reference="session topic",
                    n=1,
                )
                for vec in rest
            ],
            warnings,
            False,
        )

    async def _store(
        self, session_id: str, topic: str, items: list[FragmentInput]
    ) -> tuple[list[Fragment], list[str], bool]:
        fenced = [
            fence(item.text, f"{item.source_type}:{item.source_id or item.title or ''}")
            for item in items
        ]
        distances, warnings, degraded = await self._distances(topic, [f.text for f in fenced])
        fragments: list[Fragment] = []
        for item, result, distance in zip(items, fenced, distances, strict=True):
            fragments.append(
                Fragment(
                    id=new_id("fr"),
                    session_id=session_id,
                    text=result.text,
                    fenced_text=result.fenced_text,
                    source_type=item.source_type,
                    source_id=item.source_id,
                    url=_safe_url(item.url),
                    title=fence(item.title, item.source_type, 200).text if item.title else None,
                    truncated=result.truncated,
                    stripped=result.stripped,
                    distance_band=distance,
                    band=band_from_distance(distance.value) if distance else None,
                    created_at=now_iso(),
                )
            )
        await self._archive.save_fragments(fragments)
        stripped = sum(f.stripped for f in fragments)
        if stripped:
            warnings.append(f"{stripped} instruction-like sentence(s) were removed from the text")
        return fragments, warnings, degraded

    @staticmethod
    def _sources(fragments: list[Fragment]) -> list[dict[str, Any]]:
        return [
            {"type": f.source_type, "url": f.url, "id": f.source_id, "trusted": False}
            for f in fragments
        ]

    async def search(
        self,
        session_id: str,
        query: str | None,
        source: str,
        lang: str,
        limit: int,
        progress: ProgressFn | None = None,
    ) -> ToolResult:
        session = await require_session(self._archive, session_id)
        if not query or not query.strip():
            raise CGUError("invalid_input", "query is required for action=search")
        if source not in SUPPORTED_SOURCES:
            raise CGUError(
                "invalid_input",
                f"unsupported source {source!r}",
                f"Use one of {SUPPORTED_SOURCES}.",
            )
        limit = max(1, min(limit, MAX_SEARCH_LIMIT))
        if not self._network:
            return ToolResult.success(
                provenance(
                    "retrieval",
                    degraded=True,
                    warnings=["network is off (CGU_NETWORK=off); no search was made"],
                ),
                {"fragments": [], "count": 0},
            )
        if progress:
            await progress(0, 3, f"searching {source}")
        try:
            docs = await self._retrieval.search(query.strip(), lang=lang, limit=limit)
        except RetrievalUnavailableError as exc:
            return ToolResult.success(
                provenance(
                    "retrieval", degraded=True, warnings=[f"retrieval failed, no material: {exc}"]
                ),
                {"fragments": [], "count": 0},
            )
        if progress:
            await progress(1, 3, f"fencing {len(docs)} fragments")
        items = [
            FragmentInput(
                text=doc.text or doc.title,
                source_type=source,
                source_id=doc.source_id,
                url=doc.url,
                title=doc.title,
            )
            for doc in docs
            if (doc.text or doc.title).strip()
        ]
        fragments, warnings, degraded = await self._store(session_id, session.topic, items)
        if progress:
            await progress(3, 3, "done")
        return ToolResult.success(
            provenance(
                "retrieval",
                seed=session.seed,
                warnings=warnings,
                degraded=degraded,
                sources=self._sources(fragments),
            ),
            {"fragments": [fragment_view(f) for f in fragments], "count": len(fragments)},
        )

    async def add(self, session_id: str, fragments: list[FragmentInput] | None) -> ToolResult:
        session = await require_session(self._archive, session_id)
        if not fragments:
            raise CGUError("invalid_input", "fragments is required for action=add")
        if len(fragments) > MAX_ADD_BATCH:
            raise CGUError("invalid_input", f"at most {MAX_ADD_BATCH} fragments per call")
        stored, warnings, degraded = await self._store(session_id, session.topic, fragments)
        return ToolResult.success(
            provenance(
                "archive",
                seed=session.seed,
                warnings=warnings,
                degraded=degraded,
                sources=self._sources(stored),
            ),
            {"fragments": [fragment_view(f) for f in stored], "count": len(stored)},
        )

    async def list_fragments(self, session_id: str, band: str | None) -> ToolResult:
        await require_session(self._archive, session_id)
        if band is not None and band not in ("near", "mid", "far"):
            raise CGUError("invalid_input", "band must be near, mid or far")
        items = await self._archive.list_fragments(session_id)
        if band:
            items = [f for f in items if f.band == band]
        return ToolResult.success(
            provenance("archive"),
            {"fragments": [fragment_view(f) for f in items], "count": len(items)},
        )
