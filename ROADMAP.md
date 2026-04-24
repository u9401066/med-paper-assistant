# 🗺️ MedPaper Assistant Roadmap

## Vision

成為醫學研究人員從文獻探索到論文發表的完整 AI 輔助平台。
**支援多個論文專案並行管理，確保每篇論文都達到頂尖期刊標準。**

### 核心價值：逐步多輪演進（Iterative Multi-Round Evolution）

> **寫論文是人類高度專業化、多年累積、多輪訓練的結果，而且是在科學方法下可重現的思考與整合步驟。** > **Agent + MCP 框架應該有能力實現類似的逐步多輪演進 — 這是我們存在的理由。**

本系統不追求「一次生成完美論文」，而是透過三層架構實現**如同人類研究者般的螺旋式進步**：

```
┌─────────────────────────────────────────────────────────────────────┐
│           三層演進架構 — 核心價值的技術實現                            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  L1: Event-Driven Hooks（即時品質）                                  │
│  ├── Agent 操作時觸發 78 個品質檢查                                  │
│  ├── 類比：研究者寫作時的即時自我檢查                                │
│  └── 例：「這句話有引用嗎？」「統計方法對嗎？」                      │
│                                                                      │
│  L2: Code-Level Enforcement（結構約束）                              │
│  ├── DomainConstraintEngine + ToolInvocationStore                    │
│  ├── 類比：內化的學術規範                                            │
│  └── 例：「研究設計要匹配統計方法」「引用要驗證」                    │
│                                                                      │
│  L3: Autonomous Self-Evolution（長期演進）                           │
│  ├── 外部排程巡邏 + GitHub Actions CI/CD                             │
│  ├── 類比：多年累積的研究直覺與跨領域整合                            │
│  └── 例：「跨專案分析，哪些 Hook 最有效？」                         │
│                                                                      │
│  三層缺一不可：                                                      │
│  只有 L1 → 每次對話重來    只有 L2 → 缺乏靈活性                     │
│  只有 L3 → 缺乏即時反饋    三層合一 → 持續螺旋式進步                │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

詳見：CONSTITUTION.md §25-26「核心哲學 — 逐步多輪演進」

---

## 📊 開發優先級總覽

```
                    ┌─────────────────────────────────────────────────────────────┐
                    │              MedPaper Assistant 發展藍圖                    │
                    ├─────────────────────────────────────────────────────────────┤
2026 Q1             │  Phase 4: MVP for Original Research ✅                      │
(Current)           │  Phase 5a: Artifact-Centric Architecture                    │
                    │  Phase 5c: Full VSX + Pandoc Export 🔥                      │
                    ├─────────────────────────────────────────────────────────────┤
2026 Q2             │  Phase 5b: Project Portfolio Management                     │
                    │  Phase 8: AI Writing Intelligence                           │
                    ├─────────────────────────────────────────────────────────────┤
2026 Q3             │  Phase 6: Systematic Review Pipeline                        │
                    │  ├── PRISMA Flow Tools                                      │
                    │  ├── Risk of Bias Assessment                                │
                    │  └── Meta-analysis Integration                              │
                    ├─────────────────────────────────────────────────────────────┤
2026 Q4             │  Phase 7: AI Automation Enhancement                         │
                    │  ├── Auto-generate Full Draft from concept.md               │
                    │  ├── Cross-section Consistency Auto-fix                     │
                    │  ├── Smart Citation Suggestions                             │
                    │  └── Self-Evolution Automation (L3) 🆕                      │
                    └─────────────────────────────────────────────────────────────┘
