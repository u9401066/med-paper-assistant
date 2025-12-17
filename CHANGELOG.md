# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **MCP-to-MCP Direct Communication Architecture** ✅ 已實作
  - pubmed-search 新增 HTTP API endpoints:
    - `GET /api/cached_article/{pmid}` - 取得單一文章
    - `GET /api/cached_articles?pmids=...` - 批量取得
    - `GET /api/session/summary` - Session 狀態
  - mdpaper 新增 `PubMedAPIClient` HTTP 客戶端
  - 新工具 `save_reference_mcp(pmid, agent_notes)`:
    - Agent 只傳 PMID，無法修改書目資料
    - mdpaper 直接從 pubmed-search API 取得驗證資料
    - 防止 Agent 幻覺（hallucination）書目資訊
  - **分層信任 (Layered Trust)** 參考檔案格式:
    - `🔒 VERIFIED`: PubMed 資料（不可修改）
    - `🤖 AGENT`: AI 筆記（AI 可更新）
    - `✏️ USER`: 人類筆記（AI 絕不碰觸）
- **stdio + HTTP API 同時啟動**
  - pubmed-search 在 stdio MCP 模式下自動啟動背景 HTTP API
  - `start_http_api_background()` 在 daemon thread 運行
  - 解決 VS Code MCP (stdio) 無法同時提供 HTTP API 的問題
- **Skill 文檔完整更新**
  - `literature-review/SKILL.md` 完整重寫，含完整工具列表和 PICO 工作流
  - `parallel-search/SKILL.md` 新增工具表格和 Session 管理說明
  - `concept-development/SKILL.md` 擴展工具列表和 FAQ
  - 所有 skill 明確標示 `save_reference_mcp` 為 PRIMARY 方法

### Changed
- **Reference 內容順序優化** - Abstract 移到 Citation Formats 之前
  - Foam hover preview 現在優先顯示 Abstract（更實用）
- **Foam settings 更新** - `foam.files.ignore` 改為 `foam.files.exclude`
- **sync_references Tool** - Markdown 引用管理器
  - 掃描 `[[wikilinks]]` 自動生成 References 區塊
  - 可逆格式：`[1]<!-- [[citation_key]] -->`，支援重複同步
  - 按出現順序編號，支援 Vancouver/APA 等格式
- **Foam Project Isolation** - 專案隔離功能
  - `FoamSettingsManager` 服務：動態更新 `foam.files.ignore`
  - `switch_project()` 整合：切換專案時自動排除其他專案
  - Whitelist 邏輯：只顯示當前專案的 `references/`
- **Reference Title Display** - Foam 自動完成顯示文章標題
  - frontmatter 加入 `title` 欄位
  - `foam.completion.label: "title"` 設定
- **MCP Tool Logging System** - 統一的工具日誌記錄
  - `tool_logging.py`: log_tool_call, log_tool_result, log_agent_misuse, log_tool_error
  - 日誌存放在專案目錄 `logs/YYYYMMDD.log`（跨平台支援）
  - 已整合至 draft/writing.py, project/crud.py, validation/concept.py, reference/manager.py
- **ReferenceConverter Domain Service** - 支援多來源參考文獻
  - 支援 PubMed, Zotero, DOI 來源
  - ReferenceId Value Object 確保唯一識別符
  - Foam [[wikilink]] 整合
- **Reference Entity 更新** - 新增多來源識別符欄位
  - unique_id, citation_key, source 欄位
  - `from_standardized()` 類別方法

### Changed
- **授權變更** - 從 MIT 改為 Apache License 2.0
- **日誌位置遷移** - 從系統 temp 目錄改為專案目錄 `logs/`
- **README.md** - 新增 MCP 協調架構說明、更新工具列表
- **ARCHITECTURE.md** - 新增 MCP Orchestration 架構圖
- **Prompts 更新** - `/mdpaper.concept` 和 `/mdpaper.search` 增加 MCP 協調流程說明
- **copilot-instructions.md** - 簡化為參照 AGENTS.md，避免重複

### Fixed
- **save_reference JSON 解析** - 處理 MCP 傳遞 JSON 字串的情況
  - 新增 `Union[dict, str]` 型別支援
  - 自動偵測並解析 JSON 字串輸入

### Deprecated
- `save_reference_by_pmid` - 改用 `save_reference(article=metadata)`

## [0.2.0] - 2025-12-17

### Added
- MCP 解耦架構：mdpaper 不再直接依賴 pubmed-search
- 多 MCP 協調模式：Agent 協調 mdpaper + pubmed-search + drawio
- 文獻探索工作區：`start_exploration()` / `convert_exploration_to_project()`
- Concept 驗證系統：novelty scoring (3 rounds, 75+ threshold)
- Paper type 支援：original-research, systematic-review, meta-analysis 等

### Changed
- Python 版本需求升級至 3.11+
- ReferenceManager 重構：接受 article metadata dict 而非 PMID
- 專案結構採用 DDD (Domain-Driven Design)

### Removed
- `infrastructure/external/entrez/` - 文獻搜尋移至 pubmed-search MCP
- `infrastructure/external/pubmed/` - 同上
- `services/strategy_manager.py` - 搜尋策略移至 pubmed-search MCP
- `tools/search/` - 搜尋工具改為 facade 委派

## [0.1.0] - 2025-12-01

### Added
- 初始版本
- MCP Server 框架 (FastMCP)
- 46 個 MCP 工具
- Word 匯出功能
- 參考文獻管理
- 草稿撰寫流程


[0.2.0]: https://github.com/u9401066/med-paper-assistant/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/u9401066/med-paper-assistant/releases/tag/v0.1.0
