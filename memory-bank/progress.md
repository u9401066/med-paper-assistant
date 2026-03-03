# Progress (Updated: 2026-03-03)

## Done

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

## Doing

(none)

## Next

- Phase 5c TreeView/CodeLens/Diagnostics features
- Dashboard Webview embedding
- CI/CD pipeline for automated VSIX publish
