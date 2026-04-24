# Progress (Updated: 2026-04-24)

## Done

- **v0.7.6 agent-friction release prep (2026-04-24)**:

  - Added Phase 0 source-material intake, asset-aware ingestion receipt recording, Phase 2.1 pending-source blocking, and F4 data-anchor provenance validation
  - Added C14 claim-evidence alignment with claim-type severity for novelty, causality, superiority, magnitude, and certainty claims
  - Added `pipeline_action(action="doctor")` for one-shot 11-phase readiness, external MCP, and recent gate diagnostics
  - Added Phase 9 DOCX XML smoke via `inspect_export(action="docx_smoke"|"xml_smoke")`
  - Updated authority-driven docs/counts to 117 full / 22 compact + 3 prompts + 3 resources
  - Validation completed: targeted facade/export/C14 tests 69 passed; tool-surface authority 2 passed; full pytest 1254 passed / 17 skipped / 1 deselected; bundle check and VSIX TypeScript compile passed

- **v0.7.3 path guard + MCP surface release prep (2026-04-23)**:

  - Added central cross-platform filename/path guard and applied it across draft, analysis assets, data artifacts, validation, project/library/reference/export/storage/review entrypoints
  - Fixed `draft_action(write section=...)` empty filename regression, restored compact `analysis_action` asset routes, repaired data-artifact manifest detection, aligned `validation_action` aliases, and removed BJA/en-GB A5 false positives
  - Synced source and VS Code bundled Python runtime with zero mirror drift
  - Updated authority-driven docs/counts to 115 full / 22 compact + 3 prompts + 3 resources
  - Validation completed: compileall, tool-surface authority, repo count sync, source/bundled parity, targeted path-guard suite 479 passed, full non-integration suite 1208 passed

- **v0.6.4 release prep (2026-04-14)**:

  - main mdpaper tool surface compactification landed (full 94 / compact 44 default)
  - workspace and setup defaults now inject `MEDPAPER_TOOL_SURFACE=compact`
  - VSX runtime defaults to compact surface and tests assert env behavior
  - root/zh-TW/VSX documentation aligned to full vs compact counts
  - changelog + version bump prepared for segmented commit/push/tag flow

