# Decision Log

## [2026-07-14] v0.9.0 Provider-Neutral Production Harness

### 背景

Repository 長期未完整翻新，使用者要求同步最新 upstream 後，讓 Claude Code、Codex、OpenClaw 共用更完整的學術寫作 harness，增加 proposal/closeout/student/conference/thesis/arXiv 等正式產出、exemplar-aware 邊界、boundary/smoke tests、孤兒符號與 DDD 清理、文件網站、分段 Git 與正式 release。

### 本次決定

1. **Domain registry 是正式產出單一權威**：UI enum、hook applicability、concept requirements、writing order 與 constraint parity 都由 `domain.paper_types` 驗證，legacy shared constant 只保留相容性並用測試防漂移。
2. **Novelty 不是所有產出的固定 gate**：proposal、closeout、student paper、thesis 依各自 concept contract 驗證；conference/arXiv 與 journal novelty profiles 才執行 novelty scoring。
3. **Exemplar 與 evidence 永久分流**：`.audit/exemplar-usage.yaml` 只允許 structure/methodology/reporting/argument/style calibration，固定禁止 evidence eligibility、citation credit、verbatim copying，policy tampering 會阻擋後續紀錄。
4. **DDD 邊界由測試強制**：Application 定義 repository/export Protocol ports，Infrastructure 在 Presentation composition root 注入；Application/Domain 不再反向 import outer layers。
5. **Smoke 必須跑完整 tool surface**：greedy runner 使用隔離 project/CSV/reference fixtures，分類所有 118 tools；只有 interactive elicitation 與 live PubMed 按設計跳過，transport/runtime broken 為 release failure。
6. **正式功能採 minor release**：在 upstream v0.8.0 基礎上提升至 v0.9.0，並同步 Python、VSIX、bundle、lock、CHANGELOG、README、ROADMAP、Memory 與 release artifacts。

### 成果

- 13 output profiles / 110 DomainConstraintEngine base constraints / 79 quality checks。
- 118-tool greedy smoke：116 ok、2 designed skip、0 broken/error；基礎 smoke 14/14。
- VSIX：169 tests、92/92 validate、npm audit 0、0.9.0 install smoke passed。
- 完整 Python、security、build 與 release publication 結果將在本 release entry 完成後更新。

## [2026-05-19] v0.7.11 Phase Gate + Release Hardening

### 背景

使用者要求 13 checkpoint surface 做正式發布前 review，並在完成修正後執行 MEM、分段 git、push、tag 發布新版。審查指出 Phase 8-11 仍有「artifact exists but invalid」與「文件/發布面漂移」風險：Phase 8 legacy flat refs 會被 C5 誤判、Phase 9/11 可接受 corrupt exports、Phase 10 可被 count-only audit YAML 假陽性通過、PyPI artifacts 可能遺失 runtime templates，且 release workflow 權限與 install reproducibility 不夠嚴格。

### 本次決定

1. **Phase 8-11 改為資料品質 gate，不只檔案存在**：後續 phase 必須承接 Phase 7 review artifacts、Phase 8 citation wikilink sync、Phase 9 DOCX/PDF integrity、Phase 10 D1-D9 provenance。
2. **Phase 10 meta-learning audit 採 schema v2 + event provenance**：`MetaLearningEngine` 寫入 `source_tool` 與 `analysis_steps D1-D9`；gate 同時檢查 counts/list 一致性與 matching `run_meta_learning` event，拒絕手寫 count-only YAML。
3. **Export success 必須代表 artifact 可交付**：`export_docx()` / `export_pdf()` 在回傳 success 前執行 DOCX XML / PDF structural smoke；Phase gate 也用同一套 smoke。
4. **Release workflow 採 least privilege + reproducible install**：全域 `contents: read`，只有 GitHub Release job 有 `contents: write`；release installs 使用 pinned `setup-uv` 0.10.0 與 `uv sync --frozen --all-extras`；publish jobs 依賴 `lint-security`。
5. **sdist 必須顯式 scoped 且 wheel 必須含 runtime templates**：Hatch sdist 只 include Python package、templates 與必要 metadata，避免 VSIX/node/workspace artifacts 進 PyPI source distribution，同時用 wheel package data 保留 templates/CSL/journal profiles。

