"""cgu_judge: position-swapped pairwise judging with honest uncertainty."""

from __future__ import annotations

from typing import Annotated, Literal

from mcp.server.mcpserver import MCPServer
from mcp_types import ToolAnnotations
from pydantic import Field

from cgu.application.services.judge import Gate
from cgu.domain.common import ToolResult
from cgu.domain.judge import Verdict
from cgu.interfaces.mcp.deps import Deps
from cgu.interfaces.mcp.tools._common import Ctx, deps_of, guarded

DESCRIPTION = (
    "[experimental] 成對比較。action=plan（對 idea_ids 產生配對，每一配對各有 AB 與 BA 兩張位置交換的工單；"
    "建議至少使用兩個不同家族的評審模型）、record（存入判決：winner 為該配對的 idea_id 或 tie）、"
    "rank（每個點子的勝負和、win_rate 與 Wilson 95% 區間、AB／BA 一致率、"
    "有分項判決時的 Pareto 前緣；gate.feasibility_min 是非補償式的可行性門檻）。"
    "量測：評審給出的勝率與一致性，依賴評審模型；不量測客觀品質。"
)


def register(server: MCPServer[Deps]) -> None:
    @server.tool(
        name="cgu_judge",
        title="CGU judge",
        description=DESCRIPTION,
        annotations=ToolAnnotations(
            title="CGU judge",
            read_only_hint=False,
            destructive_hint=False,
            idempotent_hint=False,
            open_world_hint=False,
        ),
    )
    async def cgu_judge(
        action: Annotated[Literal["plan", "record", "rank"], Field(description="動作")],
        session_id: Annotated[str, Field(description="session id")],
        ctx: Ctx,
        idea_ids: Annotated[
            list[str] | None, Field(description="plan 必填：至少兩個 idea id")
        ] = None,
        rounds: Annotated[
            int | None, Field(description="plan：每個點子的對手數（點子多時使用）", ge=1, le=20)
        ] = None,
        criteria: Annotated[
            list[str] | None,
            Field(description="plan：準則（預設 novelty_vs_typical、usefulness、framing）"),
        ] = None,
        gate: Annotated[Gate | None, Field(description="plan：非補償式門檻")] = None,
        verdicts: Annotated[list[Verdict] | None, Field(description="record 必填")] = None,
    ) -> ToolResult:
        service = deps_of(ctx).services.judge

        async def run() -> ToolResult:
            if action == "plan":
                return await service.plan(session_id, idea_ids, rounds, criteria, gate)
            if action == "record":
                return await service.record(session_id, verdicts)
            return await service.rank(session_id)

        return await guarded(run())
