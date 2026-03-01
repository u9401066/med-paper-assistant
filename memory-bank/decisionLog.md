# Decision Log

## [2026-02-28] v0.4.0 文件計數動態同步與 Hook 架構完善

### 背景

深度審查（2026-02-27）後發現文件中的數量宣稱（工具數、hook 數、prompt 數等）散佈於 7+ 個檔案中，長期手動維護導致嚴重不一致：README 寫 131 tools、ARCHITECTURE 寫 89、copilot-instructions 寫 87/81，實際 AST 計數為 85。Hook 數也從 42/56/65 不等，實際為 76。

### 決定

1. **建立動態計數同步腳本** (`scripts/sync_repo_counts.py`)，以 AST 解析取代 regex 計數，支援 `--check`（CI gate）/`--fix`（自動更新）/`--json`（程式化輸出）三種模式
2. **補齊 Hook 架構缺失**：EXPECTED_HOOKS 40→58、HOOK_CATEGORIES 加入 "R"、ReviewHooksEngine 加入 `__init__.py` exports
3. **auto-paper-guide "42" 保持不變** — 確認這是 Agent-Driven 子集（A-D hooks），非總數 76

### 關鍵技術決定

| 問題 | 選項 | 決定 | 理由 |
| --- | --- | --- | --- |
| 計數方法 | A. Regex / B. AST | **B. AST** | `tool_logging.py` docstring 有 `@mcp.tool()` 示例，regex 會誤計為 89（實際 85） |
| auto-paper-guide "42" | A. 同步到 76 / B. 保持 42 | **B. 保持 42** | 該數字指 Agent-Driven 子集，非總數。加註釋說明 |
| 文件表格對齊 | A. format string / B. regex group capture | **B. `\g<1>`** | 保留原始 markdown 格式，避免空格錯亂 |
| EXPECTED_HOOKS 排除 D/G | A. 全部加入 / B. 排除 | **B. 排除** | D1-D9 是 meta-learning 引擎本身（自引用），G1-G9 在 pre-commit 獨立追蹤 |

### 成果

- `sync_repo_counts.py` 自動修復 43 個過時計數，覆蓋 7 個文件
- `check_consistency.py` 6/6 checks passed
- 698 tests passed, 0 failed
- VSX extension 同步更新（copilot-instructions.md, README.md, package.json）

### 影響

- 未來任何新增/移除 MCP tool 或 hook，只需 `uv run python scripts/sync_repo_counts.py --fix` 即可全面同步
- CI 可加入 `--check` 作為 gate，防止文件數量漂移

---

## [2026-02-27] 深度審查：框架實作完整性盤點

### 背景

文件（CONSTITUTION §25-26, AGENTS.md, ROADMAP.md）宣稱三層演進架構完整運作。需要驗證實際程式碼與文件宣稱之間的差距。

### 審查結果

| 層級           | 宣稱                  | 實際                         | 差距                                             |
| -------------- | --------------------- | ---------------------------- | ------------------------------------------------ |
| L1 Hooks       | 56 個品質檢查         | 14 個 Code-Enforced (25%)    | 42 個僅靠 Agent 遵循 SKILL.md                    |
| L2 Enforcement | 5 個元件              | 5 個完整實作 (100%)          | 無重大差距                                       |
| L3 Evolution   | D1-D9 + CI + Git Hook | D1-D9 完整 + CI health check | Git post-commit 未實作、EvolutionVerifier 未實作 |
| MCP Tools      | 文件宣稱 ~53          | 實際註冊 77 個               | 工具數量文件過時（Self-Evolution 新工具未計入）  |

### 關鍵發現

1. **L1 75% Agent-Only**：A1-A4, B1-B7, C1-C8, E1-E5, P1-P8, G1-G8 完全依賴 Agent 閱讀 SKILL.md 自行執行，無程式碼強制機制。品質取決於 Agent 是否「聽話」。
2. **L2 完整且整合良好**：DomainConstraintEngine, ToolInvocationStore, PendingEvolutionStore, guidance.py, tool_health.py 五元件完整實作且端到端串聯。
3. **L3 Phase C 完成但 A/B 部分**：PendingEvolution 跨對話機制已完整運作。Git post-commit 和自動 PR 未實作。EvolutionVerifier 被 check-evolution-health.py 引用但類別不存在。
4. **MetaLearningEngine known hooks 清單不完整**：已知 hooks 清單漏掉 A5/A6/B8/C9/F（Code-Enforced hooks）和 G1-G8（General hooks），導致 D1 效能統計無法追蹤這些 hooks。
5. **discussion/ 模組殘留**：已標記 DEPRECATED 但檔案仍存在，可清理。

### 決定

