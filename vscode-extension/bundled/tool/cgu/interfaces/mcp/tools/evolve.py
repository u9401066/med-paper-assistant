"""cgu_evolve: a quality-diversity archive keyed by rewritten frame element and distance band."""

from __future__ import annotations

from typing import Annotated, Literal

from mcp.server.mcpserver import MCPServer
from mcp_types import ToolAnnotations
from pydantic import Field

from cgu.domain.common import ToolResult
from cgu.domain.judge import Verdict
from cgu.interfaces.mcp.deps import Deps
from cgu.interfaces.mcp.tools._common import Ctx, deps_of, guarded

DESCRIPTION = (
    "[experimental] 品質多樣性存檔。格子＝（被改寫的框架元素種類）×（距離帶 near｜mid｜far；"
    "沒有語意 embedding 或沒有 typical 點子時為 unknown）。action=map（格子與覆蓋計數）、"
    "next（以 session seed 挑親代與算子，回傳 work_order）、"
    "submit（子代點子：去重、分格；格子空著就占位，被占用時回傳 AB／BA 比較工單）、"
    "resolve（依判決決定替換或丟棄，記錄譜系；子代須嚴格勝出才替換）。"
    "量測：覆蓋的格子數；不量測點子品質。"
)


def register(server: MCPServer[Deps]) -> None:
    @server.tool(
        name="cgu_evolve",
        title="CGU evolve",
        description=DESCRIPTION,
        annotations=ToolAnnotations(
            title="CGU evolve",
            read_only_hint=False,
            destructive_hint=False,
            idempotent_hint=False,
            open_world_hint=False,
        ),
    )
    async def cgu_evolve(
        action: Annotated[Literal["map", "next", "submit", "resolve"], Field(description="動作")],
        session_id: Annotated[str, Field(description="session id")],
        ctx: Ctx,
        child_text: Annotated[str | None, Field(description="submit 必填：子代點子")] = None,
        parent_id: Annotated[str | None, Field(description="submit 必填：親代 idea id")] = None,
        operator: Annotated[str | None, Field(description="submit 必填：使用的算子")] = None,
        frame_element_kind: Annotated[
            str | None, Field(description="submit 必填：被改寫的框架元素種類")
        ] = None,
        material_ids: Annotated[
            list[str] | None, Field(description="submit：用到的素材 id")
        ] = None,
        niche: Annotated[
            str | None, Field(description="resolve 必填：格子，如 assumption|unknown")
        ] = None,
        verdicts: Annotated[list[Verdict] | None, Field(description="resolve 必填")] = None,
    ) -> ToolResult:
        service = deps_of(ctx).services.evolve

        async def run() -> ToolResult:
            if action == "map":
                return await service.map(session_id)
            if action == "next":
                return await service.next(session_id)
            if action == "submit":
                return await service.submit(
                    session_id, child_text, parent_id, operator, frame_element_kind, material_ids
                )
            return await service.resolve(session_id, niche, verdicts)

        return await guarded(run())
