---
title: MedPaper Assistant Wiki
description: 從研究問題、證據蒐集到可稽核稿件與發布成品的跨 Agent 學術寫作系統。
hide:
  - toc
---

<div class="wiki-hero" markdown>

<div class="wiki-hero__copy" markdown>

<span class="wiki-kicker">PRODUCTION ACADEMIC WRITING HARNESS</span>

# 把學術寫作變成可重現的工程流程

MedPaper Assistant 讓 Claude Code、Codex、OpenClaw 與 VS Code Copilot 共用同一套研究契約：文獻必須可追溯、草稿必須經過 gate、每一輪修訂都留下 audit trail。

[五分鐘開始](wiki/quickstart.md){ .md-button .md-button--primary }
[探索完整架構](wiki/harness-architecture.md){ .md-button }

</div>

<div class="wiki-hero__visual" markdown>

![MedPaper Assistant system map](assets/wiki-system-map.svg){ loading=lazy }

</div>

</div>

<div class="wiki-stats" markdown>

<div><strong>118</strong><span>Full MCP tools</span></div>
<div><strong>13</strong><span>正式產出 profiles</span></div>
<div><strong>79</strong><span>品質檢查</span></div>
<div><strong>3</strong><span>演進治理層</span></div>

</div>

## 一張圖理解整個 repo

```mermaid
flowchart LR
    Human([研究者]) --> Agent{Claude / Codex<br/>OpenClaw / Copilot}
    Agent --> Contract[共用 writing contract]
    Contract --> MCP[mdpaper MCP<br/>118 tools]
    MCP --> Evidence[PubMed + full text<br/>Zotero + local sources]
    MCP --> Project[(Project workspace)]
    Project --> Draft[Draft + assets]
    Draft --> Hooks{79 quality checks}
    Hooks -->|revise| Draft
    Hooks -->|pass| Export[DOCX / PDF / wiki]
    Hooks --> Audit[(Audit + telemetry<br/>checkpoints + memory)]
    Audit --> Contract

    classDef actor fill:#0f766e,color:#fff,stroke:#0f766e
    classDef gate fill:#f59e0b,color:#17202a,stroke:#d97706
    classDef store fill:#e6fffa,color:#134e4a,stroke:#14b8a6
    class Human,Agent actor
    class Hooks gate
    class Evidence,Project,Audit store
```

系統不是「丟一個 prompt，拿一篇文章」。它把研究拆成可以暫停、回退、審閱與重現的 artifact pipeline；Agent 可以更換，但 evidence boundary 與品質 gate 不變。

## 依你的角色開始

<div class="wiki-paths" markdown>

<div class="wiki-path" markdown>

### 我想寫論文

從研究概念、文獻、段落草稿一路走到 Word/PDF，了解每一個人工與自動 gate。

[研究管線總覽 →](wiki/research-pipeline.md)

</div>

<div class="wiki-path" markdown>

### 我想理解架構

從 DDD、MCP facade、filesystem artifacts 到跨 Agent discovery，一次掌握系統邊界。

[Harness 架構 →](wiki/harness-architecture.md)

</div>

<div class="wiki-path" markdown>

### 我想開發或維運

了解測試矩陣、bundle mirror、Pages、VSIX、PyPI 與 release gates。

[開發與發布 →](wiki/development-and-release.md)

</div>

</div>

## 從問題到可發布成品

```mermaid
stateDiagram-v2
    [*] --> Exploration
    Exploration --> Project: concept + scope 成形
    Project --> EvidenceReady: 搜尋、全文、來源角色
    EvidenceReady --> PlanApproved: manuscript plan gate
    PlanApproved --> Drafting
    Drafting --> Reviewing: section + manuscript hooks
    Reviewing --> Drafting: rewrite / regression
    Reviewing --> Exported: review gates pass
    Exported --> Audited: D1-D9 meta-learning
    Audited --> Published
    Published --> [*]
```

每個箭頭都有對應的 MCP action、檔案產物與驗證證據。從 [Auto-Paper 指南](auto-paper-guide.md) 可查看完整 phase 契約；從 [品質與稽核](wiki/quality-and-audit.md) 可查看 gate 的實作位置。

## 這個 wiki 怎麼讀

```mermaid
flowchart TB
    Start[首頁] --> Use[使用者路線]
    Start --> Build[開發者路線]
    Use --> Pipeline[研究管線]
    Use --> Evidence[證據與引用]
    Use --> Outputs[13 種產出]
    Build --> Architecture[系統架構]
    Build --> Quality[品質與稽核]
    Build --> Ops[開發與發布]
    Pipeline & Evidence & Outputs --> Atlas[視覺圖譜]
    Architecture & Quality & Ops --> Atlas
```

左側導覽是主題式 wiki；右側目錄是單頁索引；頂部搜尋可同時檢索中英文術語。每一頁都盡量先給總覽圖，再連到實作細節與原始設計文件。

!!! info "目前穩定版本"

    `v0.9.0` 提供 13 種正式學術產出、110 個 base constraints、跨 Agent harness、exemplar audit、完整 MCP smoke 與可安裝 VSIX。版本與 artifact 請見 [GitHub Releases](https://github.com/u9401066/med-paper-assistant/releases)。
