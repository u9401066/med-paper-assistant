# Active Context

## User Preferences

- **Git Identity**: u9401066 <u9401066@gap.kmu.edu.tw>

## 當前焦點 (2026-04-14)

v0.6.4 發布準備：完成 main mdpaper compact tool surface（full 94 / compact 44 預設）、VSX 預設 compact、文件/變更紀錄對齊，進入 segmented commit + push + tag。

### 當前狀態

| 項目                    | 數量/狀態                                                                                    |
| ----------------------- | -------------------------------------------------------------------------------------------- |
| MCP Tools               | **94 full / 44 compact (default)**                                                   |
| Skills                  | **26**                                                                                       |
| Hooks                   | **78 checks** (55 Code-Enforced / 23 Agent-Driven)                                           |
| Copilot Lifecycle Hooks | **7** (SessionStart→Stop，`.github/hooks/mdpaper-lifecycle.json`)                            |
| Prompts                 | **15**                                                                                       |
| Agents                  | **10**                                                                                       |
| Infrastructure classes  | **8** core                                                                                   |
| Python unit tests       | **916 passed** (excl. external-dep tests)                                                    |
| VSX vitest              | **126 passed** (5 test files)                                                                |
| Ruff errors             | **0** (310 E501 line-length only)                                                            |

### 三層演進架構實作狀態

| 層級                         | 狀態                   | 說明                                                 |
| ---------------------------- | ---------------------- | ---------------------------------------------------- |
| L1 Event-Driven Hooks        | ✅ 52/78 Code-Enforced | 26 個 Agent-Driven 僅靠 SKILL.md                     |
| L2 Code-Level Enforcement    | ✅ 完整                | 5 元件全部上線                                       |
| L3 Autonomous Self-Evolution | ⚠️ Phase C 完成        | Git post-commit / EvolutionVerifier / Auto-PR 未實作 |

### 最近變更

#### Enforcement Gap Closure (2026-03-17)

- **P0: `scripts/hooks/paper_precommit.py`** — 新 git pre-commit hook，自動掃描 `projects/` 下有草稿的專案，呼叫 `WritingHooksEngine.run_precommit_hooks()`，CRITICAL 時阻擋 commit
- **P1: Embedded post-write hooks** — `write_draft` 和 `patch_draft` 寫入後自動跑 A-series hooks，結果嵌入回應（agent 無法跳過）
- **B2: Protected content guard** — `patch_draft` 偵測 `🔒` 標記，阻擋對 concept.md 中受保護區段的修改
- **Tests**: 11 new → 916 total passed

#### Hook Mechanism Full Audit + Fix (2026-03-17)

- **Full audit scope**: WritingHooksEngine (A/B/C/F/P/G), ReviewHooksEngine (R1-R6), MetaLearningEngine (D1-D9), DomainConstraintEngine, HookEffectivenessTracker, MCP tool layer
- **Code fixes applied**:
  - `_engine.py`: `run_post_manuscript_hooks()` added C10-C13 (4 missing hooks)
  - `audit_hooks.py`: ALL alias +A7+C7B, POST-WRITE +A7, POST-MANUSCRIPT +C7B; docstring updated to 40 hooks
  - `hook_effectiveness_tracker.py`: HOOK_CATEGORIES +P (pre-commit) +G (git-hooks)
- **Documentation alignment**: AGENTS.md + copilot-instructions.md Code-Enforced count 36→52, Agent-Driven 42→26
- **Engine docstring**: A1–A7 (not A1–A6), F (not F1–F4), P1/P2/P4/P5/P7 (not just P5/P7)
- **Tests**: 905 passed, 0 regressions

#### Asset Review Receipt Hard Gate (2026-03-11)

- **VSX `/autopaper`**: 不再是 static docs-only flow，改為直接走 `runWithTools()`
  - 新增 `TOOL_FILTERS.autopaper`
  - 注入 `buildAutopaperExecutionPrompt()`，明確要求 `validate_phase_gate()` / `approve_section()` / `start_review_round()` / `submit_review_round()` / `pipeline_heartbeat()`
  - tool loop 回合數 5 → 12（僅 autopaper）
- **Phase 5 hard gate strengthened**: `section_approval` 不再是可選檢查
  - manuscript 存在時，required sections 必須在 `.audit/checkpoint.json` 中有 explicit approval entries
  - 缺少 checkpoint、缺少 entry、或未 approved 都會直接 fail `validate_phase(5)`
- **VSX bundled skill synced**: `vscode-extension/skills/auto-paper/SKILL.md` 與 source `.claude/skills/auto-paper/SKILL.md` 重新同步
- **Tests**:
  - Python: 876 passed, 10 skipped, 1 deselected
  - VSX: 126 passed

#### Code-Enforced Reference Sufficiency & Review Loop (2026-03-11)

- **\_enforce_reference_sufficiency()**: 寫作前硬性檢查文獻數量，不足時返回結構化 REMEDIATION_REQUIRED 指令（unified_search + save_reference_mcp）
  - 接入 `write_draft` 和 `draft_section`，與 concept validation 同層級
  - 讀取 journal-profile.yaml 取得 paper_type 對應最低門檻
  - 從 concept.md 標題提取搜尋 topic hint
- **\_check_review_completed()**: PipelineGateValidator 新方法，驗證 Phase 7 review loop 完成
  - 檢查 audit-loop-review.json 存在、min_rounds 達標、verdict 合法
  - 接入 `_check_prerequisites()` 作為 `prereq:review_completed`（phase >= 8, != 65）
- **\_run_pre_export_review_gate()**: export_docx/export_pdf 直接阻擋未完成 review
- **修復 5 個既有測試**: 補上缺少的 concept-review.yaml 前置條件（Phase 4+ 需求）
- **Tests**: 871 passed（51 pipeline gate, 39 audit hooks）

#### VSX Extension Phase 2+3: runWithTools + DrawioPanel (2026-03-04)

- **runWithTools()**: 5-round tool-calling loop using LanguageModel API (sendRequest + invokeTool)
- **8 command-specific tool filters**: search/draft/concept/project/format/analysis/strategy/drawio
- **/autopaper 和 /help 維持 static**；其他命令皆走 runWithTools
- **DrawioPanel**: WebviewPanel 單例模式, iframe to localhost:6002, CSP, 3s polling
- **package.json**: 新增 /drawio 命令, hook count 76→77
- **Follow-up provider**: 新增 📐 Draw.io 選項

#### Governance Review Stack (2026-03-04)

- **Concept Review Gate**: validate_concept 阻擋 novelty < 75 的寫作
- **Pipeline Gate Validator**: Phase 4/7/9/11 Hard Gates
- **Writing Hooks**: C12 citation relevance audit, C13 figure/table quality
- **concept-review-report.template.yaml**: 結構化審查報告模板

#### Draw.io Submodule

- 整合文件: `integrations/next-ai-draw-io/docs/MEDPAPER_INTEGRATION.md`
- Submodule ref: `d289938`

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
- [ ] VSX packaging test 更新（新增 drawioPanel.ts 和 /drawio command）

2026-03-04