### 成果

- Version: `0.7.11`
- Local artifacts: `medpaper-assistant-0.7.11.vsix` (1.9 MB), wheel 656 KB, sdist 772 KB
- Validation: Python 1305 passed / 1 skipped / 26 deselected; VSIX 169 passed; VSIX validate 92 passed; ruff, format, mypy, bandit, MCP boot, tool-surface authority, uv build, install smoke, npm audit, wheel-template smoke, `git diff --check` all passed.

## [2026-05-19] v0.7.11 Release Publication Outcome

### 背景

After pushing `origin/master` and annotated tag `v0.7.11`, GitHub Actions `Release` ran for the tag. The workflow passed validation, three-platform smoke, Python tests, security/audit, bundle drift, build artifacts, and PyPI trusted publishing. It failed only at `publish-vsx`.

### 根因

`publish-vsx` reached Marketplace and attempted to publish `u9401066.medpaper-assistant v0.7.11`, but Marketplace returned `TF400813: The user 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa' is not authorized to access this resource.` The `VSCE_PAT` secret was present but lacks the required publisher/resource authorization or is no longer valid.

### 決定

1. Treat VS Marketplace failure as an external credential/permission issue, not a repository release blocker for PyPI/GitHub artifacts.
2. Manually create GitHub Release `v0.7.11` from the pushed tag and upload the locally verified VSIX, wheel, and sdist so the release is available despite the Marketplace secret failure.
3. Keep the failed Actions run as evidence that Marketplace publish did not complete; fix/rotate `VSCE_PAT` before retrying Marketplace publishing.

### 成果

- `origin/master` is synced at release commit `8df4531`.
- Tag `v0.7.11` points to `8df4531`.
- GitHub Release: `https://github.com/u9401066/med-paper-assistant/releases/tag/v0.7.11`
- Assets uploaded: `medpaper-assistant-0.7.11.vsix`, `med_paper_assistant-0.7.11-py3-none-any.whl`, `med_paper_assistant-0.7.11.tar.gz`.
- CI on `master` completed successfully; Release workflow concluded failure only because `publish-vsx` failed authorization.

## [2026-05-13] v0.7.10 Remote-First Upstream Sync + Curated VSIX Authority

### 背景

使用者要求 dependency / harness / docs 全面對齊 GitHub remote upstream 最新，並特別要求最後執行 MEM、分段 git、push、tag 發布新版。`origin/master` 已在 `v0.7.9`，因此本次 release 版本從原先本地的 `v0.6.8` 修正為 `v0.7.10`。

同步過程中發現一批 VSIX imported harness / wrong-repo harness 會把 bundle surface 擴張到 26 skills / 15 prompts / 24 agents，違反 `tool-surface-authority.json` 的正式發行面（14 skills / 13 prompts / 9 agents）。

### 本次決定

1. **Remote-first conflict policy**：rebase 到 `origin/master`，衝突時以 upstream latest 為權威，再重新套入必要的 MedPaper release 修正。
2. **VSIX 保持 curated bundle authority**：正式 marketplace/VSIX bundle 不採用全部 source harness；仍以 `tool-surface-authority.json` 的 14/13/9 為發行契約。
3. **Auto-Paper 命名採 13 main checkpoints + Phase 2.1 sub-gate**：避免把 `Phase 2.1` 與 heartbeat 主 checkpoint 混成 14/15 phase；Phase 11 維持 code authority 的 "Final Delivery"。
4. **外部 mirror 不由 root formatter 改寫**：`integrations/` 與 `vscode-extension/bundled/` 是 external/source mirror，root `ruff` / pre-commit 不應改壞 byte-for-byte parity。
5. **Reviewer 局部修稿不必整輪重跑**：真實 reviewer comment 可以走 focused patch + review/gate/test path；只有當 phase prerequisite、引用/資產/export artifact 被改壞時才需要回退或重跑對應 phase。

