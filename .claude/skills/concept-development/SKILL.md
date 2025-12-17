---
name: concept-development
description: 從文獻回顧中提煉研究概念，建立 concept.md 並通過 novelty 驗證。觸發：發展概念、concept、研究概念、創新點、novelty。
---

# 研究概念發展技能

## 概述

從文獻調查結果中識別研究機會，發展清晰的研究問題和假說，產出結構化的 concept.md 文件。

**適用情境**：
- 完成文獻回顧後，準備定義研究方向
- 有初步想法，需要結構化
- 需要驗證概念的創新性

**前置技能**：通常在 `literature-review` 之後執行

## 使用工具

| 工具 | 用途 | 必須 |
|------|------|------|
| `get_current_project` | 確認專案 | ✅ |
| `list_saved_references` | 檢視已收集的文獻 | ✅ |
| `get_reference_details` | 取得關鍵文獻細節 | ✅ |
| `write_draft` | 撰寫 concept.md | ✅ |
| `validate_concept` | 驗證概念完整性和創新性 | ✅ |
| `validate_concept_quick` | 快速結構檢查 | ⚪ |

## 工作流程

### Phase 1: 現狀分析

1. **確認專案狀態**
   ```
   呼叫：get_current_project()
   呼叫：list_saved_references()
   ```

2. **回顧關鍵文獻** - 識別：
   - 領域的主流觀點
   - 現有方法的限制
   - 尚未解決的問題

### Phase 2: 概念建構

1. **定義 PICO**
   - Population: 研究對象
   - Intervention: 介入措施
   - Comparison: 對照組
   - Outcome: 結果指標

2. **撰寫核心元素**
   - 研究問題（清晰、可回答）
   - 假說（可驗證）
   - **🔒 NOVELTY STATEMENT**（關鍵！）
   - **🔒 KEY SELLING POINTS**（3-5 個）

3. **草擬 concept.md**
   ```
   呼叫：write_draft(filename="concept.md", content="...")
   ```

### Phase 3: 驗證與迭代

1. **快速結構檢查**
   ```
   呼叫：validate_concept_quick()
   ```

2. **完整驗證**（三輪評估，每輪需 ≥ 75 分）
   ```
   呼叫：validate_concept()
   ```

3. **根據回饋迭代** - 如果失敗，修改後重新驗證

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

## 🔒 KEY SELLING POINTS
1. 賣點 1
2. 賣點 2
3. 賣點 3

## 研究設計
- 類型 / 對象 / 方法

## 預期結果
- 主要結果 / 次要結果
```

## 決策點

| 時機 | 問題 | 選項 |
|------|------|------|
| Phase 2 | 研究類型？ | RCT / SR / Case Report / Methods |
| Phase 2 | 創新角度？ | 新對象/新方法/新指標/更大樣本/不同人群 |
| Phase 3 | 驗證失敗？ | 修改概念/補充文獻/重新定義/放棄 |

## 常見問題

### Q: Novelty score 一直不到 75？

常見原因：
1. 創新點描述不夠具體
2. 沒有足夠文獻支持「這是首次」
3. 研究問題太普通

### Q: 什麼是好的 Novelty Statement？

- ✅ 「這是首次在台灣 ICU 比較 remimazolam 和 propofol」
- ✅ 「首次使用機器學習預測 X 的 Y」
- ❌ 「我們研究了 X」（太模糊）

## 相關技能

- `literature-review` - 概念發展的前置步驟
- `parallel-search` - 補充文獻搜尋
