---
description: "📊 mdpaper.analysis - 資料分析"
---

# 資料分析

📖 **核心模組**: `src/med_paper_assistant/infrastructure/services/analyzer.py`

## Step 1: 確認資料來源

詢問用戶要分析哪個 CSV 檔案：

```
請提供要分析的資料檔案路徑，或將 CSV 檔案放入專案的 data/ 目錄。
```

---

## Step 2: 探索性分析

```
mcp_mdpaper_analyze_dataset(
    data_file="data/study_data.csv",
    target_column="outcome"
)
```

**輸出：**
- 描述性統計
- 缺失值分析
- 變數分佈

---

## Step 3: Table 1 (Baseline Characteristics)

```
mcp_mdpaper_generate_table_one(
    data_file="data/study_data.csv",
    group_column="treatment_group",
    variables=["age", "gender", "bmi"],
    categorical=["gender"],
    continuous=["age", "bmi"]
)
```

---

## Step 4: 統計檢定

```
mcp_mdpaper_run_statistical_test(
    data_file="data/study_data.csv",
    test_type="t-test",  # 或 "chi-square", "correlation", "anova"
    group_column="treatment_group",
    value_column="outcome"
)
```

**可用檢定：**
| 檢定類型 | 適用情境 |
|----------|----------|
| t-test | 兩組連續變數比較 |
| chi-square | 類別變數關聯 |
| correlation | 兩連續變數相關 |
| anova | 多組比較 |
| mann-whitney | 非常態兩組比較 |

---

## Step 5: 視覺化

```
mcp_mdpaper_create_plot(
    data_file="data/study_data.csv",
    plot_type="boxplot",
    x_column="treatment_group",
    y_column="outcome",
    output_file="results/figures/outcome_comparison.png"
)
```

**可用圖表：**
- `boxplot` - 箱形圖
- `histogram` - 直方圖
- `scatter` - 散佈圖
- `bar` - 長條圖
- `line` - 折線圖

---

## 📋 完成檢查

- [ ] 資料已載入
- [ ] 描述性統計完成
- [ ] Table 1 已生成
- [ ] 統計檢定完成
- [ ] 圖表已儲存