### 成果

- Version: `0.7.10`
- Release commit: `bd5d4c2 release: prepare v0.7.10 upstream sync`
- VSIX: `medpaper-assistant-0.7.10.vsix`
- Validation: full Python suite、VSIX tests、bundle authority、repo counts、smoke test、build validation 全部通過。

## [2026-04-14] Compact-By-Default Main MCP Surface For Workspace And VSX

### 背景

`mdpaper` 原本把 90+ 個 first-party public verbs 全部直接暴露給 agent。雖然功能完整，但在 VS Code / VSX 實際使用時，工具選擇噪音偏高，且 façade-first 設計已經足以承接大多數主流程。

同時，workspace runtime、setup scripts、VSX extension、README/marketplace docs 之間的敘述也需要統一，不然會出現「執行行為是 compact，文件卻還在講舊 counts」的落差。

### 本次決定

1. **保留 full surface，但把 workspace / VSX 預設切到 compact**：新增 `MEDPAPER_TOOL_SURFACE=full|compact`，server registration 依設定決定是否公開 granular verbs。
2. **compact 模式保留 façade entrypoints**：主要保留 project/workspace/review/pipeline/export 等 façade public verbs，隱藏大多數 legacy / granular public verbs。
3. **full surface 仍作為相容與進階模式存在**：若 agent 或開發者需要完整 verb surface，可顯式設定 `MEDPAPER_TOOL_SURFACE=full`。
4. **release blocker 另補 guardrail**：`scripts/copilot_hook_guard.py` 不再因為單一 marker（如 `src`）就把外部絕對路徑 rebasing 進 workspace，改為必須命中 workspace repo alias 才轉換。

### 成果

- `mdpaper` surface 現為 **94 tools（full）/ 44 tools（compact default）**
- workspace setup / `.vscode/mcp.json` / VSX runtime 全部預設 compact
- root README、zh-TW README、VSX README、CHANGELOG、memory-bank 已對齊
- hook guard regression 已補測，避免外部絕對路徑被誤判成受保護 workspace 路徑

## [2026-04-22] Ownership Boundary Hardening + Validation Surface Compression + Library Synthesis View

### 背景

在 dual-workflow 穩定後，仍有三個收斂點：

1. `library-wiki` 的 cross-note dashboard 缺高階 synthesis 視圖，難以直接判斷「可合成」候選。
2. compact surface 仍暴露多個 validation 細粒度 verbs（`validate_concept`、`validate_wikilinks`、`compare_with_literature`），與 façade-first 原則不完全一致。
3. manuscript 與 library-wiki 的 ownership boundary 需要持續以可追蹤決策固定，避免後續回滲。

### 本次決定

1. **Validation compact surface 進一步 façade 化**

- compact 下隱藏三個 validation granular verbs。
- 新增 `validation_action`（compact only）承接 `concept / wikilinks / literature` 三類操作。

2. **Library dashboard 新增 synthesis 視圖**

- `build_library_dashboard(view="synthesis")` 提供 throughput、tag cluster 候選與 ready-to-synthesize 列表。

3. **Ownership boundary 固定原則**

- manuscript-only：concept validation、drafting、review gates、export。
- library-wiki-only：library note triage/metadata/path/dashboard/materialization。
- façade 優先做公共入口，granular verbs 以 full surface 做相容，不回滲 compact 主路徑。

### 成果

- `EXPECTED_TOOL_COUNTS`: full 115 維持不變；compact 23 → 21。
- compact 主路徑新增 `validation_action`，並移除三個 validation granular public verbs。
- library dashboard 可直接輸出 synthesis 候選訊號，提升 Foam/wiki 操作可觀測性。

## [2026-04-10] Facade-First Orchestration + Telemetry-Guided Legacy Deprecation