```

> **架構方向決策（2026-01）**：選擇 **Direction C — Full VSX + Foam + Pandoc**
>
> - VS Code Extension 升級為完整 TreeView / CodeLens / Diagnostics
> - 保留 Foam 做文獻知識圖譜
> - 新增 Pandoc 支援 LaTeX + Word 雙輸出

---

## ✅ 已完成 (Completed)

### Release Reliability & Tool Surface Hardening (2026-04)

| Feature                          | Description                                                                                                       |
| -------------------------------- | ----------------------------------------------------------------------------------------------------------------- |
| **Cross-platform Path Guard** ✅ | 全 repo filename/path 入口統一經過共享 guard，覆蓋 Linux/macOS/Windows traversal、UNC、drive、reserved names      |
| **MCP Phase 5 Surface 修復** ✅  | `draft_action(write section=...)`、`analysis_action` 資產入口、data-artifacts manifest、validation aliases 已對齊 |
| **VSX Bundled Parity** ✅        | Source 與 VS Code extension bundled Python mirror 重新同步，release 前 parity scan 無 drift                       |
| **Authority-driven Counts** ✅   | `tool-surface-authority.json` 成為 official count source；repo/VSX docs 同步至 117 full / 22 compact              |

### Phase 1: Core Features (2025-10)

| Feature            | Description              |
| ------------------ | ------------------------ |
| PubMed Integration | 搜尋、下載、參考文獻管理 |
| Draft Generation   | 智慧草稿生成、引用插入   |
| Word Export        | 匯出符合期刊格式的 .docx |
| Data Analysis      | 統計分析、Table 1 生成   |

### Phase 2: Advanced Features (2025-11 ~ 2025-12)

| Feature             | Description                  |
| ------------------- | ---------------------------- |
| Multi-Project       | 多專案管理、Exploration 模式 |
| Novelty Validation  | 研究概念原創性驗證           |
| Draw.io Integration | CONSORT/PRISMA 流程圖        |
| Skills System       | AI 工作流程引導 (.skills/)   |
| Parallel Search     | 並行搜尋、策略整合           |
| Dashboard           | 專案管理 UI                  |
| pubmed-search-mcp   | 獨立 PubMed MCP 伺服器       |

### Phase 3: Knowledge Management (2025-12 ~ 2026-01)

| Feature                      | Description                         |
| ---------------------------- | ----------------------------------- |
| Foam Integration             | Wikilinks、Hover Preview、Backlinks |
| MCP-to-MCP Communication     | 分層信任、資料完整性保證            |
| Project Memory               | `.memory/` 專案記憶系統             |
| **Three Reviewers Model**    | Novelty 三位審稿人驗證模型          |
| **Anti-AI Writing Logic**    | 去 AI 味、證據漏斗結構              |
| **uv Toolchain**             | 全專案標準化 uv 套件管理            |
| **Citation Assistant** ✨    | 智慧引用助手 - 選段落找引用         |
| **CRUD 盤點完成** ✅         | 52 工具盤點，識別 Delete 操作缺口   |
| **Tool Description 精簡** ✅ | 71 工具 docstring 精簡，-77% token  |
| **Python 3.12 遷移** ✅      | UV 管理、pyproject.toml 更新        |

### Phase 3.5: Infrastructure & Quality Cleanup (2026-01) 🆕

> **大整理：從混亂到規範化**

| Feature                                | Description                                                                                         |
| -------------------------------------- | --------------------------------------------------------------------------------------------------- |
| **Pre-commit Hooks** ✅                | 13 hooks（ruff, mypy, bandit, pytest, whitespace…）全部通過                                         |
| **DDD Import 遷移** ✅                 | 全部 19 個測試檔從 `core.*` 遷移到 DDD 路徑                                                         |
| **Test Isolation** ✅                  | 所有測試改用 `tmp_path` fixture，不再污染專案根目錄                                                 |
| **ARCHITECTURE.md 重寫** ✅            | 從 448 行過時文檔重寫為 ~240 行精確 DDD 架構文檔                                                    |
| **Legacy Cleanup** ✅                  | 刪除空的 `core/` 目錄、多餘腳本、散落檔案                                                           |
| **Copilot Hook 修復** ✅               | AGENTS.md 補齊 7 skills + 8 prompts，修正 capability index                                          |
| **Coverage Baseline** ✅               | 17 passed / 1 skipped / 26 integration-deselected（27% 覆蓋率基線）                                 |
| **架構方向決策** ✅                    | 選定 **Direction C: Full VSX + Foam + Pandoc**                                                      |
| **Citation-Aware Editing** ✅          | Layer 1 `get_available_citations` + Layer 2 `patch_draft` — 解決 Agent 繞過驗證管線的引用正確性問題 |
| **Pydantic V2 遷移** ✅                | `SearchCriteria` 從 `class Config` 遷移至 `model_config = ConfigDict`                               |
| **Code Review Clean** ✅               | unused variable 修復、路徑一致性修正、32 passed / 1 skipped                                         |
| **Tool Consolidation (Phase 8→10)** ✅ | 74→83（佔位工具實作）→76（模板轉Skill）→**53**（6策略精簡 -30%）→**77**（Self-Evolution 新增）      |

---

## 🚨 已知問題 (Known Issues) - 已大幅改善

> **2026-01 狀態更新：Issue #2, #3 已透過「三位審稿人模型」與「去 AI 味寫作邏輯」改善**

### Issue #1: 驗證機制不穩定 ⭐⭐⭐ (優先級下調)

| 問題     | 說明                                                          | 狀態      |
| -------- | ------------------------------------------------------------- | --------- |
| **現象** | Agent 不會主動去 PubMed 搜尋驗證聲稱的事實                    | ⏳ 進行中 |
| **改善** | AGENTS.md 已強化「犀利回饋」規則，要求 Agent 質疑無證據的聲稱 | ✅        |

### Issue #2: Novelty 確認機制 ~~仍在開發~~ ✅ 已改善

| 問題     | 說明                                                                    | 狀態      |
| -------- | ----------------------------------------------------------------------- | --------- |
| **現象** | ~~`validate_concept` 評分不穩定~~                                       | ✅ 已改善 |
| **改善** | **三位審稿人模型** - Skeptic / Methodologist / Clinical Expert 獨立評分 | ✅        |
| **改善** | 強化 CGU 整合，建議使用 `deep_think` 進行壓力測試                       | ✅        |

### Issue #3: AI 建議無法達到學術標準 ✅ 已改善

| 問題     | 說明                                           | 狀態      |
| -------- | ---------------------------------------------- | --------- |
| **現象** | ~~AI 給的寫作建議過於籠統~~                    | ✅ 已改善 |
| **改善** | **Anti-AI Writing Rules** - 禁止陳腔濫調       | ✅        |
| **改善** | **Evidence Funnel** - 強制引用具體數據         | ✅        |
| **改善** | `draft_section` 自動注入已存文獻的摘要作為背景 | ✅        |

### Issue #4: 跨 MCP 協調不一致 ⭐⭐ (優先級下調)

| 問題     | 說明                                             | 狀態        |
| -------- | ------------------------------------------------ | ----------- |
| **現象** | 資料流不一致                                     | ⏳ 部分改善 |
| **改善** | `save_reference_mcp` 實作 MCP-to-MCP 直接通訊    | ✅          |
| **待做** | `verify_search` HTTP API 讓 mdpaper 驗證搜尋來源 | 📋          |

---

## 🔜 Phase 4: MVP for Original Research (2026 Q1) 🔥

> **Option A 實作：讓用戶能完整寫出一篇 Original Research**

### 4.1 Table 1 自動生成 ⭐⭐⭐⭐⭐ ✅ 已完成

```
┌─────────────────────────────────────────────────────────────────────┐
│                    generate_table_one                                │
├─────────────────────────────────────────────────────────────────────┤
│  Input:                                                              │
│  ├── dataset.csv (患者資料)                                         │
│  ├── grouping_variable (分組變數，如 treatment vs control)          │
│  └── variables_config (哪些變數要放、連續/類別)                     │
│                                                                      │
│  Output:                                                             │
│  ├── Markdown Table (可直接貼入 draft)                              │
│  ├── Word Table (格式化好的 .docx)                                  │
│  ├── Descriptive Paragraph (「共納入 N 位患者...」)                 │
│  └── Statistical Notes (哪些有顯著差異、用什麼檢定)                 │
└─────────────────────────────────────────────────────────────────────┘
```

| 功能             | 說明                                          | 狀態 |
| ---------------- | --------------------------------------------- | ---- |
| 自動偵測變數類型 | `detect_variable_types`                       | ✅   |
| 分組比較         | t-test / Mann-Whitney / Chi-square / Fisher's | ✅   |
| 格式化輸出       | Markdown Table 格式                           | ✅   |
| 統計報告         | p 值、mean±SD                                 | ✅   |

**新增工具**：

- `generate_table_one` - 主要工具
- `detect_variable_types` - 資料檢視
- `list_data_files` - 檔案列表

### 4.2 稿件一致性檢查 ⭐⭐⭐⭐ ✅ 已完成

```
┌─────────────────────────────────────────────────────────────────────┐
│                    check_manuscript_consistency                      │
├─────────────────────────────────────────────────────────────────────┤
│  檢查項目:                                                           │
│  ├── 數字一致性 (N=100 在各章節要一致)                              │
│  ├── 術語一致性 (縮寫首次定義檢查)                                  │
│  ├── 引用完整性 (引用的文獻是否都有儲存)                            │
│  ├── 圖表引用 (Figure 1, Table 2 是否連續)                          │
│  └── 統計報告 (p 值格式是否一致)                                    │
│                                                                      │
│  Output:                                                             │
│  ├── Consistency Report (分類問題清單)                              │
│  ├── Issue List (具體位置 + 修復建議)                               │
│  └── Summary (error/warning/info 統計)                               │
└─────────────────────────────────────────────────────────────────────┘
```

**新增工具**：

- `check_manuscript_consistency` - 稿件一致性檢查

### 4.3 Reviewer Response 生成器 ⭐⭐⭐⭐ ✅ 已完成

```
┌─────────────────────────────────────────────────────────────────────┐
│                    create_reviewer_response                          │
├─────────────────────────────────────────────────────────────────────┤
│  Input:                                                              │
│  ├── reviewer_comments (審稿意見，可直接貼)                         │
│  └── output_format (structured/table/letter)                        │
│                                                                      │
│  Output:                                                             │
│  ├── Response Template (逐條回覆框架)                               │
│  ├── Structured Format (標準 Point-by-point)                        │
│  ├── Table Format (表格式整理)                                      │
│  └── Letter Format (正式信函格式)                                   │
└─────────────────────────────────────────────────────────────────────┘
```

**新增工具**：

- `create_reviewer_response` - 回覆模板生成
- `format_revision_changes` - 修改差異格式化

### 4.4 投稿準備清單 ✅ 已完成（部分轉為 Skill）

| 工具                          | 功能                                            | 狀態                    |
| ----------------------------- | ----------------------------------------------- | ----------------------- |
| `generate_cover_letter`       | 根據 concept + target journal 生成 Cover Letter | ✅ → Skill              |
| `check_submission_checklist`  | 期刊投稿清單檢查 (word count, figure format...) | ✅ → `check_formatting` |
| `list_supported_journals`     | 列出支援的期刊及其要求                          | ✅ → Skill              |
| `generate_highlights`         | 生成 3-5 bullet points highlights               | ✅ → Skill              |
| `generate_graphical_abstract` | Draw.io 視覺摘要模板                            | 📋                      |

> **Phase 10 Tool Consolidation (2026-02-21)**:
>
> - `generate_cover_letter`, `list_supported_journals`, `generate_highlights` 轉為 `submission-preparation/SKILL.md` 知識
> - `check_submission_checklist` 併入 `check_formatting` 工具（新增 `check_submission` 參數）
> - `create_reviewer_response`, `format_revision_changes` 轉為 Skill 知識

### 4.5 CRUD Delete 操作補齊 ✅ 已完成

> **根據 2026-01-06 CRUD 盤點結果：52 個工具中 0 個 Delete 操作 → 已補齊**

| 工具               | 功能                   | 優先級     | 狀態 |
| ------------------ | ---------------------- | ---------- | ---- |
| `delete_reference` | 刪除儲存錯誤的文獻     | ⭐⭐⭐⭐⭐ | ✅   |
| `delete_draft`     | 刪除草稿檔案           | ⭐⭐⭐     | ✅   |
| `archive_project`  | 封存專案（不完全刪除） | ⭐⭐⭐     | ✅   |
| `delete_project`   | 永久刪除專案           | ⭐⭐       | ✅   |

**CRUD 盤點摘要**：

| Entity      | Create | Read | Update | Delete | Other |
| ----------- | ------ | ---- | ------ | ------ | ----- |
| Project     | 3      | 6    | 4      | **0**  | 2     |
| Concept     | 0      | 4    | 0      | **0**  | 0     |
| Draft       | 2      | 4    | 2      | **0**  | 3     |
| Reference   | 3      | 5    | 1      | **0**  | 2     |
| Word/Export | 3      | 4    | 1      | **0**  | 0     |
| Diagram     | 2      | 1    | 0      | **0**  | 0     |

---

## 🎨 Phase 5a: Artifact-Centric Architecture (2026 Q1-Q2) 🆕

> **非線性工作流程支援 - 重大架構升級**
> 📋 設計文件：[docs/design/artifact-centric-architecture.md](docs/design/artifact-centric-architecture.md)

### 問題背景

目前架構假設「專案優先」：使用者必須先建立專案才能儲存文獻。但實際研究者的工作流程是**非線性**的：

| 入口模式    | 說明                               |
| ----------- | ---------------------------------- |
| 🔍 搜尋先行 | 先找論文，找到好題目才決定研究方向 |
| 📊 資料先行 | 已有實驗數據，需要找文獻支持       |
| 📝 草稿先行 | 從舊稿件改寫，需要更新引用         |
| 📚 PDF 匯入 | 有一堆下載好的 PDF，需要整理       |

### 解決方案

**三階段狀態機**：

```
EMPTY → EXPLORATION → PROJECT
          ↓
    _workspace/ 暫存區