- v0.4.6: uvManager.ts — cross-platform uv auto-detection + headless installation for zero-config marketplace mode
- v0.4.6: extensionHelpers.ts — 6 pure functions extracted from extension.ts for testability
- v0.4.6: Marketplace mode uses uvx med-paper-assistant (PyPI isolation, no PYTHONPATH)
- v0.4.6: Test expansion 52 → 106 vitest (extensionHelpers 30, packaging 21, uvManager 20, extension 35)
- v0.4.6: Fixed mcp.json skip check (require both mdpaper + med_paper_assistant)
- v0.4.6: Fixed getPythonPath only returning uv for med-paper-assistant pyproject.toml
- v0.4.6: CHANGELOG, ROADMAP, version bump completed
- v0.4.6: git add + commit + push + tag — released
- Humanizer anti-AI update: ANTI_AI_PHRASES 76→133 (12 categories), AI_TRANSITION_WORDS 25→33, 4 new A3b structural checks (#6 negative parallelism, #7 copula avoidance, #8 em dash, #9 false ranges), 12 new tests
- VS Code Copilot Lifecycle Hooks: 7 hook scripts (session-init, prompt-analyzer, pre-tool-guard, post-tool-check, pre-compact-save, subagent-init, session-stop) + config + design doc
- MCP instructions fix: removed ghost save_diagram_standalone, added insert_figure/insert_table/list_assets to DATA ANALYSIS, updated DIAGRAM WORKFLOW
- Tool count sync: 85→86 tools (review/ 21→22), sync_repo_counts.py --fix across 5 files (22 stale counts fixed)
- **Paper-type-aware reference minimum enforcement**: Hook A7 + Phase 2 Gate paper-type-aware + B003 constraints + journal-profile minimum_reference_limits + 15 new tests (839 total)
- **VSX Phase 2+3**: runWithTools() 5-round tool-calling loop + 8 command-specific tool filters + DrawioPanel WebviewPanel + /drawio command + 77 Hooks
- **Governance Review Stack**: Concept Review Gate (novelty<75 block) + Pipeline Gate Validator (Phase 4/7/9/11) + C12/C13 hooks + template
- **Draw.io submodule doc**: MEDPAPER_INTEGRATION.md in integrations/next-ai-draw-io (d289938)
- **Stale project state bug fixed**: unified ProjectManager singleton + MEDPAPER_BASE_DIR path resolution; fixed VSX wrong-project reads
- **AutoPaper execution hardening**:
  - VSX `/autopaper` now executes MCP tool loop instead of static markdown-only flow
  - Added `TOOL_FILTERS.autopaper` + `buildAutopaperExecutionPrompt()`
  - Phase 5 `section_approval` is now a real hard gate (checkpoint + approved required sections mandatory)
  - Synced bundled `auto-paper` skill with source workspace skill
  - Tests: Python 876 passed, VSX 126 passed
- **Asset review receipt hard gate for figures/tables**:
  - New `review_asset_for_insertion()` tool records auditable review receipts before captioning/insertion
  - `insert_figure()` / `insert_table()` now refuse captions without matching receipts
- **Enforcement gap closure (P0–P1)**:
  - P0: `scripts/hooks/paper_precommit.py` registered in `.pre-commit-config.yaml` — runs P1/P2/P4/P5/P7 on `git commit`
  - P1: `write_draft` and `patch_draft` now auto-run A-series hooks (embedded, agent cannot skip)
  - B2: `patch_draft` blocks modification of 🔒-protected content in `concept.md`
  - 11 new tests, 916 total passing
  - Phase 5 + Hook F validate caption/asset review linkage
  - Tests: Python fast suite 881 passed
- **Hook mechanism full audit + fix (2026-03-17)**:
  - Complete audit of all Code-Enforced hooks (A/B/C/D/F/P/G/R series)
  - Fixed `run_post_manuscript_hooks()` missing C10-C13 in batch runner
  - Fixed MCP `run_writing_hooks` aliases: ALL missing A7+C7B, POST-WRITE missing A7, POST-MANUSCRIPT missing C7B
  - Fixed `HOOK_CATEGORIES` missing P (pre-commit) + G (git-hooks) entries
  - Updated MCP tool docstring to list all 40 hooks
  - Updated Engine class docstring (A-series A1–A7, F not F1–F4, P-series P1/P2/P4/P5/P7)
  - Corrected hook count: 36→52 Code-Enforced / 42→26 Agent-Driven (total still 78)
  - AGENTS.md + copilot-instructions.md tables fully aligned with code
  - 905 tests all passing, 0 regressions
- **Weak model resilience — 3 hooks Code-Enforced (2026-03-18)**:
  - Converted B2 🔒保護內容, C2 投稿清單, P6 記憶同步 from Agent-Driven to Code-Enforced
  - B2: delegates to P5 with hook_id remapped; runs in post-write batch
  - C2: check_submission_checklist() reads journal_profile required_documents; 8 doc type patterns; runs in post-manuscript batch
  - P6: check_memory_sync() checks .memory/ and memory-bank/ mtimes (7200s threshold); runs in precommit batch
  - save_reference() deprecation guardrail with log_agent_misuse()
  - 17 new tests (B2×4, C2×8, P6×5) + 21 weak model simulation tests — all passing
  - Hook count: 52→55 Code-Enforced / 26→23 Agent-Driven (total still 78)
  - All docs synced: AGENTS.md, .github/copilot-instructions.md, vscode-extension/copilot-instructions.md, memory-bank/activeContext.md

## Doing

- Publishing v0.7.7: changelog/version/memory/roadmap update, commit, push branch, create and push tag

## Next

- Watch v0.7.7 release tag CI and package publication status
- Build a code-level autopaper orchestrator (reduce reliance on SKILL-only sequencing)
- Add semantic repair loop after hook failures (patch -> rerun hooks -> converge/regress/escalate)
- Phase 5c TreeView/CodeLens/Diagnostics features
- Dashboard Webview embedding
- CI/CD pipeline for automated VSIX publish
