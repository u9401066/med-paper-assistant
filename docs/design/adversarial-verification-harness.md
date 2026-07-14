# Adversarial / Metamorphic Verification Harness

> Status: implemented (MVP)
> Scope: proves the quality **verifiers** (writing hooks) actually catch bad input.

## Problem this solves

The project has 79 quality checks and a code-enforced pipeline. But there was a
structural blind spot in how we _trust_ them:

1. **MCP/agents cannot self-verify.** The agent is a generator; the harness is the
   verifier. We can only make the harness better, not the model.
2. **No benchmark.** We could say "the hooks work" but had nothing that
   _continuously proves_ they work, nor that they keep working over time.
3. **Existing tests check the happy path.** `test_e2e_pipeline_lifecycle` and the
   per-hook unit tests mostly assert _good input passes_. Very little asserted
   _bad input is caught_ — which is the entire point of a verifier.

## Core idea: verification is easier than generation

We deliberately do **not** try to verify "did we write a _good_ paper" (that needs
external ground truth and is near-impossible). Instead we verify the cheaper,
decidable property:

> **Does our verifier ACCEPT known-good input and REJECT known-bad input?**

This is **metamorphic testing**: take a known-good fixture, apply a
_known-direction mutation_ that should break exactly one quality property, and
assert the verifier's verdict flips from pass → caught.

```text
good_fixture  --(known-direction mutation)-->  bad_fixture
   hook.passed == True                            hook.passed == False
```

## Design

Located in `tests/test_adversarial_hooks.py`.

### Scenario model

Each covered hook declares:

- exactly **one known-good** scenario that MUST pass (`hook.passed is True`), and
- **one or more known-bad** scenarios that MUST be caught (`hook.passed is False`).

A scenario is a small builder `(_engine, _project_dir) -> HookResult` so hooks
that need on-disk state (e.g. P7 reads `references/`) can set it up.

`caught(result)` is defined uniformly as `not result.passed`. Every hook already
sets `passed` correctly (CRITICAL issue or threshold breach ⇒ `passed=False`), so
the harness does not need per-hook special-casing.

### Coverage ratchet (the verifier's own ratchet)

`ADVERSARIAL_TARGETS` lists the hook IDs the harness commits to covering. A
**coverage meta-test** asserts every target has both a good and a bad scenario.
This means coverage can only be _added_, never silently lost — the harness
protects itself the same way it protects the manuscript.

## Hooks covered

| Hook | Quality property                          | Known-bad mutation                                                                               |
| ---- | ----------------------------------------- | ------------------------------------------------------------------------------------------------ |
| A3   | Anti-AI phrasing                          | inject canonical AI filler ("it is important to note", "plays a crucial role", "groundbreaking") |
| A5   | Language consistency (American)           | swap American → British spelling (analyse/colour/randomised)                                     |
| A6   | Internal overlap / copy-paste             | duplicate a paragraph                                                                            |
| B8   | Stats test alignment (Results ↔ Methods) | use a statistical test in Results never declared in Methods                                      |
| B9   | Section tense                             | write Methods in present tense ("we measure/analyze/assess")                                     |
| B11  | Results objectivity                       | inject ≥5 interpretive/speculative phrases into Results                                          |
| B12  | Introduction structure                    | preview study results inside the Introduction                                                    |
| B13  | Discussion structure                      | omit the limitations paragraph                                                                   |
| B14  | Ethical statements                        | omit the ethics-approval statement                                                               |
| C3   | N-value consistency                       | report a different sample size in Results than Methods                                           |
| C4   | Abbreviation first use                    | use a non-common abbreviation with no definition                                                 |
| P7   | Reference + DOI integrity                 | attach a malformed DOI to a saved reference                                                      |

Each row has a paired known-good fixture proving the verifier does **not**
false-positive on clean input.

### Why the EQUATOR (E1-E5) hooks are excluded

The E-series reporting-guideline checks (CONSORT/STROBE/PRISMA/CARE) are
**Agent-Driven**: they have no deterministic code-level `check_` method that
returns a `HookResult`. There is no mechanical pass/fail to flip, so a
metamorphic fixture cannot be built for them without an LLM in the loop. They
are intentionally out of scope here and remain a separate (larger) effort.

## How to extend

1. Pick a Code-Enforced hook with deterministic `passed` semantics.
2. Add its ID to `ADVERSARIAL_TARGETS`.
3. Add one `good` scenario (clean input the hook must pass) and ≥1 `bad`
   scenario (a single known-direction mutation the hook must catch).
4. The coverage meta-test will fail until both exist — that is intended.

## What this is NOT

- Not a measure of paper quality. It measures _verifier fidelity_.
- Not an external fact-check. DOI existence (Crossref), citation relevance
  (retrieval), and reporting-guideline semantics remain separate, larger efforts.
- Not a replacement for the per-hook unit tests; it is the cross-cutting proof
  that the suite of verifiers rejects bad input, tracked as one ratcheting set.