### 本次背景

第一階段 façade 已落地六個穩定 public verbs：`project_action`、`workspace_state_action`、`run_quality_checks`、`pipeline_action`、`inspect_export`、`export_document`。但 first-party prompts / skills / extension autopaper prompt 仍大量直接指向 legacy verbs，導致新 façade 雖存在卻不是主路徑。

同時 `.audit/tool-telemetry.yaml` 已提供足夠訊號，可開始做「只標 deprecated、不立刻刪除」的第一批 legacy 收斂：

| Legacy Tool                  | Telemetry                                 | 決定                                                                                    |
| ---------------------------- | ----------------------------------------- | --------------------------------------------------------------------------------------- |
| `list_projects`              | 1 calls / 0 errors                        | 標 deprecated，改由 `project_action(action="list")`                                     |
| `get_current_project`        | 3 calls / 0 errors                        | 標 deprecated，改由 `project_action(action="current")`                                  |
| `run_writing_hooks`          | 5 calls / 0 errors                        | 標 deprecated，改由 `run_quality_checks(action="writing_hooks")`                        |
| `run_quality_audit`          | 2 calls / 1 error                         | 標 deprecated，改由 `run_quality_checks(action="quality_audit")`                        |
| `validate_phase_gate`        | 2 calls / 0 errors                        | 標 deprecated，改由 `pipeline_action(action="validate_phase")`                          |
| `pipeline_heartbeat`         | telemetry sparse but fully façade-covered | 主路徑改走 `pipeline_action(action="heartbeat")`                                        |
| `start_review_round`         | 6 calls / 3 errors                        | 標 deprecated，改由 `pipeline_action(action="start_review")`                            |
| `submit_review_round`        | 3 calls / 1 error                         | 標 deprecated，改由 `pipeline_action(action="submit_review")`                           |
| `export_docx` / `export_pdf` | 各 1 call / 0 errors                      | 標 deprecated，改由 `export_document(action="docx")` 或 `export_document(action="pdf")` |

### 本次決定

1. **先改 orchestrators，不先砍工具**：root `.claude/skills/`、`.github/prompts/`、VSX copies、extension autopaper execution prompt 全面改成 façade-first。
2. **greedy smoke runner 也要 façade-first**：SAFE_TOOL_ORDER 先跑 façade，再跑 legacy tools，確保新 public verbs 成為 regression 主路徑。
3. **deprecated 採分批策略**：只有 telemetry 已證明低直接使用量、且 façade 完整覆蓋的 legacy verbs 先在 docstring 標 deprecated。零 telemetry 或覆蓋不完整者暫不標。
4. **第二階段縮面延後**：等 façade adoption 持續一段時間、telemetry 再累積後，再決定哪些 legacy tools 可以真的隱藏或移除。

### 本次成果

- first-party prompts / skills / bundled instructions / extension autopaper prompt 均已切到 façade 主路徑
- greedy smoke runner 現在優先驗證 façade verbs
- 第一批 telemetry-backed legacy verbs 已有 deprecated docstring guardrail
- 保留相容性，尚未進行 destructive surface shrink

## [2026-03-17] Enforcement Gap Closure — Embedded Hooks + Pre-Commit + B2 Guard

### 背景

深入調查 Copilot Lifecycle Hooks 和 git pre-commit hooks 的真實強制力後，發現三個重大缺口：

1. Git pre-commit 只跑 prettier/ruff/mypy/bandit/pytest，完全沒有 paper quality hooks（P-series）
2. `write_draft` 只在結尾附 guidance hint（`build_guidance_hint`），agent 可以無視
3. `patch_draft` 沒有檢查 🔒 受保護內容

### 決定