1. 更新所有文件（AGENTS.md, copilot-instructions.md, ROADMAP.md, CONSTITUTION.md, architect.md）如實標記實作狀態
2. 不美化差距 — 明確區分 Code-Enforced vs Agent-Driven hooks
3. 已知缺失項目記錄為 ROADMAP 待辦事項

### 後續建議（不在此次範圍）

- 優先實作 EvolutionVerifier（已被引用但不存在）
- 將 MetaLearningEngine known hooks 清單補齊 A5/A6/B8/C9/F/G1-G8
- 考慮將高頻 Agent-Driven hooks（如 A1 字數、A3 Anti-AI）提升為 Code-Enforced

---

## [2026-02-27] 核心價值確立：逐步多輪演進（Iterative Multi-Round Evolution）

### 背景

系統已發展出三層架構：L1 Event-Driven Hook 體系（Agent 操作時觸發）、L2 Code-Level Enforcement（DomainConstraintEngine）、L3 Autonomous Self-Evolution（外部排程 + GitHub Actions）。用戶指出：這三層之所以必要，是因為「寫論文是人類高度專業化、多年累積、多輪訓練的結果，而且是在科學方法下可重現的思考與整合步驟」。Agent + MCP 框架應該能實現類似的逐步多輪演進。

### 決定

將「逐步多輪演進」正式確立為**專案核心價值**，寫入 CONSTITUTION.md 第九章（§25-26）。同步更新所有文件。

### 核心論述

1. 學術論文撰寫不是一次性生成，而是螺旋式進步：搜尋 → 批判 → 修正 → 再搜尋
2. 三層架構（L1/L2/L3）各解決不同層面的問題，缺一不可
3. 這是系統存在的根本理由 — 不是「AI 自動寫論文」，而是「用科學方法實現逐步改善」
4. 演進必須有紀律：有證據、可回溯、有邊界、服務人類

### 影響

- CONSTITUTION.md v1.5.0 → v1.6.0，新增第九章（§25-26）
- ROADMAP.md Vision 加入核心價值描述，Phase 7.4 加入哲學說明
- AGENTS.md 頂部加入核心價值段落，§22-23 擴展為 §22-23 + §25-26
- copilot-instructions.md 加入核心價值摘要
- memory-bank/architect.md 更新三層架構說明

---

## [2026-02-26] EvolutionVerifier — 跨專案演化驗證

### 背景

MetaLearningEngine 只在單一專案內運作，無法證明「系統真的有自我演進」。需要跨專案收集證據，產生可審計的演化報告。

### 決定

建立 `EvolutionVerifier` 類別 + `verify_evolution` MCP tool，五維度驗證：

- E1: 閾值自我調整證據（audit 中的 threshold adjustments）
- E2: 經驗累積（Lessons Learned 收集）
- E3: Hook 覆蓋廣度（56 hooks 的使用率）
- E4: 品質量測存在性（scorecard 數據）
- E5: 跨專案比較可能性（≥2 projects 才能比較）

### 設計考量

- 不修改 MetaLearningEngine，而是作為上層彙整
- 掃描 `projects/*/` 的 `.audit/` 目錄
- 回傳結構化 JSON + TOON 格式人類可讀報告
- 對應 CONSTITUTION §22「可審計」原則

## [2026-02-21] Comprehensive Tool Consolidation (76→53 tools)

### 背景

MCP tool 數量膨脹至 76 個，造成 Agent context window 壓力過大。用戶明確要求「tool太多了!!!應該盡量精簡」。

### 選項（6 大策略，全部採用）

| 策略            | 說明                                            | 移除數 |
| --------------- | ----------------------------------------------- | ------ |
| A. 移除無用工具 | close_other_project_files, export_word (legacy) | -2     |
| B. 簡單合併     | 功能已被其他工具涵蓋                            | -3     |
| C. 參數合併     | 相關工具合為一，新增 optional params            | -11    |
| D. 功能吸收     | consistency + submission → check_formatting     | -2     |
| E+F. Skill 轉換 | 模板/知識型工具轉為 SKILL.md                    | -7     |

### 決定

全部 6 策略同時執行，從 76 降至 53 個工具。

### 具體合併

- `validate_concept` ← `validate_concept_quick` + `validate_for_section`（新增 `structure_only` param）
- `get_current_project` ← `get_project_paths` + `get_exploration_status`（新增 `include_files` param）
- `update_project_settings` ← `get_paper_types` + `update_project_status` + `set_citation_style`（新增 `status`, `citation_style` params）
- `save_diagram` ← `save_diagram_standalone`（新增 `output_dir` param）
- `sync_workspace_state` ← `clear_recovery_state`（新增 `clear` param）
- `suggest_citations` ← `find_citation_for_claim`（新增 `claim_type`, `max_results` params）
- `verify_document` ← `check_word_limits`（新增 `limits_json` param）
- `check_formatting` ← `check_manuscript_consistency` + `check_submission_checklist`（新增 `check_submission` + 8 boolean params）

