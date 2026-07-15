# 品質與稽核

品質不是最後才跑一次 spell check，而是分布在寫作、全稿、review、commit 與跨對話演進的控制系統。

![Three-layer quality system](../assets/wiki-quality-layers.svg){ loading=lazy }

## 79 checks 在哪裡發生

```mermaid
flowchart LR
    Write[Write / patch section] --> A[A-series<br/>post-write]
    A --> B[B-series<br/>section semantics]
    B --> Manuscript[Whole manuscript]
    Manuscript --> C[C-series<br/>consistency + citations]
    C --> Data[F-series<br/>data artifacts]
    Data --> Review[R1–R6<br/>hard gate]
    Review --> Commit[P + G series<br/>precommit / general]
    Commit --> Learn[D1–D9<br/>meta-learning]
    Review -->|rewrite| Write
```

56 個 checks 由 deterministic code enforcement 執行；23 個高語義 checks 由 Agent 按 skill contract 執行。兩者都要留下可檢查結果。

## 三層演進

```mermaid
flowchart TB
    Event[L1 Event hooks<br/>immediate feedback] --> Code[L2 Code enforcement<br/>constraints + telemetry]
    Code --> Evolution[L3 Scheduled evolution<br/>D1-D9 + CI + health]
    Evolution --> Pending[(Pending evolutions)]
    Pending --> Decision{Evidence + boundary review}
    Decision -->|accept| Event
    Decision -->|reject / defer| Log[(Decision log)]
```

| 層                      | 作用                  | 典型 evidence                            |
| ----------------------- | --------------------- | ---------------------------------------- |
| L1 Event hooks          | 寫作當下發現問題      | hook id、severity、location              |
| L2 Code enforcement     | 保證 domain invariant | constraint result、checkpoint、telemetry |
| L3 Autonomous evolution | 跨輪次找系統性弱點    | D1–D9 analysis、CI、pending evolution    |

## Review hard gate

```mermaid
stateDiagram-v2
    [*] --> ReviewStarted
    ReviewStarted --> ReportSubmitted
    ReportSubmitted --> R1Depth
    R1Depth --> R2Response
    R2Response --> R3Equator
    R3Equator --> R4Traceability
    R4Traceability --> R5AntiAI
    R5AntiAI --> R6CitationBudget
    R6CitationBudget --> Passed
    R1Depth --> Rewrite: fail
    R2Response --> Rewrite: fail
    R3Equator --> Rewrite: fail
    R4Traceability --> Rewrite: fail
    R5AntiAI --> Rewrite: fail
    R6CitationBudget --> Rewrite: fail
    Rewrite --> ReviewStarted
    Passed --> [*]
```

Phase 7 未通過時，Phase 8–11 不應被視為可交付。Review report、author response 與實際修正之間必須可追蹤。

## Audit artifacts

```mermaid
flowchart TD
    Invocation[Tool invocation] --> Telemetry[tool-telemetry.yaml]
    Hook[Hook execution] --> Reports[hook / review reports]
    Exemplar[Exemplar registration] --> ExAudit[exemplar-usage.yaml]
    Health[Repeated tool issue] --> Pending[pending-evolutions.yaml]
    Phase[Phase transition] --> Checkpoint[checkpoint state]
    Meta[D1–D9 analysis] --> Evolution[evolution log]
    Telemetry & Reports & ExAudit & Pending & Checkpoint & Evolution --> Audit[(.audit/)]
```

Audit 的價值不是檔案數量，而是能回答：哪個工具、基於哪個 artifact、在什麼 gate、做了什麼決定、下一輪如何改善。

## 失敗處理原則

1. 指出具體 hook/constraint，而不是只說「品質不好」。
2. 優先修正最上游 artifact，例如 concept 或 evidence gap。
3. 只回退受影響 sections，保留已通過內容。
4. 修正後重跑相同 gate，不能用不同較弱檢查替代。
5. 重複故障進入 PendingEvolutionStore，而不是每次人工忘記。

!!! success "品質基線"

    v0.9.0 的 release baseline 包含 1523 Python tests、169 VSIX tests、118-tool greedy smoke、Ruff、mypy、Bandit、vulture、bundle parity、三平台 smoke 與 package install validation。