| 缺口                           | 解決方案                                                            | 設計考量                                                  |
| ------------------------------ | ------------------------------------------------------------------- | --------------------------------------------------------- |
| Git pre-commit 缺 paper hooks  | `scripts/hooks/paper_precommit.py` + `.pre-commit-config.yaml` 註冊 | CRITICAL 時 exit 1 阻擋 commit，WARNING 只報告            |
| write_draft 只有 guidance hint | `_run_embedded_post_write_hooks()` 取代 `build_guidance_hint()`     | 非阻擋式（結果附在回應中）但自動執行，agent 無法跳過呼叫  |
| patch_draft 無 🔒 保護         | Step 3.5 B2 guard 檢測 `🔒` 在 concept.md 的 old_text 中            | 阻擋式（直接 return error），用 `log_agent_misuse()` 記錄 |

### 關鍵設計決策：嵌入式 hooks 為非阻擋式

embedded hooks 選擇 advisory（附在回應中）而非 blocking（阻止寫入），原因：

- 寫入已發生（檔案已存），阻擋無意義
- agent 看到 CRITICAL 報告後會自行修正（大多數情況下）
- 真正的阻擋點在 git pre-commit（P-series）和 phase gate（PipelineGateValidator）
- 使用體驗優於先檢查再寫入（因為檢查需要完整內容）

### 成果

- 11 新測試，916 total（+11）
- 3 個檔案修改（writing.py, editing.py, paper_precommit.py）+ 1 config + 1 test file

## [2026-03-17] Hook Mechanism Full Audit + Fix (9 Discrepancies)

### 背景

使用者要求「從頭開始詳細檢查 hook 機制跟 code 約束機制」。對 WritingHooksEngine（7 mixins）、ReviewHooksEngine（R1-R6）、MetaLearningEngine（D1-D9）、DomainConstraintEngine、HookEffectivenessTracker、MCP tool layer 全面逐一對照程式碼與文件。

### 發現

9 個不一致：

1. `_engine.py` `run_post_manuscript_hooks()` 缺 C10-C13（4 個 hook 存在但未被 batch runner 呼叫）
2. `audit_hooks.py` ALL alias 缺 A7、C7B
3. `audit_hooks.py` POST-WRITE alias 缺 A7
4. `audit_hooks.py` POST-MANUSCRIPT alias 缺 C7B
5. `audit_hooks.py` docstring 寫 37 hooks 實際 40
6. `hook_effectiveness_tracker.py` HOOK_CATEGORIES 缺 P（pre-commit）和 G（git-hooks）
7. `AGENTS.md` Code-Enforced 表漏列 A1-A4、C3-C7d、P1/P2/P4/P5/P7（36→52）
8. `AGENTS.md` Agent-Driven 數量錯誤（42→26）
9. `copilot-instructions.md` hook 架構表與 AGENTS.md 不一致

### 決定

全部修正，保持「文件 = 程式碼」原則。

| 問題                           | 決定                                      | 理由                                         |
| ------------------------------ | ----------------------------------------- | -------------------------------------------- |
| C10-C13 未被 batch runner 呼叫 | 加入 `run_post_manuscript_hooks()`        | 已有 mixin 方法，只是漏接                    |
| HOOK_CATEGORIES 缺 P/G         | 加入 tracker                              | 否則 pre-commit/git hooks 的觸發事件不被追蹤 |
| 文件 hook count 不一致         | 統一為 52 Code-Enforced / 26 Agent-Driven | 精確計數每個 hook 後得出                     |

### 成果

- 5 個檔案修改，905 tests 全過，0 regressions
- Code-Enforced: A1-A7+A3b+A3c (9) + B8-B16 (9) + C3-C13 (11) + D1-D9 (9) + F1-F4 (4) + R1-R6 (6) + P1/P2/P4/P5/P7 (5) + G9 (1) = 54 (doc says 52, includes grouping)

## [2026-03-18] Weak Model Resilience — B2/C2/P6 Code-Enforced Conversion

### 背景

分析 Haiku 等級模型是否能可靠執行完整設計，結論是不行。26 個 Agent-Driven hooks 沒有程式碼強制，弱模型可跳過。識別快速可轉換的 hook 先行修正。

### 決定

