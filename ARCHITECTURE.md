# MedPaper Assistant — Architecture

## Overview

MedPaper Assistant 是一個**以 Copilot Agent Mode 為核心的醫學論文寫作環境**。

它不是一個獨立的應用程式，而是一組 MCP Server + VS Code Extension + Copilot Skills，讓研究者在 VS Code 中完成從文獻搜尋到 Word/LaTeX 匯出的完整論文流程。

```
┌─────────────────────────────────────────────────────────────────┐
│  VS Code                                                        │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  Copilot Agent Mode（大腦 / 編排層）                       │  │
│  │  Skills + Prompts 定義 SOP                                │  │
│  └────────┬──────────┬──────────┬──────────┬─────────────────┘  │
│           │          │          │          │                     │
│      ┌────▼───┐ ┌────▼───┐ ┌───▼────┐ ┌──▼──────┐             │
│      │mdpaper │ │pubmed- │ │  cgu   │ │ drawio  │  MCP        │
│      │  MCP   │ │search  │ │  MCP   │ │  MCP    │  Servers    │
│      └────┬───┘ └────────┘ └────────┘ └─────────┘             │
│           │                                                     │
│      ┌────▼──────────────────────────────────────┐             │
│      │  projects/{slug}/                          │  Shared     │
│      │    concept.md · drafts/ · references/      │  Filesystem │
│      └───────────────────────────────────────────┘             │
│           │              │                                      │
│      ┌────▼───┐     ┌───▼──────┐                               │
│      │  Foam  │     │Dashboard │  VS Code Extensions            │
│      │ (refs) │     │(Next.js) │                                │
│      └────────┘     └──────────┘                               │
└─────────────────────────────────────────────────────────────────┘
```

**核心設計原則**：檔案系統是共享狀態。所有元件（MCP Server、Dashboard、Foam）讀寫同一個 `projects/` 目錄。

---

## MCP Server（DDD Architecture）

主要的 Python MCP Server，提供 88 個 tools，另暴露 3 個 prompts 與 3 個 resources。

### 層級結構