### Skill 轉換

- `submission-preparation/SKILL.md` — cover letter, highlights, journal requirements, reviewer response, revision changes
- `draft-writing/SKILL.md` — section template 知識內嵌
- `project-management/SKILL.md` — 更新移除已合併工具

### 影響

- Agent context window 壓力大幅降低
- 0 regressions（35 tests pass）
- 模板/知識型功能移至 Skill 檔案，Agent 可按需讀取

---

## [2026-02-20] 架構方向選定：Direction C — Full VSX + Foam + Pandoc

### 背景

專案大整理時討論核心架構方向：這個專案本質上是什麼？

### 選項

| 方向            | 說明                                 |
| --------------- | ------------------------------------ |
| A. Lightweight  | 純 MCP + Shell Prompts（像 Speckit） |
| B. Slim MCP     | 精簡 MCP + 少數 VSX 功能             |
| **C. Full VSX** | **完整 Extension + Foam + Pandoc**   |

### 決定

選擇方案 C：Full VSX + Foam + Pandoc

### 理由

- 論文寫作需要比 shell prompts 更豐富的 UI 互動
- TreeView 顯示專案/文獻、CodeLens 顯示引用資訊、Diagnostics 即時檢查
- Foam 已深度整合 [[wikilink]]，替換成本高且功能良好
- Pandoc 能統一 Word/LaTeX 雙格式匯出，取代手工 python-docx

### 影響

- ROADMAP 新增 Phase 5c
- VS Code Extension 將大幅擴展（TreeView, CodeLens, Diagnostics, Webview）
- 新增 Pandoc export pipeline（取代現有 python-docx 基礎的匯出）
- Foam 保留並強化

---

## [2026-02-20] Infrastructure & Quality Cleanup

### 背景

專案歷經多次快速疊代，累積了大量技術債：過時的 `core.*` import 路徑、空的 legacy 目錄、測試污染根目錄、缺乏 pre-commit hooks、Copilot hook 文檔不一致。

### 決定

一次性大整理：5 個項目全部完成。

### 成果

1. Pre-commit 13 hooks（ruff, mypy, bandit, pytest, whitespace…）
2. 19 個測試檔 DDD import 遷移 + tmp_path isolation
3. ARCHITECTURE.md 從 448 行完全重寫
4. AGENTS.md 補齊 7 skills + 8 prompts
5. Legacy `core/` 目錄刪除、scripts 精簡

---

## [2025-01-22] Artifact-Centric Architecture 設計

### 背景

發現現有「專案優先」架構無法支援非線性工作流程。研究者可能從搜尋、PDF、資料等多種入口開始，不一定先建立專案。

### 選項

1. 維持專案優先，提供快速建立專案
2. 新增 Exploration 暫存區，讓成品可以先存再連結

### 決定

選擇方案 2：Artifact-Centric Architecture

### 設計決策

| 問題         | 選項                                | 決策             | 理由             |
| ------------ | ----------------------------------- | ---------------- | ---------------- |
| 成品歸屬     | A.Copy / B.Symlink / C.Reference    | **C. Reference** | 多對多關係最彈性 |
| 強制專案時機 | A.Never / B.Export / C.Validate     | **B. Export**    | 探索階段零阻力   |
| 向後相容     | A.Keep Both / B.Migrate / C.Gradual | **A. Keep Both** | 最小影響         |

### 影響

- 新增 `_workspace/` 成品暫存區
- 三階段狀態機：EMPTY → EXPLORATION → PROJECT
- 新增 6 個 Exploration 工具
- 設計文件：[docs/design/artifact-centric-architecture.md](../docs/design/artifact-centric-architecture.md)

---

## [2025-01-22] Workspace State 跨 Session 持久化

### 背景

Agent 被 summarize 後遺失專案 context，每次新對話都要重新問用戶「你在做哪個專案？」

### 決定

實作 `WorkspaceStateManager` singleton，狀態存於 `.mdpaper-state.json`

### 影響

- 三個新工具：`get_workspace_state`, `sync_workspace_state`, `clear_recovery_state`
- 新對話開始時自動恢復上次工作 context
- 工具總數：69 → 72

---

## [2025-12-17] 跨平台架構重構

### 背景

原專案在 Linux 環境開發，需要支援 Windows 開發環境。

### 選項

1. 維持 Linux only，使用 WSL
2. 重構為跨平台支援 (Windows/Linux/macOS)

### 決定

選擇方案 2：跨平台架構

### 理由

- 提高開發彈性
- 減少環境依賴
- VS Code MCP 支援 platforms 配置

### 影響