| Hook           | 轉換方式                                                  | 理由                                                   |
| -------------- | --------------------------------------------------------- | ------------------------------------------------------ |
| B2 🔒保護內容  | 委託 P5（run_protected_content_check）+ hook_id remapping | 已有 P5 邏輯，只需在 post-write 重用                   |
| C2 投稿清單    | 新 check_submission_checklist() in \_manuscript.py        | journal_profile required_documents 可程式化驗證        |
| P6 記憶同步    | 新 check_memory_sync() in \_precommit.py                  | 檔案 mtime 檢查可確定性執行                            |
| save_reference | deprecation guardrail + log_agent_misuse()                | 弱模型常選錯工具，用 warning 引導至 save_reference_mcp |

### 關鍵設計：B2 複用 P5

B2 🔒保護內容與 P5 protected content check 邏輯完全相同，差異只在 hook_id 和觸發時機（post-write vs pre-commit）。選擇用 `_run_b2_protected_content()` 薄包裝 P5，remapping hook_id='P5' → 'B2'，避免重複邏輯。

### 成果

- 55 Code-Enforced / 23 Agent-Driven（從 52/26）
- 17 新 hook 測試 + 21 弱模型模擬測試，全過
- 所有文件同步更新（4 files）

## [2026-03-03] Paper-Type-Aware Reference Minimum Enforcement

### 背景

文獻搜尋量經常不足，原有 Phase 2 Gate 僅硬編碼 ≥10（所有紙類相同），SKILL.md 的 "15-20" 指引僅 Agent-Driven 容易被忽略。使用者明確要求更強制性的約束。

### 決定

1. **Paper-type-specific minimums**: original-research (20), review-article (30), systematic-review (40), meta-analysis (40), case-report (8), letter (5), fallback (15)
2. **3-tier resolution chain**: journal-profile.yaml override → DEFAULT_MINIMUM_REFERENCES → DEFAULT_MIN_REFERENCES (15)
3. **多重強制點**: Phase 2 Gate (HARD) + Phase 3+ prerequisites + Hook A7 (pre-write) + B003 DomainConstraint
4. **Hook A7 設計**: 放在 run_post_write_hooks 而非獨立 gate，因為它與其他 A-series hooks 一起批量執行，且 CRITICAL severity 已足夠阻擋寫作

### 影響

- Hook count: 76 → 77 (35 Code-Enforced / 42 Agent-Driven)
- 修改 8 個生產檔案 + 3 個測試檔案
- 839 tests all pass

## [2026-03-03] Humanizer Anti-AI 強化 + VS Code Copilot Lifecycle Hooks + 圖表插入修正

### 背景

1. Anti-AI 偵測需要更全面的短語庫和結構分析，以應對 LLM 生成文本的典型模式
2. VS Code Copilot 缺乏 lifecycle hook 機制來自動化模式保護、品質提醒等操作
3. MCP instructions.py 中存在幽靈工具 `save_diagram_standalone` 和缺漏的 figure/table 插入工具

### 決定

1. **Anti-AI 擴展策略**：ANTI_AI_PHRASES 76→133，按 12 個語義類別組織（overly_formal, unnecessary_hedging, ai_conclusions 等）。新增 4 個 A3b 結構檢查（negative parallelism, copula avoidance, em dash, false ranges）
2. **Hook 架構選擇**：使用 VS Code Copilot Lifecycle Hooks（`.github/hooks/`），7 個 bash 腳本 + JSON 配置。stdin/stdout JSON 通訊，依賴 jq 但無 jq 時 graceful exit 0
3. **圖表插入修正**：移除 `save_diagram_standalone`（已合併進 `save_diagram` 的 `output_dir` 參數），補齊 `insert_figure`/`insert_table`/`list_assets` 到 instructions

### 關鍵技術決定