```
src/med_paper_assistant/
├── domain/                          # 領域層：純業務邏輯，無外部依賴
│   ├── entities/                    # 實體
│   │   ├── project.py              #   Project（專案）
│   │   ├── reference.py            #   Reference（文獻）
│   │   └── draft.py                #   Draft（草稿）
│   ├── value_objects/               # 值物件
│   │   ├── reference_id.py         #   ReferenceId（PMID > Zotero > DOI）
│   │   ├── citation.py             #   Citation
│   │   └── search_criteria.py      #   SearchCriteria（Pydantic）
│   ├── services/                    # 領域服務
│   │   ├── reference_converter.py  #   多來源文獻轉換
│   │   ├── novelty_scorer.py       #   新穎性評分
│   │   ├── citation_formatter.py   #   引用格式化
│   │   ├── wikilink_validator.py   #   [[wikilink]] 驗證
│   │   └── pre_analysis_checklist.py
│   └── paper_types.py              # 論文類型定義
│
├── application/                     # 應用層：Use Case 編排
│   └── use_cases/
│       ├── save_reference.py       #   儲存文獻（MCP-to-MCP 驗證流程）
│       └── create_project.py       #   建立專案
│
├── infrastructure/                  # 基礎設施層：外部世界的實作
│   ├── persistence/                 # 持久化
│   │   ├── project_manager.py      #   專案 CRUD + Exploration
│   │   ├── reference_manager.py    #   文獻存儲
│   │   ├── project_repository.py   #   專案 Repository
│   │   ├── reference_repository.py #   文獻 Repository
│   │   ├── file_storage.py         #   檔案儲存抽象
│   │   ├── workspace_state_manager.py  # 跨 Session 狀態
│   │   ├── project_memory_manager.py   # AI 記憶管理
│   │   ├── pipeline_gate_validator.py  # Phase Gate 驗證器
│   │   ├── quality_scorecard.py        # 品質計分卡（8 維度）
│   │   ├── hook_effectiveness_tracker.py # Hook 效能追蹤
│   │   ├── meta_learning_engine.py     # D1-D8 自我學習引擎
│   │   ├── evolution_verifier.py       # 跨專案演化驗證
│   │   ├── writing_hooks/              # 寫作 Hooks 套件
│   │   │   ├── _constants.py           #   常數 + Anti-AI 詞庫
│   │   │   ├── _models.py              #   HookIssue / HookResult
│   │   │   ├── _text_utils.py          #   文字處理 Mixin
│   │   │   ├── _journal_config.py      #   期刊設定 Mixin
│   │   │   ├── _post_write.py          #   A 系列 Hooks (A1-A6, A3b)
│   │   │   ├── _section_quality.py     #   B 系列 Hooks (B8-B16)
│   │   │   ├── _manuscript.py          #   C 系列 Hooks (C3-C13)
│   │   │   ├── _data_artifacts.py      #   F 系列 Hooks (F1-F4)
│   │   │   ├── _precommit.py           #   P 系列 Hooks (P5, P7)
│   │   │   ├── _git.py                 #   G 系列 Hooks (G9)
│   │   │   └── _engine.py              #   WritingHooksEngine 組合類
│   │   └── data_artifact_tracker.py    # 資料溯源追蹤
│   │   └── review_hooks.py             # R1-R6 審查品質 Hook（Phase 7 HARD GATE）
│   ├── services/                    # 外部服務
│   │   ├── drafter.py              #   草稿撰寫 + wikilink 引用
│   │   ├── formatter.py            #   引用格式化（Vancouver/APA/...）
│   │   ├── analyzer.py             #   統計分析 + Table 1
│   │   ├── concept_validator.py    #   概念驗證（Three Reviewers Model）
│   │   ├── word_writer.py          #   Word 文件操作
│   │   ├── template_reader.py      #   Word 模板解析
│   │   ├── exporter.py             #   Legacy Word 匯出
│   │   ├── foam_settings.py        #   Foam 設定動態更新
│   │   ├── pubmed_api_client.py    #   MCP-to-MCP HTTP client
│   │   ├── citation_assistant.py   #   引用助手
│   │   ├── concept_template_reader.py
│   │   └── prompts.py              #   Section 寫作指引
│   ├── external/                    # 外部 MCP 整合
│   ├── config.py                    # 配置
│   └── logging.py                   # 日誌
│
├── interfaces/                      # 介面層：MCP Protocol 對接
│   └── mcp/
│       ├── server.py               #   create_server() → FastMCP
│       ├── __main__.py             #   Entry point（python -m）
│       ├── config.py               #   SERVER_INSTRUCTIONS
│       ├── instructions.py         #   動態指令生成
│       ├── prompts/                #   MCP Prompts
│       ├── resources.py            #   MCP Resources
│       └── tools/                  #   MCP Tools（7 groups）
│           ├── project/            #     CRUD, settings, exploration, diagrams
│           ├── reference/          #     save, search, format, citations
│           ├── draft/              #     write, read, cite, templates
│           ├── validation/         #     concept validation, novelty
│           ├── analysis/           #     stats, Table 1, plots
│           ├── review/             #     audit hooks, pipeline gates, writing hooks
│           ├── export/             #     Word document pipeline
│           ├── discussion/         #     debate/discussion tools
│           └── _shared/            #     共用 helpers
│
└── shared/                          # 共用
    ├── constants.py
    └── exceptions.py
```

### 依賴方向

```
interfaces → application → domain ← infrastructure
     │              │          ↑           │
     │              │          │           │
     └── MCP ───────┘    純邏輯/無依賴  ───┘
```

- **Domain** 不依賴任何外部套件（除 Pydantic）
- **Application** 只依賴 Domain
- **Infrastructure** 實作 Domain 定義的介面
- **Interfaces** 將 MCP Protocol 對接到 Application/Infrastructure

---

## Self-Evolution Architecture（CONSTITUTION §22-23）

系統具備**可審計的閉環自我改進能力**，透過 Hook D（Meta-Learning）在每次 pipeline 完成後分析品質數據，自動調整閾值和累積經驗。

### 循環架構

