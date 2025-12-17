# Progress (Updated: 2025-12-17)

## Done

- MCP 解耦：完全移除 mdpaper 對 pubmed_search 的依賴
- ReferenceManager 重構：新 API save_reference(article)
- Skill tools 移除：已內建於 VS Code Copilot
- Deprecated API 移除：save_reference_by_pmid_legacy
- copilot-instructions.md 更新：新增 MCP 架構原則
- README 更新：Python 3.11+、工具數量 46、新架構說明
- save_reference JSON 解析修復：處理 MCP 傳遞 JSON 字串的情況
- **MCP Tool Logging 系統建立**
- **Foam 專案隔離功能**：
  - `FoamSettingsManager` 服務：動態更新 `foam.files.ignore`
  - `switch_project()` 整合：切換專案時自動更新 Foam 設定
  - Whitelist 邏輯：只顯示當前專案的 `references/`
- **Reference 格式優化**：
  - 加入 `title` frontmatter 供 Foam 顯示文章標題
  - `foam.completion.label: "title"` 設定
- **sync_references 工具**：
  - 掃描 `[[wikilinks]]` 自動生成 References 區塊
  - 可逆設計：`[1]<!-- [[citation_key]] -->` 格式
  - 支援重複同步、重新排序
- **MCP-to-MCP 直接通訊架構** ✅：
  - `pubmed-search` 新增 HTTP API endpoints:
    - `GET /api/cached_article/{pmid}` - 單一文章
    - `GET /api/cached_articles?pmids=...` - 批量取得
    - `GET /api/session/summary` - Session 狀態
  - `mdpaper` 新增 `PubMedAPIClient` HTTP 客戶端
  - 新工具 `save_reference_mcp(pmid, agent_notes)`:
    - Agent 只傳 PMID，不傳 metadata
    - mdpaper 直接從 pubmed-search 取得驗證資料
    - 防止 Agent 修改/幻覺書目資料
  - **分層信任 (Layered Trust)** 參考檔案格式:
    - `🔒 VERIFIED`: PubMed 資料（不可修改）
    - `🤖 AGENT`: AI 筆記（AI 可更新）
    - `✏️ USER`: 人類筆記（AI 絕不碰觸）
- **stdio + HTTP API 同時啟動 (2025-12-17)** ✅：
  - `pubmed-search` 在 stdio MCP 模式下自動啟動背景 HTTP API
  - `start_http_api_background()` 函數在 daemon thread 運行
  - 預設 port 8765，可透過 `PUBMED_HTTP_API_PORT` 環境變數設定
  - 解決 VS Code MCP (stdio) 無法同時提供 HTTP API 的問題
- **Skill 文檔完整更新 (2025-12-17)** ✅：
  - `literature-review/SKILL.md` 完整重寫，含 20+ pubmed-search 工具
  - `parallel-search/SKILL.md` 新增工具表格和 save_reference_mcp 說明
  - `concept-development/SKILL.md` 擴展工具列表和 FAQ
  - 所有 skill 明確標示 `save_reference_mcp` 為 PRIMARY 方法
- **Reference 內容順序優化 (2025-12-17)** ✅：
  - Abstract 移到 Citation Formats 之前
  - Foam hover preview 現在優先顯示 Abstract（更實用）
- **Project Memory 系統 (2025-12-17)** ✅：
  - `projects/{slug}/.memory/` 目錄結構
  - `activeContext.md` Agent 工作記憶
  - `progress.md` 研究進度追蹤
  - CONSTITUTION v1.2.0 第八章規範強制更新
- **Wikilink 自動驗證/修復系統 (2025-12-17)** ✅：
  - 新增 `wikilink_validator.py` 核心模組
  - 正確格式：`[[author2024_12345678]]`
  - 自動修復錯誤格式：`[[12345678]]` → 查找並補上 author_year
  - **整合點 A**: `validate_concept()` - 驗證時自動修復
  - **整合點 B**: `write_draft()` - 寫入時 pre-check
  - **整合點 C**: `insert_section()` - Export 時 pre-check
  - **整合點 D**: Skill 文檔更新格式規範
  - 新工具：`validate_wikilinks()` - 手動檢查指定檔案
- **Pre-Analysis Checklist 系統 (2025-12-17)** ✅：
  - 新增 `pre_analysis_checklist.py` domain service
  - 檢查 concept.md 在進入分析前的完整度
  - 必要區塊：Study Design, Participants, Sample Size, Outcomes
  - 建議區塊：Statistical Analysis, IRB, Target Journal
  - 更新 `concept-development/SKILL.md` 加入 Phase C: Pre-Analysis Checklist
  - ROADMAP 新增 Phase 4: Methods & Analysis Preparation

## Doing

- 無

## Next

- Migration script 更新現有參考文獻到新格式
- 批量更新舊 reference 的內容順序（Abstract 在前）
- 加入環境變數 `PUBMED_MCP_API_URL` 配置
- **Outcome Definition Templates** - 操作型定義模板庫
- **Sample Size Calculator** - 內建 power calculation 工具
- **CRF Generator** - 自動生成資料收集表單
