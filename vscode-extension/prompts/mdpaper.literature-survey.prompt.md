---
description: "📚 literature-survey - 系統性文獻調查"
---

# 系統性文獻調查

📖 **Capability 類型**: 高層編排
📖 **編排 Skills**: parallel-search → literature-review → reference-management

---

## 🎯 此 Capability 的目標

進行全面、系統性的文獻搜尋，確保：

- 不遺漏重要文獻
- 多角度搜尋覆蓋
- 結果可重現（記錄搜尋策略）

---

## Phase 1: 定義搜尋範圍 `scope`

### Step 1.1: 收集搜尋需求

```
詢問用戶：
1. 研究問題是什麼？
2. PICO 元素（如適用）
   - P: Population（研究對象）
   - I: Intervention（介入措施）
   - C: Comparator（比較對象）
   - O: Outcome（結果指標）
3. 年份範圍
4. 語言限制
5. 文章類型（RCT only? Review? All?）
```

### Step 1.2: 設定搜尋策略

```
mcp_mdpaper_configure_search_strategy(
    keywords=["..."],
    exclusions=["..."],
    year_range=[2015, 2024],
    article_types=["Clinical Trial", "Meta-Analysis"]
)
```

---

## Phase 2: 多維度搜尋 `search`

📖 Skill: `.claude/skills/parallel-search/SKILL.md`

### Step 2.1: 生成搜尋語法

```
# PICO 搜尋（如適用）
mcp_pubmed-search_parse_pico(description="...")

# 生成多組查詢
mcp_pubmed-search_generate_search_queries(
    topic="...",
    strategy="comprehensive"
)
→ 返回 5 組不同角度的搜尋語法
```

### Step 2.2: 並行執行搜尋

```
# Agent 並行呼叫（同時執行！）
mcp_pubmed-search_search_literature(query="Query 1", limit=100)
mcp_pubmed-search_search_literature(query="Query 2", limit=100)
mcp_pubmed-search_search_literature(query="Query 3", limit=100)
mcp_pubmed-search_search_literature(query="Query 4", limit=100)
mcp_pubmed-search_search_literature(query="Query 5", limit=100)
```

### Step 2.3: 合併結果

```
mcp_pubmed-search_merge_search_results(results_json='[...]')
→ 去重
→ 標記高相關性（出現在多組搜尋中）
```

---

## Phase 3: 結果評估與擴展 `evaluate`

### Step 3.1: 評估結果數量

| 結果數  | 行動       |
| ------- | ---------- |
| < 20    | 擴展搜尋   |
| 20-100  | 適中，繼續 |
| 100-300 | 需要篩選   |
| > 300   | 縮小範圍   |

### Step 3.2: 擴展搜尋（如需要）

```
mcp_pubmed-search_expand_search_queries(
    topic="...",
    expansion_type="synonyms"  # 或 "related", "broader"
)
```

### Step 3.3: 引用網絡探索

```
# 從種子文獻擴展
mcp_pubmed-search_find_related_articles(pmid="...")    # 相似文獻
mcp_pubmed-search_find_citing_articles(pmid="...")     # 引用此文的
mcp_pubmed-search_get_article_references(pmid="...")   # 此文引用的
```

---

## Phase 4: 篩選與品質評估 `filter`

### Step 4.1: 取得引用指標

```
mcp_pubmed-search_get_citation_metrics(
    pmids="last",
    sort_by="relative_citation_ratio",
    min_rcr=1.0
)
```

### Step 4.2: 呈現篩選清單

```
向用戶呈現：
- 標題、年份、期刊
- RCR 分數
- 是否有全文
- 高相關性標記

用戶選擇要保留的文獻
```

---

## Phase 5: 儲存與整理 `save`

📖 Skill: `.claude/skills/reference-management/SKILL.md`

### Step 5.1: 儲存選中文獻

```
# ⚠️ 使用 MCP-to-MCP 驗證
for pmid in selected_pmids:
    mcp_mdpaper_save_reference_mcp(
        pmid=pmid,
        agent_notes="..."
    )
```

### Step 5.2: 匯出搜尋策略

```
記錄到專案：
- 搜尋日期
- 使用的查詢語法
- 各查詢的結果數
- 最終納入數量
```

### Step 5.3: 匯出文獻清單

```
mcp_mdpaper_format_references(
    pmids="...",
    style="vancouver"
)

mcp_pubmed-search_prepare_export(
    pmids="last",
    format="ris"  # 或 "bibtex", "csv"
)
```

---

## 📋 PRISMA 檢查清單

如果是系統性回顧，記錄：

```markdown
## 搜尋策略記錄

- 搜尋日期: 2025-12-22
- 資料庫: PubMed

### 搜尋語法

1. Query 1: "..." → N 篇
2. Query 2: "..." → N 篇
   ...

### 篩選流程

- 資料庫搜尋: N 篇
- 去除重複: N 篇
- 標題/摘要篩選: N 篇
- 全文篩選: N 篇
- 最終納入: N 篇
```

---

## ⏸️ 中斷與恢復

搜尋結果暫存在 session 中：

```
mcp_pubmed-search_get_session_pmids(search_index=-1)  # 最近搜尋
mcp_pubmed-search_get_session_summary()               # session 狀態
```