```

**核心變更**：

- 新增 `_workspace/` 成品暫存區
- 無專案時成品自動進入 staging
- 使用者決定時機再建立專案

### 新增工具 (+6)

| 工具                             | 功能              |
| -------------------------------- | ----------------- |
| `start_exploration`              | 啟動探索模式      |
| `get_exploration_status`         | 查看 staging 狀態 |
| `list_staged_artifacts`          | 列出暫存成品      |
| `tag_artifact`                   | 標記成品          |
| `link_artifact_to_project`       | 連結成品到專案    |
| `convert_exploration_to_project` | 探索轉專案        |

### 設計決策

| 決策         | 選擇                | 理由             |
| ------------ | ------------------- | ---------------- |
| 成品歸屬     | Reference（多對多） | 彈性最高         |
| 強制專案時機 | Export 時           | 探索階段零阻力   |
| 向後相容     | Keep Both           | 現有專案不受影響 |

### 實作計畫

- [ ] 建立 `_workspace/` 基礎架構
- [ ] 實作 `ArtifactRegistry` 類別
- [ ] 升級 `WorkspaceStateManager` 支援 3 狀態
- [ ] 新增 6 個 Exploration 工具
- [ ] 修改現有工具支援無專案模式

---

## �️ Phase 5c: Full VSX + Pandoc Export (2026 Q1-Q2) 🔥

> **架構方向 C：將 VS Code Extension 升級為完整的論文寫作環境**
> 決策日期：2026-01 | 決策依據：需要比 Speckit-like shell prompts 更豐富的 UI 互動

### 決策背景

| 方向            | 說明                                 | 結果        |
| --------------- | ------------------------------------ | ----------- |
| A. Lightweight  | 純 MCP + Shell Prompts（像 Speckit） | ❌ 功能不足 |
| B. Slim MCP     | 精簡 MCP + 少數 VSX 功能             | ❌ 中間地帶 |
| **C. Full VSX** | **完整 Extension + Foam + Pandoc**   | **✅ 選定** |

### 5c.1 VS Code Extension 升級

```
┌─────────────────────────────────────────────────────────────────────┐
│                    MedPaper Extension 升級                          │
├─────────────────────────────────────────────────────────────────────┤
│  現有:                                                              │
│  ├── MCP Server 註冊                                                │
│  ├── @mdpaper Chat Participant                                     │
│  └── 3 Commands (start/stop/status)                                │
│                                                                      │
│  新增:                                                              │
│  ├── 🌳 TreeView  — 專案清單 + 文獻樹 + 草稿結構                   │
│  ├── 🔍 CodeLens  — concept.md 上方顯示 novelty score              │
│  │                 — draft 中 [[wikilink]] 上方顯示引用資訊         │
│  ├── 🔴 Diagnostics — 缺少引用、wikilink 斷鏈、字數超限            │
│  ├── 📊 Webview   — Dashboard 嵌入 (取代 Simple Browser)           │
│  └── 📁 File Decoration — 專案/草稿狀態標示                        │
└─────────────────────────────────────────────────────────────────────┘
```

| 功能                        | 說明                                          | 優先級     | 狀態 |
| --------------------------- | --------------------------------------------- | ---------- | ---- |
| **TreeView: Projects**      | 側邊欄顯示專案清單、狀態、進度                | ⭐⭐⭐⭐⭐ | 📋   |
| **TreeView: References**    | 當前專案的文獻樹，點擊開啟 note               | ⭐⭐⭐⭐   | 📋   |
| **CodeLens: Novelty**       | concept.md 上方顯示最近驗證分數               | ⭐⭐⭐     | 📋   |
| **CodeLens: Citations**     | [[wikilink]] 上方顯示 "Author (Year)"         | ⭐⭐⭐⭐   | 📋   |
| **Diagnostics**             | 引用缺失警告、wikilink 斷鏈、字數超限         | ⭐⭐⭐⭐   | 📋   |
| **Webview Dashboard**       | 內嵌 Next.js Dashboard（取代 Simple Browser） | ⭐⭐⭐     | 📋   |
| **File Decorations**        | 專案狀態圖示（drafting/submitted/published）  | ⭐⭐       | 📋   |
| **Agents Bundle**           | 9 個 SubAgent .agent.md 隨 VSIX 打包          | ⭐⭐⭐⭐⭐ | ✅   |
| **Auto-Scaffold**           | 偵測缺失 skills/agents/prompts 並自動提示     | ⭐⭐⭐⭐⭐ | ✅   |
| **macOS Compatibility**     | MCP env PATH 繼承、homebrew Python 支援       | ⭐⭐⭐⭐⭐ | ✅   |
| **Zero-Config Marketplace** | uv 自動安裝 + `uvx` 隔離模式，一鍵安裝即用    | ⭐⭐⭐⭐⭐ | ✅   |
| **Testability Refactor**    | 純函數抽取 + 106 vitest（4 test files）       | ⭐⭐⭐⭐   | ✅   |

### 5c.2 Pandoc 整合（雙格式匯出）

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Pandoc Export Pipeline                            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  drafts/*.md                                                         │
│       │                                                              │
│       ├──→ pandoc → .docx  (Word，投稿 / 共同作者協作)              │
│       │         ├── 套用期刊 Word template                          │
│       │         └── 引用格式化 (CSL)                                │
│       │                                                              │
│       └──→ pandoc → .tex   (LaTeX，精確排版 / 數學公式)             │
│                 ├── 套用 journal .cls/.sty                          │
│                 └── BibTeX 引用                                      │
│                                                                      │
│  取代: 現有 python-docx 基礎的 Word 匯出                            │
│  優勢: 統一 pipeline、支援更多格式、CSL 引用、LaTeX 公式            │
└─────────────────────────────────────────────────────────────────────┘
```