| 問題                    | 選項                                  | 決定            | 理由                                                        |
| ----------------------- | ------------------------------------- | --------------- | ----------------------------------------------------------- |
| Hook 實作方式           | A. VS Code API / B. Shell scripts     | **B. Shell**    | Copilot Hooks 原生支援 shell，無需 extension 改動           |
| jq 缺失處理             | A. 報錯退出 / B. Graceful degradation | **B. Graceful** | exit 0 = allow all，不阻塞正常工作流                        |
| save_diagram_standalone | A. 保留文檔 / B. 移除                 | **B. 移除**     | 工具不存在，save_diagram 已處理 project/standalone 兩種情境 |
| Anti-AI 短語組織        | A. 一個大 list / B. 分類別            | **B. 分類別**   | 12 類更易維護，可單獨啟用/停用                              |

### 成果

- 826 Python tests passed, 106 vitest passed
- 22 個過時工具計數透過 `sync_repo_counts.py --fix` 自動修復
- 7 個 Copilot hook 腳本 + 設計文件就緒

## [2026-03-02] v0.4.0 Bug Fixes + macOS Compatibility

### 背景

v0.4.0 Bug Report 報告了 5 個 Bug。驗證後發現 Bug 1, 2, 5 已在先前修復，Bug 3, 4 需新修復。同時評估 macOS + VS Code Insiders 相容性。

### 決定

1. **Bug 3 修復**：`start_document_session` 的 `template_name` 改為可選參數，空值時呼叫 `create_blank_document()`
2. **Bug 4 修復**：Hook A1 加入 `_strip_frontmatter()` 排除 YAML frontmatter；A6 加入統計標記 regex 排除
3. **macOS MCP env**：子程序環境繼承 `PATH/HOME/SHELL/LANG/USERPROFILE`，解決 homebrew 工具找不到問題
4. **`getPythonArgs` 擴展**：用 regex `/^python3(\.\d+)?$/` 匹配版本化 Python（如 `python3.12`）
5. **VS Code Insiders 不需特別處理**：API 完全相同，`.vscode/` 設定共用

### 關鍵技術決定

| 問題                    | 選項                                                         | 決定              | 理由                                                                |
| ----------------------- | ------------------------------------------------------------ | ----------------- | ------------------------------------------------------------------- |
| MCP env 策略            | A. 只傳 PYTHONPATH / B. 繼承全部 process.env / C. 選擇性繼承 | **C. 選擇性繼承** | 全部繼承可能洩漏敏感變數；只傳 PYTHONPATH 在 macOS 上 uv/git 找不到 |
| Insiders 偵測           | A. 偵測 product name / B. 不做                               | **B. 不做**       | Insiders 和 Stable 使用完全相同的 Extension API 和 `.vscode/` 目錄  |
| subagent 報告 18 issues | A. 全部修 / B. 甄別後修真正問題                              | **B. 甄別**       | 大部分是誤報（path.delimiter 已跨平台、fs.existsSync 不會炸）       |

## [2026-02-28] v0.4.0 文件計數動態同步與 Hook 架構完善

### 背景

深度審查（2026-02-27）後發現文件中的數量宣稱（工具數、hook 數、prompt 數等）散佈於 7+ 個檔案中，長期手動維護導致嚴重不一致：README 寫 131 tools、ARCHITECTURE 寫 89、copilot-instructions 寫 87/81，實際 AST 計數為 85。Hook 數也從 42/56/65 不等，實際為 76。

### 決定

1. **建立動態計數同步腳本** (`scripts/sync_repo_counts.py`)，以 AST 解析取代 regex 計數，支援 `--check`（CI gate）/`--fix`（自動更新）/`--json`（程式化輸出）三種模式
2. **補齊 Hook 架構缺失**：EXPECTED_HOOKS 40→58、HOOK_CATEGORIES 加入 "R"、ReviewHooksEngine 加入 `__init__.py` exports
3. **auto-paper-guide "42" 保持不變** — 確認這是 Agent-Driven 子集（A-D hooks），非總數 76

### 關鍵技術決定

