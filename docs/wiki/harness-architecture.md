# Harness 架構

Harness 的核心不是某一個 Agent，而是跨平台都必須遵守的「寫作契約 + 工具邊界 + artifact state」。Claude Code、Codex、OpenClaw 與 Copilot 只是不同 presentation adapters。

![Cross-agent system map](../assets/wiki-system-map.svg){ loading=lazy }

## 跨 Agent discovery

```mermaid
flowchart TB
    Contract[docs/harness/<br/>academic-writing-workflow.md]
    Contract --> Claude[CLAUDE.md<br/>.claude/skills]
    Contract --> Shared[AGENTS.md<br/>.agents/skills]
    Contract --> Copilot[.github/prompts<br/>VSIX bundled skills]
    Claude --> MCP[Same MCP facade]
    Shared --> MCP
    Copilot --> MCP
    MCP --> Workspace[(Same project artifacts)]
    Workspace --> Audit[(Same audit contracts)]
```

Adapter 可以描述 client 特有的 discovery 或 command，但不能各自發明 evidence policy。共用契約位於 [Academic-writing workflow](../harness/academic-writing-workflow.md)。

## DDD 四層

```mermaid
flowchart LR
    subgraph Presentation
      Tools[MCP tools]
      Prompts[MCP prompts]
      Resources[MCP resources]
    end
    subgraph Application
      UseCases[Use cases]
      Ports[Repository / exporter ports]
    end
    subgraph Domain
      Entities[Entities]
      Profiles[Paper type registry]
      Rules[Domain rules]
    end
    subgraph Infrastructure
      FS[Filesystem stores]
      Pandoc[Pandoc exporter]
      Hooks[Hook engines]
    end

    Tools & Prompts & Resources --> UseCases
    UseCases --> Entities & Profiles & Rules
    Infrastructure --> Ports
    FS & Pandoc & Hooks --> Domain
```

### 依賴 invariant

- Presentation → Application → Domain。
- Infrastructure 實作 Application port，且可依賴 Domain。
- Application 不 import Infrastructure。
- Domain 不 import Application、Infrastructure、Interfaces。
- Composition root 負責把 adapter 注入 use case。

## 一次 tool call 經過什麼

```mermaid
sequenceDiagram
    autonumber
    participant C as MCP client
    participant F as Facade tool
    participant G as Guard + guidance
    participant U as Application use case
    participant D as Domain
    participant I as Infrastructure adapter
    participant T as Telemetry / checkpoint

    C->>F: project_action / draft_action / validation_action
    F->>G: normalize action + validate path/mode
    G->>U: typed request
    U->>D: apply profile and domain rules
    U->>I: persist / export through port
    I-->>U: artifact result
    U->>T: invocation + audit + checkpoint
    U-->>F: structured result + next guidance
    F-->>C: compact response
```

Facade-first surface 減少 Agent 選錯工具；full tool surface 仍保留作為進階與相容入口。所有路徑都應經過相同 guard、telemetry 與 domain constraints。

## Canonical registry 如何傳播

```mermaid
flowchart TD
    Registry[domain/paper_types.py<br/>13 profiles] --> Entity[Project entity]
    Registry --> UI[MCP enum / settings]
    Registry --> Hook[Hook applicability]
    Registry --> Validator[Concept requirements]
    Registry --> Constraints[DomainConstraintEngine<br/>110 base constraints]
    Registry --> Templates[Concept templates]
    Validator & Constraints & Templates --> Draft[Type-aware writing]
```

Output profile 只能有一個 canonical authority。UI、hook 與 compatibility constants 都是投影，防止「選單有一種、驗證器又是另一種」的 drift。

## 共享 state 為什麼用檔案

Filesystem artifacts 讓不同 Agent 與不同對話可以接手，而且研究者能直接檢查：

- `concept.md`：研究問題、方法與 novelty 契約。
- `references/`：verified metadata 與 analysis notes。
- `drafts/`：可逐 section 審閱的 manuscript。
- `assets/`：圖表與資料產物。
- `.audit/`：hook、telemetry、exemplar、evolution evidence。
- `.memory/`：project-level focus、decisions、next action。

!!! info "深入設計"

    更精簡的 production diagram 與 dependency graph 見 [Production academic-writing harness](../design/production-academic-writing-harness.md)；artifact lifecycle 見 [Artifact-centric architecture](../design/artifact-centric-architecture.md)。