| 功能                    | 說明                             | 優先級     | 狀態 |
| ----------------------- | -------------------------------- | ---------- | ---- |
| **Pandoc Word Export**  | 取代現有 python-docx 匯出        | ⭐⭐⭐⭐⭐ | 📋   |
| **Pandoc LaTeX Export** | 新增 LaTeX 輸出                  | ⭐⭐⭐⭐   | 📋   |
| **CSL Citation Styles** | 用 CSL 取代手動格式化            | ⭐⭐⭐⭐⭐ | 📋   |
| **Journal Templates**   | 期刊 Word/LaTeX 模板庫           | ⭐⭐⭐     | 📋   |
| **Math Support**        | LaTeX 公式在 Word/PDF 中正確渲染 | ⭐⭐⭐     | 📋   |

### 5c.3 Foam 保留 + 強化

| 功能                      | 說明                                        | 狀態    |
| ------------------------- | ------------------------------------------- | ------- |
| **保持現有**              | [[wikilink]] 引用、hover preview、backlinks | ✅ 已有 |
| **Graph Scope**           | `foam_settings.py` 動態切換專案範圍         | ✅ 已有 |
| **Enhanced Autocomplete** | 文獻 autocomplete 加入 impact factor        | 📋      |
| **Backlink Dashboard**    | 在 Dashboard 中顯示引用圖譜                 | 📋      |