```
Pipeline Run（Phase 1-9）
    │
    │  Hook A/B/C/E/F 在寫作過程中即時觸發
    │  record_hook_event() 記錄每次 hook 的 trigger/pass/fix/false_positive
    │
    ▼
Phase 6: Quality Audit
    │  run_quality_audit() → 8 維度品質計分（0-10）
    │  generate_report() → quality-scorecard.yaml + .md
    │
    ▼
Phase 10: Meta-Learning（Hook D1-D9）
    │  run_meta_learning() → 分析 hook 效能 + 品質數據
    │  D1: Hook 效能統計分析
    │  D2: 品質計分卡趨勢
    │  D3: 閾值自動調整（±20%，CONSTITUTION §23）
    │  D4-D5: SKILL.md / AGENTS.md 改進建議
    │  D6: Audit trail 生成
    │  D7: Review 回顧性分析
    │  D8: EQUATOR 合規回顧
    │  D9: 品質趨勢分析
    │
    ▼
verify_evolution() → 跨專案演化驗證
    E1: 閾值自我調整證據
    E2: 經驗累積（Lessons Learned）
    E3: Hook 覆蓋廣度
    E4: 品質量測存在性
    E5: 跨專案比較可能性
```

### 元件責任

| 元件                         | 檔案                            | 職責                                                                                                   |
| ---------------------------- | ------------------------------- | ------------------------------------------------------------------------------------------------------ |
| **QualityScorecard**         | `quality_scorecard.py`          | 8 維度品質評分持久化（citation, methodology, text, concept, format, figure, equator, reproducibility） |
| **HookEffectivenessTracker** | `hook_effectiveness_tracker.py` | 追蹤 78 個 Hook 的 trigger/pass/fix/FP 事件，計算效能指標                                              |
| **MetaLearningEngine**       | `meta_learning_engine.py`       | D1-D9 分析引擎：統計分析 → 閾值建議 → 經驗萃取 → 審計紀錄 → 品質趨勢                                   |
| **WritingHooksEngine**       | `writing_hooks/` (package)      | Code-enforced hooks：A/B/C/F/G/P 系列，Mixin 架構；12 子模組                                           |
| **ReviewHooksEngine**        | `review_hooks.py`               | R1-R6 審查品質 Hook：報告深度、回應完整、EQUATOR、追蹤性、Anti-AI、引用預算（Phase 7 HARD GATE）       |
| **EvolutionVerifier**        | `evolution_verifier.py`         | 跨專案演化驗證：收集所有專案 `.audit/` 數據，產生演化證據報告                                          |
| **DomainConstraintEngine**   | `domain_constraint_engine.py`   | Triad-inspired JSON 約束系統：per paper type 結構化約束、Sand Spreader 驗證、約束演化                  |
| **PipelineGateValidator**    | `pipeline_gate_validator.py`    | Phase Gate 驗證器：確保每個 Phase 完成必要的品質檢查才能進入下一階段                                   |
| **WorkspaceStateManager**    | `workspace_state_manager.py`    | 跨 Session 狀態管理：writing_session 自動存檔、recovery summary、checkpoint_writing_context            |

### 自我改進邊界（CONSTITUTION §23）

| 層級           | 行為                                                                              | 限制                   |
| -------------- | --------------------------------------------------------------------------------- | ---------------------- |
| L1 Skill       | 更新 SKILL.md Lessons Learned                                                     | 自動，無需確認         |
| L2 Hook        | 調整 Hook 閾值                                                                    | ±20%，記錄 audit trail |
| L3 Instruction | 事實性內容修改                                                                    | 記錄 decisionLog       |
| **禁止**       | 修改 CONSTITUTION 原則、🔒 保護內容規則、save_reference_mcp 優先規則、Hook D 本身 | —                      |

### Hook 架構（78 checks — 55 Code-Enforced / 23 Agent-Driven）

