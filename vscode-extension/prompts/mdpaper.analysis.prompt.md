---
description: "📊 mdpaper.analysis - 資料分析與視覺化"
---

# 資料分析

技能：（無專屬 skill，直接使用 MCP tools）

## Step 1: 確認專案 + 資料

`get_current_project()` → `list_data_files()` → 確認 CSV 欄位

## Step 2: 描述統計

`analyze_dataset(file, columns?)` → 摘要統計量、缺失值、分佈

## Step 3: Table 1

`generate_table_one(file, group_column, variables:[{name,type}])` — type: continuous/categorical

## Step 4: 統計檢定

| 檢定         | 適用       |
| ------------ | ---------- |
| t-test       | 兩組連續   |
| chi-square   | 兩組類別   |
| mann-whitney | 兩組非常態 |
| anova        | 多組連續   |
| correlation  | 兩連續關聯 |

`run_statistical_test(file, test, params)`

## Step 5: 視覺化

`create_plot(file, plot_type, x, y?, group?)` — 類型：boxplot/histogram/scatter/bar/line
