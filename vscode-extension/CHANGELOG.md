# Changelog

## 0.7.9 - 2026-04-24

- Corrected marketplace README bundled-template wording to mention the packaged CSL styles.

## 0.7.8 - 2026-04-24

- Fixed Vancouver/BJA superscript export so Pandoc citeproc runs with bibliography-backed DOCX/PDF output instead of leaking raw `[@citekey]` tokens.
- Added FOAM-compatible citation handling so manuscript citations and library-wiki embeds/anchors/aliases can coexist without corrupting export or audit hooks.
- Added raw citation token checks to DOCX XML smoke validation and synced the bundled Python/CSL assets.
- Folded the remaining exports/workspace-state/review-loop branch fixes into the main release line.

## 0.7.7 - 2026-04-24

- Fixed release CI hygiene after v0.7.6 with Ruff, Prettier, mypy, Bandit, and bundled Python mirror cleanup.
- Switched DOCX XML smoke parsing to `defusedxml` for release security scanning.

## 0.7.6 - 2026-04-24

- Added `pipeline_action(action="doctor")` for one-shot 11-phase readiness, external MCP, and cached gate diagnostics.
- Added DOCX XML smoke inspection through `inspect_export(action="docx_smoke")` / `inspect_export(action="xml_smoke")`.
- Added source-material intake, asset-aware ingestion receipts, C14 claim-evidence alignment, and stronger data-anchor provenance checks to reduce autonomous agent friction.
- Updated the packaged MCP authority to `117 full / 22 compact` tools and synced bundled Python/assets.

## 0.7.2 - 2026-04-22

- Guarded `insert_citation()` against drafts already synced from citation wikilinks so numbered-bibliography workflows cannot silently contaminate library-wiki drafts.
- Added deterministic and UTF-8-safe wikilink validation, plus a `resolve_project_context()` regression fix for project info payloads that omit a `success` flag.
- Added machine-checked tool-surface authority validation, wired it into extension validation and release gating, and synchronized the published counts across repo and VSIX docs.

## 0.7.1 - 2026-04-22

- Fixed Foam graph citation visibility by emitting reversible citation wikilinks in visible form while preserving compatibility with legacy HTML-comment anchors.
- Centralized reversible citation restoration in the shared converter and restricted whitespace parsing to same-line spaces or tabs so cross-line text is not misread as synced citations.
- Added regression coverage for legacy and APA resync flows plus bundled Python mirror parity, and updated bundle drift detection to ignore Python cache artifacts.

## 0.7.0 - 2026-04-22

- Centralized MCP workflow guard resolution behind `resolve_project_context` so manuscript and library-wiki tools share one validation entrypoint instead of duplicating local helpers.
- Delegated legacy project creation flows through `ProjectManager`, keeping repository and use-case layers thin while preserving workflow-aware exploration conversion behavior.
- Tightened drafter git repo binding so the auto-committer refreshes when the active project changes.
- Expanded bundle drift detection to cover mirrored Python source directories and re-synced packaged prompts / support files so VSIX validation catches real source-to-bundle drift.

## 0.6.9 - 2026-04-21

- Added full-surface agent wiki stage 2 orchestration: `ingest_web_source`, `ingest_markdown_source`, `build_knowledge_map`, `build_synthesis_page`, and `materialize_agent_wiki`.
- Extended canonical reference persistence so markdown/web intake, knowledge maps, synthesis pages, and `notes/index.md` all flow through the same durable writer.
- Updated packaged instructions and VSIX README counts to reflect the current `101 full / 44 compact` MCP surface.
- Bundled the Foam / LLM wiki reference docs and workflow figure into the VSIX so `MedPaper: Setup Workspace` can scaffold them into a user's `docs/` directory.
- Added a command palette shortcut to open the bundled LLM wiki guide directly, and updated Setup Workspace to announce which `docs/` files were scaffolded.

## 0.6.8 - 2026-04-20

- Synced the bundled MedPaper Python package to include the latest reference persistence and MCP registration changes.
- Added the `mdpaper.toolSurface` VS Code setting so packaged VSIX installs can switch from the default compact surface to the full surface when advanced wiki/reference orchestration tools are needed.
- Updated bundled instructions and help prompt counts to reflect the current `96 full / 44 compact` MCP surface.
- Documented the local import -> canonical identity resolution workflow for agent wiki materialization in the VSIX README.
- Tightened reference identity resolution so stale DOI registry entries are cleaned up, merged artifact conflicts are preserved instead of overwritten, and the final knowledge-base index is rebuilt once at the correct point.
