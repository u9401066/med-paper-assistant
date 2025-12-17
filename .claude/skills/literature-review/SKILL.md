---
name: literature-review
description: 系統性文獻搜尋、篩選、下載、整理的完整工作流程。觸發：文獻回顧、找論文、搜尋文獻、systematic review、literature search。
---

# 系統性文獻回顧技能

## 概述

完整執行系統性文獻搜尋、篩選、下載、整理的工作流程。

**適用情境**：
- 開始新的研究專案
- 撰寫 Introduction 前的文獻調查
- 系統性回顧的文獻收集階段
- PICO 臨床問題搜尋

**不適用**：
- 只是快速查一篇特定文獻 → 直接用 `search_literature`
- 已經有文獻列表只需整理 → 用 `format_references`

---

## 可用工具

### 🔍 pubmed-search MCP 工具

#### 搜尋類
| 工具 | 說明 | 關鍵參數 |
|------|------|----------|
| `search_literature` | 基本 PubMed 搜尋 | `query`, `limit`, `min_year`, `max_year`, `article_type`, `strategy` |
| `generate_search_queries` | 從主題生成 MeSH + 同義詞材料 | `topic`, `strategy`, `check_spelling` |
| `parse_pico` | 解析 PICO 臨床問題 | `description` 或 `p`, `i`, `c`, `o` |
| `merge_search_results` | 合併多組搜尋結果並去重 | `results_json` |
| `expand_search_queries` | 結果不足時擴展搜尋 | `topic`, `current_results` |

#### 探索類
| 工具 | 說明 | 關鍵參數 |
|------|------|----------|
| `find_related_articles` | 找相似文章（PubMed 演算法） | `pmid` |
| `find_citing_articles` | 找引用此文章的後續研究 | `pmid` |
| `get_article_references` | 取得文章的參考文獻列表 | `pmid` |
| `fetch_article_details` | 取得完整文章資訊 | `pmids` (逗號分隔) |
| `get_citation_metrics` | 取得 iCite 引用指標 (RCR, percentile) | `pmids`, `sort_by`, `min_rcr` |

#### 引用網路類
| 工具 | 說明 | 關鍵參數 |
|------|------|----------|
| `build_citation_tree` | 建立引用關係樹 | `pmid`, `depth`, `direction` |
| `suggest_citation_tree` | 建議是否值得建立引用樹 | `pmid` |

#### Session 管理類
| 工具 | 說明 | 用途 |
|------|------|------|
| `get_session_pmids` | 取得 session 中的 PMID | 不需記住所有 PMID |
| `get_session_summary` | 查看 session 狀態 | 確認快取和搜尋歷史 |
| `get_cached_article` | 從快取取得文章 | 避免重複 API 呼叫 |
| `list_search_history` | 列出搜尋歷史 | 回溯過往搜尋 |

#### 匯出類
| 工具 | 說明 | 關鍵參數 |
|------|------|----------|
| `prepare_export` | 匯出引用格式 | `pmids`, `format` (ris/bibtex/csv) |
| `get_article_fulltext_links` | 取得全文連結 | `pmid` |
| `analyze_fulltext_access` | 分析 PMC 全文可用性 | `pmids` |

---

### 📚 mdpaper MCP 參考文獻工具

#### ⚠️ 儲存文獻規則（關鍵）

| 方法 | 資料來源 | Agent 可篡改？ | 使用時機 |
|------|----------|----------------|----------|
| `save_reference_mcp` | pubmed-search HTTP API | ❌ 不可能 | **永遠優先使用** |
| `save_reference` | Agent 傳遞 | ⚠️ 可能 | 僅當 API 不可用時 fallback |

```
✅ 正確：save_reference_mcp(pmid="12345678", agent_notes="...")
   → mdpaper 直接從 pubmed-search API 取得驗證資料

❌ 錯誤：save_reference(article={從 search 拿到的完整 metadata})
   → Agent 可能修改/幻覺書目資料
```

#### 完整工具列表
| 工具 | 說明 | 優先級 |
|------|------|--------|
| `save_reference_mcp` | MCP-to-MCP 驗證儲存 | **PRIMARY** ✅ |
| `save_reference` | Agent 傳遞 metadata 儲存 | FALLBACK ⚠️ |
| `list_saved_references` | 列出已儲存文獻 | - |
| `search_local_references` | 搜尋本地文獻庫 | - |
| `get_reference_details` | 取得完整引用資訊 | - |
| `check_reference_exists` | 檢查文獻是否已存在 | - |
| `read_reference_fulltext` | 讀取 PDF 全文內容 | - |
| `retry_pdf_download` | 重試 PDF 下載 | - |
| `format_references` | 格式化參考文獻列表 | - |
| `set_citation_style` | 設定引用格式 | - |
| `rebuild_foam_aliases` | 重建 Foam wikilink 別名 | - |

