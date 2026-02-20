# Progress (Updated: 2026-02-20)

## Done (Recent)

- **Citation-Aware Editing (Layer 1+2) (2026-02-20)** ✅：
  - `get_available_citations()` — 列出所有可用 [[citation_key]]
  - `patch_draft(filename, old_text, new_text)` — 部分編輯 + wikilink 驗證
  - 14 個測試，全部通過
  - SKILL.md 新增 Flow D、copilot-instructions.md 新增引用規則

- **Code Review & Fixes (2026-02-20)** ✅：
  - Pydantic V2 遷移：`SearchCriteria` class Config → model_config = ConfigDict
  - wikilink_validator.py：移除未使用的 match.group(1)
  - writing.py：list_drafts/read_draft/delete_draft 路徑解析改用 _get_drafts_dir()
  - CHANGELOG 更新：新增 Citation-Aware Editing + Phase 3.5 紀錄
  - ROADMAP 更新：Phase 3.5 加入 Citation-Aware Editing 完成項
  - 32 passed / 1 skipped / 2 warnings（Pydantic 警告已消除）

- **Infrastructure & Quality Cleanup 大整理 (2026-02-20)** ✅：
  - Pre-commit hooks：13 hooks (ruff, mypy, bandit, pytest, whitespace…) 全部通過
  - DDD Import 遷移：19 個測試檔從 `core.*` 遷移至 DDD 路徑
  - Test Isolation：所有測試改用 `tmp_path` fixture
  - ARCHITECTURE.md 重寫：448 行過時 → ~240 行精確 DDD 架構文檔
  - Legacy Cleanup：刪除空的 `core/` 目錄、多餘腳本、散落檔案
  - Copilot Hook 修復：AGENTS.md 補齊 7 skills + 8 prompts，修正 capability index
  - Coverage Baseline：17 passed / 1 skipped / 26 integration-deselected (27%)
  - ROADMAP 更新：新增 Phase 3.5 + Phase 5c (Full VSX + Pandoc)
  - 架構方向決策：選定 **Direction C: Full VSX + Foam + Pandoc**

- **AI Writing Intelligence 設計文件 (2026-01-13)** ✅：
  - 新增 `docs/design/ai-writing-intelligence.md` (500 行)
  - 定義三大問題：連貫性、引用、思考脈絡
  - Citation Intelligence MVP 設計：4 個工具
  - 技術選型：sentence-transformers, spaCy, Rule-based
  - 4 週實作計畫
  - ROADMAP 更新：新增 Phase 8

- **Tool Description 精簡 (2026-01-12)** ✅：
  - 71 個 MCP 工具 docstring 精簡
  - Token 節省：350→80 tokens (-77%)
  - 總節省：~19,170 tokens

- **Python 3.12 遷移 (2026-01-12)** ✅：
  - pyproject.toml 更新 requires-python
  - UV 管理重建環境
  - 統一 Python 3.12.12

- **Tool Consolidation Planning (2026-01-12)** ✅：
  - 新增 `docs/design/tool-consolidation-plan.md`
  - 確認 MCP 限制：Action 參數不適合、無法分段載入
  - 決定策略：描述精簡為主
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
- **Dashboard UI 增強 (2025-12-17)** ✅：
  - **Dark Mode**: 完整深色主題支援
    - `ThemeProvider.tsx` + `ThemeToggle.tsx` 元件
    - localStorage 持久化、預設深色
    - 所有元件加入 `dark:` Tailwind 類別
  - **Progress Panel**: 專案進度面板
    - `ProgressPanel.tsx` 新增 Progress Tab
    - `/api/projects/[slug]/stats` API endpoint
    - Concept 驗證狀態、Pre-Analysis 進度、Word counts
  - **ProjectCard Stats**: 卡片顯示即時統計
  - **Next.js 16.0.10**: 升級至最新版
    - `npm audit fix --force` 修復安全漏洞
    - 0 vulnerabilities
  - **VS Code 整合**: tasks.json、open-dashboard.ps1
