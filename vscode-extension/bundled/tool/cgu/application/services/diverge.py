"""Diverge: work orders that make a model leave its typical answers, or run them locally."""

from __future__ import annotations

import json
from typing import Any

from cgu.application.ports import ArchivePort, LLMPort, LLMUnavailableError
from cgu.application.services._common import (
    frame_summary,
    provenance,
    require_frame,
    require_session,
)
from cgu.application.services.ideas import IdeaInput, IdeaService
from cgu.application.services.instructions import (
    anti_typical_order,
    collide_order,
    fanout_order,
    typical_set_order,
)
from cgu.domain.common import CGUError, Session, ToolResult, WorkOrder
from cgu.domain.idea import IdeaKind
from cgu.domain.operators import OPERATOR_NAMES, OPERATORS, get_operator

AVOID_LIMIT = 20
VARY_DIMENSIONS = ("prompt", "material", "operator", "model")
PROMPT_VARIANTS = (
    "從「最小可行、明天就能做」的做法出發",
    "從「最大的限制條件」出發，把限制當成設計材料",
    "從「最不被重視的利害關係人」出發",
    "從「把問題反過來問」出發（如何讓問題更糟？再反轉）",
    "從「現有資源的重新組合」出發，不新增任何東西",
    "從「另一個領域的做法」出發",
)


def _bounded(value: int, low: int, high: int, name: str) -> int:
    if not low <= value <= high:
        raise CGUError("invalid_input", f"{name} must be between {low} and {high}")
    return value


def _parse_ideas(raw: str) -> list[str]:
    try:
        parsed = json.loads(raw)
    except ValueError:
        return []
    if isinstance(parsed, dict):
        parsed = parsed.get("ideas", [])
    if not isinstance(parsed, list):
        return []
    return [text.strip() for text in parsed if isinstance(text, str) and text.strip()]


