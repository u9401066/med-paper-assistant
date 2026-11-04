"""cgu_question_gate: a question has to earn its depth."""

from __future__ import annotations

from typing import Annotated, Literal

from mcp.server.mcpserver import MCPServer
from mcp_types import ToolAnnotations
from pydantic import Field

from cgu.domain.common import ToolResult
from cgu.domain.doubt import QuestionVerdicts
from cgu.interfaces.mcp.deps import Deps
from cgu.interfaces.mcp.tools._common import Ctx, deps_of, guarded

DESCRIPTION = (
    "[experimental] 提問閘門，防止偽深刻的問題。action=check（回傳 work_order，內含五項判準："
    "決策相關、可操作、承重、非口頭、非典型）、record（存入判決；前四項皆為 true 才通過，"
    "非典型只是加分項，不是否決項）。"
    "量測：判準的是／否判決與是否通過；不量測問題的真實價值，判決品質取決於評審。"
)


def register(server: MCPServer[Deps]) -> None:
    @server.tool(
        name="cgu_question_gate",
        title="CGU question gate",
        description=DESCRIPTION,
        annotations=ToolAnnotations(
            title="CGU question gate",
            read_only_hint=False,
            destructive_hint=False,
            idempotent_hint=False,
            open_world_hint=False,
        ),
    )
    async def cgu_question_gate(
        action: Annotated[Literal["check", "record"], Field(description="動作")],
        session_id: Annotated[str, Field(description="session id")],
        ctx: Ctx,
        question: Annotated[str | None, Field(description="要檢驗的問題")] = None,
        frame_id: Annotated[str | None, Field(description="check：相關框架（選填）")] = None,
        decision_context: Annotated[
            str | None, Field(description="check 必填：這個問題要幫助哪個決策")
        ] = None,
        verdicts: Annotated[QuestionVerdicts | None, Field(description="record 必填")] = None,
        judge_model: Annotated[str | None, Field(description="record：評審模型名稱")] = None,
    ) -> ToolResult:
        service = deps_of(ctx).services.question_gate

        async def run() -> ToolResult:
            if action == "check":
                return await service.check(session_id, question, frame_id, decision_context)
            return await service.record(session_id, question, verdicts, judge_model)

        return await guarded(run())
