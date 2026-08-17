---
name: academic-writing-harness
description: Cross-agent workflow for evidence-grounded manuscripts, proposals, reports, student papers, and preprints with auditable gates.
---

# Academic Writing Harness

Use this skill for end-to-end academic writing, revision, review, or export in
Claude Code. Codex and OpenClaw use the matching repo skill under
`.agents/skills/academic-writing-harness/`.

## Required reading

1. Read `.copilot-mode.json` and `AGENTS.md` before repository operations.
2. Read `docs/harness/academic-writing-workflow.md` completely. It is the
   platform-neutral workflow and artifact contract.
3. Read `docs/harness/evaluation-contract.md` before running or changing a
   quality evaluation. It defines solver/scorer separation, evidence locators,
   budgets, frozen fixtures, and release evidence.
4. Read the relevant source skill for the requested phase:
   - `../project-management/SKILL.md` for setup and output type.
   - `../literature-review/SKILL.md` for evidence discovery.
   - `../draft-writing/SKILL.md` for section drafting.
   - `../manuscript-review/SKILL.md` for structured review.
   - `../word-export/SKILL.md` for DOCX delivery.
   - `../auto-paper/SKILL.md` only for full autopilot runs.

## Operating contract

- Resume recorded workspace and project state before starting a new phase.
- Select an output profile before planning. Do not force every academic output
  into IMRaD.
- Build a claim-evidence ledger before prose and keep source identifiers near
  every material claim. Evidence locators must include a stable source
  revision, section/page/paragraph/span, offsets when available, and a hash of
  the cited span; a model summary is not a locator.
- Register exemplars separately from evidence sources. Extract only declared
  structural or stylistic features and record provenance.
- Write section-by-section, then score the persisted artifact in a separate,
  read-only pass. A solver must not award its own gate result or alter scorer
  fixtures, thresholds, or expected outcomes.
- Declare per-stage tool/model/time/retry budgets and enforce source-dominance
  limits. Exceeding a budget or letting one source dominate is a recorded gate
  outcome, not a reason to hide or truncate audit evidence.
- Run deterministic hooks and satisfy each hard gate before advancing. Release
  claims require frozen positive, negative, mutation, degraded, and resume
  fixtures plus the command, environment, counts, hashes, and failure details.
- Treat human acceptance as an external authority boundary. An Agent/MCP may
  inspect or revoke a host-issued Ed25519 confirmation receipt, but must never
  mint one by labeling its own input as `human`; receipts bind the project,
  reviewed artifact/state hashes, named reviewer, confirmation identifier, and
  time, and are verified only against host-configured public keys.
- Before inserting an image, re-run the read-only C2PA and pinned
  visible/open-DWT checks against its current bytes. Preserve the original,
  require documented review for raster uncertainty, and never equate a
  negative detector result with proof that no watermark exists.
- Keep verified source data, agent interpretation, and user-authored notes in
  separate trust layers.
- Finish with cross-section review, reference verification, export validation,
  audit artifacts, and Memory updates.

## Tool adaptation

Tool names can differ by runtime. Map capabilities by contract: workspace
state, project management, literature search, full-text ingestion, reference
storage, draft read/write, quality hooks, pipeline gates, and export. If a
required capability is unavailable, record the degraded path rather than
inventing evidence or silently skipping a gate.

The default MCP entrypoint is the compact 12-tool facade; the 118-tool full
surface remains an explicit compatibility and diagnostics profile. Both must
exercise the same domain rules and audit contracts.
