# Claude Code Repository Guide

This repository is a production-oriented academic-writing harness. The full
governance source is `AGENTS.md`; this file keeps Claude Code's always-loaded
context concise.

## Before any operation

- Read `.copilot-mode.json`. Only modify protected code paths in
  `development` mode.
- Follow the authority order:
  `CONSTITUTION.md` > `.github/bylaws/*.md` > skill instructions.
- Preserve user changes in a dirty worktree and use `uv` for Python tasks.

## Architecture and safety

- Keep dependencies directed as
  `Presentation -> Application -> Domain <- Infrastructure`.
- Prefer PubMed-originated verified metadata over agent-transcribed metadata.
- Never edit verified source content, user notes, or constitutional safeguards
  through an autonomous evolution step.
- Treat exemplar papers as structure/style evidence only. Never copy wording,
  claims, data, citations, or conclusions from them without independent
  verification and attribution.

## Academic-writing work

- Use `.claude/skills/academic-writing-harness/SKILL.md` for manuscripts,
  proposals, closeout reports, student papers, preprints, and other formal
  academic outputs.
- Resume state from `.mdpaper-state.json` and project `.memory/` before
  restarting a pipeline.
- Respect phase gates, audit artifacts, section approval, and citation
  provenance. Do not claim completion until the final gate passes.

## Verification

- Python: `uv run ruff check src tests scripts`, `uv run mypy src`,
  `uv run pytest`.
- Security/dead code: `uv run bandit -q -r src` and
  `uv run vulture src scripts --min-confidence 80`.
- Extension: run the relevant `npm` checks under `vscode-extension/`.
- Update tests, documentation, Memory Bank, and release notes when behavior or
  public contracts change.
