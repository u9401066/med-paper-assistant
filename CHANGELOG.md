# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.11] - 2026-02-26

### Added

- **Journal Support**: medRxiv, JAMIA, JBI added to `JOURNAL_REQUIREMENTS` (total: 11 journals)
- **Pipeline Gate Validator**: `pipeline_gate_validator.py` for phase-gate validation with reference counting fix (PMID subdirs)
- **Audit Hooks MCP Tool**: `audit_hooks.py` for Hook D meta-learning integration

### Fixed

- **`check_formatting` crash**: `'Drafter' object has no attribute 'read_draft'` — replaced with direct file reading via `get_drafts_dir()`
- **Pipeline gate**: Added `Path` import, fixed `_get_or_create_loop` signature, removed unused variables
- **Pipeline gate**: 29 API mismatches resolved in `pipeline_gate.py`
- **Gate validator**: Count PMID subdirs instead of flat `.md` for reference counting

### Changed

- **DRY refactor**: Extracted 7 duplicate helper functions into `_shared/project_context.py` (`get_project_path`, `get_drafts_dir`, `get_concept_path`, `validate_project_for_tool`)
- **VSX bundled code**: Full rsync from `src/` — 38 files updated, 5 new files added
- **Auto-paper SKILL.md**: Synced to VSX extension

## [0.3.10] - 2026-02-25

### Added

- **Author Info System**: `Author` frozen dataclass value object with structured affiliations, ORCID, corresponding author flag
  - `generate_author_block()` produces markdown with superscript affiliations + corresponding author notation
  - `update_authors` MCP tool for managing project author metadata
  - `create_project` now accepts `authors_json` parameter for structured author input
  - `get_current_project` displays formatted author information
  - `draft_section` auto-injects author block for Title Page sections
  - `journal-profile.template.yaml` updated with `authors:` section template
- **Data Artifact Provenance**: `DataArtifactTracker` persistence class for tracing data analysis artifacts
  - `validate_data_artifacts` MCP tool for cross-referencing data artifacts against drafts
  - All 4 analysis MCP tools (`run_statistical_test`, `analyze_dataset`, `create_plot`, `generate_table_one`) record provenance automatically
  - Phase 5/6 gate validators check data artifact completeness
  - CONSTITUTION §23.2 數據產出物溯源與交叉驗證 (v1.5.0)
- **Hook F1-F4**: Data artifact validation hooks (溯源追蹤、manifest↔檔案一致、draft↔manifest 交叉引用、統計宣稱驗證)

### Fixed

- **Full project ruff lint cleanup**: 60 errors → 0 (unused imports, f-string placeholders, ambiguous variable names, import ordering, unused assignments, duplicate dict keys)
- **Pre-existing duplicate `project_path` key** in `get_project_info()` dict literal (F601)

### Changed

- Hook count: 48 → 52 checks (added F1-F4 data-artifacts)

## [0.3.9] - 2026-02-24

### Added

- **Multi-Stage Review Architecture**: 設計文件 `docs/design/multi-stage-review-architecture.md`，記錄 4 層審查機制（Prompt 15 + Skill 26 + Hook 42 + Agent Mode）
- **42 Hooks 完整實作**: Hook 系統從 38 → 42 checks
  - Hook C8 (Temporal Consistency Pass): post-manuscript 時間一致性檢查
  - Hook B5 (Methodology Audit): 方法學驗證
  - Hook B6 (Writing Order): 寫作順序強制
  - Hook B7 (Section Brief Compliance): Section Brief 合規
  - Hook D7 (Review Retrospective): 自我改進回顧
- **11-Phase Pipeline (Phase 0-10)**: auto-paper 從 9-Phase 升級至 11-Phase
- **Auto-Paper Guide**: `docs/auto-paper-guide.md` 完整操作手冊
- **VSX Template Bundling**: `journal-profile.template.yaml` 打包進 VSX extension
  - `setupWorkspace` 自動複製 templates（含內容比對 auto-update）
  - `mdpaper.autoPaper` runtime safeguard（template 缺失時警告 + 一鍵修復）
  - `validateBundledTemplates()` 驗證函式 + 2 個新 unit tests
- **Citation Section**: README.md + README.zh-TW.md 加入 BibTeX 引用區塊

### Fixed

