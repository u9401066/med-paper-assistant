---
description: "📝 mdpaper.concept - 發展研究概念與文獻缺口分析"
---

# 發展研究概念

技能：concept-development + concept-validation

## Step 1: 確認專案

`project_action(action="current")` — 無專案 → 先 `/mdpaper.project`

## Step 2: 文獻搜尋

`unified_search(query)` → `fetch_article_details(pmids)` → 5-10 篇關鍵論文 → 分析 Gap

## Step 3: 儲存文獻

`save_reference_mcp(pmid, agent_notes)` ✅ — 不傳完整 metadata

## Step 4: 撰寫 concept.md

`get_concept_template(paper_type)` → 撰寫必要區塊：

| Paper Type        | 必要區塊                                            |
| ----------------- | --------------------------------------------------- |
| original-research | Research Question, NOVELTY, SELLING POINTS, Methods |
| systematic-review | PRISMA, Search Strategy, Inclusion Criteria         |
| case-report       | Case Timeline, Key Findings                         |
| letter            | Main Argument, Response Points                      |

🔒 不可刪除/弱化：NOVELTY STATEMENT + KEY SELLING POINTS

`write_draft("concept.md", content, skip_validation=true)`

## Step 5: 驗證

`validation_action(action="concept", filename="concept.md")` → 結構 + Novelty 評分（3 輪 ≥ 75）+ 一致性
✅ → `/mdpaper.draft` | ❌ → 修改

## Novelty Check 規則

✅ 直指問題、提 Reviewer 會問的、給具體修復、問「直接寫？修正？用 CGU？」
❌ 禁止：討好回饋、自動改 NOVELTY、反覆追分

CGU：`deep_think`（找弱點）、`spark_collision`（碰撞）、`generate_ideas`（發想）
