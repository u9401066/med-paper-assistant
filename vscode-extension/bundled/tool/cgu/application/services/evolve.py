"""Evolve: a quality-diversity archive over (rewritten frame element kind) x (distance band)."""

from __future__ import annotations

import random
from typing import Any

from cgu.application.ports import ArchivePort, EmbeddingPort, EmbeddingUnavailableError
from cgu.application.services._common import new_id, now_iso, provenance, require_session
from cgu.application.services.ideas import IdeaInput, IdeaService
from cgu.application.services.instructions import evolve_order, judge_order
from cgu.application.services.judge import JudgeService
from cgu.domain.common import CGUError, ToolResult
from cgu.domain.frame import ELEMENT_KINDS
from cgu.domain.idea import Idea
from cgu.domain.judge import DEFAULT_CRITERIA, TIE, Matchup, Verdict, judge_matchup_inputs
from cgu.domain.measure import BAND_NOTE, as_matrix, band_from_distance
from cgu.domain.operators import OPERATORS

BANDS = ("near", "mid", "far", "unknown")


def niche_label(kind: str, band: str) -> str:
    return f"{kind}|{band}"


class EvolveService:
    def __init__(
        self,
        archive: ArchivePort,
        embedding: EmbeddingPort,
        ideas: IdeaService,
        judge: JudgeService,
    ) -> None:
        self._archive = archive
        self._embedding = embedding
        self._ideas = ideas
        self._judge = judge

    async def map(self, session_id: str) -> ToolResult:
        session = await require_session(self._archive, session_id)
        niches = await self._archive.get_niches(session_id)
        by_id = {i.id: i for i in await self._archive.list_ideas(session_id)}
        cells = []
        for label, state in niches.items():
            kind, band = label.split("|")
            occupant = by_id.get(state.get("idea_id") or "")
            cells.append(
                {
                    "niche": label,
                    "kind": kind,
                    "band": band,
                    "idea_id": state.get("idea_id"),
                    "text": occupant.text if occupant else None,
                    "pending_idea_id": state.get("pending_idea_id"),
                    "history": state.get("history", []),
                }
            )
        total = len(ELEMENT_KINDS) * len(BANDS)
        occupied = [c["niche"] for c in cells if c["idea_id"]]
        return ToolResult.success(
            provenance("heuristic", seed=session.seed),
            {
                "cells": cells,
                "coverage": {"occupied": len(occupied), "total": total},
                "empty_niches": [
                    niche_label(k, b)
                    for k in ELEMENT_KINDS
                    for b in BANDS
                    if niche_label(k, b) not in occupied
                ],
                "band_note": BAND_NOTE,
            },
        )

    async def next(self, session_id: str) -> ToolResult:
        session = await require_session(self._archive, session_id)
        niches = await self._archive.get_niches(session_id)
        ideas = await self._archive.list_ideas(session_id)
        by_id = {i.id: i for i in ideas}
        occupants = sorted(s["idea_id"] for s in niches.values() if s.get("idea_id") in by_id)
        pool = occupants or sorted(i.id for i in ideas if i.kind == "candidate")
        pool = pool or sorted(i.id for i in ideas if i.kind == "typical")
        if not pool:
            raise CGUError(
                "invalid_input",
                "the archive has no parent to evolve from",
                'Add candidate or typical ideas with cgu_ideas(action="add") first.',
            )
        counter = await self._archive.bump_counter(session_id, "evolve_next")
        rng = random.Random(session.seed * 1_000_003 + counter)
        parent = by_id[rng.choice(pool)]
        try:
            semantic = (await self._embedding.describe()).semantic
        except EmbeddingUnavailableError:
            semantic = False
        bands = BANDS if semantic else ("unknown",)
        occupied = {label for label, s in niches.items() if s.get("idea_id")}
        empty = [(k, b) for k in ELEMENT_KINDS for b in bands if niche_label(k, b) not in occupied]
        kind, band = rng.choice(empty or [(k, b) for k in ELEMENT_KINDS for b in bands])
        card = rng.choice([c for c in OPERATORS.values() if kind in c.targets])
        niche = niche_label(kind, band)
        order = evolve_order(
            session_id=session_id,
            parent_id=parent.id,
            parent_text=parent.text,
            kind=kind,
            operator=card.name,
            operator_summary=card.summary,
            niche=niche,
        )
        return ToolResult.success(
            provenance("passthrough", seed=session.seed),
            {
                "parent_id": parent.id,
                "operator": card.name,
                "frame_element_kind": kind,
                "target_niche": niche,
                "step": counter,
                "niche_is_empty": bool(empty),
            },
            work_order=order,
        )

    async def _band(self, session_id: str, text: str) -> tuple[str, list[str], bool]:
        typical = await self._archive.list_ideas(session_id, "typical")
        if not typical:
            return "unknown", ["no typical ideas: distance band is unknown"], False
        try:
            embedded = await self._embedding.embed([text, *[t.text for t in typical]])
        except EmbeddingUnavailableError as exc:
            return "unknown", [f"distance band unknown: {exc}"], True
        warnings = list(embedded.warnings)
        if not embedded.semantic:
            return (
                "unknown",
                [*warnings, "distance band is unknown without a semantic embedding"],
                bool(warnings),
            )
        matrix = as_matrix(embedded.vectors)
        similarity = float(max(matrix[1:] @ matrix[0]))
        return band_from_distance(1.0 - similarity), warnings, False

    async def submit(
        self,
        session_id: str,
        child_text: str | None,
        parent_id: str | None,
        operator: str | None,
        frame_element_kind: str | None,
        material_ids: list[str] | None,
    ) -> ToolResult:
        session = await require_session(self._archive, session_id)
        if not child_text or not parent_id or not operator or not frame_element_kind:
            raise CGUError(
                "invalid_input",
                "child_text, parent_id, operator and frame_element_kind are required for submit",
            )
        if frame_element_kind not in ELEMENT_KINDS:
            raise CGUError(
                "invalid_input",
                f"frame_element_kind must be one of {ELEMENT_KINDS}",
            )
        band, warnings, degraded = await self._band(session_id, child_text)
        niche = niche_label(frame_element_kind, band)
        niches = await self._archive.get_niches(session_id)
        state = niches.get(niche, {})
        if state.get("pending_idea_id"):
            raise CGUError(
                "conflict",
                f"niche {niche} already has a pending challenger {state['pending_idea_id']}",
                'Resolve it first with cgu_evolve(action="resolve").',
            )
        added = await self._ideas.add(
            session_id,
            [
                IdeaInput(
                    text=child_text,
                    kind="candidate",
                    parent_id=parent_id,
                    operator=operator,
                    material_ids=material_ids or [],
                    meta={"frame_element_kind": frame_element_kind, "evolve": True},
                )
            ],
        )
        view = added.data["ideas"][0]
        idea_id: str = view["idea_id"]
        base = {"idea_id": idea_id, "niche": niche, "band_note": BAND_NOTE}
        history: list[dict[str, Any]] = list(state.get("history", []))
        if view["duplicate_of"]:
            return ToolResult.success(
                provenance(
                    "heuristic",
                    seed=session.seed,
                    warnings=[*warnings, "near-duplicate of an existing idea: not placed"],
                    degraded=degraded,
                ),
                {
                    **base,
                    "placed": False,
                    "reason": "duplicate",
                    "duplicate_of": view["duplicate_of"],
                },
            )
        if not state.get("idea_id"):
            history.append({"event": "placed", "idea_id": idea_id, "at": now_iso()})
            await self._archive.put_niche(
                session_id, niche, {"idea_id": idea_id, "pending_idea_id": None, "history": history}
            )
            return ToolResult.success(
                provenance("heuristic", seed=session.seed, warnings=warnings, degraded=degraded),
                {**base, "placed": True, "reason": "empty niche"},
            )
        incumbent = state["idea_id"]
        matchup = Matchup(
            id=new_id("m"),
            session_id=session_id,
            idea_a=incumbent,
            idea_b=idea_id,
            criteria=list(DEFAULT_CRITERIA),
            created_at=now_iso(),
        )
        await self._archive.save_matchups([matchup])
        await self._archive.put_niche(
            session_id,
            niche,
            {
                "idea_id": incumbent,
                "pending_idea_id": idea_id,
                "matchup_id": matchup.id,
                "history": history,
            },
        )
        texts = {i.id: i.text for i in await self._archive.list_ideas(session_id)}
        orders = []
        for order in ("AB", "BA"):
            shown = judge_matchup_inputs(matchup, order, texts)
            orders.append(
                judge_order(
                    session_id=session_id,
                    matchup_id=matchup.id,
                    order=order,
                    first=shown["first"],
                    second=shown["second"],
                    criteria=list(DEFAULT_CRITERIA),
                    record_call=f'cgu_evolve(action="resolve", session_id="{session_id}", niche="{niche}")',
                    submit_with={
                        "tool": "cgu_evolve",
                        "action": "resolve",
                        "args_template": {
                            "session_id": session_id,
                            "niche": niche,
                            "verdicts": [
                                {
                                    "matchup_id": matchup.id,
                                    "order": order,
                                    "winner": "<idea_id or tie>",
                                    "judge_model": "<model name>",
                                }
                            ],
                        },
                    },
                )
            )
        return ToolResult.success(
            provenance("passthrough", seed=session.seed, warnings=warnings, degraded=degraded),
            {
                **base,
                "placed": False,
                "reason": "niche occupied; judge AB and BA, then resolve",
                "incumbent_id": incumbent,
            },
            work_orders=orders,
        )

    async def resolve(
        self, session_id: str, niche: str | None, verdicts: list[Verdict] | None
    ) -> ToolResult:
        session = await require_session(self._archive, session_id)
        niches = await self._archive.get_niches(session_id)
        state = niches.get(niche or "")
        if not niche or not state or not state.get("pending_idea_id"):
            raise CGUError(
                "not_found",
                f"niche {niche!r} has no pending challenger",
                'Submit a child with cgu_evolve(action="submit") first.',
            )
        matchup_id = state["matchup_id"]
        mine = [v for v in (verdicts or []) if v.matchup_id == matchup_id]
        if len(mine) != len(verdicts or []):
            raise CGUError("invalid_input", f"all verdicts must be for matchup {matchup_id}")
        await self._judge.store_verdicts(session_id, mine)
        stored = [
            v for v in await self._archive.list_verdicts(session_id) if v.matchup_id == matchup_id
        ]
        if {v.order for v in stored} != {"AB", "BA"}:
            missing = sorted({"AB", "BA"} - {v.order for v in stored})
            return ToolResult.success(
                provenance(
                    "heuristic",
                    seed=session.seed,
                    warnings=[f"waiting for the {', '.join(missing)} verdict before resolving"],
                ),
                {
                    "niche": niche,
                    "outcome": "pending",
                    "missing_orders": missing,
                    "recorded": len(stored),
                },
            )
        challenger, incumbent = state["pending_idea_id"], state["idea_id"]
        challenger_wins = sum(1 for v in stored if v.winner == challenger)
        incumbent_wins = sum(1 for v in stored if v.winner == incumbent)
        ties = sum(1 for v in stored if v.winner == TIE)
        replaced = challenger_wins > incumbent_wins
        history = list(state.get("history", []))
        if replaced:
            history.append(
                {"event": "replaced", "idea_id": challenger, "replaced": incumbent, "at": now_iso()}
            )
        else:
            history.append({"event": "rejected", "idea_id": challenger, "at": now_iso()})
        await self._archive.put_niche(
            session_id,
            niche,
            {
                "idea_id": challenger if replaced else incumbent,
                "pending_idea_id": None,
                "history": history,
            },
        )
        ideas = {i.id: i for i in await self._archive.list_ideas(session_id)}
        await self._set_status(ideas.get(challenger), "placed" if replaced else "rejected")
        await self._set_status(ideas.get(incumbent), "replaced" if replaced else None)
        return ToolResult.success(
            provenance("heuristic", seed=session.seed),
            {
                "niche": niche,
                "outcome": "replaced" if replaced else "kept",
                "occupant_id": challenger if replaced else incumbent,
                "challenger_wins": challenger_wins,
                "incumbent_wins": incumbent_wins,
                "ties": ties,
                "rule": "the challenger replaces the incumbent only with strictly more wins",
            },
        )

    async def _set_status(self, idea: Idea | None, status: str | None) -> None:
        if idea is None or status is None:
            return
        idea.meta = {**idea.meta, "evolve_status": status}
        await self._archive.update_idea(idea)