- **分層驗證系統 (Tiered Validation) (2025-01-XX)** ✅：
  - 不同 paper type 有不同驗證需求
  - 按 target section 動態調整驗證範圍
  - `required`（blocking）vs `recommended`（warning only）
  - 新工具：`validate_for_section(section, project)`
  - 修復 selling_points 和 section content 偵測邏輯
  - SKILL.md 文檔更新
- **Skill 檔案精簡與觸發詞優化 (2025-01-XX)** ✅：
  - concept-development: 480→120 行
  - test-generator: 518→129 行
  - literature-review: 364→117 行
  - 所有 skill 增加更多觸發詞（中英文、常見用語）
  - 新增「驗證失敗處理流程」在 concept-development
  - AGENTS.md skill 表格同步更新
- **完整靜態分析修復 (2025-01-XX)** ✅：
  - Ruff: 1839 個錯誤 → 0
  - Mypy: 49 個錯誤 → 0
  - Bandit: 7 個 Low 級別 → 0（加入 nosec 註解）
  - Vulture: 0 死代碼
  - 新增 dev dependencies: bandit, vulture
  - 修復範圍：
    - Bare except → `except Exception`
    - `import *` → 明確 import
    - Implicit Optional → 明確 `Optional[T]`
    - Variable type conflicts → 重新命名
    - API confusion (`get_current_project` vs `get_project_info`)
    - Enum value extraction
    - Security nosec 註解（有意的 try_except_pass, subprocess）
  - test-generator SKILL.md 更新：完整靜態分析工具說明
- **開發模式 Toggle 系統 (2025-01-XX)** ✅：
  - `.copilot-mode.json` 配置檔
  - 三種模式：development / normal / research
  - AGENTS.md 模式說明章節
  - copilot-instructions.md 更新
- **VS Code Extension MCP 啟動修復 (2026-01-05)** ✅：
  - 修復 `uvx` 誤用 `-m` 參數導致的啟動失敗
  - 增強 `getPythonPath` 自動偵測 `.venv` 邏輯
  - 支援 `uv` 和 `uvx` 作為 `pythonPath` 設定
  - 開發模式下自動將 `src/` 加入 `PYTHONPATH`
- **全專案 uv 標準化 (2026-01-05)** ✅：
  - `scripts/setup.sh` & `setup.ps1` 遷移至 `uv sync`
  - `CONTRIBUTING.md` 更新為 `uv` 導向流程
  - `integrations/` 所有文檔更新為 `uv` / `uvx`
  - `.github/bylaws/python-environment.md` 強化 `uv` 規範並棄用 `pip`
  - `reference_manager.py` 錯誤訊息更新為 `uv add`
  - 確保所有套件管理與環境建立均使用 `uv` 工具鏈
- **Novelty Check 強化：三位審稿人模型 (2026-01-05)** ✅：
  - 實作 `Three Reviewers Model` (Skeptic, Methodologist, Clinical Impact Expert)
  - 每個審稿人有獨立的評分邏輯與質疑點
  - 報告新增 `Reviewer Panel` 表格，顯示各別分數與評論
  - 整合 CGU `deep_think` 進行壓力測試建議
  - 強化「犀利回饋」模式，直指證據缺失與量化不足問題
- **寫作邏輯優化：去 AI 味與證據導向 (2026-01-05)** ✅：
  - 更新 `SECTION_PROMPTS` 引入 `Anti-AI Writing Rules` 與 `Evidence Funnel` 結構
  - 強化 `draft_section` 工具：自動從已存文獻提取摘要與數據作為寫作背景
  - 禁止模糊開場（如 "In recent years..."）與機械式轉折語
  - `SKILL.md` 更新：明確規範「證據導向」的撰寫流程
- **智慧引用助手 (Citation Assistant) (2026-01-06)** ✅：
  - 新增 `CitationAssistant` 核心服務類
    - `analyze_text()` - 分析文字中需要引用的聲稱
    - `suggest_for_selection()` - 為選取文字提供引用建議
    - `scan_draft_for_citations()` - 掃描整篇草稿
  - 聲稱類型識別：Statistical / Comparison / Guideline / Mechanism / Definition
  - 本地文獻庫搜尋 + 相關性評分
  - 自動生成 PubMed 搜尋建議
  - 新增 MCP 工具：
    - `suggest_citations(text)` - 分析文字並建議引用
    - `scan_draft_citations(filename)` - 掃描整篇草稿
    - `find_citation_for_claim(claim, claim_type)` - 針對特定聲稱類型搜尋
  - 輸出 Foam 相容的 `[[citation_key]]` 格式
