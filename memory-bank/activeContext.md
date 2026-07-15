# Active Context

## User Preferences

- **Git Identity**: u9401066 <u9401066@gap.kmu.edu.tw>

## 當前焦點 (2026-07-15)

Production refresh 已完成 v0.9.0；公開 GitHub Pages Wiki 已上線，以 Mermaid 與 SVG 系統化說明跨 Agent harness、研究 pipeline、證據邊界、品質治理與發布維運。後續回到 evidence-context ledger、bounded exploration 與 Marketplace 授權修復。

### 當前狀態

| 項目                  | 數量/狀態                                                                                                               |
| --------------------- | ----------------------------------------------------------------------------------------------------------------------- |
| MCP Tools             | **118 full / 22 compact (default)** + 3 prompts + 3 resources                                                           |
| External MCP Surface  | **PubMed Search 46 tools** + **CGU 24 tools**                                                                           |
| Repo Skills / Prompts | **38 Claude/workflow skills + 1 shared agent skill / 15 prompt workflows**                                              |
| VSIX Bundled Surface  | **14 skills / 13 prompts / 9 agents / 4 templates / 7 support files / 11 palette / 10 chat**                            |
| Hooks                 | **79 checks** (56 Code-Enforced / 23 Agent-Driven)                                                                      |
| Pipeline Docs         | **13 main gate checkpoints** (`Phase 0-11 + 6.5`) + **Phase 2.1** fulltext/source-material sub-gate                     |
| Validation Gate       | `scripts/check_tool_surface_authority.py` + `npm run validate`                                                          |
| Latest Validation     | Python 1523 passed / 8 skipped / 26 deselected; VSIX 169 passed; MCP smoke 14/14 + 118/118 classified; validate 92/92   |
| Packaging             | **v0.9.0** GitHub Release + PyPI published; VSIX attached; Marketplace blocked by external `VSCE_PAT` authorization     |
| Documentation         | [公開 Wiki](https://u9401066.github.io/med-paper-assistant/)；**32 pages / 48 Mermaid / 8 accessible SVG**；Pages CI ✅ |

> 下方條目保留為近期演進記錄；以本節與 `tool-surface-authority.json` 作為目前 surface 判斷依據。

### 三層演進架構實作狀態

| 層級                         | 狀態                   | 說明                                                                   |
| ---------------------------- | ---------------------- | ---------------------------------------------------------------------- |
| L1 Event-Driven Hooks        | ✅ 56/79 Code-Enforced | 23 個 Agent-Driven 由 SKILL.md 與契約測試治理                          |
| L2 Code-Level Enforcement    | ✅ 完整                | 13 profiles / 110 constraints + telemetry/evolution                    |
| L3 Autonomous Self-Evolution | ⚠️ 大部分完成          | EvolutionVerifier + weekly health 已上線；缺 git post-commit / Auto-PR |

### 最近變更

#### GitHub Pages Wiki + Visual Architecture (2026-07-15)

- 以 `mkdocs.yml` 與 MkDocs Material 取代舊 `docs/index.html`、manifest 與 generated JavaScript，建立主題式 Wiki 導覽、全文搜尋、深淺色模式與響應式首頁。
- 新增 Repo、quickstart、pipeline、outputs、evidence、harness、MCP、workspace、quality、development 與 visual atlas 頁；全站目前 32 頁、48 張 native Mermaid 圖。
- 新增五張 Wiki SVG，並校正三張舊 SVG 的跨 Agent、118-tool、DDD inward dependency 與 Phase 2.1/6.5/11 敘事；八張 SVG 均有 title/desc/ARIA。
- 新增文件 source validator 與 tests，檢查 orphan pages、broken local links、Mermaid/SVG 覆蓋、SVG accessibility、legacy-site removal 與 Pages deploy ordering。
- 新增 `.github/workflows/pages.yml`：PR 執行 locked strict build，`master` 經 official Pages artifact/deploy actions 發布。
- GitHub Pages 已設為 workflow build、repository homepage 已指向 Wiki；Pages run `29381248488` 與主 CI run `29381248501` 成功，六個公開 smoke endpoints 均為 HTTP 200。

#### Cross-Agent Production Refresh — Foundation (2026-07-14)

- 新增 `CLAUDE.md` 與 `.agents/skills/academic-writing-harness`；最新 Codex/OpenClaw 共用 `.agents/skills`，Claude Code 使用 `.claude/skills` 薄入口。
- 新增 `docs/harness/academic-writing-workflow.md`，定義 proposal、closeout、student paper、preprint 與 exemplar role separation。
- 新增共享 JSONC parser，修復 `http://` 被誤刪並套用到 Foam 與 pipeline doctor。
- 修復 5 個無效 skill frontmatter，新增所有 repo skills 的 discovery contract test。
- 補上 VSIX ESLint 設定、清除 lint 發現的 unused imports/parameters，完成 bundle mirror 同步。
- 同類專案 benchmark 已記錄 PaperQA、STORM、AI-Scientist-v2、Quarto 的採納與拒絕邊界。
- 安全整合 upstream v0.8.0；保留 constraint ledger、article-type applicability、adversarial harness 與本輪跨 Agent 改造。
- 將 VSIX 工具鏈升級至 ESLint 10 flat config、typescript-eslint 8.64、VSCE 3.9、Vitest 4.1；`npm audit` 由 22 個漏洞降為 0。
- 重建並通過 `medpaper-assistant-0.8.0.vsix` install smoke；post-merge Python/VSIX/smoke/validate 全部通過。

#### v0.9.0 Formal Output + Production Harness (2026-07-14)

- 新增 research proposal、project closeout、student paper、conference paper、thesis/dissertation、arXiv/preprint 六種 code-level profiles；總計 13 profiles / 110 base constraints。
- Concept validator 改為依 profile 動態判斷必填 section 與 novelty，並修正 validation-mode cache collision。
- 新增 `.audit/exemplar-usage.yaml` 與 compact facade action；exemplar 永遠不能取得 evidence/citation credit 或逐字複製資格。
- Application layer 以 Protocol ports 取代 Infrastructure 反向 import，並新增 DDD 靜態 boundary tests。
- vulture 高可信度掃描零發現；118-tool greedy smoke 為 116 ok、2 designed skip、0 broken/error，並修復 legacy metadata `unique_id` migration bug。
- 新增 dependency-free docs site、13-page manifest、formal output guide 與 Mermaid production architecture。
- 版本已提升至 0.9.0；Python 1523 passed / 8 skipped / 26 deselected，VSIX 169/169 tests、install smoke 與 92/92 validate 通過。
- wheel、sdist 與 `medpaper-assistant-0.9.0.vsix` 已建立；封裝內容檢查確認六種新 concept templates 與 journal profile 均存在。
- 首次遠端 release dry run 發現 npm 11 optional dependency lock 漂移與 19 個 Markdown 格式問題；已補齊 `@emnapi` lock entries、以 CI-pinned Prettier 3.1 正規化並以乾淨 `npm ci` 重現通過。
- `master` CI 全綠；annotated tag `v0.9.0` 指向 `4d1bec7`，PyPI trusted publish 成功，GitHub Release 已附 2,031,016-byte VSIX、wheel 與 sdist。
- VS Marketplace publish 仍因既有 `VSCE_PAT` 身分未獲授權而回報 `TF400813`；屬外部 Marketplace 權限，非 package/build failure。

#### v0.7.11 Phase Gate + Release Hardening (2026-05-19)

- **Phase 8-11 gates hardened**: later phases now require completed Phase 7 artifacts/review events, resolved citation wikilinks, valid DOCX/PDF structure, Phase 10 D1-D9 `analysis_steps`, and Phase 10 pass before final delivery.
- **Export integrity**: `ExportPipeline.export_docx()` now fails missing/corrupt DOCX immediately; `export_pdf()` adds PDF header/trailer smoke validation and returns post-export checks.
- **Meta-learning provenance**: `MetaLearningEngine` writes `schema`, `source_tool`, and structured D1-D9 `analysis_steps`; Phase 10 rejects count-only hand-authored audit YAML and requires matching `run_meta_learning` evolution-log provenance.
- **Release workflow**: `.github/workflows/release.yml` uses global `contents: read`, job-local release write permissions, pinned `setup-uv` 0.10.0, `uv sync --frozen --all-extras`, manual dispatch version/tag guard, and `lint-security` before publish/release jobs.
- **Packaging**: sdist scoped via Hatch include list after discovering an oversized 590 MB sdist; runtime templates/CSL/journal profiles are bundled into the wheel and verified via wheel unpack smoke.
- **Docs/VSIX**: README EN/zh-TW, CHANGELOG, ROADMAP, auto-paper guide, MCP instructions, source skills, and VSIX bundled skills/Python mirror aligned to facade-first project/draft/export guidance and D1-D9.
- **Verification**: `uv run pytest tests/ -q --timeout=60 -m "not integration and not slow"` → 1305 passed / 1 skipped / 26 deselected; `npm run test:ci` → 169 passed; `npm run validate -- --skip-tests` → 92 passed; ruff/mypy/bandit/uv build/VSIX smoke/tool authority/MCP boot/wheel-template smoke all pass.
- **Publication**: `origin/master` and tag `v0.7.11` pushed at commit `8df4531`; GitHub Release exists with VSIX, wheel, and sdist assets; PyPI trusted publish succeeded in Actions.
- **External publish caveat**: VS Marketplace publish failed in Actions with `TF400813` authorization error for the configured `VSCE_PAT`; this is an external secret/Marketplace permission issue, not a repository package/build failure.

#### v0.7.10 Upstream Dependency + 13-Phase Docs Release (2026-05-13)

- **Remote-first sync**: rebased local work onto upstream `origin/master` `8db10ed` (`v0.7.9`) and kept remote as authority when conflicts appeared.
- **External MCP updates**: aligned submodules to upstream PubMed Search MCP 0.5.9 (46 tools), Asset-Aware MCP 0.6.30, and CGU upstream master; regenerated `uv.lock`.
- **PubMed harness**: setup/migration/VSX runtime now uses `NCBI_EMAIL` and the current `pubmed_search.presentation.mcp_server` entrypoint; `uvx` maps to `pubmed-search-mcp`.
- **Auto-Paper docs**: README, zh-TW README, auto-paper guide, multi-stage review design, skill/prompt assets, SVG/marketplace banner, and VSX package wording now use the 13 main checkpoint + Phase 2.1 sub-gate model.
- **VSIX authority corrected**: removed the attempted all-harness bundle expansion; package/validation remain at the curated authority surface (14 skills / 13 prompts / 9 agents).
- **External mirror guard**: root ruff/pre-commit now excludes mirrored external code under `integrations/` and `vscode-extension/bundled/`, preserving byte-for-byte source/bundle sync.
- **Reviewer/local edit workflow note**: reviewer-driven partial revisions can use focused `pipeline_action` review/gate checks plus targeted tests; they do not require rerunning the whole Auto-Paper pipeline unless phase prerequisites or exported artifacts are invalidated.
- **Post-release CI/hook hygiene**: updated GitHub Actions to Node 24-ready action majors and changed `paper_precommit.py` to skip silently unless staged draft files exist, then scan only those staged draft projects.

#### v0.7.9 Vancouver Export + FOAM Compatibility Release (2026-04-24)

- **Vancouver citeproc export**: `export_document(action="docx"|"pdf")` now always runs Pandoc citeproc when a bibliography is present, supports `vancouver-superscript`/BJA aliases, and includes `vancouver-superscript.csl`.
- **References cleanup**: Hand-maintained References sections are stripped before citation conversion across heading levels so `[[ref_key]]` trailers cannot become leaked `[@key]` tokens.
- **Export smoke hardening**: DOCX XML smoke now fails raw citation tokens (`[@`, `[[`, `]]`) after export.
- **FOAM/manuscript split**: Shared parsing now distinguishes renderable manuscript citations from FOAM embeds, anchors, aliases, and internal wiki links; C5/C10/C11/C14 use the same semantics.
- **Branch convergence**: Folded the unmerged `origin/codex/check-design-errors` fixes into master: explicit `exports/` path mapping, `MEDPAPER_BASE_DIR` workspace-state initialization, and resolved-path review-loop cache keys.

#### v0.7.6 Agent-Friction Release (2026-04-24)

- **Pipeline doctor**: 新增 `pipeline_action(action="doctor")`，一次回傳 11-phase readiness、外部 MCP declaration/command availability、最近 gate cache，讓 agent 不必用多輪 trial-and-error 自省。
- **Source-material intake**: Phase 0 新增 `project_action(action="source_materials")`，掃描 workspace root DOCX/XLSX/PDF/PPTX/CSV，產出 `.audit/source-materials.yaml/.md` 並標示 `pending_asset_aware`。
- **Asset-aware receipt**: 新增 `project_action(action="record_asset_ingestion")`，讓外部 asset-aware MCP 回填 doc_id/sections/artifacts，Phase 2.1 可阻擋 primary source 尚未 ingest 的情況。
- **Data provenance**: F4 data anchors 必須引用 ready source material、asset-aware doc、tracked data artifact 或 trusted data file，避免 concept/agent 推測數字變成真實 anchor。
- **Claim evidence**: C14 hook 新增 claim-evidence alignment，並依 novelty/causality/superiority/magnitude/certainty 分類 severity。
- **Phase 9 export smoke**: 新增 `inspect_export(action="docx_smoke"|"xml_smoke")`，檢查 DOCX zip/XML 結構、`word/document.xml`、段落與可見文字。
- **Release validation**: targeted facade/export/C14 tests `69 passed`；tool-surface authority `2 passed`；full pytest `1254 passed, 17 skipped, 1 deselected`；VSIX bundle check and TypeScript compile passed.

#### v0.7.3 Path Guard & MCP Surface Release (2026-04-23)

- **Central path guard**: 新增共享 filename/child-path guard，統一阻擋空檔名、hidden names、POSIX/Windows absolute paths、drive/UNC paths、traversal、invalid characters、reserved device names、trailing dot/space、case-insensitive collisions
- **Bug 1 fixed**: `draft_action(action="write", section="methods")` 正確寫入 `drafts/methods.md`，不再落到 `drafts/.md`
- **Bug 2 fixed**: compact surface 暴露 `analysis_action`，並恢復 figure/table asset review/list/insert 路由，Phase 5 data-artifacts provenance 不再只有文件入口
- **Bug 3 fixed**: data-artifacts validation 可讀 canonical/legacy/custom manifest 位置與 schema，避免 valid manifest 被算成 `total_artifacts: 0`
- **Bug 4 fixed**: `validation_action` 補上 list/help aliases，文件與實作的 validation type 對齊到 `concept`, `literature`, `wikilinks`
- **Locale false positive fixed**: A5 hook 讀取 `en-GB` journal profile，避免 BJA British spelling 被誤判
- **Release validation**: source/bundled mirror parity `missing=0, extra=0, different=0`；tool-surface authority passed；repo count sync passed；targeted suite `479 passed`；full non-integration suite `1208 passed`

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
- VS Marketplace publish secret needs rotation/permission repair: `VSCE_PAT` was present but Marketplace rejected it with `TF400813` during v0.7.11; PyPI and GitHub Release were completed.

## 下一步

- [x] Push segmented v0.7.11 release commits and tag `v0.7.11`
- [x] Watch GitHub release/CI result after tag propagation
- [ ] Rotate/fix `VSCE_PAT` publisher authorization, then rerun VS Marketplace publish for v0.7.11 or next release
- [ ] Phase 5c TreeView/CodeLens/Diagnostics features
- [ ] Dashboard Webview 內嵌（取代 Simple Browser）
- [ ] CI/CD pipeline for automated VSIX publish
- [ ] Run actual project pipeline to generate evolution data
- [ ] Consider grammar checker (language-tool-python as A7)
- [ ] VSX packaging test 更新（新增 drawioPanel.ts 和 /drawio command）

2026-03-04
