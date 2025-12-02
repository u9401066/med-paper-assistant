# Skill: 並行文獻搜尋

> 使用多組關鍵字並行搜尋，提高文獻覆蓋率

## 概述

這個技能展示如何利用 Agent 的並行呼叫能力來加速文獻搜尋。

**核心概念**：
1. 預設搜尋策略（日期、排除詞、文章類型）
2. 策略 tool 返回多組搜尋語法（自動整合策略設定）
3. Agent 並行呼叫搜尋 tool
4. 合併 tool 整合結果

## 使用工具

| 工具 | 用途 |
|------|------|
| `configure_search_strategy` | 設定搜尋策略（日期範圍、排除詞、文章類型等）|
| `get_search_strategy` | 查看目前的搜尋策略 |
| `generate_search_queries` | 根據主題生成多組搜尋語法（**自動整合策略**）|
| `search_literature` | 執行單一搜尋（可並行呼叫多次）|
| `merge_search_results` | 合併多個搜尋結果並去重 |
| `expand_search_queries` | **擴展搜尋**：結果不夠時生成更多查詢 |

## 工作流程

### Step 0: （可選）設定搜尋策略

```
呼叫：configure_search_strategy(criteria_json={
    "date_range": "2019-2024",          # 限制 2019-2024 年
    "exclusions": ["animal", "review"], # 排除動物實驗和 review
    "article_types": ["Clinical Trial", "Randomized Controlled Trial"],
    "min_sample_size": 20
})

返回：Strategy saved successfully
```

### Step 1: 生成搜尋策略

```
呼叫：generate_search_queries(
    topic="remimazolam ICU sedation",
    strategy="comprehensive",  # or "focused", "exploratory"
    use_saved_strategy=True    # 預設為 True，自動套用已儲存策略
)

返回：
{
  "queries": [
    {"id": "q1", "query": "(remimazolam ICU sedation)[Title] AND (2019:2024[dp]) AND (\"Clinical Trial\"[Publication Type] OR \"Randomized Controlled Trial\"[Publication Type]) NOT \"animal\" NOT \"review\"", ...},
    {"id": "q2", "query": "(remimazolam ICU sedation)[Title/Abstract] AND (2019:2024[dp]) ...", ...},
    ...
  ],
  "applied_strategy": {
    "date_range": "2019-2024",
    "exclusions": ["animal", "review"],
    "article_types": ["Clinical Trial", "Randomized Controlled Trial"],
    "note": "已儲存的搜尋策略已自動整合到查詢中"
  },
  "instruction": "請並行執行這些搜尋，然後呼叫 merge_search_results 合併結果"
}
```

### Step 2: Agent 並行執行搜尋

Agent 看到 instruction 後，會這樣做：

```xml
<parallel_tool_calls>
  <tool_call id="1">
    <name>search_literature</name>
    <args>{"query": "(remimazolam ICU sedation)[Title] AND ...", "limit": 20}</args>
  </tool_call>
  <tool_call id="2">
    <name>search_literature</name>
    <args>{"query": "(remimazolam ICU sedation)[Title/Abstract] AND ...", "limit": 20}</args>
  </tool_call>
  <!-- ... 更多並行呼叫 ... -->
</parallel_tool_calls>
```

### Step 3: 合併結果

```
呼叫：merge_search_results(
    results_json='[
      {"query_id": "q1_title", "pmids": ["123", "456", "789"]},
      {"query_id": "q2_tiab", "pmids": ["456", "012", "345"]},
      {"query_id": "q3_and", "pmids": ["789", "678", "901"]},
      {"query_id": "q4_partial", "pmids": ["234", "567"]}
    ]'
)

返回：
{
  "total_unique": 10,
  "total_with_duplicates": 11,
  "duplicates_removed": 1,
  "by_query": {...},
  "appeared_in_multiple_queries": {
    "count": 2,
    "pmids": ["456", "789"],
    "note": "這些文獻被多個搜尋策略找到，可能更相關"
  },
  "unique_pmids": [...]
}
```

## 策略整合說明

### 工具分工

| 工具 | 職責 |
|------|------|
| `configure_search_strategy` | **設定持久化策略**：日期範圍、排除詞、文章類型 |
| `generate_search_queries` | **生成多角度查詢**：自動整合已儲存策略到每個查詢 |
| `search_literature` | **執行搜尋**：直接用整合好的 query |