- `.vscode/mcp.json` 使用 platforms 配置
- `scripts/setup.sh` 和 `setup.ps1` 並行維護
- 路徑使用正斜線 `/` 以相容兩平台

---

## [2025-12-17] Memory Bank 統一化

### 背景

原本使用 `.memory/` 目錄，與 template 的 `memory-bank/` 不一致。

### 決定

統一使用 `memory-bank/` 目錄，並納入版本控制。

### 理由

- 與 template-is-all-you-need 一致
- 透過 bylaws 和 skills 強制寫入
- 便於協作和追蹤

### 影響

- 刪除 `.memory/` 目錄
- 更新所有引用路徑
- 更新 .gitignore 確保追蹤 memory-bank
  | 2025-12-17 | 將 .agent_constitution.md 整合進正式 CONSTITUTION.md，版本升級至 v1.1.0 | Agent 行為規範和研究操作規則應納入專案憲法正式管理，避免分散在多個檔案造成維護困難。新增第四至六章涵蓋：Agent 行為規範、研究操作規則（含 Concept/Draft 流程）、互動指南。 |
  | 2025-12-17 | 重構 integrations 為選擇性 submodule 架構 | 採用選擇性 submodule 策略：pubmed-search-mcp 和 CGU 作為 submodule（常改代碼），drawio 和 zotero-keeper 改用獨立 uvx 安裝（較少改動）。Python 版本升級至 >=3.11 以支援 CGU。 |
  | 2025-12-17 | mdpaper MCP 完全解耦 pubmed_search 依賴 | **MCP 對 MCP 只要 API！** 移除 mdpaper 對 pubmed_search 的所有 import，改為透過 Agent 協調 MCP 間通訊。刪除：infrastructure/external/{entrez,pubmed}、services/strategy_manager.py、tools/search/、use_cases/search_literature.py。重構 ReferenceManager 接受 metadata dict 而非 PMID。 |
  | 2025-12-17 | DDD 重構：建立 ReferenceConverter Domain Service 支援多來源 (PubMed, Zotero, DOI) | 1. Foam 需要唯一識別符支援 [[wikilink]] 功能

2. 不同來源有不同格式，需要統一轉換
3. 遵循 DDD 架構：Domain Service 處理格式轉換
4. Agent 協調 MCP 通訊，不需要 mdpaper 直接呼叫其他 MCP |

---

## [2025-01-XX] 分層驗證系統 (Tiered Validation)

### 背景

用戶想寫 Introduction，但 concept 驗證要求完整 Methods 區塊。

> "concept 雖然要求寫 method 但是其實有可能 draft 只想寫 introduction"
> "meta 跟 systematic review 或 research letter 要的又不一樣"

### 問題

1. **流程阻塞**：Methods 未填會阻擋所有 section 撰寫
2. **類型差異**：不同 paper type 需要不同區塊（case report 不需要 Methods）
3. **驗證粒度**：全有或全無，不支援漸進式撰寫

### 決定

實施 **分層驗證系統**：

1. 按 paper type 定義不同需求 (`ConceptRequirements`)
2. 按 target section 動態調整驗證範圍
3. 區分 `required`（blocking）vs `recommended`（warning only）

### 架構變更

**paper_types.py** 新增：

```python
@dataclass
class ConceptRequirements:
    core_required: List[str]      # 永遠必須
    intro_required: List[str]     # Introduction 需要
    methods_required: List[str]   # Methods 建議（不阻塞）
    special_sections: List[str]   # 類型特定

# 每種 paper type 有對應的 requirements
get_concept_requirements(paper_type) -> ConceptRequirements
get_section_requirements(paper_type, section) -> Dict
```

**concept_validator.py** 新增：

- `validate(target_section="Introduction")` - 針對特定 section
- `validate_for_section()` - 便捷方法
- `_can_write_section()` - 判斷是否可寫
- `missing_required` / `missing_recommended` 區分

**MCP tools** 新增：

- `validate_for_section(section, project)` - 推薦的驗證入口

### 驗證矩陣

| Paper Type        | Core                    | Intro                     | Methods                    | Special          |
| ----------------- | ----------------------- | ------------------------- | -------------------------- | ---------------- |
| original-research | NOVELTY, SELLING_POINTS | background, gap, question | study_design, participants | pre_analysis     |
| systematic-review | same                    | same                      | search_strategy            | prisma_checklist |
| case-report       | same                    | same                      | -                          | case_timeline    |
| letter            | NOVELTY only            | minimal                   | -                          | -                |

### 影響

- ✅ 用戶可以先寫 Introduction，Methods 稍後補
- ✅ 不同 paper type 有適當的驗證要求
- ✅ 漸進式撰寫流程
- ⚠️ SKILL.md 和文檔需更新