---

## �📊 Phase 5b: Project Portfolio Management (2026 Q2)

> **多論文專案管理：讓研究者能同時管理多個進行中的論文**

### 5.1 Dashboard 2.0

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Project Portfolio Dashboard                       │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  Active Projects                                    [+ New]   │   │
│  ├──────────────────────────────────────────────────────────────┤   │
│  │  📝 Remimazolam Elderly          │ Drafting │ BJA    │ 65% │   │
│  │  📊 ECMO Mortality Prediction    │ Analysis │ CCM    │ 40% │   │
│  │  🔬 Airway Management Review     │ Concept  │ AA     │ 15% │   │
│  │  ✅ Propofol Meta-analysis       │ Submitted│ JAMA   │ 100%│   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  Timeline View                                   [Gantt/List] │   │
│  ├──────────────────────────────────────────────────────────────┤   │
│  │  Jan ──────────── Feb ──────────── Mar ──────────── Apr      │   │
│  │  ████████░░░░░░░░ Remimazolam (Submit: Feb 15)               │   │
│  │  ░░░░████████████████████░░░░ ECMO (Submit: Mar 30)          │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

| 功能                   | 說明                                                | 狀態 |
| ---------------------- | --------------------------------------------------- | ---- |
| **Project Kanban**     | Concept → Drafting → Review → Submitted → Published | 📋   |
| **Timeline View**      | 甘特圖顯示各專案進度與 deadline                     | 📋   |
| **Milestone Tracking** | 設定里程碑並追蹤                                    | 📋   |
| **Priority Matrix**    | 依重要性/緊急性排序專案                             | 📋   |

