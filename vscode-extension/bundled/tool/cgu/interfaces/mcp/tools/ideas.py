"""cgu_ideas: the idea store, near-duplicate flags and honest novelty measurement."""

from __future__ import annotations

from typing import Annotated, Literal

from mcp.server.mcpserver import MCPServer
from mcp_types import ToolAnnotations
from pydantic import Field

from cgu.application.services.ideas import IdeaInput, Thresholds
from cgu.domain.common import ToolResult
from cgu.interfaces.mcp.deps import Deps
from cgu.interfaces.mcp.tools._common import Ctx, deps_of, guarded

DESCRIPTION = (
    "[stable] 點子庫。action=add（kind=typical｜candidate｜human｜prior_art；近重複會標記 duplicate_of "
    "並附相似度，但仍會存入）、list（可依 kind 篩選）、"
    "measure [heuristic]（預設量測所有 candidate：相對 typical／human／prior_art／其餘 session 點子的最大與平均相似度、"
    "最近鄰與參照集大小，參照集為空時該項為 null；另有整體 Vendi 多樣性）。"
    "量測：相似度與多樣性；不量測品質、可行性或「原創」與否。"
    "embedding.semantic=false 時相似度只是字元 n-gram 重疊，低相似度不代表語意不同。"
)


def register(server: MCPServer[Deps]) -> None:
    @server.tool(
        name="cgu_ideas",
        title="CGU ideas",
        description=DESCRIPTION,
        annotations=ToolAnnotations(
            title="CGU ideas",
            read_only_hint=False,
            destructive_hint=False,
            idempotent_hint=False,
            open_world_hint=False,
        ),
    )
    async def cgu_ideas(
        action: Annotated[Literal["add", "list", "measure"], Field(description="動作")],
        session_id: Annotated[str, Field(description="session id")],
        ctx: Ctx,
        ideas: Annotated[list[IdeaInput] | None, Field(description="add 必填")] = None,
        kind: Annotated[
            Literal["typical", "candidate", "human", "prior_art"] | None,
            Field(description="list 的篩選"),
        ] = None,
        idea_ids: Annotated[
            list[str] | None, Field(description="measure：要量測的 idea id（預設全部 candidate）")
        ] = None,
        thresholds: Annotated[
            Thresholds | None, Field(description="measure：覆寫重複判斷門檻")
        ] = None,
    ) -> ToolResult:
        service = deps_of(ctx).services.ideas

        async def run() -> ToolResult:
            if action == "add":
                return await service.add(session_id, ideas)
            if action == "list":
                return await service.list_ideas(session_id, kind)
            return await service.measure(session_id, idea_ids, thresholds)

        return await guarded(run())
