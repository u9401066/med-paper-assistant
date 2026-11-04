"""Frames: create, inspect, operate (work order), commit (lineage, consent) and doubt."""

from __future__ import annotations

from typing import Any

from cgu.application.ports import ArchivePort
from cgu.application.services._common import (
    new_id,
    now_iso,
    provenance,
    reject_floats,
    require_frame,
    require_session,
)
from cgu.domain.common import CGUError, ToolResult, WorkOrder
from cgu.domain.doubt import AssumptionEstimate, DoubtBudget, DoubtSignals, evaluate_doubt
from cgu.domain.frame import (
    ELEMENT_KINDS,
    LIST_FIELDS,
    RESTRICTED_KINDS,
    Assumption,
    Concept,
    ConsentRecord,
    Constraint,
    Criterion,
    Disclosure,
    Frame,
    FrameDraft,
    Hinge,
    Metaphor,
    Stakeholder,
    build_frame,
    kind_of_id,
)
from cgu.domain.operators import (
    OPERATORS,
    OperatorCard,
    get_operator,
    plan_commit,
    render_instructions,
)

TYPICAL_LIMIT = 12


def card_view(card: OperatorCard) -> dict[str, Any]:
    return {
        "name": card.name,
        "source": card.source,
        "summary": card.summary,
        "targets": card.targets,
        "default_target": card.default_target,
        "restricted": card.restricted,
        "guardrails": card.guardrails,
        "required_checks": card.required_checks,
        "example_domain": card.example_domain,
    }


def resolve_target(frame: Frame, target: str, card: OperatorCard) -> tuple[str, str | None]:
    plural = {field: kind for kind, field in LIST_FIELDS.items()}
    if target in ELEMENT_KINDS:
        kind, element_id = target, None
    elif target in plural:
        kind, element_id = plural[target], None
    elif target in frame.element_ids():
        resolved = kind_of_id(target)
        if resolved is None:
            raise CGUError("invalid_input", f"cannot tell the kind of element {target!r}")
        kind, element_id = resolved, target
    else:
        raise CGUError(
            "not_found",
            f"target {target!r} is neither an element kind nor an element id of this frame",
            "Use an id such as a1, or a kind: " + ", ".join(ELEMENT_KINDS),
        )
    if kind not in card.targets:
        raise CGUError(
            "invalid_input",
            f"{card.name} works on {card.targets}, not {kind!r}",
            "Pick a target of one of those kinds.",
        )
    return kind, element_id


