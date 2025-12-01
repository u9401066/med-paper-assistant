# Skill: 並行文獻搜尋

> 使用多組關鍵字並行搜尋，提高文獻覆蓋率

## 概述

這個技能展示如何利用 Agent 的並行呼叫能力來加速文獻搜尋。

**核心概念**：
1. 策略 tool 返回多組搜尋語法
2. Agent 並行呼叫搜尋 tool
3. 合併 tool 整合結果

## 使用工具

| 工具 | 用途 |
|------|------|
| `generate_search_queries` | 根據主題生成多組搜尋語法 |
| `search_literature` | 執行單一搜尋（可並行呼叫多次）|
| `merge_search_results` | 合併多個搜尋結果並去重 |

## 工作流程

### Step 1: 生成搜尋策略

```
呼叫：generate_search_queries(
    topic="remimazolam ICU sedation",
    strategy="comprehensive"  # or "focused", "exploratory"
)

返回：
{
  "queries": [
    {"id": "q1", "query": "remimazolam[Title] AND ICU[Title/Abstract]", "purpose": "精確匹配"},
    {"id": "q2", "query": "remimazolam AND intensive care unit", "purpose": "標準搜尋"},
    {"id": "q3", "query": "remimazolam AND critical care AND sedation", "purpose": "擴展概念"},
    {"id": "q4", "query": "(remimazolam OR CNS7056) AND mechanical ventilation", "purpose": "藥物別名+相關情境"}
  ],
  "instruction": "請並行執行這些搜尋，然後呼叫 merge_search_results 合併結果"
}
```

### Step 2: Agent 並行執行搜尋

Agent 看到 instruction 後，會這樣做：

```xml
<parallel_tool_calls>
  <tool_call id="1">
    <name>search_literature</name>
    <args>{"query": "remimazolam[Title] AND ICU[Title/Abstract]", "query_id": "q1"}</args>
  </tool_call>
  <tool_call id="2">
    <name>search_literature</name>
    <args>{"query": "remimazolam AND intensive care unit", "query_id": "q2"}</args>
  </tool_call>
  <tool_call id="3">
    <name>search_literature</name>
    <args>{"query": "remimazolam AND critical care AND sedation", "query_id": "q3"}</args>
  </tool_call>
  <tool_call id="4">
    <name>search_literature</name>
    <args>{"query": "(remimazolam OR CNS7056) AND mechanical ventilation", "query_id": "q4"}</args>
  </tool_call>
</parallel_tool_calls>
```

### Step 3: 合併結果

```
呼叫：merge_search_results(
    results=[
      {"query_id": "q1", "pmids": ["123", "456", "789"]},
      {"query_id": "q2", "pmids": ["456", "012", "345"]},
      {"query_id": "q3", "pmids": ["789", "678", "901"]},
      {"query_id": "q4", "pmids": ["234", "567"]}
    ]
)

返回：
{
  "total_unique": 10,
  "by_query": {
    "q1": 3,
    "q2": 3,
    "q3": 3,
    "q4": 2
  },
  "overlap_analysis": {
    "appeared_in_multiple": ["456", "789"],
    "unique_to_q1": ["123"],
    "unique_to_q4": ["234", "567"]
  },
  "merged_pmids": ["123", "456", "789", "012", "345", "678", "901", "234", "567"]
}
```

## 優點

1. **更快**：4 個搜尋同時執行
2. **更全面**：不同角度的關鍵字組合
3. **可追蹤**：知道每篇文獻來自哪個搜尋
4. **可重現**：策略被記錄下來

## 進階：自適應搜尋

```
Phase 1: 初始搜尋
  → 並行執行 4 組基本搜尋
  → 發現某些方向結果很少

Phase 2: 補充搜尋（Agent 決定）
  → 對結果少的方向，生成新的搜尋語法
  → 再次並行執行

Phase 3: 合併所有結果
```

## Copilot Instructions 整合

在 instructions 中加入：

```markdown
## 並行搜尋模式

當 `generate_search_queries` 返回多組 queries 時：
1. **並行呼叫** `search_literature` 對每個 query
2. 收集所有結果
3. 呼叫 `merge_search_results` 合併

這是利用並行能力加速搜尋的標準模式。
```
