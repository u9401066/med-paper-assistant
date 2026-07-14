# Progress (Updated: 2026-07-14)

## Done

- **v0.9.0 formal-output and production harness (2026-07-14)**:

  - Expanded the canonical domain registry from 7 to 13 output profiles and DomainConstraintEngine from 69 to 110 base constraints
  - Added full concept templates and writing prerequisites for proposal, closeout, student, conference, thesis/dissertation, and arXiv/preprint outputs
  - Made concept validation profile-aware, including novelty opt-out and validation-mode cache isolation
  - Added a tamper-detecting exemplar-use audit store and consolidated MCP facade action with hard non-evidence/non-citation/non-copy policy
  - Removed Application→Infrastructure imports through application-owned Protocol ports and added static DDD boundary tests
  - Reached zero vulture findings at 80% confidence and fixed legacy reference-analysis migration plus greedy-smoke data fixture failures
  - Added a dependency-free documentation hub, validated 13-page manifest, formal profile guide, and Mermaid production/DDD diagrams
  - Greedy MCP smoke: 118 total, 116 ok, 2 designed skips, 0 broken/error; basic install smoke: 14/14
  - Packaged and install-smoked `medpaper-assistant-0.9.0.vsix`; VSIX tests 169/169 and validate 92/92
  - Final release matrix: Python 1523 passed / 8 skipped / 26 deselected; Ruff, format, mypy, Bandit, vulture, consistency, tool authority, docs build, MCP boot, npm audit, bundle parity, wheel/sdist content, and VSIX install smoke all passed
  - Closed release-runner drift found by the first remote dry run: npm 11 lockfile now includes optional `@emnapi` packages, clean `npm ci` passes, and all tracked Markdown passes CI-pinned Prettier 3.1
  - Published annotated `v0.9.0` at `4d1bec7`; master CI passed, PyPI trusted publishing succeeded, and GitHub Release carries the VSIX, wheel, and sdist
  - VS Marketplace publish remains externally blocked by `TF400813` for the configured `VSCE_PAT`; the VSIX itself packages, validates, installs, and is available on GitHub Release

- **Cross-agent production refresh foundation (2026-07-14)**:

  - Added native Claude Code plus shared Codex/OpenClaw skill entrypoints and a platform-neutral academic-writing workflow
  - Added proposal/closeout/student/preprint and exemplar role contracts before code-level profile expansion
  - Fixed URL-safe JSONC parsing across MCP smoke, Foam settings, and pipeline doctor
  - Repaired five invalid/missing skill frontmatters and added all-skill discovery tests
  - Restored a real VSIX ESLint gate and synchronized managed Python/skill bundles
  - Merged upstream v0.8.0 with its constraint ledger, hook applicability, adversarial tests, DOI validation, and current pinned integrations
  - Upgraded ESLint/typescript-eslint/VSCE/Vitest and lockfile dependencies; npm audit reduced from 22 vulnerabilities to zero
  - Validation: Python 1475 passed; VSIX 169 passed; smoke 14/14; validate 92/92; ruff, format, mypy, bandit, bundle, npm audit, and VSIX install smoke passed

- **v0.7.11 Phase gate + release hardening (2026-05-19)**:

  - Completed six-agent-per-phase formal review follow-up for the 13 checkpoint surface and implemented the release-blocking fixes found in Phase 8-11.
  - Hardened Phase 8 reference sync, Phase 9 export integrity, Phase 10 D1-D9 meta-learning provenance, and Phase 11 final-delivery prerequisites.
  - Added DOCX/PDF post-export validation in `ExportPipeline`; corrupt/missing export files no longer report success.
  - Added structured `analysis_steps` to `MetaLearningEngine` audit records and made Phase 10 reject count-only audit YAML without matching `run_meta_learning` event provenance.
  - Packaged runtime templates/CSL/journal profiles into the PyPI wheel and added cross-surface template path resolution.
  - Fixed Git ahead/behind parsing for final provenance checks and G9 hook warnings.
  - Updated project skeletons so manuscript/library-wiki projects create `.audit/` and expose `paths.audit`.
  - Hardened release workflow: least-privilege permissions, pinned `setup-uv` 0.10.0, frozen installs, `lint-security` publish dependency, package.json version validation without Node pre-setup.
  - Scoped Hatch sdist includes after detecting a 590 MB accidental sdist; rebuilt sdist is 772 KB and wheel is 656 KB with templates included.
  - Updated README EN/zh-TW, CHANGELOG, ROADMAP, auto-paper guide, MCP instructions, source/VSIX skills, and bundled Python mirror to facade-first guidance.
  - Packaged `vscode-extension/medpaper-assistant-0.7.11.vsix` (1.9 MB).
  - Verification passed: Python 1305 passed / 1 skipped / 26 deselected; VSIX 169 passed; `npm run validate -- --skip-tests` 92 passed; ruff, ruff format, mypy, bandit, MCP boot, tool-surface authority, uv build, VSIX smoke, wheel-template smoke, npm audit, and `git diff --check` passed.
  - Published segmented commits and annotated tag `v0.7.11` to GitHub. CI passed on `master`; release workflow passed validate/smoke/test/security/build/PyPI, but VS Marketplace publish failed because `VSCE_PAT` was not authorized. GitHub Release was manually created with VSIX, wheel, and sdist assets.

