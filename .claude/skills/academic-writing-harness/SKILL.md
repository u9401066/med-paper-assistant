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
3. Read the relevant source skill for the requested phase:
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
  every material claim.
- Register exemplars separately from evidence sources. Extract only declared
  structural or stylistic features and record provenance.
- Write section-by-section, run deterministic hooks, and satisfy each hard gate
  before advancing.
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
