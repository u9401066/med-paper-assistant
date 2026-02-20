---
description: "📝 mdpaper.concept - 發展研究概念與文獻缺口分析"
---

# 發展研究概念

📖 **技能參考**:

- `.claude/skills/concept-development/SKILL.md`
- `.claude/skills/concept-validation/SKILL.md`
  請依序執行以下步驟，完成後打勾 ✅：

## Step 1: 確認專案 `project-context`

📖 技能參考: `.claude/skills/concept-development/SKILL.md`

**任務：**

- 使用 `mcp_mdpaper_get_current_project()` 確認目前專案
- 如果無專案 → 先執行 `/mdpaper.project`

**輸出：** 專案名稱確認

---

## Step 2: 文獻搜尋 `literature-search`

📖 技能參考: `.claude/skills/literature-review/SKILL.md`

**使用 pubmed-search MCP：**

```
mcp_pubmed-search_search_literature(query="用戶主題")
mcp_pubmed-search_fetch_article_details(pmids=[...])
```

**任務：**

- 搜尋相關文獻（5-10 篇關鍵論文）
- 分析現有研究的限制與缺口
- 向用戶說明發現的 research gap

**輸出：** 關鍵文獻列表 + Gap 分析

---

## Step 3: 儲存參考文獻 `save-references`

**使用 mdpaper MCP（MCP-to-MCP 直接通訊）：**

```
mcp_mdpaper_save_reference_mcp(pmid="12345678", agent_notes="Key paper on...")
```

⚠️ **重要**：使用 `save_reference_mcp(pmid)` 而非傳遞完整 metadata！

- 確保資料完整性（直接從 PubMed API 取得驗證資料）
- 防止 Agent 幻覺書目資訊

**輸出：** 文獻已儲存到專案

---

## Step 4: 撰寫 concept.md `concept-writing`

📖 技能參考: `.claude/skills/concept-development/SKILL.md`

**取得模板：**

```
mcp_mdpaper_get_concept_template(paper_type="original-research")
```

**必要區塊（依 paper type 不同）：**

| Paper Type        | 必要區塊                                            |
| ----------------- | --------------------------------------------------- |
| original-research | Research Question, NOVELTY, SELLING POINTS, Methods |
| systematic-review | PRISMA, Search Strategy, Inclusion Criteria         |
| case-report       | Case Timeline, Key Findings                         |
| letter            | Main Argument, Response Points                      |

**🔒 受保護內容（不可刪除或弱化）：**

- `🔒 NOVELTY STATEMENT` - 本研究的創新點
- `🔒 KEY SELLING POINTS` - 賣點清單

**儲存：**

```
mcp_mdpaper_write_draft(filename="concept.md", content="...", skip_validation=true)
```

---

## Step 5: 驗證概念 `validate-concept`

**執行驗證（會進行 Novelty Check）：**

```
mcp_mdpaper_validate_concept(filename="concept.md")
```

**驗證內容：**

1. 結構驗證 - 必要區塊是否存在
2. Novelty 評估 - LLM 評分（3 輪，需達 75+ 分）
3. 一致性檢查 - 各區塊間邏輯是否一致

**結果處理：**

- ✅ 通過 → 可進入 `/mdpaper.draft`
- ❌ 失敗 → 根據回饋修改 concept.md

---

## ⚠️ Novelty Check 犀利回饋規則

**正確行為：**

1. 直指問題：「您聲稱『首次』，但沒有搜尋證據」
2. 提出 Reviewer 會問的問題
3. 給具體修復方案（不是「可以考慮」）
4. 主動問：「直接寫？修正問題？用 CGU 創意工具？」
5. 用戶決定後立即執行

**❌ 禁止行為：**

- 討好式回饋「您的 concept 很好喔～」
- 自動開始修改 NOVELTY STATEMENT
- 反覆修改追分數

**CGU 創意工具（可選）：**

- `cgu_deep_think` - 從 reviewer 角度找弱點
- `cgu_spark_collision` - 碰撞現有限制與優勢
- `cgu_generate_ideas` - 發想無可辯駁的 novelty

---

## 📋 完成檢查

- [ ] Step 1: 專案已確認
- [ ] Step 2: 文獻已搜尋，gap 已分析
- [ ] Step 3: 關鍵文獻已儲存
- [ ] Step 4: concept.md 已撰寫（含 🔒 區塊）
- [ ] Step 5: 驗證通過（Novelty Score ≥ 75）
