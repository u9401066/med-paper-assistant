---
name: concept-development
description: 發展研究概念並驗證創新性。觸發：concept、發展概念、研究概念、novelty、創新點、補充概念、幫我補充、擴展概念、加強、驗證失敗、novelty不夠、怎麼改。
---

# 研究概念發展技能

## 核心哲學：像頂尖 Reviewer 一樣犀利

- **直指問題核心** — 不繞彎、不糖衣
- **用證據說話** — 「你說 X，但文獻顯示 Y」
- **提出 Reviewer 會問的問題** — 讓作者無法反駁
- **給具體修復方案** — 不是「可以考慮」，而是「加入這句話」

## 黃金法則

1. **永遠先問用戶** — 不自動修改 NOVELTY/SELLING_POINTS
2. **犀利但建設性** — 嚴格導師，非敵人
3. **用戶說「直接寫」就開始** — 尊重決定
4. **反覆修改 = 危險信號** — 改兩次沒改善就停下討論

---

## 工具

| 工具                         | 用途                        |
| ---------------------------- | --------------------------- |
| `read_draft` / `write_draft` | 讀寫 concept.md             |
| `validate_for_section`       | ⭐ 針對特定 section 驗證    |
| `validate_concept`           | 完整驗證（犀利回饋）        |
| `list_saved_references`      | 檢視文獻                    |
| `save_reference_mcp`         | 儲存文獻（**永遠優先**）    |
| `sync_references`            | 同步 wikilinks → References |
| `mcp_cgu_deep_think`         | CGU 深度分析弱點            |

---

## 完整流程

### Phase 1: 文獻搜尋

`search_literature()` → `fetch_article_details()` → 分析 Research Gap

### Phase 2: 專案建立

`create_project()` → `save_reference_mcp(pmid)`

### Phase 3: 概念撰寫

用 concept.md template 撰寫：Research Question, 🔒 NOVELTY STATEMENT, Methods Overview, 🔒 KEY SELLING POINTS

### Phase 4: 驗證與迭代

`validate_concept()` → 犀利回饋 → 三選項（直接寫/修正/用 CGU）

---

## 🔒 Protected Content

| 標記                  | 規則                                  |
| --------------------- | ------------------------------------- |
| 🔒 NOVELTY STATEMENT  | 不可刪除或弱化。Introduction 必須呼應 |
| 🔒 KEY SELLING POINTS | 必須全部保留。Discussion 必須強調     |

Agent 修改前必須問用戶確認。

---

## Novelty Score 低的處理（犀利回饋模式）

**禁止**：自動改 NOVELTY、反覆追分、討好式回饋

**正確流程**：

1. 給犀利回饋（具體問題 + Reviewer 會問什麼 + 修復方案）
2. 給三選項：✅ 直接寫 | 🔧 修正問題 | 🤖 用 CGU 想

### 犀利回饋模式

| Pattern            | 問題                | Reviewer 問      | 修復                 |
| ------------------ | ------------------- | ---------------- | -------------------- |
| 聲稱「首次」沒證據 | 沒文獻搜尋紀錄      | 搜尋策略是什麼？ | 加入 PubMed 搜尋紀錄 |
| 模糊量化           | 「更好」沒數字      | 好多少？顯著嗎？ | 改為具體數值/OR/CI   |
| 引用沒說限制       | 有 ref 但沒指出 gap | 貢獻在哪？       | 加入 ref 的具體限制  |

### 危險信號

| 信號             | 行動                   |
| ---------------- | ---------------------- |
| 改 2 次沒改善    | 停。問用戶要不要換方向 |
| 分數反而變低     | 停。恢復原版           |
| 需大幅改研究方向 | 停。用戶決定           |

---

## CGU 使用指南

| 情境       | 工具              | 用法                     |
| ---------- | ----------------- | ------------------------ |
| 找弱點     | `deep_think`      | 從 reviewer 角度找攻擊點 |
| 找強化論點 | `spark_collision` | 碰撞限制 vs 優勢         |
| 廣泛發想   | `generate_ideas`  | 讓 novelty 無可辯駁      |

流程：CGU 工具 → 整理 2-3 建議 → 問用戶選哪個 → 只改那一個

---

## 好的 Novelty Statement

✅ `PubMed 搜 "X AND Y" (日期) 結果 0 篇。本研究首次在台灣 ICU 比較 remimazolam 和 propofol`
✅ `[[author2024]] 比較了 A vs B，但未納入 C。本研究首次加入 C`
❌ `我們研究了 X`（太模糊）
❌ `這是首次...`（沒搜尋證據）

## Wikilink 格式

✅ `[[author2024_12345678]]`（作者年份\_PMID）
❌ `[[12345678]]`（缺 author_year）
取得：`save_reference_mcp(pmid)` 回傳 citation_key
