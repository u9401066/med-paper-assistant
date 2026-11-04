"""cgu_frame: frames, the 11 operators, lineage-preserving commits, consent and doubt."""

from __future__ import annotations

from typing import Annotated, Any, Literal

from mcp.server.mcpserver import (
    AcceptedElicitation,
    CancelledElicitation,
    DeclinedElicitation,
    Elicit,
    ElicitationResult,
    MCPServer,
    Resolve,
)
from mcp_types import ToolAnnotations
from pydantic import BaseModel, Field

from cgu.domain.common import CGUError, ToolResult
from cgu.domain.doubt import AssumptionEstimate, DoubtBudget, DoubtSignals
from cgu.domain.frame import (
    Assumption,
    Concept,
    Consent,
    ConsentRecord,
    Constraint,
    Criterion,
    FrameDraft,
    Hinge,
    Metaphor,
    Stakeholder,
)
from cgu.interfaces.mcp.deps import Deps
from cgu.interfaces.mcp.tools._common import Ctx, deps_of, guarded

DESCRIPTION = (
    "[heuristic] 框架（Frame）是點子的產生情境：goal、assumption（core｜belt）、concept、metaphor、"
    "criterion、stakeholder、constraint（hard｜soft｜self_imposed）、unit、hinge。"
    "action=create（必填 problem）、get（含譜系）、operators（11 張算子卡）、"
    "operate（回傳 work_order，要求你產生 FrameDraft 子框架）、"
    "commit（驗證並寫入譜系，回傳 disclosure 說明改了什麼）、"
    "doubt（依你以 0–1 估計的 load_bearing／uncertainty／decision_impact／irreversibility，"
    "計算懷疑優先度）。改寫 goal、stakeholder、criterion 屬受限元素，須使用者同意："
    "伺服器會先向用戶端徵求同意；用戶端不支援時回傳 consent_required，請詢問使用者後以 "
    "consent={granted: true, note} 重送。未同意不會寫入。"
    "量測：框架差異與懷疑優先度（呼叫端估計值的乘積，未校準啟發式）；不量測框架好壞。"
)


class ConsentForm(BaseModel):
    granted: bool = Field(description="是否同意改寫上述受限元素")
    note: str = Field(default="", description="備註（可留空）")


class NotAsked:
    """The resolver had no consent to ask for (or the client cannot be asked)."""


NOT_ASKED = NotAsked()


async def consent_resolver(
    ctx: Ctx,
    action: str,
    session_id: str,
    frame_id: str | None,
    operator: str | None,
    child: FrameDraft | None,
    consent: Consent | None,
) -> Elicit[ConsentForm] | NotAsked:
    """Ask the client only when a commit would rewrite restricted elements and none was given."""
    if action != "commit" or child is None or not frame_id or not operator or consent is not None:
        return NOT_ASKED
    capabilities = ctx.client_capabilities
    elicitation = capabilities.elicitation if capabilities is not None else None
    if elicitation is None or (elicitation.form is None and elicitation.url is not None):
        return NOT_ASKED
    frames = deps_of(ctx).services.frame
    restricted = await frames.preview_restricted(session_id, frame_id, operator, child)
    if not restricted:
        return NOT_ASKED
    return Elicit(
        f"這個改寫會動到受限元素（{', '.join(restricted)}）。算子：{operator}。"
        f"理由：{child.why}。是否同意寫入？",
        ConsentForm,
    )


def _consent_record(
    asked: ElicitationResult[ConsentForm], given: Consent | None
) -> ConsentRecord | None:
    if isinstance(asked, AcceptedElicitation) and isinstance(asked.data, ConsentForm):
        return ConsentRecord(granted=asked.data.granted, note=asked.data.note, via="elicitation")
    if isinstance(asked, DeclinedElicitation | CancelledElicitation):
        return ConsentRecord(
            granted=False, note=f"user {asked.action}ed the elicitation", via="elicitation"
        )
    if given is not None:
        return ConsentRecord(granted=given.granted, note=given.note, via="caller")
    return None


def _items(values: list[Any] | None, build: Any) -> list[Any]:
    return [build(v) if isinstance(v, str) else v for v in values or []]