class FrameService:
    def __init__(self, archive: ArchivePort) -> None:
        self._archive = archive

    async def create(
        self,
        session_id: str,
        problem: str | None,
        *,
        goal: str | None = None,
        unit: str | None = None,
        stakeholders: list[Stakeholder] | None = None,
        concepts: list[Concept] | None = None,
        assumptions: list[Assumption] | None = None,
        constraints: list[Constraint] | None = None,
        metaphors: list[Metaphor] | None = None,
        criteria: list[Criterion] | None = None,
        hinges: list[Hinge] | None = None,
    ) -> ToolResult:
        session = await require_session(self._archive, session_id)
        if not problem or not problem.strip():
            raise CGUError("invalid_input", "problem is required for action=create")
        frame = build_frame(
            frame_id=new_id("f"),
            session_id=session_id,
            problem=problem.strip(),
            created_at=now_iso(),
            goal=goal,
            unit=unit,
            elements={
                "stakeholder": stakeholders or [],
                "concept": concepts or [],
                "assumption": assumptions or [],
                "constraint": constraints or [],
                "metaphor": metaphors or [],
                "criterion": criteria or [],
                "hinge": hinges or [],
            },
        )
        await self._archive.save_frame(frame)
        ids = {
            kind: [item.id for item in frame.items(kind)]
            for kind in LIST_FIELDS
            if frame.items(kind)
        }
        if frame.goal:
            ids["goal"] = ["goal"]
        if frame.unit:
            ids["unit"] = ["unit"]
        return ToolResult.success(
            provenance("archive", seed=session.seed),
            {"frame_id": frame.frame_id, "element_ids": ids, "frame": frame.view()},
        )

    async def get(self, session_id: str, frame_id: str) -> ToolResult:
        await require_session(self._archive, session_id)
        frame = await require_frame(self._archive, session_id, frame_id)
        frames = {f.frame_id: f for f in await self._archive.list_frames(session_id)}
        chain: list[Frame] = []
        cursor: Frame | None = frame
        while cursor is not None:
            chain.append(cursor)
            cursor = frames.get(cursor.parent_id) if cursor.parent_id else None
        lineage = [
            {
                "frame_id": f.frame_id,
                "parent_id": f.parent_id,
                "operator": f.operator,
                "why": f.disclosure.why if f.disclosure else None,
                "changed": [c.model_dump() for c in f.disclosure.changed] if f.disclosure else [],
            }
            for f in reversed(chain)
        ]
        return ToolResult.success(
            provenance("archive"),
            {
                "frame": frame.view(),
                "disclosure": frame.disclosure.model_dump() if frame.disclosure else None,
                "lineage": lineage,
                "children": [f.frame_id for f in frames.values() if f.parent_id == frame_id],
            },
        )

    async def operators(self) -> ToolResult:
        return ToolResult.success(
            provenance("passthrough"),
            {
                "operators": [card_view(card) for card in OPERATORS.values()],
                "restricted_kinds": sorted(RESTRICTED_KINDS),
            },
        )

    async def operate(
        self,
        session_id: str,
        frame_id: str,
        operator: str,
        target: str | None,
        params: dict[str, Any] | None,
    ) -> ToolResult:
        session = await require_session(self._archive, session_id)
        frame = await require_frame(self._archive, session_id, frame_id)
        card = get_operator(operator)
        reject_floats(params or {}, "params")
        warnings: list[str] = []
        if not target and card.default_target:
            target = card.default_target
            warnings.append(f"target omitted; defaulted to {target!r} for {operator}")
        if not target:
            raise CGUError(
                "invalid_input",
                "target is required for action=operate",
                f"Give an element id (for example a1) or a kind from {card.targets}.",
            )
        kind, element_id = resolve_target(frame, target, card)
        requires_consent = kind in RESTRICTED_KINDS
        inputs: dict[str, Any] = {
            "parent_frame": frame.view(),
            "operator": operator,
            "target": {"kind": kind, "id": element_id},
            "params": params or {},
            "requires_consent": requires_consent,
        }
        if operator == "explicate":
            typical = await self._archive.list_ideas(session_id, "typical")
            inputs["typical_ideas"] = [i.text for i in typical[:TYPICAL_LIMIT]]
            if not typical:
                warnings.append(
                    "no typical ideas in this session; run cgu_diverge(action='typical_set') first"
                )
        order = WorkOrder(
            id=new_id("wo"),
            kind="frame_operate",
            instructions=render_instructions(
                card,
                problem=frame.problem,
                target=f"{kind}" + (f" {element_id}" if element_id else ""),
                params=params,
            ),
            inputs=inputs,
            output_schema=FrameDraft.model_json_schema(),
            submit_with={
                "tool": "cgu_frame",
                "action": "commit",
                "args_template": {
                    "session_id": session_id,
                    "frame_id": frame_id,
                    "operator": operator,
                    "child": "<FrameDraft>",
                    **({"consent": {"granted": True, "note": ""}} if requires_consent else {}),
                },
            },
            independence="same_context_ok",
        )
        return ToolResult.success(
            provenance("passthrough", seed=session.seed, warnings=warnings),
            {
                "operator": operator,
                "target": {"kind": kind, "id": element_id},
                "requires_consent": requires_consent,
                "restricted_kinds": sorted(RESTRICTED_KINDS),
            },
            work_order=order,
        )

    async def preview_restricted(
        self, session_id: str, frame_id: str, operator: str, child: FrameDraft
    ) -> list[str] | None:
        """Restricted kinds a commit would touch, or None when the commit is not valid yet."""
        try:
            parent = await require_frame(self._archive, session_id, frame_id)
            plan = plan_commit(parent, operator, child, frame_id="preview", created_at="")
        except CGUError:
            return None
        return plan.restricted

    async def commit(
        self,
        session_id: str,
        frame_id: str,
        operator: str,
        child: FrameDraft | None,
        consent: ConsentRecord | None,
    ) -> ToolResult:
        session = await require_session(self._archive, session_id)
        parent = await require_frame(self._archive, session_id, frame_id)
        if child is None:
            raise CGUError(
                "invalid_input",
                "child (a FrameDraft) is required for action=commit",
                'Get the shape from cgu_frame(action="operate").',
            )
        plan = plan_commit(parent, operator, child, frame_id=new_id("f"), created_at=now_iso())
        if plan.restricted and (consent is None or not consent.granted):
            declined = consent is not None
            return ToolResult.failure(
                "consent_required",
                (
                    "the user declined the rewrite of "
                    if declined
                    else "rewriting restricted elements needs the user's consent: "
                )
                + ", ".join(plan.restricted),
                "Show the changes to the user, ask, and resend with consent={granted: true, note}. "
                "Nothing was written.",
                provenance=provenance("archive", seed=session.seed),
                data={
                    "requires_consent": True,
                    "restricted_kinds": plan.restricted,
                    "changes": [c.model_dump() for c in plan.changes],
                    "declined": declined,
                },
            )
        child_frame = plan.child
        child_frame.disclosure = Disclosure(
            changed=plan.changes,
            why=child.why,
            operator=operator,
            source=plan.card.source,
            restricted_kinds=plan.restricted,
            consent=consent if plan.restricted else None,
            checks=child.checks,
        )
        await self._archive.save_frame(child_frame)
        return ToolResult.success(
            provenance("archive", seed=session.seed),
            {
                "child_frame_id": child_frame.frame_id,
                "disclosure": child_frame.disclosure.model_dump(),
                "frame": child_frame.view(),
                "next_steps": (
                    "A frame without a concrete idea does not count: submit at least one idea made "
                    f'inside it with cgu_ideas(action="add", frame_id="{child_frame.frame_id}", '
                    f'operator="{operator}").'
                ),
            },
        )

    async def doubt(
        self,
        session_id: str,
        frame_id: str,
        signals: DoubtSignals | None,
        estimates: dict[str, AssumptionEstimate] | None,
        budget: DoubtBudget | None,
    ) -> ToolResult:
        session = await require_session(self._archive, session_id)
        frame = await require_frame(self._archive, session_id, frame_id)
        assumptions = {a.id: a.text for a in frame.assumptions if a.id}
        given = estimates or {}
        unknown = sorted(set(given) - set(assumptions))
        if unknown:
            raise CGUError(
                "invalid_input",
                f"estimates refer to unknown assumption ids: {unknown}",
                "Known ids: " + ", ".join(sorted(assumptions)) if assumptions else None,
            )
        report = evaluate_doubt(
            assumptions, signals or DoubtSignals(), given, budget or DoubtBudget()
        )
        return ToolResult.success(
            provenance("heuristic", seed=session.seed),
            report.model_dump(),
        )