| 類型                  | 時機            | 數量 | 重點                                                                                                                                                                                     |
| --------------------- | --------------- | ---- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **A** post-write      | 每次寫入後      | 9    | 字數、引用密度、Anti-AI、Wikilink、語言一致性(A5)、段落重複(A6)、AI結構信號(A3b)、語體一致性(A3c)、文獻充足性(A7)                                                                        |
| **B** post-section    | section 完成後  | 16   | 概念一致、🔒保護、方法學、寫作順序、Brief 合規、統計對齊(B8)、時態(B9)、段落品質(B10)、Results客觀性(B11)、Intro結構(B12)、Discussion結構(B13)、倫理聲明(B14)、Hedging(B15)、效果量(B16) |
| **C** post-manuscript | 全稿完成後      | 13   | 全稿一致性、投稿清單、數量交叉引用、時間一致性、補充材料交叉引用(C9)、全文驗證(C10)、引用分布(C11)、引用決策審計(C12)、圖表品質(C13)                                                     |
| **D** meta-learning   | Phase 10        | 9    | SKILL/Hook 自我改進、Review Retro、EQUATOR Retro、D9 品質趨勢                                                                                                                            |
| **E** EQUATOR 合規    | Phase 7 每輪    | 5    | 報告指引偵測、checklist 驗證、合規報告                                                                                                                                                   |
| **F** data-artifacts  | post-manuscript | 4    | 溯源追蹤、manifest 一致、交叉引用、統計驗證                                                                                                                                              |
| **R** review-hooks    | Phase 7 submit  | 6    | R1 報告深度、R2 回應完整、R3 EQUATOR、R4 追蹤性、R5 Anti-AI、R6 引用預算（Phase 7 HARD GATE）                                                                                            |
| **P** pre-commit      | git commit 前   | 8    | 引用、Anti-AI、概念、字數、🔒、.memory、文獻、方法學                                                                                                                                     |
| **G** general         | git commit 前   | 8    | Memory、README、CHANGELOG、ROADMAP、架構、專案一致性                                                                                                                                     |

### Domain Constraint Engine（Triad-inspired）

受 Triad Engine 啟發的結構化 JSON 約束系統。將「自然語言 SKILL.md 指令」轉為「可演化的 JSON Domain Guide」。

**核心概念對應**：

| Triad Engine      | MedPaper 對應                                        |
| ----------------- | ---------------------------------------------------- |
| JSON Domain Guide | `DomainConstraintEngine` 約束模板                    |
| Multi-Agent 議事  | Hook 層級 A/B/C/E/F（已有）                          |
| Sand Spreader     | `validate_against_constraints()`                     |
| 約束演化          | `MetaLearningEngine.suggest_constraint_evolutions()` |

**演化流程**：

```
Hook A/B/C 在寫作中偵測到重複模式
    │
    ▼
Phase 10: MetaLearningEngine.analyze()
    │  suggest_constraint_evolutions() 萃取結構化約束建議
    │
    ▼
DomainConstraintEngine.evolve()
    │  新增 learned constraint 到 .constraints/learned-constraints.json
    │  記錄 evolution log 到 .constraints/constraint-evolution.json
    │
    ▼
下次 Pipeline: validate_against_constraints()
    自動應用 base + learned 約束
```

**約束類別**：`statistical` · `structural` · `vocabulary` · `evidential` · `temporal` · `reporting` · `boundary`

**安全邊界**：Learned constraint 僅能**提升** severity（WARNING→CRITICAL），不能弱化。Base constraint 不可移除。

---

## External MCP Servers

Copilot Agent Mode 同時連接多個 MCP Server：

| Server | 來源 | 用途 | Tools 數量 |
| --- | --- | --- | --- |
| **mdpaper** | 本專案 | 專案管理、草稿、引用、審查、匯出；另含 3 prompts / 3 resources | 88 |
| **pubmed-search** | `integrations/pubmed-search-mcp/` (submodule) | PubMed 文獻搜尋 | 37 |
| **cgu** | `integrations/cgu/` (submodule) | 創意發想（快思慢想） | 13 |
| **drawio** | `uv run --directory integrations/next-ai-draw-io/mcp-server python -m drawio_mcp_server` → fallback `node integrations/drawio-mcp/src/index.js` → `npx -y @drawio/mcp` | CONSORT/PRISMA 圖表 | ~5 |
| **zotero-keeper** | `uvx zotero-keeper` | Zotero 書目管理 | ~15 |

