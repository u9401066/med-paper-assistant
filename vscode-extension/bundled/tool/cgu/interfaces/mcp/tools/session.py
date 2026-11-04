"""cgu_session: open, inspect, list, export and delete sessions."""

from __future__ import annotations

from typing import Annotated, Literal

from mcp.server.mcpserver import MCPServer
from mcp_types import ToolAnnotations
from pydantic import Field

from cgu.domain.common import CGUError, ToolResult
from cgu.interfaces.mcp.deps import Deps
from cgu.interfaces.mcp.tools._common import Ctx, deps_of, guarded

DESCRIPTION = (
    "[stable] Session 是所有狀態的邊界。action=open（必填 topic；選填 domain、language、seed）、"
    "get（概況與各類筆數）、list（最新在前）、export（該 session 全部資料）、"
    "delete（必須 confirm=true；永久刪除該 session 的全部資料，無法復原，先 export 留存）。"
    "其餘工具都要帶 session_id。量測：只有筆數；不量測任何內容。"
)


def register(server: MCPServer[Deps]) -> None:
    @server.tool(
        name="cgu_session",
        title="CGU session",
        description=DESCRIPTION,
        annotations=ToolAnnotations(
            title="CGU session",
            read_only_hint=False,
            destructive_hint=True,
            idempotent_hint=False,
            open_world_hint=False,
        ),
    )
    async def cgu_session(
        action: Annotated[
            Literal["open", "get", "list", "export", "delete"], Field(description="動作")
        ],
        ctx: Ctx,
        session_id: Annotated[str | None, Field(description="get／export／delete 必填")] = None,
        topic: Annotated[
            str | None, Field(description="open 必填：這個 session 要發想的主題")
        ] = None,
        domain: Annotated[str | None, Field(description="領域，例如「醫療商品開發」")] = None,
        language: Annotated[str | None, Field(description="預設 zh-TW")] = None,
        seed: Annotated[int | None, Field(description="可重現的種子；省略則隨機")] = None,
        confirm: Annotated[bool, Field(description="delete 必須為 true")] = False,
    ) -> ToolResult:
        service = deps_of(ctx).services.session

        async def run() -> ToolResult:
            if action == "open":
                return await service.open(topic, domain, language, seed)
            if action == "list":
                return await service.list_sessions()
            if not session_id:
                raise CGUError("invalid_input", f"session_id is required for action={action}")
            if action == "get":
                return await service.get(session_id)
            if action == "export":
                return await service.export(session_id)
            return await service.delete(session_id, confirm)

        return await guarded(run())
