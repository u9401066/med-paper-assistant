---
description: "🎯 mdpaper.strategy - 配置搜尋策略"
---

# 配置搜尋策略

📖 **技能參考**: `.claude/skills/literature-review/SKILL.md`

## Step 1: 收集搜尋參數

詢問用戶以下資訊：

| 參數 | 說明 | 範例 |
|------|------|------|
| Keywords | 主要關鍵字 | "remimazolam", "sedation" |
| Exclusions | 排除關鍵字 | "pediatric", "animal" |
| Year Range | 年份範圍 | 2015-2024 |
| Article Types | 文章類型 | "Clinical Trial", "Review" |
| Sample Size | 最小樣本數 | 50 |

---

## Step 2: 設定搜尋策略

```
mcp_mdpaper_configure_search_strategy(
    keywords=["keyword1", "keyword2"],
    exclusions=["exclude1"],
    year_range=[2015, 2024],
    article_types=["Clinical Trial", "Meta-Analysis"],
    min_sample_size=50
)
```

---

## Step 3: 確認策略

```
mcp_mdpaper_get_search_strategy()
```

顯示目前設定供用戶確認。

---

## 📋 完成檢查

- [ ] 關鍵字已設定
- [ ] 排除條件已設定
- [ ] 年份範圍已設定
- [ ] 可以開始 `/mdpaper.search`
