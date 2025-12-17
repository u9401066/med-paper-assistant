---
name: parallel-search
description: 使用多組關鍵字並行搜尋，提高文獻覆蓋率。觸發：並行搜尋、parallel search、批量搜尋、擴展搜尋。
---

# 並行文獻搜尋技能

## 概述

利用 Agent 的並行呼叫能力來加速文獻搜尋，提高覆蓋率。

**核心概念**：
1. 預設搜尋策略（日期、排除詞、文章類型）
2. 策略工具返回多組搜尋語法（自動整合策略設定）
3. Agent 並行呼叫搜尋工具
4. 合併工具整合結果

## 使用工具

| 工具 | 用途 |
|------|------|
| `configure_search_strategy` | 設定搜尋策略（日期、排除詞、文章類型）|
| `get_search_strategy` | 查看目前的搜尋策略 |
| `generate_search_queries` | 根據主題生成多組搜尋語法（**自動整合策略**）|
| `search_literature` | 執行單一搜尋（可並行呼叫多次）|
| `merge_search_results` | 合併多個搜尋結果並去重 |
| `expand_search_queries` | **擴展搜尋**：結果不夠時生成更多查詢 |

## 工作流程

### Step 0: （可選）設定搜尋策略

```
呼叫：configure_search_strategy(criteria_json={
    "date_range": "2019-2024",
    "exclusions": ["animal", "review"],
    "article_types": ["Clinical Trial", "Randomized Controlled Trial"]
})
```

### Step 1: 生成搜尋策略

```
呼叫：generate_search_queries(
    topic="remimazolam ICU sedation",
    strategy="comprehensive",
    use_saved_strategy=True
)
```

返回 5 組 queries，策略已自動整合。

### Step 2: Agent 並行執行搜尋

Agent 看到 instruction 後，會並行呼叫：

```xml
<parallel_tool_calls>
  <tool_call id="1">
    <name>search_literature</name>
    <args>{"query": "...", "limit": 20}</args>
  </tool_call>
  <tool_call id="2">
    <name>search_literature</name>
    <args>{"query": "...", "limit": 20}</args>
  </tool_call>
  <!-- ... 更多並行呼叫 ... -->
</parallel_tool_calls>
```

### Step 3: 合併結果

```
呼叫：merge_search_results(results_json='[
  {"query_id": "q1_title", "pmids": ["123", "456"]},
  {"query_id": "q2_tiab", "pmids": ["456", "012"]}
]')
```

返回去重後的結果，標記高相關性文獻（出現在多個搜尋中）。

## 迭代式搜尋擴展

當初始搜尋結果不夠時：

```
Phase 1: 初始搜尋
  → generate_search_queries(topic="...")
  → 並行執行 5 組查詢
  → merge_search_results → 只找到 15 篇，不夠！

Phase 2: 擴展搜尋
  → expand_search_queries(
      topic="...",
      existing_query_ids="q1,q2,q3,q4,q5",
      expansion_type="synonyms"
    )
  → 並行執行新查詢
  → merge_search_results → 共 32 篇

Phase 3: 如果還不夠
  → expand_search_queries(..., expansion_type="related")
  → 繼續...
```

### 擴展類型選擇指南

| 情況 | expansion_type | 預期效果 |
|------|----------------|----------|
| 擔心遺漏不同術語 | `synonyms` | sedation → conscious sedation |
| 想找類似比較研究 | `related` | remimazolam → propofol |
| 結果太少 | `broader` | 使用 OR、移除限制 |
| 結果太多 | `narrower` | 限定 RCT、最近 2 年 |

## 流程圖

```
generate_search_queries(topic)
        │ 5 組查詢
        ▼
並行執行 search_literature
        │
        ▼
merge_search_results
        │
        ▼
┌───────┴───────┐
│ 結果足夠嗎？  │
└───────┬───────┘
        │ No
        ▼
expand_search_queries(type=...)
        │ 新查詢
        ▼
並行執行新查詢
        │
        ▼
merge（含所有結果）
        │
        └──→ 重複直到足夠
```

## 優點

1. **更快**：多個搜尋同時執行
2. **更全面**：不同角度的關鍵字組合
3. **可追蹤**：知道每篇文獻來自哪個搜尋
4. **可重現**：策略被記錄下來
5. **策略整合**：日期/排除詞自動套用

## 相關技能

- `literature-review` - 完整的文獻回顧流程
- `concept-development` - 搜尋後發展概念
