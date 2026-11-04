"""cgu_feedback: what the human did with each idea."""

from __future__ import annotations

from typing import Annotated, Literal

from mcp.server.mcpserver import MCPServer
from mcp_types import ToolAnnotations
from pydantic import Field

from cgu.domain.common import ToolResult
from cgu.interfaces.mcp.deps import Deps
from cgu.interfaces.mcp.tools._common import Ctx, deps_of, guarded

DESCRIPTION = (
    "[stable] 記錄使用者對點子的決定。action=record（idea_id、decision=adopt｜modify｜abandon、reasons、note）、"
    "summary（依決定、算子、框架元素的計數）、export（全部紀錄）、"
    "delete（必須 confirm=true；刪除該 session 的全部回饋紀錄）。"
    "量測：只有計數；不做個人化、不做預測，也不代表點子品質。"
)


def register(server: MCPServer[Deps]) -> None:
    @server.tool(
        name="cgu_feedback",
        title="CGU feedback",
        description=DESCRIPTION,
        annotations=ToolAnnotations(
            title="CGU feedback",
            read_only_hint=False,
            destructive_hint=True,
            idempotent_hint=False,
            open_world_hint=False,
        ),
    )
    async def cgu_feedback(
        action: Annotated[
            Literal["record", "summary", "export", "delete"], Field(description="動作")
        ],
        session_id: Annotated[str, Field(description="session id")],
        ctx: Ctx,
        idea_id: Annotated[str | None, Field(description="record 必填")] = None,
        decision: Annotated[
            Literal["adopt", "modify", "abandon"] | None, Field(description="record 必填")
        ] = None,
        reasons: Annotated[list[str] | None, Field(description="record：理由")] = None,
        note: Annotated[str | None, Field(description="record：備註")] = None,
        confirm: Annotated[bool, Field(description="delete 必須為 true")] = False,
    ) -> ToolResult:
        service = deps_of(ctx).services.feedback

        async def run() -> ToolResult:
            if action == "record":
                return await service.record(session_id, idea_id, decision, reasons, note)
            if action == "summary":
                return await service.summary(session_id)
            if action == "export":
                return await service.export(session_id)
            return await service.delete(session_id, confirm)

        return await guarded(run())
