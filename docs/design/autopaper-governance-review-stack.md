# Auto-Paper Governance Review Stack

> 目的：把 Auto-Paper 的 review 從單一「檢查有沒有過」提升成可治理、可審計、可演進的多層架構。

---

## 1. 為什麼需要 Review Stack

Auto-Paper 現在已經有 phase gate、writing hooks、review hooks、tool health、hook effectiveness，但它們分別解不同問題。

如果不把它們整理成一個正式 review stack，就會出現三種常見誤判：

1. 以為通過 hook 就代表題目值得做
2. 以為新增 hook 就等於品質變好
3. 以為文件寫了規格就等於系統已經有該能力

因此 review 必須分層，而不是混成一種 generic review。

---

## 2. 五層 Review

| 層級 | 名稱                   | 核心問題                                | 主要輸出                     |
| ---- | ---------------------- | --------------------------------------- | ---------------------------- |
| L1   | Concept Review         | 題目值不值得做、能不能支撐後續寫作      | `.audit/concept-review.yaml` |
| L2   | Reuse Review           | 這是不是在重造輪子                      | 設計文件中的 reuse gate 決策 |
| L3   | Code / Pipeline Review | pipeline 是否正確、可恢復、不可繞過     | 測試、gate、validator        |
| L4   | Hook Portfolio Review  | hook 值不值得存在、是否重複、是否高誤報 | 版本/季度盤點報告            |
| L5   | Failure Review         | 這次為什麼失敗、下次怎麼避免            | `.audit/failure-review.yaml` |

---

## 3. Layer 1: Concept Review

### 3.1 重要原則

`concept.md` 不應假設一定由 Agent 撰寫。

可能來源：

- human-authored
- agent-authored
- hybrid

因此 Concept Review 的責任不是「重寫 concept」，而是把 concept 正規化成固定欄位，供 Phase 4 與 Phase 5 消費。

### 3.2 Gate 條件

Concept Review 至少要回答：

- canonical research question 是什麼
- 哪些 claim 是必要的
- 每個 claim 需要什麼 evidence
- 哪些 figure/table/analysis 是必要 obligations
- 哪些風險仍未解決

若這些欄位缺失，應視為 `revise` 或 `blocked`，而不是直接進入 manuscript planning。

---

## 4. Layer 2: Reuse Review

### 4.1 觸發時機

以下情況必須做 Reuse Review：

- 新增 MCP tool
- 新增 hook / gate
- 新增 prompt / skill
- 新增 dashboard 或 extension 功能，但背後已有相似 pipeline 能力

### 4.2 強制問題

必須回答：

- 既有 internal capability 是什麼
- 既有 external capability 是什麼
- 為什麼 wrapper / config 不夠
- 為什麼真的需要新增 primitive
- 舊能力如何 merge / retire

### 4.3 預設決策

若無法證明新 primitive 必要，預設回到重用方案。

---

## 5. Layer 3: Code / Pipeline Review

這一層不是 style review，而是 correctness review。

重點包括：

- phase gate 是否可被繞過
- schema 變更是否向後相容
- checkpoint / recovery 是否能恢復
- asset / export / review path 是否一致
- Windows / macOS / Linux 是否一致

這一層主要依靠：

- tests/
- `PipelineGateValidator`
- `ReviewHooksEngine`
- CI cross-platform smoke

---

## 6. Layer 4: Hook Portfolio Review

### 6.1 目的

避免 hook 數量增加，但總體品質沒有提升。

### 6.2 資料來源

- `HookEffectivenessTracker`
- `ToolInvocationStore` telemetry
- review rounds
- gate failures

### 6.3 盤點指標

最少應統計：

- `trigger_rate`
- `fix_rate`
- `false_positive_rate`
- `overlap_score`
- `token_cost`
- `phase_value`

### 6.4 決策分類

- keep
- tune
- merge
- retire

---

## 7. Layer 5: Failure Review

### 7.1 目的

把失敗從 log 提升成 taxonomy。

### 7.2 類型

- `concept_failure`
- `pipeline_failure`
- `review_failure`
- `tool_failure`
- `export_failure`

### 7.3 最小欄位

- `failure_id`
- `failure_type`
- `phase`
- `blocking`
- `symptom`
- `root_cause`
- `detection_source`
- `affected_artifacts`
- `recovery_action`
- `preventive_action`

---

## 8. Structured Output Policy

不應該把所有輸出都變成同一格式。

### 8.1 建議分工

| 輸出類型                                    | 格式     | 原因                          |
| ------------------------------------------- | -------- | ----------------------------- |
| gate / audit / tool health / review summary | TOON     | agent 反覆消費，重 token 效率 |
| spec artifacts                              | YAML     | 可版本控制、可人工編輯        |
| README / long-form guide                    | Markdown | 人類可讀性優先                |

### 8.2 統一命名族群

- `TOON-GATE`
- `TOON-AUDIT`
- `TOON-HEALTH`
- `YAML-SPEC`

---

## 9. 目前狀態判定

截至目前，repo 的真實狀態應判定為：

- `Review Hooks`: 已有相當完整的 code-enforced 基礎
- `Tool Health`: 已有 TOON 輸出與 telemetry 支撐
- `Concept Review`: 尚未正式落地為獨立 artifact
- `Reuse Review`: 尚未成為硬 gate
- `Hook Portfolio Review`: 有資料來源，但尚未形成正式盤點流程
- `Failure Review`: 有零散 failure records，但尚未形成 taxonomy artifact

因此接下來的重點不是再加更多 hook，而是把 L1、L2、L4、L5 變成真正可執行的治理層。