---

## 工作流程

### Phase 0: 環境準備

```
# 確認當前專案
呼叫：get_current_project()

# ⭐ 讀取專案記憶（了解之前做了什麼）
讀取：projects/{slug}/.memory/activeContext.md
讀取：projects/{slug}/.memory/progress.md

# 如果沒有專案，可以先開始探索
呼叫：start_exploration()

# 或建立新專案
呼叫：create_project(name="...", paper_type="...")
```

**詢問用戶**：
- 研究主題是什麼？
- 是否有特定的 PICO 臨床問題？
- 文獻類型限制？（RCT, Review, Meta-Analysis...）
- 時間範圍？

---

### Phase 1: 建立搜尋策略

#### 情境 A：關鍵字搜尋（一般主題）

```
# 取得 MeSH 詞彙和同義詞材料
呼叫：generate_search_queries(
    topic="remimazolam sedation ICU",
    strategy="comprehensive"
)

# 回傳結果包含：
# - corrected_topic: 拼字校正後的主題
# - mesh_terms: MeSH 詞彙及其同義詞
# - suggested_queries: 建議的搜尋語法
```

#### 情境 B：PICO 臨床問題搜尋

```
# Step 1: 解析 PICO
呼叫：parse_pico(
    description="remimazolam 在 ICU 鎮靜比 propofol 好嗎？會減少 delirium 嗎？"
)
# → 回傳：P=ICU patients, I=remimazolam, C=propofol, O=delirium, sedation

# Step 2: 對每個 PICO 元素並行取得 MeSH（同時呼叫！）
呼叫：generate_search_queries(topic="ICU patients")
呼叫：generate_search_queries(topic="remimazolam")
呼叫：generate_search_queries(topic="propofol")
呼叫：generate_search_queries(topic="delirium")

# Step 3: 組合 Boolean 查詢
# High precision: (P) AND (I) AND (C) AND (O)
# High recall: (P) AND (I OR C) AND (O)
```

---

### Phase 2: 並行搜尋執行

```
# 同時執行多組搜尋（並行呼叫！）
呼叫：search_literature(query='"Intensive Care Units"[MeSH] AND remimazolam', limit=50)
呼叫：search_literature(query='remimazolam AND propofol AND sedation', limit=50)
呼叫：search_literature(query='remimazolam[tiab] AND ICU[tiab]', limit=50)

# 合併結果
呼叫：merge_search_results(results_json='[
    {"query_id": "mesh_search", "pmids": ["123", "456"]},
    {"query_id": "keyword_search", "pmids": ["456", "789"]},
    {"query_id": "tiab_search", "pmids": ["789", "012"]}
]')

# 回傳：
# - unique_pmids: 去重後的 PMID 列表
# - high_relevance_pmids: 出現在多次搜尋中的 PMID（更相關）
```

---

### Phase 3: 結果評估與擴展

```
# 如果結果太少（<20篇），擴展搜尋
呼叫：expand_search_queries(topic="...", current_results=15)

# 對重要種子文獻進行引用網路探索
呼叫：find_citing_articles(pmid="12345678")  # 誰引用了這篇？(forward)
呼叫：find_related_articles(pmid="12345678")  # 相似的文章？
呼叫：get_article_references(pmid="12345678")  # 這篇引用了誰？(backward)

# 取得引用指標排序
呼叫：get_citation_metrics(pmids="last", sort_by="relative_citation_ratio", min_rcr=1.0)
```

---

### Phase 4: 篩選與儲存

1. **呈現篩選清單給用戶**
   - 顯示標題、年份、期刊、RCR
   - 標記 high_relevance_pmids

2. **儲存選中的文獻**

```
# ✅ PRIMARY：使用 MCP-to-MCP 驗證
呼叫：save_reference_mcp(
    pmid="12345678",
    project="my-project",  # 可選，預設使用當前專案
    agent_notes="Key paper on remimazolam pharmacokinetics"
)

# ⚠️ FALLBACK：僅當 pubmed-search API 不可用時
呼叫：save_reference(
    article={完整 metadata dict},
    project="my-project"
)
```

3. **驗證儲存結果**

```
呼叫：list_saved_references(project="my-project")
呼叫：search_local_references(keywords="remimazolam")
```

---

### Phase 5: 輸出與匯出

