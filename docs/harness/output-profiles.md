# Formal academic output profiles

MedPaper selects an output profile before concept validation or drafting. The
domain registry is the canonical source for names, section order, typical
length, concept requirements, and writing prerequisites. The constraint engine
adds machine-enforced structure, evidence, voice, overlap, reference, and
word-count boundaries.

## Supported profiles

| Key | Intended output | Concept contract | Typical words | Statistical hooks |
| --- | --- | --- | ---: | --- |
| `original-research` | Clinical or empirical journal article | novelty + selling points | 3,000 | yes |
| `systematic-review` | Reproducible qualitative evidence synthesis | novelty + selling points | 4,000 | yes |
| `meta-analysis` | Quantitative evidence synthesis | novelty + selling points | 4,500 | yes |
| `case-report` | Single case or case series | novelty + selling points | 1,500 | no |
| `review-article` | Narrative or invited review | novelty + selling points | 5,000 | no |
| `letter` | Correspondence or brief commentary | novelty | 500 | no |
| `research-proposal` | Grant, protocol, or institutional plan | background + gap + objectives + methods + expected impact | 5,000 | no |
| `project-closeout-report` | Final delivery and variance report | baseline + methods + deliverables | 5,000 | no |
| `student-paper` | Course paper, capstone, or assessed essay | background + question/thesis | 3,000 | no |
| `conference-paper` | Full proceedings manuscript | novelty + selling points | 3,500 | yes |
| `thesis-dissertation` | Degree thesis or dissertation | background + gap + question + methodology | 40,000 | yes |
| `arxiv-preprint` | Versioned repository preprint | novelty + selling points | 6,000 | yes |
| `other` | Explicitly customized formal output | novelty | 2,000 | no |

The statistical-hook column controls B8, B11, and B16. Common provenance,
anti-AI, language, citation, paragraph, and cross-reference checks continue to
run for every profile. A skipped type-specific hook remains visible in the
audit record as not applicable.

## Profile-specific integrity rules

### Research proposal

- Keep proposed activities and expected impact distinct from completed work or
  observed results.
- Make objectives, design, milestones, ethics, data lifecycle, resources, and
  risks internally traceable.
- State assumptions behind budget and feasibility claims.

### Project closeout report

- Preserve the original baseline and success criteria.
- Separate delivered artifacts, measured outcomes, deviations, corrective
  actions, remaining risks, and handoff obligations.
- Link status and financial claims to dated records; do not silently rewrite
  the approved scope after observing the outcome.

### Student paper

- The student remains the author and verifies all sources, quotations,
  calculations, and conclusions.
- Record course-rubric alignment and the institution's permitted AI-use rule.
- Never generate a false reading record or claim that the student personally
  reviewed a source they did not inspect.

### Conference paper

- Enforce the venue's page, anonymity, artifact, and presentation constraints.
- Keep the paper, abstract, poster, slides, and demo consistent while avoiding
  duplicated or unsupported claims.

### Thesis or dissertation

- Treat chapters as dependent artifacts with a single question, method, data,
  terminology, and contribution contract.
- Preserve committee decisions, ethics approvals, scope changes, and data
  provenance across revisions.

### arXiv or repository preprint

- State the review status without implying peer-review acceptance.
- Record data/code availability, licenses, access restrictions, persistent
  identifiers, reproduction instructions, and material version changes.

## Creating a project

Use the same consolidated project facade for all profiles:

```text
project_action(
  action="create",
  name="Prospective feasibility protocol",
  paper_type="research-proposal",
  workflow_mode="manuscript"
)
```

`get_paper_types` returns the registry exposed by the domain layer. The MCP UI
enum is generated from the same registry, and cross-layer tests prevent the
legacy compatibility constant from drifting.

## Recording exemplar use

An exemplar may calibrate organization or reporting but cannot supply evidence
or citation credit:

```text
project_action(
  action="exemplar_usage",
  exemplar_source_id="PMID:12345678",
  exemplar_roles_json='["structure", "methodology"]',
  exemplar_target_sections_json='["Methods", "Discussion"]',
  exemplar_purpose="Compare reporting order; verify every claim independently."
)
```

The resulting `.audit/exemplar-usage.yaml` fixes `evidence_eligible`,
`citation_credit`, and `verbatim_copy` to `false`. Code rejects prohibited
roles and refuses new records if the policy artifact has been tampered with.