### 5.2 跨專案文獻庫

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Cross-Project Reference Library                   │
├─────────────────────────────────────────────────────────────────────┤
│  目前架構:                                                           │
│  projects/                                                           │
│  ├── remimazolam-elderly/references/  ← 專案獨立                    │
│  ├── ecmo-mortality/references/        ← 專案獨立                   │
│  └── ...                                                             │
│                                                                      │
│  新架構:                                                             │
│  references/                            ← 全域文獻庫                 │
│  ├── 12345678/                                                       │
│  ├── 23456789/                                                       │
│  └── ...                                                             │
│  projects/                                                           │
│  ├── remimazolam-elderly/                                           │
│  │   └── .references → [12345678, 23456789]  ← 引用清單             │
│  └── ...                                                             │
│                                                                      │
│  好處:                                                               │
│  ├── 同一篇文獻不用重複儲存                                         │
│  ├── 跨專案搜尋已存文獻                                             │
│  └── 文獻使用統計 (被幾個專案引用)                                  │
└─────────────────────────────────────────────────────────────────────┘
```

### 5.3 專案模板庫

| 模板                  | 說明                         |
| --------------------- | ---------------------------- |
| **Original Research** | RCT, Cohort, Cross-sectional |
| **Systematic Review** | PRISMA workflow 內建         |
| **Meta-analysis**     | 含 Forest plot 工作流        |
| **Case Report**       | CARE checklist 整合          |
| **Technical Note**    | 簡化結構                     |

---

## 🔬 Phase 6: Systematic Review Pipeline (2026 Q3)

> **Option B 實作：完整支援系統性回顧 / Meta-analysis**

### 6.1 PRISMA 流程工具

```
┌─────────────────────────────────────────────────────────────────────┐
│                    PRISMA Flow Manager                               │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  Identification ─────────────────────────────────────────────────   │
│  ├── search_databases()     → PubMed, Embase, Cochrane             │
│  ├── record_search_results() → 自動記錄各資料庫筆數                 │
│  └── remove_duplicates()     → 去重並記錄                           │
│                                                                      │
│  Screening ──────────────────────────────────────────────────────   │
│  ├── screen_titles_abstracts() → Title/Abstract 篩選介面           │
│  ├── screen_fulltext()         → 全文篩選 + 排除原因記錄           │
│  └── resolve_conflicts()       → 雙人篩選不一致處理                │
│                                                                      │
│  Eligibility ────────────────────────────────────────────────────   │
│  ├── assess_eligibility()      → PICOS 對照表                       │
│  └── record_exclusion_reasons() → 標準化排除原因                   │
│                                                                      │
│  Included ───────────────────────────────────────────────────────   │
│  ├── extract_data()            → 資料萃取表單                       │
│  └── generate_prisma_diagram() → 自動生成 PRISMA 流程圖            │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### 6.2 Risk of Bias 評估

| 工具                      | 說明               | 支援量表 |
| ------------------------- | ------------------ | -------- |
| `assess_rob2`             | RCT 風險評估       | RoB 2.0  |
| `assess_robins_i`         | 觀察性研究風險評估 | ROBINS-I |
| `assess_newcastle_ottawa` | 非隨機研究評估     | NOS      |
| `generate_rob_summary`    | 彙總圖 (紅綠燈)    | All      |
| `generate_rob_graph`      | Traffic light plot | All      |

### 6.3 Meta-analysis 整合

| 工具                       | 說明                      |
| -------------------------- | ------------------------- |
| `calculate_effect_size`    | OR, RR, MD, SMD 計算      |
| `run_meta_analysis`        | Fixed/Random effects 模型 |
| `generate_forest_plot`     | Forest plot (Draw.io)     |
| `test_heterogeneity`       | I², Q test, Tau²          |
| `run_sensitivity_analysis` | Leave-one-out, influence  |
| `run_subgroup_analysis`    | 亞組分析                  |
| `test_publication_bias`    | Funnel plot, Egger's test |
| `generate_grade_summary`   | GRADE 證據品質評估        |

---

## 🤖 Phase 7: AI Automation Enhancement (2026 Q4)

> **Option C 實作：讓 AI 從「輔助」進化到「自動化」**

### 7.1 Concept → Full Draft 自動化

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Auto-Draft Pipeline                               │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  Input: concept.md + saved references                                │
│                       ↓                                              │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │  Step 1: Structure Planning                                  │    │
│  │  • 根據 paper_type 決定章節結構                              │    │
│  │  • 為每個章節分配 key references                            │    │
│  │  • 預估每章節字數                                            │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                       ↓                                              │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │  Step 2: Section-by-Section Drafting                        │    │
│  │  • Introduction: Evidence Funnel (已實作)                   │    │
│  │  • Methods: Template + concept.md 填空                      │    │
│  │  • Results: 數據 → 文字自動轉換                             │    │
│  │  • Discussion: Novelty → Limitations → Conclusion           │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                       ↓                                              │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │  Step 3: Consistency Check & Polish                         │    │
│  │  • check_manuscript_consistency()                           │    │
│  │  • 專業術語統一                                              │    │
│  │  • 被動語態調整                                              │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                       ↓                                              │
│  Output: complete_draft.md (人類審閱後可直接投稿)                   │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### 7.2 Smart Citation Suggestions

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Citation Intelligence                             │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  功能類似 Grammarly，但針對學術引用:                                │
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │  "Recent studies have shown that remimazolam provides       │    │
│  │   better hemodynamic stability."                             │    │
│  │                          ↑                                   │    │
│  │   ⚠️ Citation needed! Suggested:                            │    │
│  │   • Wang 2023 (PMID: 36941285) - directly supports          │    │
│  │   • Lee 2022 (PMID: 35123456) - related                     │    │
│  │   [Insert] [Ignore] [Search for more]                       │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                      │
│  觸發條件:                                                           │
│  • 發現 "studies show", "research indicates" 等無引用              │
│  • 發現數字聲稱無來源                                               │
│  • 發現與 concept 的 novelty claim 衝突的敘述                       │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### 7.3 Cross-section Consistency Auto-fix

