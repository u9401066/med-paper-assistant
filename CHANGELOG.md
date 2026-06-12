# Changelog

<!-- markdownlint-disable MD024 -->

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Added an offline DOI validator (`med_paper_assistant.shared.doi`) and wired it into Hook P7 (reference integrity) so any DOI attached to a cited reference must be syntactically valid (`10.<registrant>/<suffix>`) before the manuscript is finalized; malformed DOIs are now CRITICAL blocking issues while references without a DOI remain acceptable.
- Added a shared `normalize_doi_for_filename` helper in `med_paper_assistant.shared.doi` as the single source of truth for filesystem-safe DOI slugs.
- Added a shared slug module (`med_paper_assistant.shared.slug`) exposing `slugify_name` (project-name slugs that drop punctuation) and `slugify_token` (generic tokens that keep punctuation as hyphen separators) as the single source of truth for the two distinct slug algorithms.
- Added an adversarial / metamorphic verification harness (`tests/test_adversarial_hooks.py`, design in `docs/design/adversarial-verification-harness.md`) that continuously PROVES the quality hooks reject bad input, not just accept good input. Each covered hook (A3 anti-AI, A5 language, A6 overlap, B8 stats alignment, C3 N-value, C4 abbreviation, P7 reference/DOI integrity) has a known-good fixture that must pass and a known-bad mutation that must be caught, plus a coverage ratchet that prevents silently losing adversarial coverage.

### Changed

