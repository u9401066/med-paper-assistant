# Skill: 研究概念發展

> 從文獻回顧中提煉研究概念，建立有效的 concept.md

## 概述

這個技能用於：
- 從文獻調查結果中識別研究機會
- 發展清晰的研究問題和假說
- 產出結構化的 concept.md 文件
- 確保概念通過驗證（novelty score ≥ 75）

**適用情境**：
- 完成文獻回顧後，準備定義研究方向
- 有初步想法，需要結構化
- 需要驗證概念的創新性

**前置技能**：通常在 `literature_review.md` 之後執行

## 前置條件

- [ ] 已完成相關領域的文獻回顧
- [ ] 有明確的專案（或準備建立）
- [ ] 對研究方向有初步想法

## 使用工具

| 工具 | 用途 | 必須 |
|------|------|------|
| `get_current_project` | 確認專案 | ✅ |
| `list_saved_references` | 檢視已收集的文獻 | ✅ |
| `get_reference_details` | 取得關鍵文獻細節 | ✅ |
| `search_literature` | 補充搜尋 | ⚪ |
| `write_draft` | 撰寫 concept.md | ✅ |
| `validate_concept` | 驗證概念完整性和創新性 | ✅ |
| `validate_concept_quick` | 快速結構檢查 | ⚪ |

## 工作流程

### Phase 1: 現狀分析

**目標**：理解目前已知的內容

**步驟**：

1. **確認專案狀態**
   ```
   呼叫：get_current_project()
   呼叫：list_saved_references()
   ```

2. **回顧關鍵文獻**
   
   識別：
   - 領域的主流觀點
   - 現有方法的限制
   - 尚未解決的問題
   - 矛盾的研究結果

3. **與用戶討論**
   
   詢問：
   - 你注意到什麼研究缺口？
   - 你想解決什麼問題？
   - 你有什麼獨特的資源或角度？

---

### Phase 2: 概念建構

**目標**：建立結構化的研究概念

**步驟**：

1. **定義 PICO（或適用的框架）**
   - Population: 研究對象
   - Intervention: 介入措施
   - Comparison: 對照組
   - Outcome: 結果指標

2. **撰寫核心元素**

   **研究問題**：
   - 清晰、可回答的問題
   - 避免太寬泛或太狹隘

   **假說**：
   - 明確的預期結果
   - 可驗證

   **🔒 NOVELTY STATEMENT**（關鍵！）：
   - 這個研究的創新點是什麼？
   - 與現有研究的差異？
   - 為什麼現在需要這個研究？

   **🔒 KEY SELLING POINTS**：
   - 3-5 個核心賣點
   - 這些會貫穿整篇論文

3. **草擬 concept.md**
   ```
   呼叫：write_draft(
       filename="concept.md",
       content="結構化的概念內容"
   )
   ```

---

### Phase 3: 驗證與迭代

**目標**：確保概念通過驗證

**步驟**：

1. **快速結構檢查**
   ```
   呼叫：validate_concept_quick()
   ```
   - 確認必要區塊都有
   - 確認格式正確

2. **完整驗證**
   ```
   呼叫：validate_concept()
   ```
   - 三輪獨立評估
   - 每輪 novelty score 需 ≥ 75
   - 如果失敗，會得到改進建議

3. **根據回饋迭代**
   
   如果驗證失敗：
   - 分析失敗原因
   - 與用戶討論調整方向
   - 更新 concept.md
   - 重新驗證

4. **最終確認**
   
   通過驗證後：
   - 向用戶展示最終概念
   - 確認可以進入下一階段

---

## 決策點

### 決策 1: 研究類型

**時機**：Phase 2 開始時
**問題**：「這是什麼類型的研究？」
**選項**：
- Original Research (RCT, Cohort, Case-control...)
- Systematic Review / Meta-analysis
- Case Report / Case Series
- Technical Note / Methods Paper

---

### 決策 2: 創新角度

**時機**：定義 Novelty Statement 時
**問題**：「這個研究的創新點是什麼？」
**選項**（可複選）：
- 新的研究對象
- 新的介入方法
- 新的結果指標
- 更大的樣本
- 不同的地區/人群
- 方法學創新
- 首次比較 A vs B

---

### 決策 3: 驗證失敗處理

**時機**：Phase 3，驗證未通過
**問題**：「概念驗證未通過（score: X）。怎麼處理？」
**選項**：
- A: 根據建議修改概念
- B: 補充更多文獻支持
- C: 重新定義研究問題
- D: 放棄此方向，嘗試其他

---

## Concept.md 結構模板

```markdown
# [研究標題]

## 研究背景
- 領域現狀
- 為什麼重要

## 研究問題
[清晰的研究問題]

## 假說
[可驗證的假說]

## 🔒 NOVELTY STATEMENT
**這是首次...**
- 創新點 1
- 創新點 2
- 與現有研究的差異

## 🔒 KEY SELLING POINTS
1. 賣點 1
2. 賣點 2
3. 賣點 3

## 研究設計
- 類型：
- 對象：
- 方法：

## 預期結果
- 主要結果
- 次要結果

## 📝 Author Notes (不會出現在論文中)
- 備註
- 提醒
```

## 輸出產物

| 產物 | 格式 | 位置 |
|------|------|------|
| concept.md | .md | `project/concept.md` |
| 驗證報告 | 顯示 | 終端輸出 |

## 常見問題

### Q: Novelty score 一直不到 75？

A: 常見原因：
1. 創新點描述不夠具體
2. 沒有足夠文獻支持「這是首次」
3. 研究問題太普通

解法：
- 更仔細地定義差異點
- 補充文獻搜尋，確認真的沒人做過
- 考慮更獨特的角度

### Q: 什麼是好的 Novelty Statement？

A: 好的 Novelty Statement：
- ✅ 「這是首次在台灣 ICU 比較 remimazolam 和 propofol」
- ✅ 「首次使用機器學習預測 X 的 Y」
- ❌ 「我們研究了 X」（太模糊）
- ❌ 「這很重要」（不是創新點）

## 相關技能

- `literature_review.md` - 概念發展的前置步驟
- `gap_analysis.md` - 更深入的缺口分析
- `draft_introduction.md` - 將概念轉為 Introduction

---

*最後更新：2025-12-01*