class DivergeService:
    def __init__(
        self,
        archive: ArchivePort,
        ideas: IdeaService,
        llm: LLMPort | None,
        *,
        execute_locally: bool,
    ) -> None:
        self._archive = archive
        self._ideas = ideas
        self._llm = llm
        self._execute = execute_locally and llm is not None

    async def _frame(self, session_id: str, frame_id: str | None) -> tuple[str | None, str | None]:
        if not frame_id:
            return None, None
        frame = await require_frame(self._archive, session_id, frame_id)
        return frame.problem, frame_summary(frame)

    async def _run_locally(
        self,
        session: Session,
        order: WorkOrder,
        kind: IdeaKind,
        count: int,
        *,
        frame_id: str | None = None,
        seed: int | None = None,
        meta: dict[str, Any] | None = None,
    ) -> list[str] | None:
        """Ideas written by the local model, or None when it failed (caller returns the order)."""
        assert self._llm is not None
        prompt = (
            f"{order.instructions}\n\n輸入資料：{json.dumps(order.inputs, ensure_ascii=False)}\n\n"
            f'輸出要求：只輸出 JSON 物件 {{"ideas": ["..."]}}，共 {count} 個字串，不要其他文字。'
        )
        try:
            raw = await self._llm.complete(prompt, seed=seed if seed is not None else session.seed)
        except LLMUnavailableError:
            return None
        texts = _parse_ideas(raw)[:count]
        if not texts:
            return None
        result = await self._ideas.add(
            session.id,
            [
                IdeaInput(
                    text=t,
                    kind=kind,
                    frame_id=frame_id,
                    meta={"engine": "ollama", "model": self._llm.model, **(meta or {})},
                )
                for t in texts
            ],
        )
        return [view["idea_id"] for view in result.data["ideas"]]

    def _executed(self, session: Session, order: WorkOrder, idea_ids: list[str]) -> ToolResult:
        assert self._llm is not None
        return ToolResult.success(
            provenance("ollama", seed=session.seed, model=self._llm.model),
            {"executed": True, "work_order_kind": order.kind, "idea_ids": idea_ids},
        )

    def _fallback(self, session: Session, *orders: WorkOrder) -> ToolResult:
        warning = "local model failed or returned no usable ideas; execute the work order yourself"
        return ToolResult.success(
            provenance("ollama", seed=session.seed, degraded=True, warnings=[warning]),
            {"executed": False},
            work_order=orders[0] if len(orders) == 1 else None,
            work_orders=list(orders) if len(orders) > 1 else [],
        )

    async def typical_set(self, session_id: str, frame_id: str | None, k: int) -> ToolResult:
        session = await require_session(self._archive, session_id)
        _bounded(k, 1, 30, "k")
        problem, summary = await self._frame(session_id, frame_id)
        order = typical_set_order(
            session_id=session_id, problem=problem or session.topic, k=k, frame_summary=summary
        )
        if self._execute:
            ids = await self._run_locally(session, order, "typical", k, frame_id=frame_id)
            return self._executed(session, order, ids) if ids else self._fallback(session, order)
        return ToolResult.success(
            provenance("passthrough", seed=session.seed),
            {"requires_execution_by_caller": True},
            work_order=order,
        )

    async def anti_typical(
        self, session_id: str, frame_id: str | None, operators: list[str] | None, n: int
    ) -> ToolResult:
        session = await require_session(self._archive, session_id)
        _bounded(n, 1, 20, "n")
        problem, summary = await self._frame(session_id, frame_id)
        cards = [get_operator(name) for name in (operators or [])]
        typical = await self._archive.list_ideas(session_id, "typical")
        avoid = [i.text for i in typical[:AVOID_LIMIT]]
        warnings = []
        if not avoid:
            warnings.append(
                "no typical ideas in this session; run action=typical_set first, "
                "otherwise nothing can be avoided"
            )
        order = anti_typical_order(
            session_id=session_id,
            problem=problem or session.topic,
            n=n,
            avoid=avoid,
            operators=[{"name": c.name, "summary": c.summary} for c in cards],
            frame_summary=summary,
            frame_id=frame_id,
        )
        if self._execute and avoid:
            ids = await self._run_locally(session, order, "candidate", n, frame_id=frame_id)
            return self._executed(session, order, ids) if ids else self._fallback(session, order)
        return ToolResult.success(
            provenance("passthrough", seed=session.seed, warnings=warnings),
            {"avoid_count": len(avoid), "requires_execution_by_caller": True},
            work_order=order,
        )

    async def fanout(
        self, session_id: str, n: int, vary: list[str] | None, frame_id: str | None
    ) -> ToolResult:
        session = await require_session(self._archive, session_id)
        _bounded(n, 1, 8, "n")
        dimensions = vary or ["prompt"]
        unknown = [d for d in dimensions if d not in VARY_DIMENSIONS]
        if unknown:
            raise CGUError(
                "invalid_input",
                f"unknown vary values {unknown}",
                f"Use a subset of {VARY_DIMENSIONS}",
            )
        problem, summary = await self._frame(session_id, frame_id)
        problem = problem or session.topic
        fragments = await self._archive.list_fragments(session_id)
        warnings: list[str] = []
        if "material" in dimensions and not fragments:
            warnings.append(
                "vary includes material but the session has none; that dimension is skipped"
            )
        offset = session.seed % len(OPERATOR_NAMES)
        orders: list[WorkOrder] = []
        for i in range(n):
            parts: list[str] = []
            extra: dict[str, Any] = {}
            materials: list[dict[str, str]] = []
            if "prompt" in dimensions:
                parts.append(PROMPT_VARIANTS[(session.seed + i) % len(PROMPT_VARIANTS)])
            if "material" in dimensions and fragments:
                fragment = fragments[i % len(fragments)]
                parts.append(f"以素材 {fragment.id} 為起點（內容見 inputs.materials）")
                materials.append({"id": fragment.id, "fenced_text": fragment.fenced_text})
            if "operator" in dimensions:
                card = OPERATORS[OPERATOR_NAMES[(offset + i) % len(OPERATOR_NAMES)]]
                parts.append(f"套用算子 {card.name}（{card.summary}）")
                extra["operator"] = card.name
            if "model" in dimensions:
                parts.append(f"請用與其他工單不同家族的模型執行（第 {i + 1} 個模型槽）")
                extra["model_slot"] = i + 1
            if not parts:
                parts.append("自由發想，但不要重複其他工單可能寫出的典型答案")
            if summary:
                extra["frame"] = summary
            orders.append(
                fanout_order(
                    session_id=session_id,
                    problem=problem,
                    index=i + 1,
                    total=n,
                    n_each=3,
                    seed=(session.seed + i + 1) % (2**31),
                    variation="；".join(parts),
                    materials=materials,
                    extra_inputs=extra,
                )
            )
        if self._execute:
            all_ids: list[str] = []
            for i, order in enumerate(orders):
                ids = await self._run_locally(
                    session,
                    order,
                    "candidate",
                    3,
                    frame_id=frame_id,
                    seed=int(order.inputs["seed"]),
                    meta={"fanout": f"{i + 1}/{n}"},
                )
                if ids is None:
                    return self._fallback(session, *orders)
                all_ids.extend(ids)
            return self._executed(session, orders[0], all_ids)
        return ToolResult.success(
            provenance("passthrough", seed=session.seed, warnings=warnings),
            {"count": len(orders), "note": "run each work order in a separate context"},
            work_orders=orders,
        )

    async def _side(self, session_id: str, ref: str) -> tuple[str, bool]:
        text = ref.strip()
        if text.startswith("fr-"):
            for fragment in await self._archive.list_fragments(session_id):
                if fragment.id == text:
                    return fragment.fenced_text, True
        if text.startswith("i-"):
            for idea in await self._archive.list_ideas(session_id):
                if idea.id == text:
                    return idea.text, False
        return text.replace("<", "&lt;").replace(">", "&gt;")[:500], False

    async def collide(self, session_id: str, a: str | None, b: str | None, mode: str) -> ToolResult:
        session = await require_session(self._archive, session_id)
        if not a or not b:
            raise CGUError("invalid_input", "a and b are required for action=collide")
        if mode not in ("analogy", "bridge"):
            raise CGUError("invalid_input", "mode must be analogy or bridge")
        text_a, untrusted_a = await self._side(session_id, a)
        text_b, untrusted_b = await self._side(session_id, b)
        untrusted = [name for name, flag in (("a", untrusted_a), ("b", untrusted_b)) if flag]
        order = collide_order(
            session_id=session_id, a=text_a, b=text_b, mode=mode, untrusted=untrusted
        )
        return ToolResult.success(
            provenance("passthrough", seed=session.seed),
            {"mode": mode, "untrusted_sides": untrusted},
            work_order=order,
        )
