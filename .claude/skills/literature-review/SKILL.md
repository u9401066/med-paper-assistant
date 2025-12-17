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

**不適用**：
- 只是快速查一篇特定文獻 → 直接用 `search_literature`
- 已經有文獻列表只需整理 → 用 `format_references`

## 使用工具

| 工具 | 用途 | 必須 |
|------|------|------|
| `get_current_project` | 確認當前專案 | ✅ |
| `configure_search_strategy` | 定義搜尋策略 | ✅ |
| `generate_search_queries` | 生成多組搜尋語法 | ✅ |
| `search_literature` | 執行 PubMed 搜尋 | ✅ |
| `merge_search_results` | 合併並去重 | ✅ |
| `find_related_articles` | 擴展相關文獻 | ⚪ |
| `find_citing_articles` | 找引用文獻 | ⚪ |
| `save_reference` | 儲存選中的文獻 | ✅ |
| `format_references` | 格式化參考文獻列表 | ✅ |

## 工作流程

### Phase 1: 準備階段

1. **確認工作環境**
   ```
   呼叫：get_current_project()
   ```

2. **理解搜尋需求** - 詢問用戶：
   - 研究主題是什麼？
   - 有特定的 PICO 嗎？
   - 要限制哪些文獻類型？
   - 時間範圍？

3. **建立搜尋策略**
   ```
   呼叫：configure_search_strategy(criteria_json={...})
   ```

### Phase 2: 並行搜尋

1. **生成多組查詢**
   ```
   呼叫：generate_search_queries(topic="...", use_saved_strategy=True)
   ```

2. **並行執行搜尋** - Agent 同時呼叫多個 `search_literature`

3. **合併結果**
   ```
   呼叫：merge_search_results(results_json='[...]')
   ```

### Phase 3: 擴展搜尋（可選）

對重要的種子文獻：
```
呼叫：find_citing_articles(pmid="...")
呼叫：find_related_articles(pmid="...")
```

### Phase 4: 篩選與儲存

1. 呈現篩選清單給用戶
2. 儲存選中的文獻
   ```
   呼叫：save_reference(pmid="...", tags=[...])
   ```

### Phase 5: 輸出

```
呼叫：format_references(style="vancouver")
```

## 決策點

| 時機 | 問題 | 預設 |
|------|------|------|
| Phase 1 | 建立專案 or 探索？ | 先探索 |
| Phase 2 | 結果數量合理嗎？ | 50-300篇繼續 |
| Phase 3 | 要做擴展搜尋嗎？ | 非系統性回顧不需要 |
| Phase 4 | 篩選方式？ | <30篇逐篇，否則學習偏好 |

## 輸出產物

| 產物 | 位置 |
|------|------|
| 儲存的文獻 | `project/references/` |
| 文獻摘要 | `project/drafts/literature_review.md` |
| 參考文獻列表 | `project/drafts/references.md` |
| 搜尋策略 | `project/config/search_strategy.json` |

## 相關技能

- `concept-development` - 文獻回顧後發展研究概念
- `parallel-search` - 並行搜尋詳細說明