| 問題                    | 選項                                      | 決定           | 理由                                                                            |
| ----------------------- | ----------------------------------------- | -------------- | ------------------------------------------------------------------------------- |
| 計數方法                | A. Regex / B. AST                         | **B. AST**     | `tool_logging.py` docstring 有 `@mcp.tool()` 示例，regex 會誤計為 89（實際 85） |
| auto-paper-guide "42"   | A. 同步到 76 / B. 保持 42                 | **B. 保持 42** | 該數字指 Agent-Driven 子集，非總數。加註釋說明                                  |
| 文件表格對齊            | A. format string / B. regex group capture | **B. `\g<1>`** | 保留原始 markdown 格式，避免空格錯亂                                            |
| EXPECTED_HOOKS 排除 D/G | A. 全部加入 / B. 排除                     | **B. 排除**    | D1-D9 是 meta-learning 引擎本身（自引用），G1-G9 在 pre-commit 獨立追蹤         |

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

---

## [2026-07-14] Shared Codex/OpenClaw Skill Root and Platform-Neutral Writing Contract

### 背景

Repo 原有 `.claude/skills` 與 integration-generated `.codex/skills`，但最新 Codex 與 OpenClaw 都原生支援 repo `.agents/skills`；持續複製大型 auto-paper 流程會造成 drift。範本文獻若未分角色，也容易被誤當 claim evidence 或產生近似仿寫。

### 決定

1. 以 `.agents/skills` 作為 Codex + OpenClaw 共用 repo skill root，Claude Code 保留 `.claude/skills` adapter。
2. 把平台中立流程放在 `docs/harness/academic-writing-workflow.md`，adapter 僅負責 discovery 與 tool capability mapping。
3. 將 `claim_evidence`、`method_authority`、`exemplar_structure`、`exemplar_style`、`user_primary_material` 分成不同來源角色。
4. 範文只可抽取結構與可量測風格特徵；不得複製或輕度改寫獨特措辭、資料、聲稱、引用、圖表或結論。

### 理由

- 同一 skill root 同時符合 Codex 與 OpenClaw 官方 discovery 慣例。
- 單一流程權威降低三平台規範漂移。
- 角色分離可讓引用驗證、著作權與 anti-plagiarism gate 可被程式化審計。

### 後續

- 擴充 code-level output profiles 與 exemplar/evidence artifacts。
- 新增三平台 smoke、文件網站與 release/install smoke。

---

## [2026-07-14] Canonical Formal Output Registry and Audited Exemplar Boundary

### 背景

七種 article profile 無法涵蓋計畫書、結案、學生小論文、會議論文、學位論文與 arXiv/preprint；既有 concept validator 又把 novelty 契約套用到所有輸出。範本文獻規則若只存在於 prompt，亦無法留下可驗證軌跡。

### 決定

1. Domain `paper_types.py` 是 13 種正式輸出 profile、writing order 與 concept requirements 的唯一權威；shared/UI/hook applicability 從該 registry 投影。
2. DomainConstraintEngine 將六種新增輸出納入 code-level enforcement，總計 13 profiles / 110 base constraints。
3. Concept validation 依 profile 動態選擇 required sections 與 novelty gate，且 cache key 必須包含 validation-mode flags。
4. 範文使用寫入 `.audit/exemplar-usage.yaml`；只允許 structure、methodology、reporting、argument-map、style-calibration，且 evidence/citation/verbatim-copy 權限永遠為 false。
5. Application layer 只依賴自身 Protocol ports 與 Domain；以 AST boundary test 防止重新引入 Infrastructure 依賴。

### 證據

- Python：1523 passed / 8 skipped / 26 deselected。
- MCP：118 tools 全面 greedy classification（116 ok、2 designed skip、0 broken/error）與 14/14 basic smoke。
- 品質：Ruff、format、mypy、Bandit、vulture 80%、DDD boundary、package content、bundle parity 全通過。
- VSIX：169/169 tests、92/92 validate、install smoke、npm audit 0 vulnerabilities。
