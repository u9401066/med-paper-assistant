# External academic-agent project benchmark

This benchmark records which mechanisms are worth adapting and which are not.
It is a design input, not an instruction to copy code or silently add runtime
dependencies. Re-evaluate upstream behavior and licenses before implementation.

## Compared projects

| Project                                                                 | Useful upstream mechanism                                                                                                     | Local gap                                                                                                                               | Decision                                                                                                                                                              |
| ----------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [Future-House/PaperQA](https://github.com/Future-House/paper-qa)        | Iterative agentic retrieval, chunked evidence contexts, relevance ranking, and redundant metadata lookup                      | The current harness validates references and some claims but lacks a first-class ranked evidence-context ledger for every planned claim | Adopt the artifact contract and evaluation idea; keep PubMed-first verified metadata and existing MCP boundaries                                                      |
| [Stanford OVAL/STORM](https://github.com/stanford-oval/storm)           | Separates pre-writing research from drafting and expands coverage through perspective-guided questions                        | Current planning can reach an outline before documenting unanswered questions from multiple stakeholder/method perspectives             | Adopt a question map before the outline for reviews, proposals, and broad topics; do not simulate unsupported experts as evidence                                     |
| [SakanaAI/AI-Scientist-v2](https://github.com/SakanaAI/AI-Scientist-v2) | Progressive branch exploration with an experiment-manager role and iterative reviewer feedback                                | Concept exploration is mostly linear outside CGU and review regressions                                                                 | Adopt bounded alternative branches, explicit scoring, stop criteria, and audit records; reject unrestricted autonomous experiments or automatic publication decisions |
| [Quarto CLI](https://github.com/quarto-dev/quarto-cli)                  | Project profiles, shared metadata, scientific cross-references, executable outputs, websites, books, and manuscript rendering | Export is manuscript-centric and the human documentation website is not a first-class reproducible output                               | Adopt output-profile vocabulary and plan an optional publishing adapter/docs site; retain DOCX/Pandoc paths and avoid a mandatory new runtime until smoke-tested      |

## Mechanisms to implement

### 1. Ranked evidence-context ledger

Add an artifact that maps a planned claim to candidate source spans and records
relevance, source trust, full-text status, contradictions, and the selected
supporting span. Retrieval may iterate, but drafting cannot treat a generated
summary as the source of truth.

Minimum fields:

```yaml
claim_id: C-INTRO-001
claim_text: "..."
contexts:
  - source_id: "PMID:..."
    locator: "section/paragraph/span"
    relevance: 0.0
    trust: verified
    supports: true
    contradicts: false
selected_contexts: []
decision_reason: ""
```

### 2. Perspective question map

Before an outline, record what a domain expert, methodologist, statistician,
editor, stakeholder/patient, and implementation reviewer would need answered.
Applicable perspectives vary by output profile. Each question is linked to an
answer, an evidence need, a user decision, or an explicit out-of-scope reason.

### 3. Bounded branch exploration

Concept or structure alternatives may branch only when the decision materially
changes aims, methods, interpretation, or deliverable structure. Each branch
must share the same scoring dimensions, maximum branch count, and stop rule.
The selected branch and discarded alternatives remain in the audit trail.

### 4. Output profiles and publishing adapters

Keep scientific content and output constraints separate. A profile defines
sections, terminology, gates, metadata, and render targets; an adapter renders
DOCX, PDF, HTML, preprint source, or a documentation website. Rendering must not
change scientific claims.

## Explicit non-adoptions

- No automatic import of evidence from general web pages when a verified
  biomedical source is required.
- No simulated persona may be cited as an expert or treated as evidence.
- No autonomous experiment execution, submission, or publication without the
  user's explicit scope and applicable ethical/safety review.
- No mandatory model/provider framework. The MCP and domain contracts remain
  provider-neutral.
- No publishing dependency becomes required until Linux, macOS, Windows, clean
  install, offline/degraded, and artifact smoke paths are defined.

## Evaluation plan

For each adopted mechanism, add a fixture-based golden flow and at least one
failure test:

1. unsupported claim is blocked despite a plausible generated summary;
2. an unanswered high-priority question blocks planning;
3. branch limit and stop criteria prevent runaway exploration;
4. one source manuscript renders through two profiles without claim drift;
5. a missing optional publishing binary yields a clear degraded status rather
   than corrupting or deleting output.
