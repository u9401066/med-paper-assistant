# 研究管線總覽

Pipeline 把「寫一篇論文」拆成可稽核的階段。每一階段都有輸入、輸出、gate 與可恢復狀態；Agent 可以自主推進，但不能假裝缺少的 evidence 已存在。

## Phase 地圖

```mermaid
flowchart LR
    P0[0 Intake] --> P1[1 Project]
    P1 --> P2[2 Literature]
    P2 --> P21[2.1 Full text]
    P21 --> P3[3 Concept]
    P3 --> P4{4 Plan approval}
    P4 --> P5[5 Draft sections]
    P5 --> P6[6 Manuscript hooks]
    P6 --> P65[6.5 Assets]
    P65 --> P7{7 Review loop}
    P7 -->|rewrite| P5
    P7 --> P8[8 Reference sync]
    P8 --> P9[9 Export]
    P9 --> P10[10 Meta-learning]
    P10 --> P11[11 Delivery]

    classDef gate fill:#f59e0b,color:#17202a,stroke:#b45309
    class P4,P7 gate
```

Phase 0–11 加上 6.5 是主要 checkpoint surface；2.1 是文獻階段內的全文／來源材料 sub-gate。完整規格見 [Auto-Paper 指南](../auto-paper-guide.md)。

## 每階段產出什麼

| 階段               | 核心問題               | 主要 artifact                        | Gate 證據                                |
| ------------------ | ---------------------- | ------------------------------------ | ---------------------------------------- |
| 0 Intake           | 有哪些資料與限制？     | source inventory、ingestion receipts | 檔案存在且角色明確                       |
| 1 Project          | 寫什麼類型？           | config、concept skeleton             | profile 可解析                           |
| 2 / 2.1 Literature | 有哪些可用證據？       | references、fulltext status          | verified metadata、來源狀態              |
| 3 Concept          | 問題值得且可寫嗎？     | concept validation                   | required sections、novelty if applicable |
| 4 Plan             | 寫作順序與資產是什麼？ | manuscript plan                      | 人工核准                                 |
| 5 Draft            | 每節是否有足夠依據？   | section drafts                       | section approval + hooks                 |
| 6 / 6.5 Quality    | 全稿與圖表是否一致？   | hook reports、assets                 | C/F checks                               |
| 7 Review           | 批判性審閱是否閉環？   | review report、author response       | R1–R6 hard gate                          |
| 8 Reference sync   | 引用是否可解析？       | citation audit                       | wikilinks、budget、distribution          |
| 9 Export           | 成品是否真的有效？     | DOCX / PDF                           | header/trailer/token smoke               |
| 10 Learning        | 本輪學到什麼？         | D1–D9 analysis                       | provenance-matched audit                 |
| 11 Delivery        | 是否可交付？           | final checklist                      | 所有前置 gate 通過                       |

## 寫作與回退

```mermaid
stateDiagram-v2
    [*] --> SectionBrief
    SectionBrief --> DraftSection
    DraftSection --> SectionHooks
    SectionHooks --> DraftSection: fail / revise
    SectionHooks --> SectionApproved: pass
    SectionApproved --> NextSection
    NextSection --> SectionBrief
    NextSection --> ManuscriptHooks: all sections complete
    ManuscriptHooks --> DraftSection: targeted rewrite
    ManuscriptHooks --> ReviewRound: pass
    ReviewRound --> DraftSection: request_section_rewrite
    ReviewRound --> ExportReady: R1–R6 pass
```

回退不是失敗，而是 pipeline 的正式 transition。Phase 7 可以指定 sections 與 reason 回到 Phase 5；同一區域回退過多時，系統會要求研究者介入。

## 暫停、恢復與 checkpoint

```mermaid
sequenceDiagram
    participant A as Agent
    participant C as CheckpointManager
    participant W as Workspace
    participant R as Researcher

    A->>C: checkpoint phase / section context
    C->>W: state + draft hash + audit event
    R->>A: pause_pipeline(reason)
    A->>C: persist paused state
    Note over W: Researcher may edit files
    R->>A: resume_pipeline()
    A->>C: compare current hash
    C-->>A: changed sections + suggested revalidation
    A-->>R: resume plan with explicit checks
```

## 自動化的邊界

Autopilot 可以自我審閱 section、執行 hooks、決定一次合理回退；但不能：

- 自動改寫 `CONSTITUTION` 原則。
- 把範文轉成 claim evidence。
- 在缺少全文或資料時捏造結果。
- 跳過 Phase 4 的 manuscript plan 人工核准。
- 在 Phase 7 review gate 未閉環時宣稱 final。

!!! note "管線是可重組的"

    你可以從任一已驗證 checkpoint 繼續，不必每次從 Phase 0 重跑。可拆解、可回退、可重組正是 artifact-centric architecture 的核心。