- Consolidated duplicated DOI filename-normalization logic: `ReferenceId._normalize_doi` and `ReferenceConverter._normalize_doi` now delegate to the shared `normalize_doi_for_filename` instead of each carrying an identical regex implementation.
- Consolidated four duplicated slug implementations onto the shared slug module: `Project.generate_slug` and `ProjectManager._slugify` now delegate to `slugify_name`, while `ReferenceManager._slugify` and `FoamSettingsManager._slugify` delegate to `slugify_token` (preserving each call site's exact fallback and dot-handling behavior).

### Removed

- Removed two verified dead private helpers with zero call sites across source, tests, and the bundled mirror: `ReferenceManager._create_foam_alias` and the unused `_insert_line_before` in the legacy DOCX exporter.

### Fixed

- Re-synced the bundled Python mirror (`vscode-extension/bundled/tool/med_paper_assistant`) with source, restoring the v0.7.12 continuity-harness changes in `checkpoint_manager.py` and `pipeline_gate.py` that had not been mirrored, so the bundled-mirror parity test passes again.

## [0.7.12] - 2026-06-11

### Added

- Added a pipeline continuity harness so paused runs return an explicit auto-resume decision: `CheckpointManager.get_continuity_plan()` and an enriched `resume_from_pause()` now report `auto_resume`, `next_action`, and `reason`, wired into the `resume_pipeline` and `request_section_rewrite` MCP reports.
- Added bounded-autonomy safeguards to the continuity harness: a `MAX_CONSECUTIVE_AUTO_RESUMES` budget forces a periodic human checkpoint, and regression states escalate to a human checkpoint once the regression count exceeds the safe threshold.
- Added a full Phase 0→11 end-to-end lifecycle test (`tests/test_e2e_pipeline_lifecycle.py`) that walks every gate FAIL→PASS in order, plus edge cases for prerequisite skipping, corrupted artifacts, out-of-order execution, regression recovery, and partial review loops.

### Changed

- Extended the pause/resume continuity decision into a single shared helper so the peek (`get_continuity_plan`) and resume (`resume_from_pause`) paths cannot drift, and surfaced the auto-resume status in the checkpoint recovery summary.

## [0.7.11] - 2026-05-19

### Added

- Added release-hardening tests for version parity, README authority counts, least-privilege release permissions, frozen dependency installs, and publish-time security gates.
- Added a VSIX package smoke script plus `test:ci` / `sync-assets:check` package scripts for explicit extension release validation.

### Changed

- Hardened Phase 8-11 gates so later phases now require completed Phase 7 artifacts, resolved citation wikilinks, structurally valid DOCX/PDF exports, Phase 10 D1-D9 `analysis_steps`, and clean final-delivery prerequisites before optional Git provenance checks run.
- Packaged built-in templates/CSL/journal profiles into PyPI wheels and taught runtime template resolution to work from repo, VSIX, and installed-wheel layouts.
- Updated GitHub release workflow to least-privilege permissions, pinned `setup-uv` to 0.10.0, switched release installs to `uv sync --frozen --all-extras`, and added a blocking `lint-security` job before publish/release jobs.
- Synced README / README.zh-TW / bundled instructions / skills to facade-first `project_action`, `draft_action`, `inspect_export`, and `export_document` calls, and refreshed tool counts for the 117 full / 22 compact mdpaper surface plus 46 PubMed and 24 CGU tools.
- Updated project skeletons so manuscript and library-wiki projects both create `.audit/` and expose an `audit` path from project metadata.

### Fixed

- Updated GitHub Actions workflows to Node 24-ready action majors (`checkout@v6`, `setup-node@v6`, `setup-python@v6`, `setup-uv@v7`, artifact actions, `github-script@v9`, and `action-gh-release@v3`) and switched Node jobs to Node.js 24.
- Made the paper pre-commit hook skip silently when no draft files are staged, and limit P-series checks to projects with staged draft files so unrelated release commits no longer print research-draft warnings.
- Fixed remote drift parsing for Git provenance checks so `branch.ab +0 -N` is correctly reported as behind upstream instead of "pushed".
- Fixed `project_action(action="create")` with no workflow argument so the facade preserves the manuscript default rather than passing an empty workflow mode.
- Fixed Phase 8 wikilink resolution for legacy flat `references/*.md` projects and tied Phase 10 audit validation to matching `run_meta_learning` evolution-log provenance.

## [0.7.10] - 2026-05-13

### Changed

- Updated Auto-Paper README, guide, prompt, skill, VSX copy, and visual assets to describe the current 13 main gate checkpoints (`Phase 0-11 + Phase 6.5`) plus the independently validated `Phase 2.1` fulltext/source-material sub-gate.
- Synced upstream MCP integration refs and release counts for PubMed Search MCP 0.5.9 (46 tools), Asset-Aware MCP 0.6.30, CGU upstream master, 117 full / 22 compact `mdpaper` tools, and 79 quality hooks.
- Expanded source/VSX harness parity so bundled skills, prompts, agents, and Python mirrors stay aligned with the repository authoring surface.

### Fixed

- Fixed VSX package validation so it selects the `.vsix` matching `package.json` when older local package files are present.

## [0.7.9] - 2026-04-24

### Changed

- Synced VSIX marketplace README wording and tool-surface authority for the bundled CSL templates shipped with v0.7.8.

## [0.7.8] - 2026-04-24

### Added

- Added `vancouver-superscript.csl` and citation-style aliases for BJA/Vancouver superscript export.
- Added FOAM-compatible citation parsing helpers so manuscript citations, knowledge-base anchors, aliases, and embeds are handled by one shared conversion/audit layer.

### Changed

- Updated DOCX export smoke validation to fail raw citation token leaks (`[@`, `[[`, `]]`) after export.
- Updated project workflow paths so manuscript projects include an explicit `exports/` directory and path mapping.
- Updated review-loop cache keys to use resolved project paths instead of slug-only keys, preventing cross-workspace collisions.

### Fixed

- Fixed Vancouver DOCX/PDF exports leaving raw `[@citekey]` tokens when a CSL alias such as `vancouver-superscript` was requested.
- Fixed hand-written References sections being converted into leaked `[@key]` trailers by stripping References before citation conversion across heading levels.
- Fixed FOAM wiki links such as `![[ref#^block]]`, `[[ref#^block]]`, and `[[ref|alias]]` being mistaken for manuscript citations during export, validation, and C-series audit hooks.
- Fixed workspace state initialization so `get_workspace_state_manager()` honors `MEDPAPER_BASE_DIR` when no base path is passed.

## [0.7.7] - 2026-04-24

### Fixed

- Fixed release CI hygiene after v0.7.6 by applying Ruff import/format cleanup, Prettier Markdown formatting, mypy type narrowing, Bandit-safe DOCX XML parsing via `defusedxml`, and synced VSIX bundle mirrors.

## [0.7.6] - 2026-04-24

### Added

- Added Phase 0 source-material intake via `project_action(action="source_materials")`, producing `.audit/source-materials.yaml` and `.audit/source-materials.md` before literature search or drafting.
- Added agent-readable source-material manifests that mark DOCX/XLSX/PDF/PPTX inputs as `pending_asset_aware` and provide concrete `asset_aware_file_paths` for follow-up ingestion.
- Added Phase 0 gate enforcement for `.audit/source-materials.yaml` so user-provided primary materials cannot be silently skipped.
- Added Hook F4 data-anchor provenance validation so `data_anchors` must cite ready source materials, asset-aware docs, tracked data artifacts, or trusted data files.
- Added `project_action(action="record_asset_ingestion")` to write asset-aware ingestion receipts back into `.audit/source-materials.yaml`.
- Added Hook C14 claim-evidence alignment so strong scientific claims require visible literature, source-material, figure/table, or data-artifact backing.
- Added golden mini-project and external MCP contract smoke tests for the source-material ingestion critical path.
- Added `pipeline_action(action="doctor")` as a one-shot agent diagnostic for 11-phase readiness, external MCP declarations, command availability, and cached gate state.
- Added `inspect_export(action="docx_smoke")` / `inspect_export(action="xml_smoke")` for Phase 9 DOCX XML structural smoke checks before final delivery.

### Changed

- Updated Auto-Paper, repository, Copilot, and VSIX documentation to describe Phase 0 as source-material intake plus journal-profile generation.
- Updated the VSIX Marketplace description and keywords to mention source-material intake and asset-aware workflows.
- Clarified Phase 11 as final delivery with Git provenance optional rather than a hard commit/push requirement.
- Tightened Phase 2.1 so primary source materials that remain `pending_asset_aware` block progression until an ingestion receipt is recorded.
- Refined Hook C14 severity by claim type so novelty, causality, superiority, certainty, and magnitude claims can be triaged separately.

### Fixed

- Fixed the workflow design gap where workspace-root DOCX/XLSX/PDF materials could be missed because asset-aware ingestion was only described for reference full text in Phase 2.1.
- Fixed the GIGO gap where agent/concept-derived or un-ingested source-material values could be copied into `data_anchors` and pass because the manuscript and anchor file were consistently wrong.

## [0.7.5] - 2026-04-23

### Fixed

- Synced VS Code bundled assets and Python mirror before release to resolve `bundle:check`/`test_bundled_python_mirror` drift failures.
- Restored `pipeline` and `analysis` asset workflows compatibility for 11-phase execution under release-validated code paths.
- Rebuilt release artifacts after fixing bundled source parity and CI mirror validation.

## [0.7.4] - 2026-04-23

### Added

- Restored figure/table asset workflow entrypoints and alias handling so `analysis_action` routes for `insert_figure`/`insert_table`/`list_assets`/`review_asset` are available.

### Fixed

- Fixed `draft_action(action=\"write\", section=...)` routing so section names map to canonical filenames (例如 `methods` → `drafts/methods.md`) instead of writing to `drafts/.md`.
- Tightened repository-wide filename/path guards for cross-platform safety (Linux/macOS/Windows), including reserved names, traversal, drive/UNC absolute paths, and special-character sanitization.
- Improved data-artifacts pipeline handling so manifest discovery and artifact counting align across canonical and legacy custom manifest shapes.
- Improved tool-surface consistency across documented/runtime `analysis_action`, `draft_action`, and `pipeline_action` flows for all 11 phases.

## [0.7.3] - 2026-04-23

### Added

- **Repository-wide cross-platform path guard**: Added one shared path guard for filename and child-path entrypoints, covering POSIX/Windows absolute paths, drive/UNC paths, traversal, hidden names, reserved Windows device names, invalid filename characters, trailing dot/space names, and case-insensitive collisions
- **Analysis asset facade restoration**: Exposed the compact `analysis_action` surface and restored review/list/insert routes for figure and table assets so Phase 5 asset provenance workflows have real MCP entrypoints instead of documentation-only verbs
- **Path-guard regression coverage**: Added focused tests for draft/storage/library/reference import/diagram/Word export path handling plus bundled-source parity checks for the VS Code extension runtime

### Fixed

- **Draft section write routing**: Fixed `draft_action(action="write", section=...)` so known sections such as `methods` map to `drafts/methods.md` instead of falling through to `drafts/.md`
- **Data artifact provenance manifests**: Made data-artifact validation recognize canonical project, audit, and data-artifact manifest locations, including legacy/custom manifest shapes, so artifact counts no longer collapse to zero when a valid manifest exists
- **Validation facade parity**: Added list/help aliases for `validation_action` and aligned the documented validation types with the implemented `concept`, `literature`, and `wikilinks` routes
- **British English hook locale handling**: Adjusted the A5 language-consistency hook so BJA-style `en-GB` journal profiles do not produce false-positive American spelling warnings

### Changed

- **Authority-driven tool count sync**: Synced repository and VS Code extension documentation to the authoritative `116 full / 22 compact` MCP tool surface with 3 prompts and 3 resources
- **Release validation baseline**: Revalidated source/bundled Python parity, tool-surface authority, repository-count sync, targeted path-guard suites, and the full non-integration pytest suite before tagging

## [0.7.1] - 2026-04-22

### Fixed

- **Foam-visible reversible citations**: Switched synced draft citations and reference anchors to visible wikilinks so Foam graph edges are created again while preserving backward compatibility with legacy HTML-comment reversible citations
- **Cross-line citation parsing**: Centralized reversible citation restoration in the shared citation converter and narrowed whitespace matching to same-line spaces or tabs so stray line breaks are not misread as synced citations
- **Bundle drift false positives**: Updated the VS Code extension bundle drift checker to ignore `__pycache__` and `.pyc` artifacts so local pytest runs no longer produce release-blocking mirror mismatches

### Added

- **Regression coverage for citation resync**: Added tests for legacy reversible draft resync, APA visible reversible resync, newline edge cases, mixed legacy plus visible key extraction, and byte-for-byte Python bundled mirror parity

## [0.6.7] - 2026-04-15

### Fixed

- **Bandit-facing runtime guards**: Replaced release-blocking runtime `assert` usage in writing hook constants plus MCP stats and pipeline gate tools with explicit exceptions so security scans no longer flag `B101 assert_used` on these validation paths
- **VS Marketplace banner rendering**: Switched the extension README banner image to an absolute GitHub raw URL so Marketplace stops rewriting the path against the repository root and dropping the `vscode-extension/` segment

## [0.6.6] - 2026-04-15

### Added

- **Repository visual asset set**: Added overview, architecture, and Auto Paper flow SVG assets under `docs/assets/` so the repository now has first-party graphics for the main README and guide entrypoints
- **VSX branding assets**: Added the MedPaper Assistant icon and marketplace banner assets under `vscode-extension/resources/` to give the extension listing a consistent visual system

### Changed

- **Bilingual documentation entrypoints**: Synced `README.md`, `README.zh-TW.md`, and `docs/auto-paper-guide.md` to use the new overview, architecture, and pipeline visuals instead of relying on text-only entrypoints
- **VS Code extension marketplace presentation**: Updated `vscode-extension/README.md` and `vscode-extension/package.json` so the extension advertises the new icon plus gallery banner configuration in line with the repository visuals

## [0.6.5] - 2026-04-14

### Fixed

- **Release gate normalization**: absorbed repository-wide EOF, Prettier, and Ruff auto-fixes across prompts, skills, tests, and bundle helper scripts so `uv run pre-commit run --all-files` no longer leaves release work in a half-formatted state
- **Hook and harness revalidation**: rechecked the hook guard, embedded hooks, audit hooks, MCP boot verification, install smoke, greedy MCP smoke, full fast pytest suite, and VS Code extension tests before tagging the marketplace build

## [0.6.4] - 2026-04-14

### Changed

- **Compact tool surface default**: `mdpaper` now supports `MEDPAPER_TOOL_SURFACE=full|compact`; default runtime in workspace/VSX paths is compact, exposing 44 tools while retaining 94 tools in full mode
- **Documentation alignment for release**: Synced `README.md`, `README.zh-TW.md`, and `vscode-extension/README.md` to describe full/compact counts and facade-first behavior consistently

## [0.6.3] - 2026-04-11

### Fixed

- **Unsupported macOS runner lane**: Removed the `macos-13` cross-platform smoke lane from CI and release matrices because GitHub Actions resolves it to an unsupported `macos-13-us-default` configuration for this repository, which was forcing otherwise healthy release runs to end as `cancelled`

## [0.6.2] - 2026-04-11

### Fixed

- **Windows release smoke quoting**: Replaced inline `python -c` MCP boot checks in CI/release workflows with the shared `scripts/verify_mcp_server_boot.py` runner so PowerShell quoting and Unicode parsing no longer break the Windows cross-platform smoke job

## [0.6.1] - 2026-04-11

### Fixed

- **Cross-platform hook guard path rebasing**: `scripts/copilot_hook_guard.py` now prefers the full workspace path signature before falling back to repo-name rebasing, preventing duplicated workspace segments such as `.../med-paper-assistant/med-paper-assistant/...` in GitHub Actions workspaces
- **Release smoke guard regressions**: `tests/test_copilot_hook_guard.py` now covers duplicated-workspace-path scenarios for patch parsing, protected-path denial, and nested path extraction so the release smoke suite stays stable across GitHub-hosted runners

## [0.6.0] - 2026-04-10

### Added

- **Facade-first MCP surface**: Added stable public entrypoints for project/workspace, review/pipeline, and export flows via `project_action`, `workspace_state_action`, `run_quality_checks`, `pipeline_action`, `export_document`, and `inspect_export`, plus lightweight MCP resources for workspace state, project catalog, and template catalog
- **Greedy MCP smoke runner**: Added `scripts/greedy_mcp_tool_smoke.py` with isolated fixture setup, CI-friendly JSON v2 output, stable summary formatting, and categorized skip reporting (`interactive`, `external`, `other`) for regression diffs
- **Release-grade smoke coverage**: Added façade routing tests, legacy deprecation guidance tests, real MCP stdio workspace smoke, greedy smoke report tests, and VS Code extension host smoke covering activation, MCP provider registration, and a core command path
- **Runtime mode guard**: Added `.github/hooks/mode-guard.json` and `scripts/copilot_hook_guard.py` so protected-path edits and destructive terminal commands are checked consistently across Windows-safe `apply_patch` and terminal flows

### Changed

- **First-party orchestration guidance**: Updated root prompts, skills, bundled instructions, and extension autopaper guidance so first-party flows prefer façade verbs over legacy compatibility verbs, with explicit deprecation messaging for legacy public tools
- **VS Code extension packaging**: Switched bundle/build validation to a manifest-driven model using `vscode-extension/bundle-manifest.json` plus shared Node-based bundle and validate scripts, and reused the same manifest data in packaging tests and workflow assertions
- **CI and release validation**: Expanded CI/release smoke to cover `ubuntu-latest`, `windows-latest`, `macos-13`, and `macos-14`, added committed bundle drift checks before sync/build steps, and routed `npm run validate` through a platform-aware launcher for cross-platform parity

### Fixed

- **Stable smoke diff normalization**: Normalized Windows path separators and workspace-root substitutions in greedy smoke summaries so CI diffs stay stable across operating systems
- **Cross-platform VSX assertions**: Reworked extension path assertions and packaging checks to use native path handling and shared command manifests, preventing Windows-only false negatives
- **Documentation parity**: Synced repository and VSX documentation with the façade-first MCP surface, stable smoke coverage, and current cross-platform validation flow

## [0.5.2] - 2026-03-18

### Fixed

- **VSX marketplace MCP deduplication**: `vscode-extension/src/extension.ts` now detects when another installed VS Code extension already provides `PubMed Search` or `Zotero Keeper` MCP servers and skips both persistent tool installation and duplicate MCP registration, preventing doubled tool lists in Copilot Chat
- **VSX persistent tool upgrades**: `vscode-extension/src/uvManager.ts` now runs `uv tool upgrade` for already-installed managed tools during activation, so older machine-level installs are refreshed on newer extension releases instead of staying pinned silently
- **VSX documentation alignment**: Synced root `README.md`, `README.zh-TW.md`, and `vscode-extension/README.md` with current MCP counts, 11-phase Auto Paper wording, persistent-install behavior, and external VSX deduplication notes
- **Cross-platform setup reproducibility**: `scripts/setup.sh`, `scripts/setup.ps1`, and `vscode-extension/scripts/build.sh` no longer auto-track remote submodule HEAD during install/build; they now use repository-pinned submodule commits, generate the full repo `.vscode/mcp.json` shape consistently, and verify current MedPaper/CGU startup paths
- **JSONC mcp.json support**: `scripts/migrate_mcp_json.py` now strips `//` comments from `.vscode/mcp.json` before parsing, preventing failures when VS Code leaves JSONC-style comments in the config
- **setup.sh heredoc template corruption**: Rewrote the mcp.json heredoc block with consistent 2-space indentation and all 6 canonical servers, fixing structural corruption from overlapping patches
- **CHANGELOG first-line corruption**: Removed garbage prefix from `CHANGELOG.md` first line that would fail Prettier CI checks
- **Ruff lint/format compliance**: Fixed E402 import ordering and formatting issues in new test files to pass CI checks

### Added

- **MCP progress notifications for long-running tools**: Audit/review pipeline tools now use FastMCP `Context.report_progress()` when the client provides a progress token, covering phase validation, pipeline heartbeat, review-round start/submit, quality audit, meta-learning, data artifact validation, writing hooks, and review hooks
- **Cross-platform migration script** (`scripts/migrate_mcp_json.py`): Non-destructive mcp.json migration — detects missing servers, normalizes JSONC→JSON, creates timestamped backups; shared loader used by `smoke_test.py`
- **Installation smoke test** (`scripts/smoke_test.py`): 13-check cross-platform verification covering environment, core imports, MCP server creation, CGU integration, mcp.json validation, git submodules, and migration dry-run

## [0.5.1] - 2026-03-17

### Added

- **Top 20 anesthesiology journal profiles**: Added `templates/journal-profiles/` with 20 ready-to-use journal YAML presets, `_index.yaml`, README, and `scripts/generate_journal_profiles.py` to regenerate the catalog from source metadata
- **Paper pre-commit hook (P-series)**: New `scripts/hooks/paper_precommit.py` registered in `.pre-commit-config.yaml` — runs P1/P2/P4/P5/P7 quality checks automatically on `git commit`, blocking on CRITICAL issues
- **Embedded post-write hooks**: `write_draft` and `patch_draft` now auto-run A-series hooks (A1–A7, B9, B10, B15) after successful write — agent cannot skip, non-blocking advisory report appended to output
- **B2 protected content guard**: `patch_draft` now blocks modification of 🔒-marked sections in `concept.md` — prevents agent from altering NOVELTY STATEMENT or KEY SELLING POINTS without user approval
- **Weak-model guardrails expansion**: Added Code-Enforced B2/C2/P6 coverage, deprecated `save_reference()` warning + telemetry, and a dedicated weak-model regression suite in `tests/test_weak_model_guardrails.py`
- **Domain constraint expansion**: Added shared anti-AI vocabulary core and broader paper-type coverage for `meta-analysis`, `review-article`, `letter`, and `other`, plus structural/temporal/evidential constraints such as methods-before-results, minimum references, and section-overlap detection

### Fixed

- **Hook batch runner**: `run_post_manuscript_hooks()` now calls C10 (full manuscript validation), C11 (citation distribution), C12 (citation decision audit), C13 (figure/table quality) — previously defined in mixin but not wired into the batch runner
- **MCP hook aliases**: `audit_hooks.py` ALL set now includes A7 (reference sufficiency) and C7B (asset coverage); POST-WRITE +A7, POST-MANUSCRIPT +C7B; docstring corrected from 37→40 hooks
- **Hook effectiveness tracker**: `HOOK_CATEGORIES` now tracks P (pre-commit) and G (git-hooks) event categories
- **Consistency checker accuracy**: `scripts/check_consistency.py` now understands sub-hooks like `A3b`, counts 78 hooks correctly, and validates P/G hook categories instead of misreporting false failures
- **Documentation alignment**: AGENTS.md, `.github/copilot-instructions.md`, `vscode-extension/copilot-instructions.md`, and `vscode-extension/README.md` now reflect 78 hooks / 55 Code-Enforced / 23 Agent-Driven and 88 MCP tools consistently
- **VSX bundled parity**: Re-synced bundled Python sources and bundled skills with workspace source so local `vitest` sync checks and packaged extension content match the repository state

## [0.5.0] - 2026-03-11

### Added

- **Hook A3c: Voice Consistency Detector (Anti-AI 語體一致性偵測)**:

  - New Code-Enforced hook `check_voice_consistency()` in `_post_write.py` — detects paragraph-level style breaks via z-score outlier analysis
  - Per-paragraph metrics: avg_sent_len, avg_word_len, type_token_ratio, punct_complexity
  - Document baseline computation (mean + std per metric)
  - Outlier detection (z-score > 1.8) + vocabulary sophistication gap (max−min avg_word_len > 1.2)
  - Catches the #1 human-reviewer signal: ESL paragraphs suddenly switching to polished corporate-academic prose
  - Registered in WritingHooksEngine batch runner (`run_post_write_hooks`) and pre-commit P2c delegation
  - Integrated into R5 post-review anti-AI gate (now runs A3 + A3b + A3c)
  - MCP dispatch: `run_writing_hooks(hooks="A3C")` available in ALL and POST-WRITE hook sets
  - 18 new tests covering uniform text, mixed voice detection, sophistication gap, custom thresholds, markdown handling, and batch integration
  - Hook count: 77 → 78 (36 Code-Enforced / 42 Agent-Driven)

- **Dual-Subagent Anti-AI Cross-Audit Protocol (Stage C3)**:

  - SKILL.md Stage C3 rewritten: three-layer code scan (A3+A3B+A3C) → agent self-review (6 criteria incl. voice breaks) → dual-subagent cross-audit → verification
  - Concept-Challenger: new Anti-AI Surface Scanner role (blacklist + structural signals + GPTZero risk assessment)
  - Domain-Reviewer: new Voice Analyst role (per-paragraph AI probability scoring 1-5, ESL baseline analysis, TOP 5 suspicious sentences)
  - Cross-comparison protocol: 🔴 both flag → must rewrite, ⚠️ one flags → judge, ✅ both safe → pass

- **Asset Review Receipt Hard Gate for Figures/Tables**:

  - New analysis tool `review_asset_for_insertion()` records auditable review receipts in `.audit/data-artifacts.yaml`
  - `insert_figure()` / `insert_table()` now BLOCK caption registration unless a matching review receipt exists first
  - Phase 5 gate now validates planned figure/table captions are backed by review receipts
  - Hook F / `validate_data_artifacts()` now report missing or incomplete asset review receipts as gate-blocking issues
  - 1 new targeted tool test file + expanded Phase 5 / Hook F coverage

- **Paper-Type-Aware Reference Minimum Enforcement (Hook A7 + Phase 2 Gate)**:
  - New Hook A7 `check_reference_sufficiency()` — Code-Enforced pre-write gate that blocks writing when reference library is insufficient
  - Phase 2 Gate now paper-type-aware: reads `paper.type` from `journal-profile.yaml`, resolves minimum via 3-tier chain
  - Per-type minimums: original-research (20), review-article (30), systematic-review (40), meta-analysis (40), case-report (8), letter (5), fallback (15)
  - `journal-profile.template.yaml`: new `minimum_reference_limits` field for per-project override
  - `DomainConstraintEngine`: B003 `minimum_references` BOUNDARY constraint added to all 3 paper types
  - Phase 3+ prerequisite checks also paper-type-aware (can't bypass by skipping Phase 2)
  - 8 new A7 hook tests + 7 new Phase 2 gate tests (839 tests total)
  - Hook count: 76 → 77 (35 Code-Enforced / 42 Agent-Driven)
- **Humanizer Anti-AI Enhancement**:
  - `ANTI_AI_PHRASES`: 76 → 133 phrases across 12 semantic categories (overly_formal, unnecessary_hedging, ai_conclusions, filler_boosters, generic_linking, hollow_emphasis, ai_structuring, inflated_academic, ai_discourse, passive_deflectors, nominalised_verbs, hollow_intensifiers)
  - `AI_TRANSITION_WORDS`: 25 → 33 (added: Nevertheless, Conversely, Correspondingly, Notably, Importantly, Significantly, Fundamentally, Substantially)
  - 4 new A3b structural pattern checks: #6 negative parallelism, #7 copula avoidance, #8 em dash overuse, #9 false ranges (X to Y)
  - 12 new tests for anti-AI detection (826 Python tests total)
- **VS Code Copilot Lifecycle Hooks**:
  - 7 hook scripts: `session-init.sh`, `prompt-analyzer.sh`, `pre-tool-guard.sh`, `post-tool-check.sh`, `pre-compact-save.sh`, `subagent-init.sh`, `session-stop.sh`
  - `.github/hooks/mdpaper-lifecycle.json` configuration
  - Design doc: `docs/design/copilot-lifecycle-hooks.md`
  - State communication via `.github/hooks/_state/` (gitignored)
  - Graceful degradation when jq is not installed

### Fixed

- **Asset Review Receipt — Caption Normalization & Auto-Review**:
  - Caption comparison now uses `_normalize_caption()` — strips trailing punctuation, whitespace, and lowercases before matching (fixes brittle exact-match failures)
  - `insert_table()` with inline `table_content` now auto-records review receipt (agent has full content access), eliminating redundant `review_asset_for_insertion()` call
  - File-based tables (no `table_content`) still require explicit review receipt (hard gate preserved)
  - 5 new tests: `TestCaptionNormalization` (4 unit tests) + auto-review integration test
- **MCP Instructions**: Removed ghost tool `save_diagram_standalone` (merged into `save_diagram`), added missing `insert_figure`/`insert_table`/`list_assets` to DATA ANALYSIS section, updated DIAGRAM WORKFLOW
- **Tool count drift**: 85 → 86 tools (review/ 21 → 22), synced across 5 files via `sync_repo_counts.py --fix`

### Changed

- **Tool count**: 86 → 88 tools (analysis/ 9 → 10: `review_asset_for_insertion`, review/ 22 → 23: `approve_concept_review`)
- **Hook count**: 76 → 78 (34 → 36 Code-Enforced): added A3c Voice Consistency + A7 Reference Sufficiency
- **VSX Extension**: Synced `copilot-instructions.md` + `auto-paper/SKILL.md`, added 3 research skills (`memory-checkpoint`, `memory-updater`, `project-init`)

## [0.4.6] - 2026-03-02

### Added

- **VSX Zero-Config Marketplace Mode**:
  - `uvManager.ts` — cross-platform uv auto-detection + headless installation (Windows PowerShell / Unix curl)
  - `ensureUvReady()` — auto-install uv on activation with VS Code progress notification
  - Marketplace mode uses `uvx med-paper-assistant` from PyPI (complete isolation, no PYTHONPATH contamination)
  - CGU marketplace mode uses `uvx creativity-generation-unit`
- **VSX Testability Refactor**:
  - `extensionHelpers.ts` — 6 pure functions extracted from `extension.ts` (no vscode API dependency): `shouldSkipMcpRegistration`, `isDevWorkspace`, `isMedPaperProject`, `determinePythonPath`, `countMissingBundledItems`, `buildDevPythonPath`
  - `extensionHelpers.test.ts` — 30 tests covering all extracted helpers
  - `packaging.test.ts` — 21 tests for manifest schema, `.vscodeignore`, module structure, version consistency
  - `uvManager.test.ts` — 20 tests (expanded from 17) including async `findUvPath` tests

### Fixed

- **Critical**: `shouldSkipMcpRegistration()` now checks both `"mdpaper"` server name AND `med_paper_assistant` module path — prevents skipping when user has unrelated `mcp.json` entries
- **Critical**: `determinePythonPath()` only returns `'uv'` fallback for `med-paper-assistant` pyproject.toml — prevents wrongly treating any `pyproject.toml` as a valid Python path

### Changed

- VSX vitest: 52 → **106 passed** (+54 new tests across 4 test files)
- CGU bundled tools updated to latest version

## [0.4.5] - 2026-03-02

### Fixed

- **Critical**: `_strip_references_section()` greedy regex (`.*` with `re.DOTALL`) deleted all content after `## References` — any sections like `## Appendix` or `## Supplementary Materials` were silently lost during export. Fixed to non-greedy `.*?(?=\n## |\Z)` with lookahead.
- 2 regression tests added for post-References content preservation

## [0.4.4] - 2026-03-02

### Added

- **Pre-export citation gate (C5 HARD GATE)**: `export_docx()` and `export_pdf()` now run Hook C5 (Wikilink Resolvable) as a blocking gate — export is refused if any `[[wikilink]]` citations cannot be resolved to saved references
- **Strict mode for `prepare_for_pandoc()`**: New `strict=True` parameter raises `ValueError` on unresolved citation keys (used by `export_docx/pdf` internally as second defense layer)
- **Word export residual wikilink warning**: `save_document()` scans the final Word document for any remaining `[[...]]` patterns and warns the user
- 9 new tests covering all three defense layers

## [0.4.3] - 2026-03-02

### Fixed

- **Critical**: MCP server now uses `MEDPAPER_BASE_DIR` env var (set by VSX extension to workspace folder) instead of CWD for `projects/` and `logs/` paths — fixes end-user issue where output went to extension install directory instead of workspace

## [0.4.2] - 2026-03-02

### Fixed

- **CI**: Add `# nosec B110` to `checkpoint.py` — bandit false positive on intentional try/except/pass causing CI failure

## [0.4.1] - 2026-03-02

### Fixed

- **Dashboard ThemeProvider**: Replace `setState`-in-effect with `useSyncExternalStore` for hydration detection (ESLint `react-hooks/set-state-in-effect`)
- **Dashboard DrawioEditor**: Fix `ExportFormats` type mismatch (`xml` → `xmlsvg`), remove unsupported `style` prop
- **Dashboard stats/route.ts**: Next.js 16 `params` type changed to `Promise<>` with `await`
- **sync_repo_counts.py**: Remove unused `warnings` variable (ruff F841)
- **Bundled Python sync**: Fix rsync target to correct `bundled/tool/` path

## [0.4.0] - 2026-03-02

### Added

- **VSX Extension Completeness**:
  - `agents/` directory with 9 bundled `.agent.md` files (concept-challenger, domain-reviewer, literature-searcher, meta-learner, methodology-reviewer, paper-reviewer, reference-analyzer, review-orchestrator, statistics-reviewer)
  - `autoScaffoldIfNeeded()` — auto-detect missing skills/agents/prompts and prompt user
  - `build.sh` step 2d — agent bundle copy
  - `validate-build.sh` V3c — agent sync validation
  - `validateBundledAgents()` utility function
  - `mdpaper.audit` bundled prompt
  - Agent sync tests (vitest)
- **macOS / VS Code Insiders Compatibility**:
  - MCP environment inherits `PATH`, `HOME`, `SHELL`, `LANG`, `USERPROFILE` — fixes homebrew `uv`/`uvx`/`git` discovery on macOS
  - `getPythonArgs` supports versioned Python names (`python3.12`, `python3.11`) via regex
  - New test: versioned Python (homebrew/macOS) path matching
- **Dynamic Count Sync Script** (`scripts/sync_repo_counts.py`): AST-based counting of all repo metrics, auto-sync into 7 docs, 43 stale counts auto-fixed
- **ReviewHooksEngine** (`R1-R6`): Review report depth, author response completeness, EQUATOR compliance, review-fix traceability, post-review anti-AI, citation budget
- **EXPECTED_HOOKS**: 40→58 (added B9-B16, C10-C13, R1-R6)
- **`reset_review_loop` MCP tool**: Stuck review state recovery
- **`citeproc-py`**: Moved to core dependencies (previously optional)

### Fixed

- **Bug 1 (Critical)**: `_compute_manuscript_hash()` now hashes ALL `.md` files in `drafts/` via sorted glob — resolves review pipeline deadlock when using multi-file drafts
- **Bug 2 (Critical)**: `citeproc-py` import failure crashes — added try/except lazy import with `_CITEPROC_AVAILABLE` flag at all 3 usage points
- **Bug 3 (Medium)**: `start_document_session` required `template_name` even when no templates available — now optional, creates blank document when omitted
- **Bug 4 (Medium)**: Writing Hooks false positives:
  - A1: Added `_strip_frontmatter()` to exclude YAML frontmatter from word counts
  - A6: Added statistical notation regex exclusion (F-tests, p-values, η²p, CI, OR/HR/RR, β, SD/SE) from n-gram overlap detection
- **Bug 5 (Minor)**: `export_pdf` citeproc crash chain — covered by Bug 2 lazy import guards
- **MCP server env**: Child processes (uv/uvx/git) now inherit system PATH on macOS — prevents "command not found" errors
- **Hash mismatch error messages**: Added diagnostic info showing current vs expected hashes

### Changed

- MCP tools: **85** (review/ 20→21 with reset_review_loop)
- Hook architecture: **76 checks** (34 Code-Enforced / 42 Agent-Driven)
- Python tests: 698 → **730 passed** (excl. external-dep tests)
- VSX vitest: 34 → **35 passed**
- VSIX package: `medpaper-assistant-0.4.0.vsix` (615 KB, 224 files, 9 agents)
- 4 outdated bundled skills synced from source

## [0.3.12] - 2026-02-27

### Added

- **B9-B16 Section-Specific Writing Quality Hooks** (8 new Code-Enforced):
  - B9 Tense consistency — validates verb tense per section (past for Methods/Results, present for Discussion)
  - B10 Paragraph quality — minimum sentences, max length, transition word density
  - B11 Results objectivity — flags interpretive language in Results section
  - B12 Introduction structure — validates funnel structure (broad → specific → gap → aim)
  - B13 Discussion structure — validates interpretation → comparison → limitations → implications
  - B14 Ethical statements — checks for IRB/ethics approval and consent statements
  - B15 Hedging density — flags over-hedging (>15%) or under-hedging (<3%)
  - B16 Effect size reporting — checks for effect sizes alongside p-values
- **Self-Evolution Infrastructure (L2 complete)**:
  - `ToolInvocationStore` — tool telemetry persistence to `.audit/tool-telemetry.yaml`
  - `PendingEvolutionStore` — cross-conversation evolution persistence to `.audit/pending-evolutions.yaml`
  - `guidance.py` — `build_guidance_hint` + `build_startup_guidance` (auto-prompt pending evolutions on new conversations)
  - `tool_health.py` — `diagnose_tool_health` + flush health alerts to PendingEvolutionStore
- **Pipeline Flexibility (4 new MCP tools)**:
  - `request_section_rewrite` — Phase rollback with regression count guard
  - `pause_pipeline` / `resume_pipeline` — Pipeline suspend/resume with draft hash tracking
  - `approve_section` — Section-level approval gate (autopilot or manual)
- **Autonomous Audit Loop**: `autonomous_audit_loop.py` — structured audit loop execution
- **CheckpointManager enhancements**: Section approval tracking, pause/resume state, rollback history
- **WritingHooksEngine expansion**: +1120 lines — Anti-AI pattern detection, data claim alignment, supplementary crossref, language consistency, overlap detection, data artifact validation
- **MetaLearningEngine**: pending evolution flush (`_flush_meta_learning_evolutions`) for cross-conversation persistence
- **GitHub Actions**: `evolution-health.yml` weekly health check workflow
- **Tool Logging**: `tool_logging.py` — automatic tool invocation telemetry via decorator
- **New MCP tools**: `apply_pending_evolutions`, `diagnose_tool_health`, `run_autonomous_audit`, `get_tool_telemetry` + 5 pipeline flexibility tools
- **CONSTITUTION v1.6.0**: 新增第九章「核心哲學 — 逐步多輪演進」(§25-26)
- **Tests**: +163 tests (test_writing_hooks +636 lines, test_meta_learning +191 lines, test_guidance, test_pending_evolution_store, test_pipeline_flexibility, test_tool_health, test_tool_invocation_store)

### Fixed

- **C6 Word Count (ICMJE Convention)**: Body-only counting — excludes Abstract, References, Tables (markdown `| |` rows), Figure legends, Acknowledgments, Author info. New helpers: `BODY_SECTIONS` constant (12 sections), `_strip_markdown_tables()`, `_extract_body_word_count()`. Journal profile override via `counts_toward_total` flag.
- **count_words MCP tool**: Rewritten to show Body? column (✅/—), ICMJE-labeled manuscript total
- **Deep review round 2**: Defensive guards, assert removal, input validation
- **Code review**: Input validation, regex robustness, safety guards across 6 files
- **Writing hooks**: Word boundary regex for supplementary file matching, `rglob` for dir traversal, code block state tracking, wikilink stripping
- **Pipeline gate validator**: Reference counting by PMID subdirs

### Changed

- MCP tools: 77 → **81** (pipeline flexibility + self-evolution tools)
- Hook architecture: 23 Code-Enforced / 42 Agent-Driven (65 total)
- Three-tier evolution: L1 Event-Driven Hooks ⚠️ / L2 Code-Level Enforcement ✅ / L3 Autonomous Self-Evolution ⚠️
- Test count: 525 → **738 passed** (42 test files)
- AGENTS.md, copilot-instructions.md: complete rewrite reflecting actual implementation status

## [0.3.11] - 2026-02-26

### Added

- **Journal Support**: medRxiv, JAMIA, JBI added to `JOURNAL_REQUIREMENTS` (total: 11 journals)
- **Pipeline Gate Validator**: `pipeline_gate_validator.py` for phase-gate validation with reference counting fix (PMID subdirs)
- **Audit Hooks MCP Tool**: `audit_hooks.py` for Hook D meta-learning integration

### Fixed

- **`check_formatting` crash**: `'Drafter' object has no attribute 'read_draft'` — replaced with direct file reading via `get_drafts_dir()`
- **Pipeline gate**: Added `Path` import, fixed `_get_or_create_loop` signature, removed unused variables
- **Pipeline gate**: 29 API mismatches resolved in `pipeline_gate.py`
- **Gate validator**: Count PMID subdirs instead of flat `.md` for reference counting

### Changed

- **DRY refactor**: Extracted 7 duplicate helper functions into `_shared/project_context.py` (`get_project_path`, `get_drafts_dir`, `get_concept_path`, `validate_project_for_tool`)
- **VSX bundled code**: Full rsync from `src/` — 38 files updated, 5 new files added
- **Auto-paper SKILL.md**: Synced to VSX extension

## [0.3.10] - 2026-02-25

### Added

- **Author Info System**: `Author` frozen dataclass value object with structured affiliations, ORCID, corresponding author flag
  - `generate_author_block()` produces markdown with superscript affiliations + corresponding author notation
  - `update_authors` MCP tool for managing project author metadata
  - `create_project` now accepts `authors_json` parameter for structured author input
  - `get_current_project` displays formatted author information
  - `draft_section` auto-injects author block for Title Page sections
  - `journal-profile.template.yaml` updated with `authors:` section template
- **Data Artifact Provenance**: `DataArtifactTracker` persistence class for tracing data analysis artifacts
  - `validate_data_artifacts` MCP tool for cross-referencing data artifacts against drafts
  - All 4 analysis MCP tools (`run_statistical_test`, `analyze_dataset`, `create_plot`, `generate_table_one`) record provenance automatically
  - Phase 5/6 gate validators check data artifact completeness
  - CONSTITUTION §23.2 數據產出物溯源與交叉驗證 (v1.5.0)
- **Hook F1-F4**: Data artifact validation hooks (溯源追蹤、manifest↔檔案一致、draft↔manifest 交叉引用、統計宣稱驗證)

### Fixed

- **Full project ruff lint cleanup**: 60 errors → 0 (unused imports, f-string placeholders, ambiguous variable names, import ordering, unused assignments, duplicate dict keys)
- **Pre-existing duplicate `project_path` key** in `get_project_info()` dict literal (F601)

### Changed

- Hook count: 48 → 52 checks (added F1-F4 data-artifacts)

## [0.3.9] - 2026-02-24

### Added

- **Multi-Stage Review Architecture**: 設計文件 `docs/design/multi-stage-review-architecture.md`，記錄 4 層審查機制（Prompt 15 + Skill 26 + Hook 42 + Agent Mode）
- **42 Hooks 完整實作**: Hook 系統從 38 → 42 checks
  - Hook C8 (Temporal Consistency Pass): post-manuscript 時間一致性檢查
  - Hook B5 (Methodology Audit): 方法學驗證
  - Hook B6 (Writing Order): 寫作順序強制
  - Hook B7 (Section Brief Compliance): Section Brief 合規
  - Hook D7 (Review Retrospective): 自我改進回顧
- **11-Phase Pipeline (Phase 0-10)**: auto-paper 從 9-Phase 升級至 11-Phase
- **Auto-Paper Guide**: `docs/auto-paper-guide.md` 完整操作手冊
- **VSX Template Bundling**: `journal-profile.template.yaml` 打包進 VSX extension
  - `setupWorkspace` 自動複製 templates（含內容比對 auto-update）
  - `mdpaper.autoPaper` runtime safeguard（template 缺失時警告 + 一鍵修復）
  - `validateBundledTemplates()` 驗證函式 + 2 個新 unit tests
- **Citation Section**: README.md + README.zh-TW.md 加入 BibTeX 引用區塊

### Fixed

- **Bash Arithmetic Bug**: `build.sh` / `validate-build.sh` 中 `((VAR++))` 在 `set -e` 下 VAR=0 時回傳 exit code 1 → 改用 `VAR=$((VAR + 1))`
- **V6 Vitest Detection**: `validate-build.sh` 測試結果擷取修復（vitest v4 輸出格式變更）
- **Integration Test Async**: 6 個 integration tests 修正為 `async def` + `await`（`searcher.search()` 已改為 async）
- **Integration Test CWD**: `test_drafter` / `test_insertion` 改用 `tmp_path` fixture 避免 CWD 相依路徑問題
- **CI VSX Template Sync**: `ci.yml` + `release.yml` 的 VSX sync step 加入 templates 同步
- **project_path resolution bug**: `get_project_info()` 返回值缺少 `project_path` key

### Changed

- **pytest default config**: `addopts = "-m 'not integration and not slow'"` — 本地 `pytest` 預設只跑 unit tests（與 CI 行為一致）
- **VSX autopaper 描述**: "9-Phase Pipeline + Hooks" → "11-Phase Pipeline + 42 Hooks"
- **Hook C7 (Temporal Consistency)**: 新增 post-manuscript hook 修正過時引用

## [0.3.8] - 2026-02-20

### Fixed

- **Lazy Import**: `matplotlib`、`seaborn`、`scipy` 改為方法內 lazy import，修復 `uvx` 安裝時 `ModuleNotFoundError: No module named 'matplotlib'`（這些是可選依賴，核心 MCP server 啟動不應依賴）

## [0.3.7] - 2026-02-20

### Fixed

- **PyPI Entry Point**: 加入 `[project.scripts]` 讓 `uvx med-paper-assistant` 正確啟動 MCP server（v0.3.6 缺少 CLI entry point 導致 `Package does not provide any executables` 錯誤）

## [0.3.6] - 2026-02-20

### Added

- **`MedPaper: Setup Workspace` 命令** ✅
  - 一鍵將 bundled skills (14)、prompts (12)、copilot-instructions.md 複製到 workspace
  - 只複製不存在的檔案（不覆寫已客製化的內容）
  - 完成後提示「重新載入」以啟用全部功能
  - Marketplace 安裝後執行一次即可獲得完整 Agent Mode 體驗

### Fixed

- **CI Pipeline**: test-vsx / publish-vsx 加入 skills/prompts/copilot-instructions.md 同步步驟
- **PyPI 重複發佈**: publish-pypi 加入 `skip-existing: true`（v0.3.5 已上 PyPI）

### Removed

- **Dead Code 清理**: 移除 `MDPAPER_INSTRUCTIONS`、`MDPAPER_EXTENSION_PATH` 環境變數（Python MCP server 從未讀取）
- **Dead Code 清理**: 移除 `registerMcpServerProvider` 中的 `loadSkillsAsInstructions()` 呼叫

## [0.3.5] - 2026-02-20

### Added

- **Figure/Table Archive + Insert Tools** ✅
  - Hook: `_check_figure_table_archive` 一致性驗證
  - 3 個新工具: `insert_figure`, `insert_table`, `list_assets`（54 → 57 tools）
- **GitHub Repo Metadata + Doc-Update Hook (G8)** ✅
  - Repo description, 15 topics, 9 custom labels
  - `scripts/check-doc-updates.py`: 13 條規則映射檔案變更至文檔依賴
  - Pre-commit hook #15: doc-update-reminder (warn-only)
  - Hook 計數: 37 → 38 checks (G1-G8)
- **Prettier Markdown Formatter** ✅
  - Pre-commit hook #14: `mirrors-prettier v3.1.0`
  - 格式化所有 121 個 .md 檔案
- **CI/CD Pipeline Upgrade** ✅
  - CI: 2 → 5 jobs (python-lint, python-test, vsx, dashboard, markdown)
  - Release: 5-stage pipeline (validate → test → publish-pypi + publish-vsx → github-release)
  - Branch protection: 5 required CI checks, strict mode
  - 移除 Dependabot 配置

### Fixed

- **README Submodule Links**: 子模組相對路徑 404 → 改用 GitHub 絕對連結
- **VSX One-Click Install** ✅
  - 移除 `extensionDependencies` 硬依賴（`vscode-zotero-mcp` 未上架會阻擋安裝）
  - Python fallback 改為 `uvx`（PyPI 已發布即可自動下載執行）
  - CGU MCP server 改為條件註冊（偵測到才啟用，避免錯誤訊息）

### Documentation

- README/README.zh-TW: 更新所有工具/Hook 計數（20 處：57 tools, ~107 total, 15 hooks）

### Added

- **Placeholder Tools Implementation (Phase 8)** ✅
  - 9 個佔位工具升級為完整實作（74→83 tools）
  - Analysis: `analyze_dataset`, `detect_variable_types`, `list_data_files`, `create_plot`, `run_statistical_test`, `generate_table_one`
  - Review: `check_manuscript_consistency`, `create_reviewer_response`, `format_revision_changes`
- **Tool Layer Architecture Audit (Phase 9)** ✅
  - 7 個模板型工具（debate, critique, idea-validation）轉為 3 個 Skill 檔案
  - 新增 `.claude/skills/academic-debate/SKILL.md`
  - 新增 `.claude/skills/idea-validation/SKILL.md`
  - 新增 `.claude/skills/manuscript-review/SKILL.md`
  - 工具數量：83→76
- **Comprehensive Tool Consolidation (Phase 10)** ✅
  - 6 大策略精簡 76→53 tools（-30%）
  - **Strategy A: 移除無用工具** — `close_other_project_files`, `export_word`（legacy）
  - **Strategy B: 簡單合併** — `validate_for_section`, `get_project_paths`, `check_reference_exists` 併入現有工具
  - **Strategy C: 參數合併** — 6 組工具對合併（validate_concept +structure_only, get_current_project +include_files, update_project_settings +status/citation_style, save_diagram +output_dir, sync_workspace_state +clear, suggest_citations +claim_type/max_results, verify_document +limits_json）
  - **Strategy D: 功能吸收** — consistency 檢查 + submission checklist 併入 `check_formatting`
  - **Strategy E+F: Skill 轉換** — 7 個工具轉為 skill 知識（get_section_template, generate_cover_letter, list_supported_journals, generate_highlights, check_submission_checklist, create_reviewer_response, format_revision_changes）
  - 新增 `.claude/skills/submission-preparation/SKILL.md`（cover letter、highlights、journal requirements、reviewer response 模板）
  - 更新 `draft-writing/SKILL.md`、`project-management/SKILL.md` 反映工具變更
  - 測試驗證：35 passed / 21 pre-existing failures / 0 regressions
- **Citation-Aware Editing Tools (Layer 1+2)** ✅
  - `get_available_citations()` — 列出所有可用 `[[citation_key]]`，含 PMID/作者/年份/標題表格
  - `patch_draft(filename, old_text, new_text)` — 部分編輯草稿，自動驗證所有 wikilinks
    - 唯一匹配檢查（防止模糊替換）
    - Wikilink 格式自動修復（`[[12345678]]` → `[[author2024_12345678]]`）
    - 引用存在驗證（拒絕 hallucinated citations）
  - 解決 Agent 使用 `replace_string_in_file` 繞過 MCP 驗證管線的核心問題
  - 14 個測試（3 test classes: GetAvailableCitations, PatchDraft, EditingIntegration）
  - SKILL.md 新增 Flow D: Citation-Aware 部分編輯
  - copilot-instructions.md 新增草稿編輯引用規則
- **Infrastructure & Quality Cleanup (Phase 3.5)** ✅
  - Pre-commit hooks: 13 hooks（ruff, ruff-format, mypy, bandit, pytest, whitespace, yaml, json, toml, large files, merge conflicts, debug statements）全部通過
  - DDD Import 遷移：19 個測試檔從 `core.*` 遷移至 DDD 路徑
  - Test Isolation：所有測試改用 `tmp_path` fixture，不再污染專案根目錄
  - ARCHITECTURE.md 重寫：從 448 行過時文檔重寫為 ~240 行精確 DDD 架構文檔
  - Legacy Cleanup：刪除空的 `core/` 目錄、多餘腳本、散落檔案
  - Copilot Hook 修復：AGENTS.md 補齊 7 skills + 8 prompts，修正 capability index
  - Coverage Baseline：32 passed / 1 skipped / 26 integration-deselected
  - 架構方向決策：選定 **Direction C: Full VSX + Foam + Pandoc**
- **Prompt Files 機制**
  - 新增 `.github/prompts/` 目錄，包含 9 個 prompt files
  - `/mdpaper.project` - 專案設置與切換
  - `/mdpaper.concept` - 研究概念發展（含 novelty 驗證）
  - `/mdpaper.search` - 智能文獻搜尋（情境 A/B 判斷）
  - `/mdpaper.draft` - 草稿撰寫（需先通過 concept 驗證）
  - `/mdpaper.strategy` - 搜尋策略配置
  - `/mdpaper.analysis` - 資料分析與 Table 1
  - `/mdpaper.clarify` - 內容改進與潤飾
  - `/mdpaper.format` - Word 匯出
  - `/mdpaper.help` - 指令說明
  - 參考 copilot-capability-manager 架構設計
- **犀利回饋模式 (Sharp Reviewer Feedback)**
  - `concept_validator.py`: 新增 `_generate_novelty_feedback()` 方法
  - 回饋格式：verdict / critical_issues / questions / actionable_fixes
  - CGU 創意工具整合建議
  - 像頂尖期刊 Reviewer 一樣審查：直指問題、用證據說話
- **檔案保護模式 (File Protection)**
  - `.copilot-mode.json`: 新增 `protected_paths` 設定
  - Normal/Research 模式下禁止修改開發檔案
  - 受保護路徑：`.claude/`, `.github/`, `src/`, `tests/`, `integrations/`
- **Session 檢視工具**
  - `scripts/view_session.py`: 顯示 pubmed-search 搜尋紀錄
  - 可供人工驗證 Agent 確實執行了搜尋
- **已知問題追蹤 (Known Issues)**
  - ROADMAP.md 新增 4 個 Critical Issues
  - 新增 Phase 3.5: 學術品質保證系統

### Changed

- **Novelty Check 改為 Advisory（不阻擋）**
  - `writing.py`: `_enforce_concept_validation()` 改為建議性質
  - 用戶可選擇：直接寫 / 修正問題 / 用 CGU 發想
  - 仍然檢查結構完整性（NOVELTY STATEMENT, KEY SELLING POINTS）
- **concept-development SKILL 大幅更新**
  - 新增犀利回饋原則和模板
  - 新增 CGU 工具使用指南
  - 新增危險信號處理流程
- **Pydantic V2 遷移**
  - `SearchCriteria`: `class Config` → `model_config = ConfigDict(frozen=True)`
  - 消除 `PydanticDeprecatedSince20` 警告

### Fixed

- **wikilink_validator.py**: 移除未使用的 `match.group(1)` 呼叫
- **list_drafts / read_draft**: 路徑解析改用 `_get_drafts_dir()` 取得專案路徑，與 `patch_draft` 一致

### Documentation

- **AGENTS.md**: 新增 Novelty Check 規則和 CGU 整合
- **copilot-instructions.md**: 新增犀利回饋做法
- **pubmed-search-mcp ROADMAP.md**: 新增 Phase 5.5 搜尋紀錄驗證機制

---

## [0.2.2] - 2025-12-18 (Previous)

### Added

- **完整靜態分析工具鏈**
  - Ruff linter/formatter: 修復 1839 個錯誤
  - Mypy 類型檢查: 修復 49 個類型錯誤
  - Bandit 安全掃描: 7 個 Low severity 已加 `# nosec` 註解
  - Vulture 死代碼檢測: 0 個問題
- **開發模式切換功能** (`.copilot-mode.json`)
  - `development`: 完整功能（所有 skills、Memory Bank 同步、靜態分析）
  - `normal`: 一般使用（僅研究技能）
  - `research`: 專注寫作（只同步專案 .memory/）
- **test-generator SKILL 擴展**
  - 新增 Bandit/Vulture 工具文檔
  - 新增 `# nosec` 註解使用指南
  - 完整執行流程說明

### Changed

- **代碼品質改進**
  - 所有 `import *` 改為明確導入
  - 所有 `except:` 改為 `except Exception:`
  - 統一使用 ruff format 風格
  - 修復所有 Optional type hints
- **pyproject.toml** - 新增 dev 依賴: `bandit>=1.9.2`, `vulture>=2.14`

### Fixed

- **類型錯誤修復**
  - `concept_validator.py`: 修正 `result` 變數衝突
  - `project_context.py`: 使用 `get_project_info()` 替代 `get_current_project()`
  - `writing.py`: 修正 `Optional[str]` 回傳類型
  - 多處 `dict/list` 變數加入明確類型註解

---

## [0.2.1] - 2025-12-18 (靜態分析大掃除)

### Added

- **MCP-to-MCP Direct Communication Architecture** ✅ 已實作
  - pubmed-search 新增 HTTP API endpoints:
    - `GET /api/cached_article/{pmid}` - 取得單一文章
    - `GET /api/cached_articles?pmids=...` - 批量取得
    - `GET /api/session/summary` - Session 狀態
  - mdpaper 新增 `PubMedAPIClient` HTTP 客戶端
  - 新工具 `save_reference_mcp(pmid, agent_notes)`:
    - Agent 只傳 PMID，無法修改書目資料
    - mdpaper 直接從 pubmed-search API 取得驗證資料
    - 防止 Agent 幻覺（hallucination）書目資訊
  - **分層信任 (Layered Trust)** 參考檔案格式:
    - `🔒 VERIFIED`: PubMed 資料（不可修改）
    - `🤖 AGENT`: AI 筆記（AI 可更新）
    - `✏️ USER`: 人類筆記（AI 絕不碰觸）
- **stdio + HTTP API 同時啟動**
  - pubmed-search 在 stdio MCP 模式下自動啟動背景 HTTP API
  - `start_http_api_background()` 在 daemon thread 運行
  - 解決 VS Code MCP (stdio) 無法同時提供 HTTP API 的問題
- **Skill 文檔完整更新**
  - `literature-review/SKILL.md` 完整重寫，含完整工具列表和 PICO 工作流
  - `parallel-search/SKILL.md` 新增工具表格和 Session 管理說明
  - `concept-development/SKILL.md` 擴展工具列表和 FAQ
  - 所有 skill 明確標示 `save_reference_mcp` 為 PRIMARY 方法

### Changed

- **Reference 內容順序優化** - Abstract 移到 Citation Formats 之前
  - Foam hover preview 現在優先顯示 Abstract（更實用）
- **Foam settings 更新** - `foam.files.ignore` 改為 `foam.files.exclude`
- **sync_references Tool** - Markdown 引用管理器
  - 掃描 `[[wikilinks]]` 自動生成 References 區塊
  - 可逆格式：`[1]<!-- [[citation_key]] -->`，支援重複同步
  - 按出現順序編號，支援 Vancouver/APA 等格式
- **Foam Project Isolation** - 專案隔離功能
  - `FoamSettingsManager` 服務：動態更新 `foam.files.ignore`
  - `switch_project()` 整合：切換專案時自動排除其他專案
  - Whitelist 邏輯：只顯示當前專案的 `references/`
- **Reference Title Display** - Foam 自動完成顯示文章標題
  - frontmatter 加入 `title` 欄位
  - `foam.completion.label: "title"` 設定
- **MCP Tool Logging System** - 統一的工具日誌記錄
  - `tool_logging.py`: log_tool_call, log_tool_result, log_agent_misuse, log_tool_error
  - 日誌存放在專案目錄 `logs/YYYYMMDD.log`（跨平台支援）
  - 已整合至 draft/writing.py, project/crud.py, validation/concept.py, reference/manager.py
- **ReferenceConverter Domain Service** - 支援多來源參考文獻
  - 支援 PubMed, Zotero, DOI 來源
  - ReferenceId Value Object 確保唯一識別符
  - Foam [[wikilink]] 整合
- **Reference Entity 更新** - 新增多來源識別符欄位
  - unique_id, citation_key, source 欄位
  - `from_standardized()` 類別方法

### Changed

- **授權變更** - 從 MIT 改為 Apache License 2.0
- **日誌位置遷移** - 從系統 temp 目錄改為專案目錄 `logs/`
- **README.md** - 新增 MCP 協調架構說明、更新工具列表
- **ARCHITECTURE.md** - 新增 MCP Orchestration 架構圖
- **Prompts 更新** - `/mdpaper.concept` 和 `/mdpaper.search` 增加 MCP 協調流程說明
- **copilot-instructions.md** - 簡化為參照 AGENTS.md，避免重複

### Fixed

- **save_reference JSON 解析** - 處理 MCP 傳遞 JSON 字串的情況
  - 新增 `Union[dict, str]` 型別支援
  - 自動偵測並解析 JSON 字串輸入

### Deprecated

- `save_reference_by_pmid` - 改用 `save_reference(article=metadata)`

## [0.2.0] - 2025-12-17

### Added

- MCP 解耦架構：mdpaper 不再直接依賴 pubmed-search
- 多 MCP 協調模式：Agent 協調 mdpaper + pubmed-search + drawio
- 文獻探索工作區：`start_exploration()` / `convert_exploration_to_project()`
- Concept 驗證系統：novelty scoring (3 rounds, 75+ threshold)
- Paper type 支援：original-research, systematic-review, meta-analysis 等

### Changed

- Python 版本需求升級至 3.11+
- ReferenceManager 重構：接受 article metadata dict 而非 PMID
- 專案結構採用 DDD (Domain-Driven Design)

### Removed

- `infrastructure/external/entrez/` - 文獻搜尋移至 pubmed-search MCP
- `infrastructure/external/pubmed/` - 同上
- `services/strategy_manager.py` - 搜尋策略移至 pubmed-search MCP
- `tools/search/` - 搜尋工具改為 facade 委派

## [0.1.0] - 2025-12-01

### Added

- 初始版本
- MCP Server 框架 (FastMCP)
- 46 個 MCP 工具
- Word 匯出功能
- 參考文獻管理
- 草稿撰寫流程

[0.3.5]: https://github.com/u9401066/med-paper-assistant/compare/v0.3.1...v0.3.5
[0.2.2]: https://github.com/u9401066/med-paper-assistant/compare/v0.2.0...v0.2.2
[0.2.0]: https://github.com/u9401066/med-paper-assistant/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/u9401066/med-paper-assistant/releases/tag/v0.1.0
