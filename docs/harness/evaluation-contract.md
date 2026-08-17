# Evaluation contract: solve, score, and release evidence

The evaluation harness measures persisted academic artifacts, not confidence,
verbosity, or a solver's self-reported success. It applies to autonomous and
human-guided runs and supplements—without replacing—the constitutional gates.

## Solve and score are separate jobs

| Role   | May do                                                                    | Must not do                                                          |
| ------ | ------------------------------------------------------------------------- | -------------------------------------------------------------------- |
| Solver | retrieve, call tools, create artifacts, revise after structured errors    | grade its own prose as evidence, rewrite fixtures, hide failed calls |
| Scorer | read frozen inputs and outputs, resolve locators, run deterministic gates | silently repair the submission, invent ground truth, relax a rubric  |

If the same process performs both roles, it must persist the solver output
before scoring and write a separate score report. The scorer reads the frozen
artifact hash and rubric version so a later rewrite cannot inherit an earlier
pass.

## Score dimensions

```yaml
evaluation_id: EVAL-2026-001
fixture_id: original-research-mini-v1
rubric_version: "1.0"
artifact_sha256: "..."
critical_failures: []
dimensions:
  factual_correctness: { score: 0.0, evidence: [] }
  attribution: { score: 0.0, evidence: [] }
  coverage: { score: 0.0, evidence: [] }
  reproducibility: { score: 0.0, evidence: [] }
  profile_compliance: { score: 0.0, evidence: [] }
  editorial_quality: { score: 0.0, evidence: [] }
budget:
  tool_calls: 0
  retrieved_sources: 0
  elapsed_ms: 0
  model_tokens: null
  estimated_cost: null
result: FAIL
```

Each score needs locators or deterministic check output. Critical failures—such
as fabricated citations, tampered content-integrity receipts, missing consent,
or unresolved primary-data provenance—force `FAIL` regardless of the mean.

## Evidence-locator rules

Prefer multiple stable coordinates when available:

- source identifier and immutable/retrievable revision;
- `span_id` and locator schema version;
- section/page plus line, character, or byte offsets;
- bounded context excerpt and its SHA-256;
- support/contradiction/uncertain relation;
- retrieval and full-text status.

The scorer must re-resolve locators against the recorded revision. A locator
that no longer matches is stale evidence, not partial credit.

## Budget and source-dominance reporting

Budgets are observations and stop rules, not incentives to skip verification.
Record tool calls, retrieval iterations, wall time, tokens, and cost when the
runtime exposes them. A timeout or unavailable optional tool yields a named
degraded result.

Report source dominance by section and claim class. Thresholds belong to the
output profile or fixture; there is no universal maximum. The scorer should
flag an unexplained single-source synthesis while allowing documented cases
such as a reporting standard, protocol, dataset, or case report.

## Frozen fixture families

Each fixture contains inputs, allowed source corpus, source revisions, expected
artifacts, rubric, budget, and failure oracle. Minimum fixture families are:

1. supported claim with an exact full-text locator;
2. plausible but unsupported claim that must fail;
3. contradictory sources requiring qualified synthesis;
4. stale or hash-mismatched locator;
5. source-dominance warning with an allowed and a disallowed example;
6. optional MCP unavailable with an explicit degraded path;
7. C2PA valid, absent, unsupported, invalid, and post-review hash change;
8. manual versus autopilot Phase 4 transitions;
9. one scientific artifact rendered through two output profiles without claim drift.

Fixtures never use a live changing search result as ground truth. Network tests
may supplement them but cannot replace deterministic release evidence.

## Release gates

A release candidate passes evaluation only when:

- compact (12-tool) and full (118-tool) discovery match authority;
- facade and representative specialized calls pass MCP protocol smoke;
- solver/scorer artifacts and hashes are reproducible;
- critical negative fixtures fail for the expected reason;
- optional-dependency absence follows the documented degraded path;
- DOCX/PDF, Pages, VSIX, wheel, and container artifacts pass their applicable smoke checks;
- no score, test count, or benchmark claim is copied from an earlier release without rerun evidence.

Store the fixture version, command, platform, dependency lock hash, artifact
hashes, and raw score report with the release evidence.