### MCP-to-MCP 通訊

文獻儲存採用**分層信任架構**，避免 Agent 幻覺污染書目資料：

```
Agent: "存這篇 PMID:24891204"
    │
    │  只傳 PMID + agent_notes
    ▼
mdpaper MCP: save_reference_mcp(pmid="24891204")
    │
    │  Direct HTTP API（不經過 Agent）
    ▼
pubmed-search MCP: /api/cached_article/24891204
    │
    │  回傳驗證過的 PubMed 資料
    ▼
Reference file:
  🔒 VERIFIED: title, authors, journal（PubMed 原始資料，不可修改）
  🤖 AGENT:    notes, relevance（AI 產生，清楚標記）
  ✏️ USER:     highlights（人類筆記，AI 不碰觸）
```

---

## VS Code Extension

[vscode-extension/](vscode-extension/) — TypeScript，提供五個 commands 與十個 chat commands：

1. **MCP Server 註冊**：在 workspace 沒有自行管理 `.vscode/mcp.json` 時，自動註冊 mdpaper，並依環境條件註冊 cgu、pubmed-search、zotero-keeper、drawio
2. **Chat Participant**：`@mdpaper` with 10 commands (`/search`, `/draft`, `/concept`, `/project`, `/format`, `/autopaper`, `/drawio`, `/analysis`, `/strategy`, `/help`)
3. **Commands**：`mdpaper.startServer`, `mdpaper.stopServer`, `mdpaper.showStatus`, `mdpaper.autoPaper`, `mdpaper.setupWorkspace`
4. **Workspace Bootstrap**：複製 14 個 bundled skills、13 個 bundled prompts、9 個 reviewer agents、`copilot-instructions.md`、期刊模板

---

## Foam Integration

Foam (VS Code extension) 提供論文引用的知識圖譜功能：

- 每篇文獻存為 Markdown note（含 YAML frontmatter）在 `projects/{slug}/references/{pmid}/`
- 草稿中用 `[[citation_key]]` wikilink 引用
- `Drafter.sync_references_from_wikilinks()` 掃描 wikilinks 產生 References section
- `foam_settings.py` 動態切換專案範圍（只顯示當前專案的引用圖譜）
- Hover preview 顯示論文摘要，autocomplete 補全論文標題

---

## Dashboard

[dashboard/](dashboard/) — Next.js + React + Tailwind，嵌入 VS Code Simple Browser：

- 專案切換 UI
- 寫作進度追蹤
- 內嵌 Draw.io 編輯器
- 與 MCP Server 共享同一個 `projects/` 目錄（直接讀檔案系統）

---

## Copilot Skills & Prompts

行為指引層（不是代碼，是 Copilot 的 SOP）：

| 類型 | 位置 | 數量 | 作用 |
| --- | --- | --- | --- |
| **Skills** | `.claude/skills/*/SKILL.md` | 26 | 單一任務的知識（如何組合 tools） |
| **Prompts** | `.github/prompts/*.prompt.md` | 15 | 高層編排（多 skill 組合的工作流程） |
| **Hooks** | `.github/hooks/*.json` | 1 | deterministic runtime guard for mode/protected-path policy |
| **Bylaws** | `.github/bylaws/*.md` | 4 | 規範（架構、git、memory、python 環境） |
| **Instructions** | `.github/copilot-instructions.md` | 1 | 全域指引入口 |

補充：Skill/Prompt 文件中的 Hook A/B/C/D 屬於 workflow-level 指引與審計慣例；真正會在 VS Code agent 執行期 deterministic 攔截的，是 `.github/hooks/` 中的 official hook configuration。

補充：`.github/copilot-instructions.md` 是目前 VS Code extension 打包與 `Setup Workspace` 流程使用的 authoritative workspace instructions 檔；`AGENTS.md` 保留做 repo-level 相容與人類閱讀入口。

層級關係：

```
Capability (Prompt) = 編排多個 Skills 完成完整任務
Skill               = 知道如何使用多個 Tools
Tool                = 單一 MCP 操作
```

---

## Project Structure（每個研究專案）

