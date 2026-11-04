"""cgu_inquiry: a local, opt-in memory of the user's own questions, and creative sources mined from it."""

from __future__ import annotations

from typing import Annotated, Literal

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

from cgu.application.services.inquiry import CaptureItem, CaptureRequest, ThemeLabel
from cgu.domain.common import CGUError, ToolResult
from cgu.domain.frame import Consent
from cgu.domain.inquiry import InquiryConsent
from cgu.domain.inquiry_material import InquiryReview, MaterialDraft
from cgu.interfaces.mcp.deps import Deps
from cgu.interfaces.mcp.tools._common import Ctx, deps_of, guarded
from cgu.interfaces.mcp.tools.frame import NOT_ASKED, NotAsked

DESCRIPTION = (
    "[heuristic] 提問記憶：本機、預設關閉（opt-in）的使用者提問歷史，從中找創意來源。"
    "action=settings（enable 需要使用者同意：用戶端支援時 SDK 直接詢問；否則請先問使用者，"
    "再以 consent={granted: true, note: 使用者原話} 重送；停用不需同意；excluded_projects 排除專案；"
    "回傳 enabled、consent、counts、coverage、funnel 與各管道計數）、"
    "capture（text 必填；未啟用或專案被排除時回傳 recorded=false 與 reason，這不是錯誤；"
    "會去識別並回報 redactions，姓名與臨床細節不會被偵測，含病人資訊請先改寫；items 可批次，最多 200）、"
    "list、themes（詞面或語意群聚；未命名主題附 inquiry_label 工單）、label、"
    "mine（kinds=frame｜bridge｜stalled｜dormant；frame 附 inquiry_explicate 工單）、"
    "related（query 必填；回傳你問過類似的、已採用與已放棄的點子，以及可直接加入 human 參照集的 ideas_payload）、"
    "organize（待整理提問的工單，由你的模型提煉創意素材，不呼叫另一個 LLM）、"
    "distill（回交 reviewed 的 ID 與 text_sha256、materials 的 kind／text／inquiry_ids）、"
    "materials（取回跨 session 創意素材與來源；query 為詞面篩選）；settings 可設 organize_after（預設 20），"
    "export、delete（需 confirm=true；連同向量、主題成員與來源紀錄一併刪除）。"
    "量測：詞面或語意相似度、主題大小、問句開頭占比、共現次數，皆為未校準的啟發式 Measurement；"
    "不量測創意或點子品質，也沒有合成的創意分數。"
    "輸出只反映使用者已在想的事；semantic=false 時主題是詞面群聚。"
)


class InquiryConsentForm(BaseModel):
    granted: bool = Field(description="是否同意 CGU 在本機記錄你送給 agent 的提問")
    note: str = Field(default="", description="備註（可留空）")


CONSENT_QUESTION = (
    "要啟用「提問記憶」嗎？CGU 會在這台電腦本機記錄你送給 agent 的提問文字（去識別後，最多 2000 字）、"
    "時間、來源管道與專案名稱；不記錄助理回覆、工具輸出與檔案內容，也不上傳。"
    "姓名與臨床細節不會被偵測，請勿在提問中放病人資訊。你可以隨時查看、匯出或刪除。是否同意？"
)


async def consent_resolver(
    ctx: Ctx, action: str, enable: bool | None, consent: Consent | None
) -> Elicit[InquiryConsentForm] | NotAsked:
    """Ask the client only when recording would be switched on and no consent was given."""
    if action != "settings" or enable is not True or consent is not None:
        return NOT_ASKED
    capabilities = ctx.client_capabilities
    elicitation = capabilities.elicitation if capabilities is not None else None
    if elicitation is None or (elicitation.form is None and elicitation.url is not None):
        return NOT_ASKED
    if await deps_of(ctx).services.inquiry.is_enabled():
        return NOT_ASKED
    return Elicit(CONSENT_QUESTION, InquiryConsentForm)


def _consent(
    asked: ElicitationResult[InquiryConsentForm], given: Consent | None
) -> InquiryConsent | None:
    if isinstance(asked, AcceptedElicitation) and isinstance(asked.data, InquiryConsentForm):
        return InquiryConsent(granted=asked.data.granted, note=asked.data.note, via="elicitation")
    if isinstance(asked, DeclinedElicitation):
        return InquiryConsent(granted=False, note="user declined the dialog", via="elicitation")
    if isinstance(asked, CancelledElicitation):
        return InquiryConsent(
            granted=False, note="user dismissed the dialog", via="elicitation", final=False
        )
    if given is not None:
        return InquiryConsent(granted=given.granted, note=given.note, via="caller")
    return None