### 避免重複的設計

```
configure_search_strategy()  ─────┐
                                  │
                                  ▼
                         [StrategyManager 持久化]
                                  │
                                  │ 自動讀取
                                  ▼
generate_search_queries(use_saved_strategy=True)
                                  │
                                  │ 策略已整合到 query
                                  ▼
search_literature(query=...)  ← 直接用整合好的 query
```

## 優點

1. **更快**：4 個搜尋同時執行
2. **更全面**：不同角度的關鍵字組合
3. **可追蹤**：知道每篇文獻來自哪個搜尋
4. **可重現**：策略被記錄下來
5. **策略整合**：日期/排除詞自動套用到所有查詢

## 進階：迭代式搜尋擴展

當初始搜尋結果不夠時，使用 `expand_search_queries` 擴展：

```
Phase 1: 初始搜尋
  → generate_search_queries(topic="remimazolam ICU sedation")
  → 並行執行 5 組查詢
  → merge_search_results → 只找到 15 篇，不夠！

Phase 2: 擴展搜尋
  → expand_search_queries(
      topic="remimazolam ICU sedation",
      existing_query_ids="q1_title,q2_tiab,q3_and,q4_partial,q5_mesh",
      expansion_type="synonyms"  # 同義詞擴展
    )
  → 返回 4 組新查詢（使用 sedation → conscious sedation 等同義詞）
  → 並行執行新查詢
  → merge_search_results（包含所有結果）→ 共 32 篇

Phase 3: 如果還不夠，繼續擴展
  → expand_search_queries(..., expansion_type="related")
  → 返回相關概念查詢（propofol, dexmedetomidine 比較研究）
  → 並行執行 → 合併 → 共 58 篇
```

### 擴展類型選擇指南

| 情況 | 使用 expansion_type | 預期效果 |
|------|---------------------|----------|
| 擔心遺漏不同術語的文獻 | `synonyms` | sedation → conscious sedation, procedural sedation |
| 想找類似主題的比較研究 | `related` | remimazolam → propofol, midazolam |
| 結果太少，需要更多 | `broader` | 使用 OR 搜尋、移除日期限制 |
| 結果太多，想精選高品質 | `narrower` | 限定 RCT、Meta-analysis、最近 2 年 |

### 完整迭代流程圖

```
                    ┌─────────────────────┐
                    │ generate_search_    │
                    │ queries(topic)      │
                    └─────────┬───────────┘
                              │ 5 組查詢
                              ▼
                    ┌─────────────────────┐
                    │ 並行執行            │
                    │ search_literature   │
                    └─────────┬───────────┘
                              │
                              ▼
                    ┌─────────────────────┐
                    │ merge_search_       │
                    │ results             │
                    └─────────┬───────────┘
                              │
                              ▼
                    ┌─────────────────────┐
               ┌────┤ 結果足夠嗎？        │
               │    └─────────┬───────────┘
               │              │ No
               │              ▼
               │    ┌─────────────────────┐
               │    │ expand_search_      │
               │    │ queries(type=...)   │
               │    └─────────┬───────────┘
               │              │ 新查詢
               │              ▼
               │    ┌─────────────────────┐
               │    │ 並行執行新查詢      │
               │    └─────────┬───────────┘
               │              │
               │              ▼
               │    ┌─────────────────────┐
               │    │ merge（含所有結果） │
               │    └─────────┬───────────┘
               │              │
               │              └─────────────┐
               │                            │
               │ Yes                        │ 重複直到足夠
               ▼                            │
        ┌──────────────┐                    │
        │ 完成搜尋     │ ◄──────────────────┘
        └──────────────┘
```

## Copilot Instructions 整合

在 instructions 中加入：

```markdown
## 並行搜尋模式

當 `generate_search_queries` 返回多組 queries 時：
1. **並行呼叫** `search_literature` 對每個 query
2. 收集所有結果
3. 呼叫 `merge_search_results` 合併
4. **如果結果不夠**：
   - 呼叫 `expand_search_queries` 生成更多查詢
   - 並行執行新查詢
   - 再次 merge（包含所有結果）
   - 重複直到足夠

這是利用並行能力加速搜尋的標準模式。
```