- **CRUD 盤點完成 (2026-01-06)** ✅：
  - 完成 52 個 MCP 工具的 CRUD 分類盤點
  - 識別關鍵缺口：所有 6 個 Entity 皆無 Delete 操作
  - ROADMAP 更新 Phase 4.5 加入 Delete 操作補齊計畫
  - 優先級排序：Reference Delete > Draft Delete > Project Archive
- **CRUD Delete 操作實作 (2026-01-06)** ✅：
  - `delete_reference(pmid, confirm)` - 刪除文獻（兩階段確認）
  - `delete_draft(filename, confirm)` - 刪除草稿（兩階段確認）
  - `archive_project(slug, confirm)` - 軟刪除/封存專案
  - `delete_project(slug, confirm)` - 永久刪除專案
  - 工具數量：52 → 56 個
- **Phase 4 MVP 核心工具實作 (2026-01-06)** ✅：
  - **Analysis Tools** (`tools/analysis/`):
    - `generate_table_one` - Table 1 自動生成 (mean±SD, p-values)
    - `detect_variable_types` - 自動偵測連續/類別變數
    - `list_data_files` - 列出可用資料檔案
    - `analyze_dataset` - 描述性統計
    - `run_statistical_test` - t-test, ANOVA, chi2, correlation 等
    - `create_plot` - 統計圖表 (boxplot, scatter, histogram 等)
  - **Review Tools** (`tools/review/`):
    - `check_manuscript_consistency` - 稿件一致性檢查
      - 引用一致性（PMID 存在檢查、未引用文獻）
      - 數字一致性（N 值檢查）
      - 縮寫定義檢查
      - Table/Figure 連續性
      - p 值格式一致性
    - `create_reviewer_response` - Reviewer 回覆模板生成
      - structured/table/letter 三種格式
      - 自動解析審稿意見
    - `format_revision_changes` - 修改差異格式化
  - 工具數量：56 → 65 個

## Doing

- 無

## Next

### 🔥 Phase 5c: Full VSX + Pandoc Export (優先)

| 功能 | 說明 |
|------|------|
| TreeView: Projects | 側邊欄專案清單 + 狀態 |
| CodeLens: Citations | [[wikilink]] 上方顯示引用資訊 |
| Diagnostics | 引用缺失、wikilink 斷鏈警告 |
| Pandoc Word Export | 取代 python-docx 匯出 |
| Pandoc LaTeX Export | 新增 LaTeX 雙輸出 |
| CSL Citation Styles | 取代手動格式化 |

### Phase 4 剩餘

| 工具 | 說明 |
|------|------|
| `generate_cover_letter` | Cover Letter 自動生成 |
| `check_submission_checklist` | 期刊投稿清單檢查 |

### Phase 5: Project Portfolio Management (2026 Q2)

| 功能 | 說明 |
|------|------|
| Dashboard 2.0 | Kanban + Timeline + Milestone 追蹤 |
| 跨專案文獻庫 | 全域 references/ + 專案引用清單 |
| 專案模板庫 | Original Research / SR / Meta / Case Report |

### Phase 6: Systematic Review Pipeline (2026 Q3)

| 功能 | 說明 |
|------|------|
| PRISMA 流程工具 | 篩選介面 + 自動生成流程圖 |
| Risk of Bias | RoB 2.0, ROBINS-I, NOS 評估 |
| Meta-analysis | Forest plot, Heterogeneity, Subgroup |

### Phase 7: AI Automation Enhancement (2026 Q4)

| 功能 | 說明 |
|------|------|
| Concept → Full Draft | 自動從 concept.md 生成完整初稿 |
| Smart Citation | 類似 Grammarly 的引用建議 |
| Cross-section Auto-fix | 自動同步數字、術語、格式 |

### 其他待處理

- Migration script 更新現有參考文獻到新格式
- 批量更新舊 reference 的內容順序（Abstract 在前）
- 加入環境變數 `PUBMED_MCP_API_URL` 配置