def register(server: MCPServer[Deps]) -> None:
    @server.tool(
        name="cgu_inquiry",
        title="CGU inquiry memory",
        description=DESCRIPTION,
        annotations=ToolAnnotations(
            title="CGU inquiry memory",
            read_only_hint=False,
            destructive_hint=True,
            idempotent_hint=False,
            open_world_hint=False,
        ),
    )
    async def cgu_inquiry(
        action: Annotated[
            Literal[
                "settings",
                "capture",
                "list",
                "themes",
                "label",
                "mine",
                "related",
                "organize",
                "distill",
                "materials",
                "export",
                "delete",
            ],
            Field(description="動作"),
        ],
        ctx: Ctx,
        consent_decision: Annotated[
            ElicitationResult[InquiryConsentForm], Resolve(consent_resolver)
        ],
        enable: Annotated[bool | None, Field(description="settings：啟用（需同意）或停用")] = None,
        consent: Annotated[
            Consent | None,
            Field(description="settings：使用者同意的紀錄；granted=true 且 note 為使用者原話"),
        ] = None,
        excluded_projects: Annotated[
            list[str] | None, Field(description="settings：不記錄的專案名稱（資料夾最後一段）")
        ] = None,
        organize_after: Annotated[
            int | None, Field(description="settings：累積幾筆後提示 agent 整理（1..200，預設 20）")
        ] = None,
        reviewed: Annotated[
            list[InquiryReview] | None,
            Field(description="distill：已讀提問的 inquiry_id 與原始 text_sha256（最多 100）"),
        ] = None,
        materials: Annotated[
            list[MaterialDraft] | None,
            Field(description="distill：由你整理的創意素材（最多 100）；沒有可用素材時 []"),
        ] = None,
        agent_model: Annotated[
            str | None, Field(description="distill：呼叫端使用的模型名稱，知道才填")
        ] = None,
        text: Annotated[str | None, Field(description="capture 必填：使用者的提問")] = None,
        gist: Annotated[str | None, Field(description="capture：一句話摘要（選填）")] = None,
        project: Annotated[
            str | None,
            Field(
                description="capture／list／themes／mine／organize／materials／export／delete 的專案篩選"
            ),
        ] = None,
        session_id: Annotated[
            str | None, Field(description="capture：連結的 CGU session id（選填）")
        ] = None,
        source: Annotated[
            Literal["agent", "hook", "import", "manual"], Field(description="capture：來源管道")
        ] = "agent",
        occurred_at: Annotated[
            str | None, Field(description="capture：ISO-8601 時間（預設現在）")
        ] = None,
        items: Annotated[
            list[CaptureItem] | None, Field(description="capture：批次（最多 200 筆）")
        ] = None,
        since_days: Annotated[int | None, Field(description="list／themes：最近幾天")] = None,
        theme_id: Annotated[str | None, Field(description="list：只列這個主題的提問")] = None,
        limit: Annotated[
            int | None,
            Field(
                description="list（預設 50）／mine（每類，預設 3）／organize 與 materials（預設 20，最多 100）"
            ),
        ] = None,
        offset: Annotated[int, Field(description="list／materials：位移")] = 0,
        min_size: Annotated[
            int | None, Field(description="themes：主題最少 family 數（3）")
        ] = None,
        threshold: Annotated[
            float | None, Field(description="themes：群聚的餘弦距離門檻（預設見回傳；未校準）")
        ] = None,
        labels: Annotated[
            list[ThemeLabel] | None, Field(description="label 必填：[{theme_id, label ≤ 60 字}]")
        ] = None,
        kinds: Annotated[
            list[Literal["frame", "bridge", "stalled", "dormant"]] | None,
            Field(description="mine：來源種類（預設全部）"),
        ] = None,
        query: Annotated[
            str | None, Field(description="related 必填；materials 選填，詞面篩選")
        ] = None,
        k: Annotated[int | None, Field(description="related：每類回傳筆數（5）")] = None,
        ids: Annotated[list[str] | None, Field(description="delete：提問 id")] = None,
        older_than_days: Annotated[
            int | None, Field(description="delete：刪除早於這麼多天的提問")
        ] = None,
        all: Annotated[bool, Field(description="delete：刪除全部")] = False,
        confirm: Annotated[bool, Field(description="delete 必須為 true")] = False,
    ) -> ToolResult:
        service = deps_of(ctx).services.inquiry

        async def run() -> ToolResult:
            if action == "settings":
                return await service.settings(
                    enable=enable,
                    consent=_consent(consent_decision, consent),
                    excluded_projects=excluded_projects,
                    organize_after=organize_after,
                )
            if action == "capture":
                if items:
                    if text is not None:
                        raise CGUError("invalid_input", "give either text or items, not both")
                    batch = [
                        CaptureRequest(
                            text=i.text,
                            gist=i.gist or gist,
                            project=i.project or project,
                            session_id=i.session_id or session_id,
                            source=i.source or source,
                            occurred_at=i.occurred_at or occurred_at,
                        )
                        for i in items
                    ]
                    return await service.capture(batch, batch=True)
                if text is None:
                    raise CGUError(
                        "invalid_input", "text (or items) is required for action=capture"
                    )
                single = CaptureRequest(
                    text=text,
                    gist=gist,
                    project=project,
                    session_id=session_id,
                    source=source,
                    occurred_at=occurred_at,
                )
                return await service.capture([single], batch=False)
            if action == "list":
                return await service.list_items(
                    project=project,
                    since_days=since_days,
                    theme_id=theme_id,
                    limit=limit,
                    offset=offset,
                )
            if action == "themes":
                return await service.themes(
                    min_size=min_size, threshold=threshold, project=project, since_days=since_days
                )
            if action == "label":
                return await service.label(labels)
            if action == "mine":
                return await service.mine(
                    kinds=list(kinds) if kinds else None, limit=limit, project=project
                )
            if action == "related":
                return await service.related(query, k)
            if action == "organize":
                return await service.maintenance.organize(project, limit)
            if action == "distill":
                return await service.maintenance.distill(reviewed, materials, agent_model)
            if action == "materials":
                return await service.maintenance.materials(project, query, limit, offset)
            if action == "export":
                return await service.export(project)
            return await service.delete(
                ids=ids,
                project=project,
                older_than_days=older_than_days,
                everything=all,
                confirm=confirm,
            )

        return await guarded(run())
