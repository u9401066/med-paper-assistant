---
description: "✍️ mdpaper.draft - 撰寫論文草稿"
---

# 撰寫論文草稿

技能：draft-writing + concept-validation

⚠️ **前置條件**：`validate_concept("concept.md")` → Novelty ≥ 75 才能寫

## Step 0: 寫作順序

`check_writing_order()` → ✅ 繼續 / ⚠️ 缺前置 section → 詢問用戶先寫或忽略

## Step 1: 確認專案 + 驗證

`get_current_project()` → `validate_for_section(section)` → ✅ CAN WRITE / ❌ 缺區塊

## Step 2: 讀 Concept

`read_draft("concept.md")` → 提取 🔒 NOVELTY STATEMENT + 🔒 KEY SELLING POINTS

## Step 3: 寫作指南

`get_section_template(section)` → 各 section 重點：

| Section      | 重點                                                |
| ------------ | --------------------------------------------------- |
| Introduction | 背景→Gap→目的（含 🔒 NOVELTY）                      |
| Methods      | 設計→樣本→分析                                      |
| Results      | 主要→次要→表/圖                                     |
| Discussion   | 發現討論→文獻比較（含 🔒 SELLING POINTS）→限制→結論 |
| Abstract     | 依期刊格式                                          |

## Step 4: 撰寫

`draft_section(topic, notes)` 或 `write_draft(filename, content)`

🔒 規則：Introduction 含 NOVELTY、Discussion 含 SELLING POINTS、修改 🔒 前須問用戶

## Step 5: 字數

`count_words(filename)` — Abstract 250-350, Intro 400-600, Methods 800-1200, Results 600-1000, Discussion 1000-1500

## Step 6: 引用

`sync_references(filename)` — 掃描 [[wikilinks]] 生成 References