def register(server: MCPServer[Deps]) -> None:
    @server.tool(
        name="cgu_frame",
        title="CGU frame",
        description=DESCRIPTION,
        annotations=ToolAnnotations(
            title="CGU frame",
            read_only_hint=False,
            destructive_hint=False,
            idempotent_hint=False,
            open_world_hint=False,
        ),
    )
    async def cgu_frame(
        action: Annotated[
            Literal["create", "get", "operators", "operate", "commit", "doubt"],
            Field(description="動作"),
        ],
        session_id: Annotated[str, Field(description="session id")],
        ctx: Ctx,
        consent_decision: Annotated[ElicitationResult[ConsentForm], Resolve(consent_resolver)],
        frame_id: Annotated[
            str | None, Field(description="get／operate／commit（父框架）／doubt 必填")
        ] = None,
        problem: Annotated[str | None, Field(description="create 必填：問題陳述")] = None,
        goal: Annotated[str | None, Field(description="create：目標（受限元素）")] = None,
        unit: Annotated[str | None, Field(description="create：分析單位")] = None,
        stakeholders: Annotated[
            list[str | Stakeholder] | None, Field(description="create：利害關係人（受限元素）")
        ] = None,
        concepts: Annotated[list[str | Concept] | None, Field(description="create：概念")] = None,
        assumptions: Annotated[
            list[str | Assumption] | None, Field(description="create：假設（core｜belt）")
        ] = None,
        constraints: Annotated[
            list[str | Constraint] | None, Field(description="create：限制")
        ] = None,
        metaphors: Annotated[list[str] | None, Field(description="create：隱喻")] = None,
        criteria: Annotated[
            list[str | Criterion] | None, Field(description="create：評估準則（受限元素）")
        ] = None,
        hinges: Annotated[
            list[str] | None, Field(description="create：這次探究不質疑的鉸鏈前提")
        ] = None,
        operator: Annotated[str | None, Field(description="operate／commit：算子名稱")] = None,
        target: Annotated[
            str | None, Field(description="operate 必填：元素 id（如 a1）或種類（如 assumption）")
        ] = None,
        params: Annotated[dict[str, Any] | None, Field(description="operate 的額外參數")] = None,
        child: Annotated[
            FrameDraft | None, Field(description="commit 必填：子框架 FrameDraft")
        ] = None,
        consent: Annotated[
            Consent | None, Field(description="commit：使用者已同意受限元素改寫時的紀錄")
        ] = None,
        signals: Annotated[DoubtSignals | None, Field(description="doubt：觸發訊號")] = None,
        estimates: Annotated[
            dict[str, AssumptionEstimate] | None,
            Field(description="doubt：{assumption_id: 四因子的 0–1 估計}"),
        ] = None,
        budget: Annotated[DoubtBudget | None, Field(description="doubt：提問預算")] = None,
    ) -> ToolResult:
        service = deps_of(ctx).services.frame

        async def run() -> ToolResult:
            if action == "operators":
                return await service.operators()
            if action == "create":
                return await service.create(
                    session_id,
                    problem,
                    goal=goal,
                    unit=unit,
                    stakeholders=_items(stakeholders, lambda v: Stakeholder(who=v)),
                    concepts=_items(concepts, lambda v: Concept(term=v)),
                    assumptions=_items(assumptions, lambda v: Assumption(text=v)),
                    constraints=_items(constraints, lambda v: Constraint(text=v)),
                    metaphors=[Metaphor(text=m) for m in metaphors or []],
                    criteria=_items(criteria, lambda v: Criterion(text=v)),
                    hinges=[Hinge(text=h) for h in hinges or []],
                )
            if not frame_id:
                raise CGUError("invalid_input", f"frame_id is required for action={action}")
            if action == "get":
                return await service.get(session_id, frame_id)
            if action == "operate":
                if not operator:
                    raise CGUError("invalid_input", "operator is required for action=operate")
                return await service.operate(session_id, frame_id, operator, target, params)
            if action == "commit":
                if not operator:
                    raise CGUError("invalid_input", "operator is required for action=commit")
                record = _consent_record(consent_decision, consent)
                return await service.commit(session_id, frame_id, operator, child, record)
            return await service.doubt(session_id, frame_id, signals, estimates, budget)

        return await guarded(run())