```
# 格式化參考文獻列表
呼叫：format_references(style="vancouver")  # 或 apa, nature

# 匯出到其他工具
呼叫：prepare_export(pmids="last", format="ris")  # EndNote, Zotero
呼叫：prepare_export(pmids="12345,67890", format="bibtex")  # LaTeX

# 檢查全文可用性
呼叫：analyze_fulltext_access(pmids="last")
```

---

### Phase 6: ⭐ 更新專案記憶

**關鍵：每次文獻回顧後必須更新！**

```
# 更新 activeContext.md - 記錄搜尋策略和發現
寫入：projects/{slug}/.memory/activeContext.md

內容更新：
- Current Focus: 文獻回顧進度
- Recent Decisions: 選擇哪些搜尋策略、篩選標準
- Key References: 找到的關鍵文獻及其重要性
- Memo / Notes: Agent 對文獻整體的觀察

# 更新 progress.md - 勾選完成項目
寫入：projects/{slug}/.memory/progress.md

勾選：
- [x] Literature review
- [x] Identify research gap
```

---

## 決策點

| 時機 | 問題 | 預設選擇 | 備註 |
|------|------|----------|------|
| Phase 0 | 建立專案 or 探索模式？ | 先探索 | 熟悉文獻後再建專案 |
| Phase 1 | 關鍵字 or PICO？ | 判斷問題類型 | 比較性問題用 PICO |
| Phase 2 | 幾組並行查詢？ | 3-5 組 | 涵蓋 MeSH + 自由詞 |
| Phase 2 | 結果數量合理嗎？ | 50-300 篇繼續 | <20 需擴展，>500 需限縮 |
| Phase 3 | 要做引用網路探索？ | 系統性回顧需要 | 非系統性可跳過 |
| Phase 4 | 篩選方式？ | <30 篇逐篇確認 | >30 篇用 RCR 排序 |
| Phase 4 | API 可用嗎？ | 用 `save_reference_mcp` | 否則 fallback |

---

## 輸出產物

| 產物 | 位置 | 說明 |
|------|------|------|
| 儲存的文獻 | `project/references/{PMID}/` | 含 metadata.json, content.md, PDF |
| 搜尋策略 | `search_strategy.json` | 可重複使用的搜尋條件 |
| 參考文獻列表 | 匯出的 RIS/BibTeX | 匯入到 EndNote/Zotero |

---

## 完整範例：PICO 搜尋工作流

**用戶問**：「remimazolam 在 ICU 鎮靜比 propofol 好嗎？」

```
# 1. 解析 PICO
parse_pico(description="remimazolam 在 ICU 鎮靜比 propofol 好嗎")
→ P: ICU patients
   I: remimazolam  
   C: propofol
   O: sedation outcomes

# 2. 並行取得各元素 MeSH（4個同時呼叫）
generate_search_queries(topic="ICU patients")
generate_search_queries(topic="remimazolam")
generate_search_queries(topic="propofol")
generate_search_queries(topic="sedation")

# 3. 組合搜尋語法
High precision query:
("Intensive Care Units"[MeSH] OR "Critical Care"[MeSH]) 
AND (remimazolam OR CNS-7056) 
AND ("Propofol"[MeSH] OR propofol) 
AND ("Conscious Sedation"[MeSH] OR sedation)
AND therapy[filter]

# 4. 執行搜尋
search_literature(query="...", limit=100)

# 5. 取得詳細資訊和引用指標
fetch_article_details(pmids="last")
get_citation_metrics(pmids="last", sort_by="relative_citation_ratio")

# 6. 篩選後儲存
save_reference_mcp(pmid="38123456", agent_notes="RCT comparing remimazolam vs propofol in ICU")
save_reference_mcp(pmid="38234567", agent_notes="Meta-analysis of sedation outcomes")
```

---

## 常見問題

### Q: 搜尋結果太多怎麼辦？
A: 使用更精確的 MeSH 詞彙、加上 article_type 限制（如 "Review", "Clinical Trial"）、縮小年份範圍。

### Q: 搜尋結果太少怎麼辦？
A: 使用 `expand_search_queries`、移除 Comparator 限制、擴大年份範圍、使用 `find_related_articles` 探索。

### Q: 要不要用 `save_reference` 還是 `save_reference_mcp`？
A: **永遠優先用 `save_reference_mcp`**。只有當 pubmed-search HTTP API 不可用（返回錯誤）時，才 fallback 到 `save_reference`。

### Q: Session 工具有什麼用？
A: 搜尋結果會自動暫存在 session 中，使用 `get_session_pmids(search_index=-1)` 可以取回最近搜尋的 PMID，不需要記住所有編號。

---

## 相關技能

- `concept-development` - 文獻回顧後發展研究概念
- `parallel-search` - 並行搜尋的詳細說明與範例