```
projects/{slug}/
├── project.json          # 專案元資料（paper_type, sections, status）
├── concept.md            # 研究概念（NOVELTY STATEMENT, KEY SELLING POINTS）
├── .memory/              # AI 記憶
│   ├── activeContext.md  #   當前工作焦點
│   └── progress.md       #   研究進度
├── drafts/               # 論文草稿（Markdown）
├── references/           # 文獻（每個 PMID 一個子目錄）
│   └── {pmid}/
│       └── metadata.json
├── data/                 # 分析用 CSV
└── results/              # 匯出結果（.docx, figures）
```

---

## Key Workflows

### 1. 文獻搜尋 → 儲存

```
pubmed-search: search_literature(query)
    → Agent 選擇文獻
    → mdpaper: save_reference_mcp(pmid) → Direct API → 驗證資料存入 references/
```

### 2. 草稿撰寫

```
mdpaper: get_section_template(section)
    → Agent 撰寫內容
    → mdpaper: write_draft(filename, content)
    → 草稿中用 [[wikilink]] 引用文獻
    → mdpaper: sync_references() → 掃描 wikilinks → 產生 References section
```

### 3. Word 匯出

```
mdpaper: list_templates() → read_template()
    → mdpaper: start_document_session()
    → mdpaper: insert_section() × N
    → mdpaper: check_word_limits()
    → mdpaper: save_document()
```

### 4. 概念驗證

```
mdpaper: validate_concept(concept.md)
    → Three Reviewers Model（Methodology, Evidence, Clinical Impact）
    → Novelty Score ≥ 75 → 允許開始撰寫草稿
```

---

## Citation Styles

| Style     | 範例                                                      |
| --------- | --------------------------------------------------------- |
| Vancouver | `[1] Kim SH, Lee JW. Title. Journal 2024; 1: 1-10.`       |
| APA       | `Kim, S.H., Lee, J.W. (2024). Title. *Journal*, 1, 1-10.` |
| Harvard   | `Kim, S.H. (2024) 'Title', *Journal*, vol. 1, pp. 1-10.`  |
| Nature    | `1. Kim SH, Lee JW. Title. Journal 1, 1-10 (2024).`       |
| AMA       | `1. Kim SH, Lee JW. Title. Journal 1, 1-10 (2024).`       |

---

## Dependencies

### Python (managed by uv)

| 套件                     | 用途                       |
| ------------------------ | -------------------------- |
| `mcp[cli]`               | Model Context Protocol SDK |
| `python-docx`            | Word 文件操作              |
| `pandas`                 | 資料分析                   |
| `scipy`                  | 統計檢定                   |
| `matplotlib` / `seaborn` | 繪圖                       |
| `pydantic`               | 資料驗證                   |
| `structlog`              | 結構化日誌                 |
| `tabulate`               | 表格格式化                 |
| `httpx`                  | MCP-to-MCP HTTP 通訊       |

### Dev Tools

| 工具         | 用途                       |
| ------------ | -------------------------- |
| `uv`         | 套件管理（唯一，禁止 pip） |
| `ruff`       | Lint + Format              |
| `mypy`       | Type checking              |
| `bandit`     | Security scanning          |
| `pytest`     | Testing                    |
| `pre-commit` | Git hooks                  |

---

## Workspace Layout

```
med-paper-assistant/
├── src/med_paper_assistant/    # MCP Server（DDD）
├── integrations/               # 外部 MCP Servers（git submodules）
│   ├── pubmed-search-mcp/      #   PubMed 搜尋
│   └── cgu/                    #   創意發想
├── vscode-extension/           # VS Code Extension
├── dashboard/                  # Next.js Dashboard
├── templates/                  # Word 模板（.docx）
├── projects/                   # 研究專案（每個 slug 一個目錄）
├── tests/                      # 測試
├── scripts/                    # 工具腳本
├── docs/                       # 設計文件
├── memory-bank/                # 全域 AI 記憶
├── .claude/skills/             # Copilot Skills（26 個）
├── .github/prompts/            # Copilot Prompts（15 個）
├── .github/bylaws/             # 規範（4 個）
└── .pre-commit-config.yaml     # Git hooks
```