- **Bash Arithmetic Bug**: `build.sh` / `validate-build.sh` 中 `((VAR++))` 在 `set -e` 下 VAR=0 時回傳 exit code 1 → 改用 `VAR=$((VAR + 1))`
- **V6 Vitest Detection**: `validate-build.sh` 測試結果擷取修復（vitest v4 輸出格式變更）
- **Integration Test Async**: 6 個 integration tests 修正為 `async def` + `await`（`searcher.search()` 已改為 async）
- **Integration Test CWD**: `test_drafter` / `test_insertion` 改用 `tmp_path` fixture 避免 CWD 相依路徑問題
- **CI VSX Template Sync**: `ci.yml` + `release.yml` 的 VSX sync step 加入 templates 同步
- **project_path resolution bug**: `get_project_info()` 返回值缺少 `project_path` key

### Changed

- **pytest default config**: `addopts = "-m 'not integration and not slow'"` — 本地 `pytest` 預設只跑 unit tests（與 CI 行為一致）
- **VSX autopaper 描述**: "9-Phase Pipeline + Hooks" → "11-Phase Pipeline + 42 Hooks"
- **Hook C7 (Temporal Consistency)**: 新增 post-manuscript hook 修正過時引用

## [Unreleased]

## [0.3.8] - 2026-02-20

### Fixed

- **Lazy Import**: `matplotlib`、`seaborn`、`scipy` 改為方法內 lazy import，修復 `uvx` 安裝時 `ModuleNotFoundError: No module named 'matplotlib'`（這些是可選依賴，核心 MCP server 啟動不應依賴）

## [0.3.7] - 2026-02-20

### Fixed

- **PyPI Entry Point**: 加入 `[project.scripts]` 讓 `uvx med-paper-assistant` 正確啟動 MCP server（v0.3.6 缺少 CLI entry point 導致 `Package does not provide any executables` 錯誤）

## [0.3.6] - 2026-02-20

### Added

- **`MedPaper: Setup Workspace` 命令** ✅
  - 一鍵將 bundled skills (14)、prompts (12)、copilot-instructions.md 複製到 workspace
  - 只複製不存在的檔案（不覆寫已客製化的內容）
  - 完成後提示「重新載入」以啟用全部功能
  - Marketplace 安裝後執行一次即可獲得完整 Agent Mode 體驗

### Fixed

- **CI Pipeline**: test-vsx / publish-vsx 加入 skills/prompts/copilot-instructions.md 同步步驟
- **PyPI 重複發佈**: publish-pypi 加入 `skip-existing: true`（v0.3.5 已上 PyPI）

### Removed

- **Dead Code 清理**: 移除 `MDPAPER_INSTRUCTIONS`、`MDPAPER_EXTENSION_PATH` 環境變數（Python MCP server 從未讀取）
- **Dead Code 清理**: 移除 `registerMcpServerProvider` 中的 `loadSkillsAsInstructions()` 呼叫

## [0.3.5] - 2026-02-20

### Added

- **Figure/Table Archive + Insert Tools** ✅
  - Hook: `_check_figure_table_archive` 一致性驗證
  - 3 個新工具: `insert_figure`, `insert_table`, `list_assets`（54 → 57 tools）
- **GitHub Repo Metadata + Doc-Update Hook (G8)** ✅
  - Repo description, 15 topics, 9 custom labels
  - `scripts/check-doc-updates.py`: 13 條規則映射檔案變更至文檔依賴
  - Pre-commit hook #15: doc-update-reminder (warn-only)
  - Hook 計數: 37 → 38 checks (G1-G8)
- **Prettier Markdown Formatter** ✅
  - Pre-commit hook #14: `mirrors-prettier v3.1.0`
  - 格式化所有 121 個 .md 檔案
- **CI/CD Pipeline Upgrade** ✅
  - CI: 2 → 5 jobs (python-lint, python-test, vsx, dashboard, markdown)
  - Release: 5-stage pipeline (validate → test → publish-pypi + publish-vsx → github-release)
  - Branch protection: 5 required CI checks, strict mode
  - 移除 Dependabot 配置

### Fixed

- **README Submodule Links**: 子模組相對路徑 404 → 改用 GitHub 絕對連結
- **VSX One-Click Install** ✅
  - 移除 `extensionDependencies` 硬依賴（`vscode-zotero-mcp` 未上架會阻擋安裝）
  - Python fallback 改為 `uvx`（PyPI 已發布即可自動下載執行）
  - CGU MCP server 改為條件註冊（偵測到才啟用，避免錯誤訊息）

### Documentation

- README/README.zh-TW: 更新所有工具/Hook 計數（20 處：57 tools, ~107 total, 15 hooks）

