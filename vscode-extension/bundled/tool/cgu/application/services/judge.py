"""Judge: position-swapped pairwise work orders, recorded verdicts, honest ranking."""

from __future__ import annotations

from pydantic import BaseModel, Field

from cgu.application.ports import ArchivePort
from cgu.application.services._common import (
    new_id,
    now_iso,
    provenance,
    require_session,
)
from cgu.application.services.instructions import judge_order
from cgu.domain.common import CGUError, ToolResult
from cgu.domain.judge import (
    DEFAULT_CRITERIA,
    TIE,
    Matchup,
    Verdict,
    generate_pairs,
    judge_matchup_inputs,
)
from cgu.domain.judge import (
    rank as rank_verdicts,
)

MAX_VERDICTS = 200


class Gate(BaseModel):
    feasibility_min: float | None = Field(
        default=None,
        ge=0,
        le=1,
        description="Non-compensatory floor on the feasibility win rate (adds the criterion)",
    )


class JudgeService:
    def __init__(self, archive: ArchivePort) -> None:
        self._archive = archive

    async def plan(
        self,
        session_id: str,
        idea_ids: list[str] | None,
        rounds: int | None,
        criteria: list[str] | None,
        gate: Gate | None,
    ) -> ToolResult:
        session = await require_session(self._archive, session_id)
        if not idea_ids or len(set(idea_ids)) < 2:
            raise CGUError("invalid_input", "idea_ids needs at least two distinct ideas")
        ideas = {i.id: i for i in await self._archive.list_ideas(session_id)}
        missing = [i for i in idea_ids if i not in ideas]
        if missing:
            raise CGUError("not_found", f"ideas not found: {missing}")
        if rounds is not None and not 1 <= rounds <= 20:
            raise CGUError("invalid_input", "rounds must be between 1 and 20")
        names = list(dict.fromkeys(criteria or DEFAULT_CRITERIA))
        floor = gate.feasibility_min if gate else None
        if floor is not None and "feasibility" not in names:
            names.append("feasibility")
        pairs = generate_pairs(list(idea_ids), rounds, session.seed)
        matchups = [
            Matchup(
                id=new_id("m"),
                session_id=session_id,
                idea_a=a,
                idea_b=b,
                criteria=names,
                feasibility_min=str(floor) if floor is not None else None,
                created_at=now_iso(),
            )
            for a, b in pairs
        ]
        await self._archive.save_matchups(matchups)
        texts = {i: ideas[i].text for i in idea_ids}
        record_call = f'cgu_judge(action="record", session_id="{session_id}")'
        orders = []
        for matchup in matchups:
            for order in ("AB", "BA"):
                shown = judge_matchup_inputs(matchup, order, texts)
                orders.append(
                    judge_order(
                        session_id=session_id,
                        matchup_id=matchup.id,
                        order=order,
                        first=shown["first"],
                        second=shown["second"],
                        criteria=names,
                        record_call=record_call,
                        submit_with={
                            "tool": "cgu_judge",
                            "action": "record",
                            "args_template": {
                                "session_id": session_id,
                                "verdicts": [
                                    {
                                        "matchup_id": matchup.id,
                                        "order": order,
                                        "winner": "<idea_id or tie>",
                                        "criteria_winners": dict.fromkeys(
                                            names, "<idea_id or tie>"
                                        ),
                                        "judge_model": "<model name>",
                                        "reason": "<two sentences>",
                                    }
                                ],
                            },
                        },
                    )
                )
        warnings = [
            "Use at least two different judge model families and keep the AB/BA pair of one "
            "matchup with the same judge; a single family prefers its own writing."
        ]
        return ToolResult.success(
            provenance("passthrough", seed=session.seed, warnings=warnings),
            {
                "matchups": [
                    {"matchup_id": m.id, "idea_a": m.idea_a, "idea_b": m.idea_b} for m in matchups
                ],
                "criteria": names,
                "gate": (
                    f"feasibility win rate >= {floor} (non-compensatory, applied by action=rank)"
                    if floor is not None
                    else None
                ),
                "work_order_count": len(orders),
            },
            work_orders=orders,
        )

    async def store_verdicts(self, session_id: str, verdicts: list[Verdict]) -> None:
        if not verdicts:
            raise CGUError("invalid_input", "verdicts is required")
        if len(verdicts) > MAX_VERDICTS:
            raise CGUError("invalid_input", f"at most {MAX_VERDICTS} verdicts per call")
        matchups = {m.id: m for m in await self._archive.list_matchups(session_id)}
        seen = {
            (v.matchup_id, v.order, v.judge_model or "unknown")
            for v in await self._archive.list_verdicts(session_id)
        }
        for position, verdict in enumerate(verdicts):
            label = f"verdicts[{position}]"
            matchup = matchups.get(verdict.matchup_id)
            if matchup is None:
                raise CGUError(
                    "not_found",
                    f"{label}.matchup_id {verdict.matchup_id!r} is not a planned matchup",
                    'Plan matchups with cgu_judge(action="plan").',
                )
            allowed = {matchup.idea_a, matchup.idea_b, TIE}
            if verdict.winner not in allowed:
                raise CGUError(
                    "invalid_input",
                    f"{label}.winner must be one of {sorted(allowed)}",
                    "Answer with an idea_id of the matchup, or tie.",
                )
            for criterion, winner in verdict.criteria_winners.items():
                if winner not in allowed:
                    raise CGUError(
                        "invalid_input",
                        f"{label}.criteria_winners[{criterion!r}] must be one of {sorted(allowed)}",
                    )
            key = (verdict.matchup_id, verdict.order, verdict.judge_model or "unknown")
            if key in seen:
                raise CGUError(
                    "conflict",
                    f"{label} repeats an already recorded (matchup, order, judge_model): {key}",
                    "Each judge records each order of a matchup once.",
                )
            seen.add(key)
        await self._archive.save_verdicts(session_id, verdicts)

    async def record(self, session_id: str, verdicts: list[Verdict] | None) -> ToolResult:
        session = await require_session(self._archive, session_id)
        await self.store_verdicts(session_id, verdicts or [])
        matchups = await self._archive.list_matchups(session_id)
        stored = await self._archive.list_verdicts(session_id)
        done = {(v.matchup_id, v.order) for v in stored}
        pending = sum(1 for m in matchups for o in ("AB", "BA") if (m.id, o) not in done)
        return ToolResult.success(
            provenance("archive", seed=session.seed),
            {
                "recorded": len(verdicts or []),
                "total_verdicts": len(stored),
                "pending_orders": pending,
            },
        )

    async def rank(self, session_id: str) -> ToolResult:
        session = await require_session(self._archive, session_id)
        matchups = await self._archive.list_matchups(session_id)
        verdicts = await self._archive.list_verdicts(session_id)
        if not verdicts:
            return ToolResult.success(
                provenance(
                    "heuristic",
                    seed=session.seed,
                    warnings=["no verdicts recorded yet; plan and record before ranking"],
                ),
                {"standings": [], "pareto_front": None},
            )
        report = rank_verdicts(matchups, verdicts)
        data = report.model_dump()
        warnings = data.pop("warnings")
        return ToolResult.success(
            provenance("heuristic", seed=session.seed, warnings=warnings),
            data,
        )
