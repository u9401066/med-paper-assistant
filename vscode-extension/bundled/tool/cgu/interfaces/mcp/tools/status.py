"""cgu_status: what this server can and cannot do right now."""

from __future__ import annotations

from mcp.server.mcpserver import MCPServer
from mcp_types import ToolAnnotations

from cgu import __version__
from cgu.application.ports import EmbeddingUnavailableError
from cgu.application.services._common import provenance
from cgu.domain.common import ToolResult
from cgu.interfaces.mcp.deps import Deps
from cgu.interfaces.mcp.tools._common import TOOL_MATURITY, Ctx, deps_of

DESCRIPTION = (
    "[stable] 回報版本、provider（passthrough｜ollama）、embedding 後端與是否具語意（semantic）、"
    "檢索是否啟用、資料目錄、各工具成熟度，以及提問記憶是否啟用（inquiry.enabled：null 表示從未詢問）與筆數。"
    "開工前先呼叫：inquiry.maintenance.due=true 時用 cgu_inquiry(organize) 取得整理工單，"
    "由你的模型整理並用 distill 回交創意素材；semantic=false 時，"
    "cgu_ideas(measure) 的新穎度只是字元 n-gram 的詞面重疊，不代表語意不同。"
    "量測：能力與設定；不量測任何創意品質。"
)


def register(server: MCPServer[Deps]) -> None:
    @server.tool(
        name="cgu_status",
        title="CGU status",
        description=DESCRIPTION,
        annotations=ToolAnnotations(
            title="CGU status",
            read_only_hint=True,
            destructive_hint=False,
            idempotent_hint=True,
            open_world_hint=False,
        ),
    )
    async def cgu_status(ctx: Ctx) -> ToolResult:
        deps = deps_of(ctx)
        warnings: list[str] = []
        try:
            info = await deps.embedding.describe()
            embedding = {"backend": info.backend, "semantic": info.semantic}
        except EmbeddingUnavailableError as exc:
            embedding = {"backend": "unavailable", "semantic": False}
            warnings.append(f"embedding backend unavailable: {exc}")
        if not embedding["semantic"]:
            warnings.append(
                "semantic=false: novelty measurements are lexical overlap only, not meaning"
            )
        return ToolResult.success(
            provenance("archive", warnings=warnings, degraded=bool(warnings)),
            {
                "version": __version__,
                "provider": deps.settings.provider,
                "embedding": embedding,
                "retrieval": {"enabled": deps.settings.network},
                "data_dir": str(deps.settings.data_dir),
                "maturity": dict(TOOL_MATURITY),
                "inquiry": await deps.services.inquiry.status(),
            },
        )