### Added

- **Placeholder Tools Implementation (Phase 8)** ✅
  - 9 個佔位工具升級為完整實作（74→83 tools）
  - Analysis: `analyze_dataset`, `detect_variable_types`, `list_data_files`, `create_plot`, `run_statistical_test`, `generate_table_one`
  - Review: `check_manuscript_consistency`, `create_reviewer_response`, `format_revision_changes`
- **Tool Layer Architecture Audit (Phase 9)** ✅
  - 7 個模板型工具（debate, critique, idea-validation）轉為 3 個 Skill 檔案
  - 新增 `.claude/skills/academic-debate/SKILL.md`
  - 新增 `.claude/skills/idea-validation/SKILL.md`
  - 新增 `.claude/skills/manuscript-review/SKILL.md`
  - 工具數量：83→76
- **Comprehensive Tool Consolidation (Phase 10)** ✅
  - 6 大策略精簡 76→53 tools（-30%）
  - **Strategy A: 移除無用工具** — `close_other_project_files`, `export_word`（legacy）
  - **Strategy B: 簡單合併** — `validate_for_section`, `get_project_paths`, `check_reference_exists` 併入現有工具
  - **Strategy C: 參數合併** — 6 組工具對合併（validate_concept +structure_only, get_current_project +include_files, update_project_settings +status/citation_style, save_diagram +output_dir, sync_workspace_state +clear, suggest_citations +claim_type/max_results, verify_document +limits_json）
  - **Strategy D: 功能吸收** — consistency 檢查 + submission checklist 併入 `check_formatting`
  - **Strategy E+F: Skill 轉換** — 7 個工具轉為 skill 知識（get_section_template, generate_cover_letter, list_supported_journals, generate_highlights, check_submission_checklist, create_reviewer_response, format_revision_changes）
  - 新增 `.claude/skills/submission-preparation/SKILL.md`（cover letter、highlights、journal requirements、reviewer response 模板）
  - 更新 `draft-writing/SKILL.md`、`project-management/SKILL.md` 反映工具變更
  - 測試驗證：35 passed / 21 pre-existing failures / 0 regressions
- **Citation-Aware Editing Tools (Layer 1+2)** ✅
  - `get_available_citations()` — 列出所有可用 `[[citation_key]]`，含 PMID/作者/年份/標題表格
  - `patch_draft(filename, old_text, new_text)` — 部分編輯草稿，自動驗證所有 wikilinks
    - 唯一匹配檢查（防止模糊替換）
    - Wikilink 格式自動修復（`[[12345678]]` → `[[author2024_12345678]]`）
    - 引用存在驗證（拒絕 hallucinated citations）
  - 解決 Agent 使用 `replace_string_in_file` 繞過 MCP 驗證管線的核心問題
  - 14 個測試（3 test classes: GetAvailableCitations, PatchDraft, EditingIntegration）
  - SKILL.md 新增 Flow D: Citation-Aware 部分編輯
  - copilot-instructions.md 新增草稿編輯引用規則
- **Infrastructure & Quality Cleanup (Phase 3.5)** ✅
  - Pre-commit hooks: 13 hooks（ruff, ruff-format, mypy, bandit, pytest, whitespace, yaml, json, toml, large files, merge conflicts, debug statements）全部通過
  - DDD Import 遷移：19 個測試檔從 `core.*` 遷移至 DDD 路徑
  - Test Isolation：所有測試改用 `tmp_path` fixture，不再污染專案根目錄
  - ARCHITECTURE.md 重寫：從 448 行過時文檔重寫為 ~240 行精確 DDD 架構文檔
  - Legacy Cleanup：刪除空的 `core/` 目錄、多餘腳本、散落檔案
  - Copilot Hook 修復：AGENTS.md 補齊 7 skills + 8 prompts，修正 capability index
  - Coverage Baseline：32 passed / 1 skipped / 26 integration-deselected
  - 架構方向決策：選定 **Direction C: Full VSX + Foam + Pandoc**
- **Prompt Files 機制**
  - 新增 `.github/prompts/` 目錄，包含 9 個 prompt files
  - `/mdpaper.project` - 專案設置與切換
  - `/mdpaper.concept` - 研究概念發展（含 novelty 驗證）
  - `/mdpaper.search` - 智能文獻搜尋（情境 A/B 判斷）
  - `/mdpaper.draft` - 草稿撰寫（需先通過 concept 驗證）
  - `/mdpaper.strategy` - 搜尋策略配置
  - `/mdpaper.analysis` - 資料分析與 Table 1
  - `/mdpaper.clarify` - 內容改進與潤飾
  - `/mdpaper.format` - Word 匯出
  - `/mdpaper.help` - 指令說明
  - 參考 copilot-capability-manager 架構設計
