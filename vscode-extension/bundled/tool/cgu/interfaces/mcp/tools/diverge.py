"""cgu_diverge: work orders that push a model off its typical answers."""

from __future__ import annotations

from typing import Annotated, Literal

from mcp.server.mcpserver import MCPServer
from mcp_types import ToolAnnotations
from pydantic import Field

from cgu.domain.common import CGUError, ToolResult
from cgu.interfaces.mcp.deps import Deps
from cgu.interfaces.mcp.tools._common import Ctx, deps_of, guarded

DESCRIPTION = (
    "[heuristic] 發散工單。action=typical_set（先在不看素材下列出 k 個最直覺的回答，當作要避開的靶子）、"
    "anti_typical（附上 avoid 清單與要套用的算子，要求每個點子標明改寫了哪個框架元素）、"
    "fanout（n 張獨立工單，每張變因不同，建議各用獨立 context 或不同模型執行）、"
    "collide（a 與 b 的結構映射 analogy 或橋接 bridge；a、b 可以是文字、idea id 或素材 id）。"
    "provider=passthrough（預設）時只回傳 work_order，由你執行後用 cgu_ideas(action=add) 回交；"
    "provider=ollama 時由本機模型代為產生並存入點子（provenance.engine=ollama）。"
    "量測：無；本工具不產生任何分數，新穎度請用 cgu_ideas(action=measure)。"
)


def register(server: MCPServer[Deps]) -> None:
    @server.tool(
        name="cgu_diverge",
        title="CGU diverge",
        description=DESCRIPTION,
        annotations=ToolAnnotations(
            title="CGU diverge",
            read_only_hint=False,
            destructive_hint=False,
            idempotent_hint=False,
            open_world_hint=False,
        ),
    )
    async def cgu_diverge(
        action: Annotated[
            Literal["typical_set", "anti_typical", "fanout", "collide"], Field(description="動作")
        ],
        session_id: Annotated[str, Field(description="session id")],
        ctx: Ctx,
        frame_id: Annotated[str | None, Field(description="以此框架為情境（選填）")] = None,
        k: Annotated[int, Field(description="typical_set：典型答案數", ge=1, le=30)] = 8,
        n: Annotated[
            int | None,
            Field(
                description="anti_typical 的點子數（預設 6）；fanout 的工單數（預設 4，最多 8）",
                ge=1,
                le=20,
            ),
        ] = None,
        operators: Annotated[
            list[str] | None, Field(description="anti_typical：要套用的算子名稱")
        ] = None,
        vary: Annotated[
            list[Literal["prompt", "material", "operator", "model"]] | None,
            Field(description="fanout：每張工單要變化的面向（預設 prompt）"),
        ] = None,
        a: Annotated[str | None, Field(description="collide：A（文字、idea id 或素材 id）")] = None,
        b: Annotated[str | None, Field(description="collide：B（文字、idea id 或素材 id）")] = None,
        mode: Annotated[
            Literal["analogy", "bridge"], Field(description="collide：結構映射或橋接")
        ] = "analogy",
    ) -> ToolResult:
        service = deps_of(ctx).services.diverge

        async def run() -> ToolResult:
            if action == "typical_set":
                return await service.typical_set(session_id, frame_id, k)
            if action == "anti_typical":
                return await service.anti_typical(session_id, frame_id, operators, n or 6)
            if action == "fanout":
                if n is not None and n > 8:
                    raise CGUError("invalid_input", "fanout n must be between 1 and 8")
                return await service.fanout(
                    session_id, n or 4, list(vary) if vary else None, frame_id
                )
            return await service.collide(session_id, a, b, mode)

        return await guarded(run())