| 功能                      | 說明                    |
| ------------------------- | ----------------------- |
| **Number Sync**           | 自動同步所有章節的 N 值 |
| **Term Standardization**  | 建立術語表並自動替換    |
| **Reference Renumbering** | 依出現順序自動重編號    |
| **Figure/Table Check**    | 確保所有圖表都有被引用  |
| **Statistical Style**     | 統一 p 值、CI 格式      |

### 7.4 Self-Evolution Automation 🆕

> **核心價值的技術實現**：逐步多輪演進（CONSTITUTION §25-26）。
> **MCP 協議限制**：Server 無法主動呼叫 Client（Agent），只能被動回應 request-response。
> 因此「自動化自我演進」需要外部觸發機制。

#### 為什麼需要三層架構

寫論文是人類高度專業化的過程：課程 → 文獻閱讀 → 研究設計 → 撰寫 → 審查 → 修改 → 再投稿，每一輪都比前一輪更精煉。本系統的核心價值就是用 Agent + MCP 重現這個「逐步多輪演進」的過程。

#### 三個層級

```
┌─────────────────────────────────────────────────────────────────────┐
│              Self-Evolution Automation Levels                        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  Level 1: Agent-in-the-Loop (現行) ✅                               │
│  ├── Phase 10 MetaLearningEngine 已實作 D1-D9                       │
│  ├── L1 Skill + L2 Hook 調整已可自動執行                            │
│  └── 限制：需要 Agent 在對話中主動執行 run_meta_learning            │
│                                                                      │
│  Level 2: Code-Level Enforcement (已完整實作) ✅                    │
│  ├── DomainConstraintEngine (Sand Spreader) JSON 約束               │
│  ├── run_writing_hooks 強制 A5/A6/B8/C9/F checks                   │
│  ├── ToolInvocationStore 遙測 + tool_health 診斷                    │
│  ├── PendingEvolutionStore 跨對話演化持久化 🆕                      │
│  ├── build_startup_guidance 新對話自動提示 pending evolutions 🆕    │
│  └── apply_pending_evolutions MCP tool 預覽/套用/駁回 🆕            │
│                                                                      │
│  Level 3: Autonomous Self-Evolution (部分實作) ⚠️                   │
│  ├── ✅ GitHub Actions weekly health check + auto-issue              │
│  ├── ✅ PendingEvolution 跨對話持久化（Phase C 完成）               │
│  ├── ❌ Git post-commit hook 自動觸發（Phase A 未開始）             │
│  ├── ❌ EvolutionVerifier 跨專案驗證類別（被引用但未實作）          │
│  └── ❌ L3 建議自動產生 GitHub PR                                   │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

#### Level 3 可行路徑

| 路徑                          | 方式                                                                | 觸發時機            | 優劣                          | 狀態                                   |
| ----------------------------- | ------------------------------------------------------------------- | ------------------- | ----------------------------- | -------------------------------------- |
| **A. Git Post-Commit Hook**   | `post-commit` → `claude -p "run_meta_learning + apply L1/L2"`       | 每次 commit         | 最自然，commit = 階段結束信號 | ❌ 未實作                              |
| **B. GitHub Actions CI**      | `.github/workflows/meta-learning.yml` → Claude API                  | PR merge / 每週排程 | 與 CI/CD 整合，可產生 PR      | ⚠️ Health check 已上線，自動 PR 未實作 |
| **C. Pending-Evolution 檔案** | Server 寫 `.audit/pending-evolutions.yaml` + Agent 新對話時自動讀取 | 每次新對話          | 無需外部呼叫，但被動          | ✅ 完整實作                            |

**推薦實作順序**：C → A → B（從低風險到高自動化）

#### 技術待驗證 ⚠️

| 問題                    | 說明                                                       | 狀態      |
| ----------------------- | ---------------------------------------------------------- | --------- |
| `claude` CLI 非互動執行 | `claude -p "prompt"` 是否能帶 MCP 在非互動模式執行         | 📋 待驗證 |
| Workspace MCP 存取      | 非互動模式是否能存取 `.vscode/mcp.json` 定義的 MCP servers | 📋 待驗證 |
| API 費用控制            | 每次 commit 觸發 Agent 的 token 用量與費用                 | 📋 需評估 |
| 安全邊界                | 非互動模式下 L3 操作是否要額外安全機制                     | 📋 需設計 |

#### 實作計畫

- [x] **Phase C**：在 `run_meta_learning` 結尾寫入 `pending-evolutions.yaml` ✅ `_flush_meta_learning_evolutions()`
- [x] **Phase C**：新增啟動引導 — 新對話時自動檢查 pending evolutions ✅ `build_startup_guidance()` via `get_workspace_state()`
- [ ] **Phase A**：撰寫 `scripts/post-commit-evolution.sh` 呼叫 `claude` CLI
- [ ] **Phase A**：在 `.pre-commit-config.yaml` 或 git hooks 中註冊
- [x] **Phase B**：GitHub Actions workflow 每週排程跑 evolution health check ✅ `evolution-health.yml`
- [ ] **Phase B**：L3 建議自動產生 GitHub PR（含 diff preview）
- [ ] **待修**：`EvolutionVerifier` 類別被 `check-evolution-health.py` 引用但不存在（已 graceful fallback）

---

## 🧠 Phase 8: AI Writing Intelligence (2026 Q1-Q2) 🆕

> **代碼層面解決 AI 寫作三大問題**
> 📋 設計文件：[docs/design/ai-writing-intelligence.md](docs/design/ai-writing-intelligence.md)

### 問題陳述

| 問題         | 症狀               | 目前解法                     | 為什麼不夠   |
| ------------ | ------------------ | ---------------------------- | ------------ |
| **連貫性**   | 段落跳躍、邏輯斷裂 | Prompt 說「要連貫」          | 沒有強制機制 |
| **引用**     | 不知哪裡該引用     | `suggest_citations` 事後建議 | 補引用很彆扭 |
| **思考脈絡** | 缺乏全局架構       | `validate_concept` 檢查      | 只檢查不引導 |

### 8.1 Citation Intelligence（MVP）🎯

| 工具                             | 功能                               | 狀態      |
| -------------------------------- | ---------------------------------- | --------- |
| `analyze_citation_needs`         | 分析句子引用需求（Rule-based）     | 📋 設計中 |
| `find_supporting_references`     | 為 claim 找引用（Semantic search） | 📋 設計中 |
| `verify_citation_support`        | 驗證引用是否支持 claim             | 📋 設計中 |
| `write_paragraph_with_citations` | 寫作時即時插入引用                 | 📋 設計中 |

**技術選型**：

- `sentence-transformers` - 語義搜尋
- `spaCy` - NLP 句子分析
- Rule-based patterns - 引用需求偵測

**4 週實作計畫**：
| Week | 內容 |
|------|------|
| Week 1 | Foundation - patterns + analyzer |
| Week 2 | Search - embedding + local/PubMed |
| Week 3 | Verification - claim-citation 匹配 |
| Week 4 | Integration - MCP tools + 測試 |

### 8.2 Coherence Engine（Phase 2）

| 工具                           | 功能         |
| ------------------------------ | ------------ |
| `generate_section_outline`     | 段落級大綱   |
| `write_paragraph_with_context` | 帶上下文寫作 |
| `check_coherence`              | 連貫性檢查   |

### 8.3 Argument Tracker（Phase 3）

| 工具                        | 功能                            |
| --------------------------- | ------------------------------- |
| `create_argument_map`       | 論點地圖（整合 CGU deep_think） |
| `generate_structured_draft` | 結構化生成                      |
| `track_logic_chain`         | 邏輯鏈追蹤                      |

---

## 🛠️ Phase 9: API & Deployment (2026 Q4+)

**參考 medical-calc-mcp 的部署架構**

| Feature           | Description             | Use Case     |
| ----------------- | ----------------------- | ------------ |
| **REST API Mode** | 將 MCP 工具以 API 公開  | 外部系統整合 |
| SSE Mode          | Server-Sent Events 支援 | 輕量即時通訊 |
| Docker Support    | 容器化部署              | 一鍵啟動     |
| HTTPS + Nginx     | 生產環境安全部署        | 團隊使用     |

---

## 💡 構想中 (Ideas)

| Idea                  | Description                          | Priority |
| --------------------- | ------------------------------------ | -------- |
| **Tool Discovery**    | 兩層級工具索引 (Low/High Level)      | Medium   |
| **Resources API**     | `paper://list`, `reference://{pmid}` | Medium   |
| **Multi-Author Mode** | 多人協作、版本控制                   | Low      |
| **Reference Graph**   | 文獻引用關係視覺化                   | Low      |
| **Voice Input**       | 語音輸入筆記                         | Idea     |

---

## 🔗 Related Projects

| Project                                                            | Description         | Status        |
| ------------------------------------------------------------------ | ------------------- | ------------- |
| [pubmed-search-mcp](https://github.com/u9401066/pubmed-search-mcp) | PubMed 文獻搜尋 MCP | ✅ Integrated |
| [next-ai-draw-io](https://github.com/u9401066/next-ai-draw-io)     | Draw.io 流程圖 MCP  | ✅ Integrated |
| [medical-calc-mcp](https://github.com/u9401066/medical-calc-mcp)   | 醫學計算器 MCP      | 📋 Planned    |
| [CGU](integrations/cgu/)                                           | 創意發想 MCP        | ✅ Integrated |

---

## Contributing

有興趣參與開發？歡迎：

- 🐛 回報問題
- 💡 提出功能建議
- 🔧 提交 Pull Request

詳見 [CONTRIBUTING.md](CONTRIBUTING.md)