- **犀利回饋模式 (Sharp Reviewer Feedback)**
  - `concept_validator.py`: 新增 `_generate_novelty_feedback()` 方法
  - 回饋格式：verdict / critical_issues / questions / actionable_fixes
  - CGU 創意工具整合建議
  - 像頂尖期刊 Reviewer 一樣審查：直指問題、用證據說話
- **檔案保護模式 (File Protection)**
  - `.copilot-mode.json`: 新增 `protected_paths` 設定
  - Normal/Research 模式下禁止修改開發檔案
  - 受保護路徑：`.claude/`, `.github/`, `src/`, `tests/`, `integrations/`
- **Session 檢視工具**
  - `scripts/view_session.py`: 顯示 pubmed-search 搜尋紀錄
  - 可供人工驗證 Agent 確實執行了搜尋
- **已知問題追蹤 (Known Issues)**
  - ROADMAP.md 新增 4 個 Critical Issues
  - 新增 Phase 3.5: 學術品質保證系統

### Changed

- **Novelty Check 改為 Advisory（不阻擋）**
  - `writing.py`: `_enforce_concept_validation()` 改為建議性質
  - 用戶可選擇：直接寫 / 修正問題 / 用 CGU 發想
  - 仍然檢查結構完整性（NOVELTY STATEMENT, KEY SELLING POINTS）
- **concept-development SKILL 大幅更新**
  - 新增犀利回饋原則和模板
  - 新增 CGU 工具使用指南
  - 新增危險信號處理流程
- **Pydantic V2 遷移**
  - `SearchCriteria`: `class Config` → `model_config = ConfigDict(frozen=True)`
  - 消除 `PydanticDeprecatedSince20` 警告

### Fixed

- **wikilink_validator.py**: 移除未使用的 `match.group(1)` 呼叫
- **list_drafts / read_draft**: 路徑解析改用 `_get_drafts_dir()` 取得專案路徑，與 `patch_draft` 一致

### Documentation

- **AGENTS.md**: 新增 Novelty Check 規則和 CGU 整合
- **copilot-instructions.md**: 新增犀利回饋做法
- **pubmed-search-mcp ROADMAP.md**: 新增 Phase 5.5 搜尋紀錄驗證機制

---

## [0.2.2] - 2025-12-18 (Previous)

### Added

- **完整靜態分析工具鏈**
  - Ruff linter/formatter: 修復 1839 個錯誤
  - Mypy 類型檢查: 修復 49 個類型錯誤
  - Bandit 安全掃描: 7 個 Low severity 已加 `# nosec` 註解
  - Vulture 死代碼檢測: 0 個問題
- **開發模式切換功能** (`.copilot-mode.json`)
  - `development`: 完整功能（所有 skills、Memory Bank 同步、靜態分析）
  - `normal`: 一般使用（僅研究技能）
  - `research`: 專注寫作（只同步專案 .memory/）
- **test-generator SKILL 擴展**
  - 新增 Bandit/Vulture 工具文檔
  - 新增 `# nosec` 註解使用指南
  - 完整執行流程說明

### Changed

- **代碼品質改進**
  - 所有 `import *` 改為明確導入
  - 所有 `except:` 改為 `except Exception:`
  - 統一使用 ruff format 風格
  - 修復所有 Optional type hints
- **pyproject.toml** - 新增 dev 依賴: `bandit>=1.9.2`, `vulture>=2.14`

### Fixed

- **類型錯誤修復**
  - `concept_validator.py`: 修正 `result` 變數衝突
  - `project_context.py`: 使用 `get_project_info()` 替代 `get_current_project()`
  - `writing.py`: 修正 `Optional[str]` 回傳類型
  - 多處 `dict/list` 變數加入明確類型註解

---

## [0.2.1] - 2025-12-18 (靜態分析大掃除)

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

[0.3.5]: https://github.com/u9401066/med-paper-assistant/compare/v0.3.1...v0.3.5
[0.2.2]: https://github.com/u9401066/med-paper-assistant/compare/v0.2.0...v0.2.2
[0.2.0]: https://github.com/u9401066/med-paper-assistant/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/u9401066/med-paper-assistant/releases/tag/v0.1.0
