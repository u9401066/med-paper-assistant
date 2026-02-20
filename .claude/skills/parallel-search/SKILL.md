# Parallel Search Skill

觸發：並行搜尋、parallel search、批量搜尋、多組搜尋、廣泛搜尋、comprehensive search

使用 pubmed-search MCP 多次搜尋 + 合併結果，提高覆蓋率。

---

## 工具

| 階段 | Tool | 說明 |
|------|------|------|
| 搜尋 | `search_literature(query, limit)` | 每組關鍵字獨立搜尋 |
| 結果 | `merge_search_results(search_indices)` | 合併 + 去重 |
| Session | `get_session_pmids(search_index)` | 取回暫存 PMIDs |
| Session | `list_search_history()` | 列出搜尋歷史 |
| 儲存 | `save_reference_mcp(pmid)` | 存入專案（永遠優先） |

---

## 工作流

1. **拆分關鍵字**：同一主題拆 3-5 組變體（同義詞、MeSH、縮寫）
2. **並行搜尋**：每組 `search_literature()` 各取 20-30 篇
3. **合併去重**：`merge_search_results([-1,-2,-3])` 或手動比對
4. **篩選**：review title/abstract，標記 relevant
5. **儲存**：`save_reference_mcp(pmid)` 存入專案
6. **不足時擴展**：選擇下方擴展策略

## 擴展策略

| 類型 | 適用 | 方法 |
|------|------|------|
| broaden | 結果太少 | 移除限制詞、用上位概念 |
| narrow | 結果太多 | 加 AND 條件、限制 study type |
| lateral | 結果偏離 | 換同義詞、相關但不同角度 |
| temporal | 需歷史脈絡 | 分年代搜尋 |
| citation | 找到核心文獻 | `find_related_articles` / `find_citing_articles` |

## Session 提示

- `search_index=-1` = 最近一次搜尋
- `query_filter="keyword"` = 篩選特定搜尋
- 搜尋結果自動暫存，用 `get_session_pmids()` 取回
