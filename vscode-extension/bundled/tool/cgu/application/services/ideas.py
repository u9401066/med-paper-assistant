"""Ideas: stored with provenance, de-duplicated, and measured against explicit reference sets."""

from __future__ import annotations

import asyncio
from typing import Any

import numpy as np
from pydantic import BaseModel, Field

from cgu.application.ports import ArchivePort, EmbeddingPort, EmbeddingUnavailableError
from cgu.application.services._common import (
    new_id,
    now_iso,
    provenance,
    reject_floats,
    require_frame,
    require_session,
)
from cgu.domain.common import CGUError, Measurement, ToolResult
from cgu.domain.idea import MAX_IDEA_CHARS, Idea, IdeaKind
from cgu.domain.measure import (
    COSINE_DUPLICATE_THRESHOLD,
    JACCARD_DUPLICATE_THRESHOLD,
    NoveltyAgainst,
    as_matrix,
    diversity,
    lexical_duplicate,
    novelty_against,
    semantic_duplicate,
)
from cgu.domain.operators import OPERATORS

MAX_ADD_BATCH = 100
NOVELTY_SETS = (
    ("vs_typical", "typical", "session typical set"),
    ("vs_human", "human", "session human ideas"),
    ("vs_prior_art", "prior_art", "session prior-art set"),
)


class IdeaInput(BaseModel):
    text: str = Field(min_length=1, max_length=MAX_IDEA_CHARS)
    kind: IdeaKind
    frame_id: str | None = None
    operator: str | None = None
    parent_id: str | None = None
    material_ids: list[str] = Field(default_factory=list)
    meta: dict[str, Any] = Field(default_factory=dict)


class Thresholds(BaseModel):
    jaccard: float | None = Field(default=None, ge=0, le=1, description="Shingle Jaccard cut-off")
    cosine: float | None = Field(default=None, ge=0, le=1, description="Embedding cosine cut-off")


def _duplicate_view(found: tuple[str, Measurement] | None) -> dict[str, Any] | None:
    if found is None:
        return None
    return {"idea_id": found[0], "similarity": found[1].model_dump()}


