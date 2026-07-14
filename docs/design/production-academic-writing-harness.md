# Production academic-writing harness architecture

This design describes the provider-neutral production surface shared by Claude
Code, Codex, and OpenClaw. Runtime discovery differs, but scientific evidence,
output-profile constraints, phase gates, review, and audit artifacts do not.

## System flow

```mermaid
flowchart TB
    subgraph Runtime[Agent runtimes]
        Claude[Claude Code<br/>CLAUDE.md + .claude/skills]
        Codex[Codex<br/>AGENTS.md + .agents/skills]
        OpenClaw[OpenClaw<br/>AGENTS.md + .agents/skills]
    end

    Claude --> Contract[Platform-neutral academic-writing contract]
    Codex --> Contract
    OpenClaw --> Contract

    Contract --> Facades[Stable MCP facades]
    Facades --> Profiles[13 output profiles]
    Facades --> Intake[Source-material and full-text intake]
    Facades --> Pipeline[Phase 0-11 pipeline]

    Profiles --> Constraints[DomainConstraintEngine<br/>13 profiles · 110 base constraints]
    Intake --> Evidence[Verified evidence and user-primary materials]
    Pipeline --> Hooks[79 writing/review checks]
    Pipeline --> Review[Independent review and regression loop]

    Exemplar[Exemplar calibration<br/>structure · methods · reporting · argument · style]
    Exemplar -->|audit only| Audit[(Project audit artifacts)]
    Exemplar -. never evidence or citation credit .-> Evidence

    Constraints --> Audit
    Evidence --> Claims[Claim-evidence drafting]
    Hooks --> Audit
    Review --> Audit
    Claims --> Outputs[DOCX · PDF · HTML · preprint · formal reports]
    Audit --> Outputs
    Review -->|material rewrite| Claims
```

The dotted exemplar edge is a prohibition, not a data-flow path: a document
used for structural or stylistic calibration does not become scientific
evidence. If it is independently appraised as evidence, that is a separate
reference decision with its own provenance.

## Layer boundaries

```mermaid
flowchart LR
    Presentation[Presentation<br/>MCP tools · VSIX] --> Application[Application<br/>use cases · ports]
    Application --> Domain[Domain<br/>entities · profiles · rules]
    Infrastructure[Infrastructure<br/>persistence · Pandoc · services] --> Domain
    Infrastructure -. implements .-> Ports[Application-owned Protocol ports]
    Ports --> Application
```

Static tests reject Application imports from Infrastructure or Presentation,
and reject Domain imports from all outer layers. Infrastructure adapters are
constructed at the MCP boundary and injected through application-owned ports.

## Production verification

The release evidence combines complementary checks:

1. formatting, lint, type checking, Bandit, and high-confidence vulture scan;
2. deterministic unit, boundary, adversarial, lifecycle, and export tests;
3. a 118-tool greedy MCP smoke in an isolated workspace;
4. Linux, Windows, and macOS CI smoke;
5. VSIX lint, TypeScript, Vitest, bundle-drift, package, and install smoke;
6. tool/hook authority and documentation consistency checks;
7. audit, Memory Bank, changelog, and release provenance.

Expected domain failures are assertions of policy and remain distinguishable
from transport/runtime failures. The greedy runner fails the build only for
broken calls, while its fixtures deliberately exercise validation and
precondition behavior.