- **v0.7.10 upstream dependency + docs/harness release prep (2026-05-13)**:

  - Rebasing completed on top of upstream `origin/master` `8db10ed` (`v0.7.9`), using remote latest as conflict authority.
  - Updated external MCP contracts: PubMed Search MCP 0.5.9 / 46 tools, Asset-Aware MCP 0.6.30, CGU upstream master, regenerated `uv.lock`.
  - Updated setup/migration/VSX runtime for PubMed `NCBI_EMAIL`, `pubmed_search.presentation.mcp_server`, and `uvx pubmed-search-mcp`.
  - Updated README EN/zh-TW, Auto-Paper guide, multi-stage review design, skill/prompt assets, SVG/banner, VSX README/package wording, and repo counts to 117 full / 22 compact, PubMed 46, total ~176 tools, 79 hooks, and 13 pipeline checkpoints.
  - Corrected VSIX bundle scope back to authority-defined curated surface: 14 skills, 13 prompt workflows, 9 agents, 4 templates, 7 support files, 10 chat commands, 11 palette commands.
  - Added tests for 13 checkpoint docs, PubMed harness currency, tool-surface authority, source/bundle mirror sync, and PubMed migration/runtime entrypoint behavior.
  - Added pre-commit/ruff exclusions for external mirrored code under `integrations/` and `vscode-extension/bundled/` so source/bundle parity is not broken by root formatters.
  - Fixed Windows CI path/config tests by making UTF-8 text decoding explicit in `tests/test_config_paths.py`.
  - Packaged `vscode-extension/medpaper-assistant-0.7.10.vsix` (1.9 MB).
  - Verification passed: `uv lock --check`; `uv run ruff check .`; `uv run mypy src --ignore-missing-imports`; `uv run pytest` (1285 passed / 1 skipped / 26 deselected); `uv run python scripts/sync_repo_counts.py --check`; `uv run python scripts/smoke_test.py` (14 checks); `npm run bundle:check`; `npm test` (169 passed); `npm run validate` (92 passed / 0 warnings / 0 failed); `git diff --check`.
  - Published `v0.7.10`; release workflow and CI completed successfully after the CI follow-up commit/tag alignment.

- **Post-v0.7.10 CI/hook hygiene follow-up (2026-05-13)**:

  - Updated GitHub Actions workflows to Node 24-ready major actions and switched Node jobs to Node.js 24 to address deprecation warnings.
  - Changed `scripts/hooks/paper_precommit.py` so non-draft commits skip silently and staged draft commits only scan projects with staged draft files.
  - Added workflow contract tests and paper-precommit regression tests for the new behavior.
  - Validation passed: `tests/test_embedded_hooks.py`, `tests/test_ci_workflows.py`, targeted `ruff check/format`, `paper_precommit.py`, and `git diff --check`.

- **v0.7.9 Vancouver export + FOAM compatibility release prep (2026-04-24)**:

  - Fixed Vancouver/BJA superscript DOCX/PDF export raw `[@citekey]` leakage by always enabling Pandoc citeproc when bibliography data is present and adding `vancouver-superscript.csl`
  - Stripped hand-maintained References sections before citation conversion so reference-list `[[ref_key]]` trailers cannot contaminate exported references
  - Added DOCX XML raw citation token smoke checks for `[@`, `[[`, and `]]`
  - Split manuscript citation conversion from FOAM library-wiki links/embeds/anchors/aliases and aligned C5/C10/C11/C14 hooks to the shared parser
  - Folded remaining `codex/check-design-errors` branch fixes into master: `exports/` paths, workspace state `MEDPAPER_BASE_DIR`, and resolved project-path audit loop cache keys
  - Targeted validation passed: citation converter, wikilink validator, export pipeline, Pandoc exporter, C5, and FOAM citation hook compatibility

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

- Segmented production refresh: first foundation commit, then academic output domain profiles and evidence/exemplar artifacts
- Monitor VS Marketplace secret authorization before the next publication attempt

## Next

- Add research proposal, closeout report, student paper, conference/thesis, and arXiv/preprint profiles with code-enforced constraints and templates
- Implement ranked evidence-context ledger, perspective question map, and bounded branch audit artifacts
- Continue vulture/orphan cleanup and DDD dependency remediation with regression tests
- Build the human-facing documentation website with Mermaid-enabled architecture/workflow pages
- Fix/rotate `VSCE_PAT` publisher authorization before the next Marketplace publish attempt.
- Push segmented commits after each validated milestone; release a new version only after full validate/VSIX install smoke
- Build a code-level autopaper orchestrator (reduce reliance on SKILL-only sequencing)
- Add semantic repair loop after hook failures (patch -> rerun hooks -> converge/regress/escalate)
- Phase 5c TreeView/CodeLens/Diagnostics features
- Dashboard Webview embedding
- CI/CD pipeline for automated VSIX publish
