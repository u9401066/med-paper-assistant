# Active Context

## User Preferences

- **Git Identity**: u9401066 <u9401066@gap.kmu.edu.tw>

## 當前焦點 (2026-03-03)

Paper-type-aware 文獻最低數量強制完成：Hook A7 + Phase 2 Gate 紙類感知 + B003 約束 + 15 新測試。

### 當前狀態

| 項目                    | 數量/狀態                                                                                   |
| ----------------------- | ------------------------------------------------------------------------------------------- |
| MCP Tools               | **86** (project/17, reference/12, draft/13, validation/3, analysis/9, review/22, export/10) |
| Skills                  | **26**                                                                                      |
| Hooks                   | **77 checks** (35 Code-Enforced / 42 Agent-Driven)                                          |
| Copilot Lifecycle Hooks | **7** (SessionStart→Stop，`.github/hooks/mdpaper-lifecycle.json`)                           |
| Prompts                 | **15**                                                                                      |
| Agents                  | **9**                                                                                       |
| Infrastructure classes  | **8** core                                                                                  |
| Python unit tests       | **839 passed** (excl. external-dep tests)                                                   |
| VSX vitest              | **106 passed** (4 test files)                                                               |
| Ruff errors             | **0**                                                                                       |

### 三層演進架構實作狀態

| 層級                         | 狀態                   | 說明                                                 |
| ---------------------------- | ---------------------- | ---------------------------------------------------- |
| L1 Event-Driven Hooks        | ⚠️ 35/77 Code-Enforced | 42 個 Agent-Driven 僅靠 SKILL.md                     |
| L2 Code-Level Enforcement    | ✅ 完整                | 5 元件全部上線                                       |
| L3 Autonomous Self-Evolution | ⚠️ Phase C 完成        | Git post-commit / EvolutionVerifier / Auto-PR 未實作 |

### 最近變更

#### Humanizer Anti-AI 強化

- **ANTI_AI_PHRASES**: 76→133 (12 categories: overly_formal, unnecessary_hedging, ai_conclusions, filler_boosters, generic_linking, hollow_emphasis, ai_structuring, inflated_academic, ai_discourse, passive_deflectors, nominalised_verbs, hollow_intensifiers)
- **AI_TRANSITION_WORDS**: 25→33 (8 新增: Nevertheless, Conversely, Correspondingly, Notably, Importantly, Significantly, Fundamentally, Substantially)
- **A3b 新增 4 個結構檢查**: #6 negative parallelism、#7 copula avoidance、#8 em dash overuse、#9 false ranges (X to Y)
- **Tests**: 12 新測試, 826 Python tests passed

#### VS Code Copilot Lifecycle Hooks

- 7 個 hook 腳本：session-init / prompt-analyzer / pre-tool-guard / post-tool-check / pre-compact-save / subagent-init / session-stop
- 設計文件：`docs/design/copilot-lifecycle-hooks.md`
- 狀態通訊：`.github/hooks/_state/`（已加入 .gitignore）
- 依賴 jq（無 jq 時 graceful degradation）

#### MCP Instructions 修正

- 移除幽靈工具 `save_diagram_standalone`（已合併進 `save_diagram`）
- 新增 `insert_figure` / `insert_table` / `list_assets` 至 DATA ANALYSIS section
- 更新 DIAGRAM WORKFLOW 加入 figure registration 步驟
- 工具計數 85→86（review/ 21→22），`sync_repo_counts.py --fix` 修復 22 個過時計數

### 已知問題

- `application/__init__.py` 的 import chain（missing pubmed modules）— 測試用 sys.modules mock 繞過
- 部分 test files 需外部模組（pubmed_search, matplotlib）— 已 ignore
- jq 未安裝 — Copilot Lifecycle Hooks 會 graceful degradation

## 下一步

- [ ] Phase 5c TreeView/CodeLens/Diagnostics features
- [ ] Dashboard Webview 內嵌（取代 Simple Browser）
- [ ] CI/CD pipeline for automated VSIX publish
- [ ] Run actual project pipeline to generate evolution data
- [ ] Consider grammar checker (language-tool-python as A7)

2026-03-02
