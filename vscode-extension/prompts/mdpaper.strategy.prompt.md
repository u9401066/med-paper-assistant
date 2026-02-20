---
description: "🔍 mdpaper.strategy - 搜尋策略設定"
---

# 搜尋策略

技能：（無專屬 skill，使用 mdpaper tools）

## 流程

1. 收集參數：keywords, exclusions, year_range, study_type, min_sample_size
2. `configure_search_strategy(params)` → 儲存策略
3. `get_search_strategy()` → 確認

策略會套用至後續所有 `/mdpaper.search` 搜尋。

下一步：`/mdpaper.search` 執行搜尋