class IdeaService:
    def __init__(self, archive: ArchivePort, embedding: EmbeddingPort) -> None:
        self._archive = archive
        self._embedding = embedding

    async def _validate(
        self, session_id: str, items: list[IdeaInput], existing: list[Idea]
    ) -> None:
        known_ids = {i.id for i in existing}
        fragment_ids = {f.id for f in await self._archive.list_fragments(session_id)}
        for position, item in enumerate(items):
            label = f"ideas[{position}]"
            if not item.text.strip():
                raise CGUError("invalid_input", f"{label}.text is empty")
            if item.frame_id:
                await require_frame(self._archive, session_id, item.frame_id)
            if item.operator and item.operator not in OPERATORS:
                raise CGUError(
                    "invalid_input",
                    f"{label}.operator {item.operator!r} is not an operator",
                    "Use one of: " + ", ".join(OPERATORS),
                )
            if item.parent_id and item.parent_id not in known_ids:
                raise CGUError("not_found", f"{label}.parent_id {item.parent_id!r} not found")
            missing = [m for m in item.material_ids if m not in fragment_ids]
            if missing:
                raise CGUError("not_found", f"{label}.material_ids not found: {missing}")
            reject_floats(item.meta, f"{label}.meta")

    async def add(self, session_id: str, items: list[IdeaInput] | None) -> ToolResult:
        session = await require_session(self._archive, session_id)
        if not items:
            raise CGUError("invalid_input", "ideas is required for action=add")
        if len(items) > MAX_ADD_BATCH:
            raise CGUError("invalid_input", f"at most {MAX_ADD_BATCH} ideas per call")
        existing = await self._archive.list_ideas(session_id)
        await self._validate(session_id, items, existing)

        warnings: list[str] = []
        degraded = False
        matrix: np.ndarray | None = None
        try:
            embedded = await self._embedding.embed(
                [i.text for i in items] + [e.text for e in existing]
            )
            warnings.extend(embedded.warnings)
            degraded = bool(embedded.warnings)
            if embedded.semantic:
                matrix = as_matrix(embedded.vectors)
            method = f"cosine over {embedded.backend} embeddings"
        except EmbeddingUnavailableError as exc:
            warnings.append(f"embedding unavailable, lexical duplicate check only: {exc}")
            degraded = True
            method = ""

        created: list[Idea] = []
        pool: list[tuple[str, str]] = [(e.id, e.text) for e in existing]
        pool_rows: list[int] = [len(items) + j for j in range(len(existing))]
        ids = [new_id("i") for _ in items]
        founds = await asyncio.to_thread(
            self._find_duplicates, items, ids, pool, pool_rows, matrix, method
        )
        views: list[dict[str, Any]] = []
        for item, idea_id, found in zip(items, ids, founds, strict=True):
            idea = Idea(
                id=idea_id,
                session_id=session_id,
                text=item.text.strip(),
                kind=item.kind,
                frame_id=item.frame_id,
                operator=item.operator,
                parent_id=item.parent_id,
                material_ids=item.material_ids,
                meta=item.meta,
                duplicate_of=found[0] if found else None,
                created_at=now_iso(),
            )
            created.append(idea)
            views.append(
                {
                    "idea_id": idea.id,
                    "kind": idea.kind,
                    "duplicate_of": _duplicate_view(found),
                }
            )
        await self._archive.save_ideas(created)
        duplicates = sum(1 for v in views if v["duplicate_of"])
        if duplicates:
            warnings.append(
                f"{duplicates} idea(s) are near-duplicates of existing ideas (stored, flagged)"
            )
        return ToolResult.success(
            provenance("archive", seed=session.seed, warnings=warnings, degraded=degraded),
            {"ideas": views, "count": len(views)},
        )

    @staticmethod
    def _find_duplicates(
        items: list[IdeaInput],
        ids: list[str],
        pool: list[tuple[str, str]],
        pool_rows: list[int],
        matrix: np.ndarray | None,
        method: str,
    ) -> list[tuple[str, Measurement] | None]:
        pool = list(pool)
        pool_rows = list(pool_rows)
        founds: list[tuple[str, Measurement] | None] = []
        for position, (item, idea_id) in enumerate(zip(items, ids, strict=True)):
            found = lexical_duplicate(item.text, pool)
            if found is None and matrix is not None and pool_rows:
                found = semantic_duplicate(
                    matrix[position],
                    matrix[pool_rows],
                    [p[0] for p in pool],
                    threshold=COSINE_DUPLICATE_THRESHOLD,
                    method=method,
                )
            founds.append(found)
            pool.append((idea_id, item.text.strip()))
            pool_rows.append(position)
        return founds

    async def list_ideas(self, session_id: str, kind: str | None) -> ToolResult:
        await require_session(self._archive, session_id)
        if kind is not None and kind not in ("typical", "candidate", "human", "prior_art"):
            raise CGUError("invalid_input", f"unknown kind {kind!r}")
        ideas = await self._archive.list_ideas(session_id, kind)
        return ToolResult.success(
            provenance("archive"),
            {
                "ideas": [i.model_dump(mode="json", exclude={"session_id"}) for i in ideas],
                "count": len(ideas),
            },
        )

    async def measure(
        self,
        session_id: str,
        idea_ids: list[str] | None,
        thresholds: Thresholds | None,
    ) -> ToolResult:
        session = await require_session(self._archive, session_id)
        ideas = await self._archive.list_ideas(session_id)
        by_id = {i.id: i for i in ideas}
        if idea_ids:
            missing = [i for i in idea_ids if i not in by_id]
            if missing:
                raise CGUError("not_found", f"ideas not found: {missing}")
            targets = [by_id[i] for i in idea_ids]
        else:
            targets = [i for i in ideas if i.kind == "candidate"]
        warnings: list[str] = []
        if not targets:
            warnings.append("no candidate ideas to measure; add some with cgu_ideas(action='add')")
            return ToolResult.success(
                provenance("heuristic", seed=session.seed, warnings=warnings),
                {"results": [], "diversity": None, "embedding": None},
            )
        try:
            embedded = await self._embedding.embed([i.text for i in ideas])
        except EmbeddingUnavailableError as exc:
            raise CGUError(
                "unavailable",
                f"embedding backend unavailable: {exc}",
                "Start Ollama or set CGU_EMBEDDING=auto (falls back to n-grams) or ngram.",
            ) from exc
        warnings.extend(embedded.warnings)
        if not embedded.semantic:
            warnings.append(
                "semantic=false: similarities are char n-gram overlap, not meaning; "
                "low similarity does not prove a different idea"
            )
        matrix = as_matrix(embedded.vectors)
        index = {i.id: n for n, i in enumerate(ideas)}
        flavour = (
            "semantic embeddings" if embedded.semantic else "char n-gram hashing, lexical only"
        )
        method = f"cosine over {embedded.backend} ({flavour})"
        jaccard_cut = (
            thresholds.jaccard
            if thresholds and thresholds.jaccard is not None
            else JACCARD_DUPLICATE_THRESHOLD
        )
        cosine_cut = (
            thresholds.cosine
            if thresholds and thresholds.cosine is not None
            else COSINE_DUPLICATE_THRESHOLD
        )

        results, spread = await asyncio.to_thread(
            self._compute,
            targets,
            ideas,
            matrix,
            index,
            embedded.semantic,
            method,
            jaccard_cut,
            cosine_cut,
        )
        return ToolResult.success(
            provenance(
                "heuristic",
                seed=session.seed,
                warnings=warnings,
                degraded=not embedded.semantic,
            ),
            {
                "results": results,
                "diversity": spread.model_dump() if spread else None,
                "embedding": {"backend": embedded.backend, "semantic": embedded.semantic},
                "duplicate_rule": (
                    f"duplicate if shingle Jaccard >= {jaccard_cut}"
                    + (f" or embedding cosine >= {cosine_cut}" if embedded.semantic else "")
                ),
            },
        )

    @staticmethod
    def _compute(
        targets: list[Idea],
        ideas: list[Idea],
        matrix: np.ndarray,
        index: dict[str, int],
        semantic: bool,
        method: str,
        jaccard_cut: float,
        cosine_cut: float,
    ) -> tuple[list[dict[str, Any]], Measurement | None]:
        results: list[dict[str, Any]] = []
        for target in targets:
            row = index[target.id]
            novelty: dict[str, NoveltyAgainst | None] = {}
            for key, kind, label in NOVELTY_SETS:
                refs = [n for n, i in enumerate(ideas) if i.kind == kind and i.id != target.id]
                novelty[key] = novelty_against(
                    matrix[row],
                    matrix[refs] if refs else np.empty((0, matrix.shape[1])),
                    [ideas[n].id for n in refs],
                    method=method,
                    reference=f"{label} (n={len(refs)})",
                )
            others = [n for n, i in enumerate(ideas) if i.id != target.id]
            novelty["vs_session"] = novelty_against(
                matrix[row],
                matrix[others] if others else np.empty((0, matrix.shape[1])),
                [ideas[n].id for n in others],
                method=method,
                reference=f"all other session ideas (n={len(others)})",
            )
            earlier = [(i.id, i.text) for i in ideas[: index[target.id]]]
            found = lexical_duplicate(target.text, earlier, jaccard_cut)
            if found is None and semantic and index[target.id] > 0:
                found = semantic_duplicate(
                    matrix[row],
                    matrix[: index[target.id]],
                    [e[0] for e in earlier],
                    threshold=cosine_cut,
                    method=method,
                )
            results.append(
                {
                    "idea_id": target.id,
                    "kind": target.kind,
                    "novelty": {k: (v.model_dump() if v else None) for k, v in novelty.items()},
                    "duplicate_of": _duplicate_view(found),
                }
            )

        distinct = [
            t
            for t in targets
            if not any(r["idea_id"] == t.id and r["duplicate_of"] for r in results)
        ]
        spread = diversity(
            matrix[[index[t.id] for t in distinct]] if distinct else np.empty((0, matrix.shape[1])),
            method=method,
            reference=f"measured set (n={len(distinct)}, {len(targets) - len(distinct)} flagged duplicates excluded)",
        )
        return results, spread
