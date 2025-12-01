# Skill: 系統性文獻回顧

> 完整執行系統性文獻搜尋、篩選、下載、整理的工作流程

## 概述

這個技能用於：
- 針對特定研究主題進行全面的文獻搜尋
- 系統性篩選相關文獻
- 自動下載可用的全文 PDF
- 整理並產出結構化的文獻摘要

**適用情境**：
- 開始新的研究專案
- 撰寫 Introduction 前的文獻調查
- 系統性回顧 (Systematic Review) 的文獻收集階段

**不適用**：
- 只是快速查一篇特定文獻 → 直接用 `search_literature`
- 已經有文獻列表只需整理 → 用 `format_references`

## 前置條件

執行此技能前，需要確認：

- [ ] 有明確的研究主題或問題
- [ ] 知道大概要找哪類文獻（RCT、meta-analysis、cohort...）
- [ ] 有 project 或 exploration workspace（沒有會自動建立）

## 使用工具

| 工具 | 用途 | 必須 |
|------|------|------|
| `start_exploration` | 建立探索工作區（如果沒有 project） | ⚪ |
| `get_current_project` | 確認當前專案 | ✅ |
| `configure_search_strategy` | 定義搜尋策略 | ✅ |
| `search_literature` | 執行 PubMed 搜尋 | ✅ |
| `find_related_articles` | 擴展相關文獻 | ⚪ |
| `find_citing_articles` | 找引用文獻（前向搜尋） | ⚪ |
| `save_reference` | 儲存選中的文獻 | ✅ |
| `retry_pdf_download` | 重試 PDF 下載 | ⚪ |
| `get_reference_details` | 取得完整引用資訊 | ✅ |
| `read_reference_fulltext` | 讀取 PDF 內容 | ⚪ |
| `list_saved_references` | 列出已儲存文獻 | ✅ |
| `format_references` | 格式化參考文獻列表 | ✅ |
| `write_draft` | 輸出文獻回顧摘要 | ⚪ |

## 工作流程

### Phase 1: 準備階段

**目標**：確認工作環境和搜尋策略

**步驟**：

1. **確認工作環境**
   ```
   呼叫：get_current_project()
   ```
   - 如果有專案 → 繼續
   - 如果沒有專案 → 詢問用戶：
     - 要建立正式專案？ → `create_project(...)`
     - 只是先探索？ → `start_exploration(topic="...")`

2. **理解搜尋需求**
   
   詢問用戶（如果尚未說明）：
   - 研究主題是什麼？
   - 有特定的 PICO 嗎？(Population, Intervention, Comparison, Outcome)
   - 要限制哪些文獻類型？(RCT, Review, Meta-analysis...)
   - 時間範圍？(最近 5 年？10 年？不限？)
   - 語言限制？(English only?)

3. **建立搜尋策略**
   ```
   呼叫：configure_search_strategy(
       topic="主題",
       keywords=["關鍵字1", "關鍵字2", ...],
       mesh_terms=["MeSH1", "MeSH2", ...],
       inclusion_criteria="納入條件",
       exclusion_criteria="排除條件",
       date_range="2020-2025",
       article_types=["RCT", "Review"]
   )
   ```

**檢查點**：
- [ ] 工作環境已確認
- [ ] 搜尋策略已儲存
- [ ] 用戶確認搜尋條件正確

---

### Phase 2: 初步搜尋

**目標**：執行主要搜尋，取得候選文獻列表

**步驟**：

1. **執行主搜尋**
   ```
   呼叫：search_literature(
       query="建構的搜尋語法",
       max_results=100,   # 初步抓多一點
       sort_by="relevance"
   )
   ```

2. **評估搜尋結果**
   
   向用戶報告：
   - 總共找到 N 篇
   - 顯示前 10-20 篇的標題和摘要
   - 詢問：
     - 結果相關嗎？
     - 需要調整搜尋條件嗎？
     - 這批文獻中，有沒有特別重要的「種子文獻」？

3. **如果需要調整**
   - 修改關鍵字 → 重新 `search_literature`
   - 太多結果 → 增加篩選條件
   - 太少結果 → 放寬條件或增加同義詞

**檢查點**：
- [ ] 搜尋結果數量合理（通常 50-500 篇）
- [ ] 前幾篇看起來相關
- [ ] 用戶滿意搜尋品質

---

### Phase 3: 擴展搜尋（可選）

**目標**：透過引用關係找到可能遺漏的文獻

**觸發條件**：
- 用戶要求更全面的搜尋
- 這是系統性回顧
- 發現重要的種子文獻

**步驟**：

1. **識別種子文獻**
   
   從 Phase 2 結果中，找出：
   - 高引用數的文獻
   - 最相關的 3-5 篇
   - 用戶特別標記的文獻

2. **前向搜尋（找誰引用了種子）**
   ```
   呼叫：find_citing_articles(pmid="種子PMID")
   ```
   - 對每個種子文獻執行
   - 這些可能是更新的研究

3. **相關文獻搜尋**
   ```
   呼叫：find_related_articles(pmid="種子PMID")
   ```
   - PubMed 的相似文獻演算法
   - 可能找到不同關鍵字但相關的研究

4. **合併去重**
   
   將所有來源的文獻合併，去除重複的 PMID

**檢查點**：
- [ ] 擴展搜尋增加了 N 篇新文獻
- [ ] 總候選數量仍可管理

---

### Phase 4: 篩選與儲存

**目標**：篩選相關文獻並儲存到專案

**步驟**：

1. **呈現篩選清單**
   
   向用戶展示每篇文獻：
   ```
   [1] 標題
       作者 (年份) - 期刊
       摘要前 200 字...
       [納入] [排除] [稍後決定]
   ```

2. **用戶篩選**（決策點 - 見下方）
   
   - 可以一次全部決定
   - 可以分批處理
   - 可以設定自動規則（如：排除 case report）

3. **儲存選中的文獻**
   ```
   對每篇納入的文獻：
   呼叫：save_reference(
       pmid="文獻PMID",
       notes="用戶的備註（如果有）",
       tags=["標籤1", "標籤2"]
   )
   ```
   
   系統會自動：
   - 取得完整 metadata
   - 嘗試下載 PDF（如果可用）
   - 儲存到專案的 references 目錄

4. **處理 PDF 下載失敗**
   
   如果有些 PDF 下載失敗：
   ```
   呼叫：retry_pdf_download(pmid="PMID")
   ```
   
   或告知用戶需要手動取得

**檢查點**：
- [ ] N 篇文獻已儲存
- [ ] X 篇有 PDF
- [ ] Y 篇需要手動取得 PDF

---

### Phase 5: 深度整理

**目標**：整理文獻內容，產出可用的摘要

**步驟**：

1. **取得完整資訊**
   ```
   對每篇已儲存的文獻：
   呼叫：get_reference_details(pmid="PMID")
   ```
   
   取得：
   - 完整作者列表
   - 詳細摘要
   - MeSH 標籤
   - 引用數

2. **讀取全文（如果有 PDF）**
   ```
   呼叫：read_reference_fulltext(pmid="PMID")
   ```
   
   提取關鍵資訊：
   - 研究設計
   - 樣本數
   - 主要發現
   - 限制

3. **分類整理**
   
   按照用戶需求分類，例如：
   - 按主題
   - 按研究類型
   - 按結論方向（支持/反對/中立）
   - 按發表年份

4. **建立文獻摘要表**
   
   產出結構化的表格：
   
   | 作者(年份) | 設計 | N | 主要發現 | 品質 |
   |------------|------|---|----------|------|
   | ... | RCT | 200 | ... | 高 |

**檢查點**：
- [ ] 所有文獻都有基本資訊
- [ ] 重要文獻有詳細摘要
- [ ] 分類結構合理

---

### Phase 6: 輸出

**目標**：產出最終的文獻回顧文件

**步驟**：

1. **格式化參考文獻**
   ```
   呼叫：format_references(
       style="vancouver",  # 或用戶指定的格式
       output_format="markdown"
   )
   ```

2. **產出文獻回顧摘要**
   ```
   呼叫：write_draft(
       filename="literature_review.md",
       content="結構化的文獻摘要內容"
   )
   ```
   
   內容包含：
   - 搜尋策略說明
   - PRISMA 流程圖數據
   - 文獻分類摘要
   - 參考文獻列表

3. **提供下一步建議**
   
   告知用戶：
   - 文獻回顧已完成
   - 建議的後續步驟（撰寫 Introduction？進行 meta-analysis？）

---

## 決策點

### 決策 1: 工作環境選擇

**時機**：Phase 1，沒有現有專案時
**問題**：「你想要建立正式專案，還是先在探索區試試？」
**選項**：
- A: 建立正式專案 → `create_project`
- B: 先探索 → `start_exploration`
- C: 用現有專案 → `switch_project`

**預設**：B（先探索），因為文獻回顧常是專案初期

---

### 決策 2: 搜尋結果評估

**時機**：Phase 2，初步搜尋後
**問題**：「找到 N 篇文獻，看起來相關嗎？需要調整嗎？」
**選項**：
- A: 結果很好，繼續
- B: 太多了，需要更嚴格的條件
- C: 太少了，放寬條件
- D: 方向不對，重新定義關鍵字

**預設**：如果 50-300 篇且前 10 篇看起來相關 → A

---

### 決策 3: 文獻篩選方式

**時機**：Phase 4，開始篩選時
**問題**：「你想怎麼篩選這 N 篇文獻？」
**選項**：
- A: 逐篇審閱（嚴謹但慢）
- B: 我設定規則自動篩選，你再確認（快但可能漏）
- C: 先看前 20 篇，我學習你的偏好後自動處理剩下的

**預設**：如果 < 30 篇 → A，否則 → C

---

### 決策 4: 擴展搜尋

**時機**：Phase 3，問是否要擴展
**問題**：「要做擴展搜尋（引用追蹤）嗎？這會更完整但需要更多時間。」
**選項**：
- A: 是，這是系統性回顧，需要完整
- B: 不用，初步搜尋已足夠
- C: 只對最重要的 3 篇做擴展

**預設**：B（除非用戶說是系統性回顧）

---

## 輸出產物

| 產物 | 格式 | 位置 | 說明 |
|------|------|------|------|
| 儲存的文獻 | 目錄結構 | `project/references/` | 每篇一個子目錄 |
| PDF 全文 | .pdf | `project/references/{pmid}/` | 如果可下載 |
| 文獻摘要 | .md | `project/drafts/literature_review.md` | 完整的文獻回顧 |
| 參考文獻列表 | .md | `project/drafts/references.md` | 格式化的引用 |
| 搜尋策略 | JSON | `project/config/search_strategy.json` | 可重現的搜尋 |

## 範例對話

```
用戶：幫我做 remimazolam 用於 ICU 鎮靜的文獻回顧

Agent：好的，我來幫你做系統性文獻回顧。
       
       首先確認一下：
       1. 你已經有專案了嗎？還是要先建立一個？
       2. 有特定的 PICO 嗎？
          - P: ICU 病人？
          - I: Remimazolam
          - C: 其他鎮靜劑（propofol, midazolam）？
          - O: 鎮靜效果？副作用？
       3. 要限制文獻類型嗎？（RCT only? 包含 observational?）

用戶：沒有專案，先探索就好。PICO 對，不限文獻類型，最近 5 年

Agent：了解，我先建立探索工作區...
       [呼叫 start_exploration(topic="remimazolam ICU sedation")]
       
       現在設定搜尋策略...
       [呼叫 configure_search_strategy(...)]
       
       開始搜尋...
       [呼叫 search_literature(...)]
       
       找到 47 篇文獻！前 10 篇：
       1. "Remimazolam for sedation in ICU: a RCT" - Wang et al. 2023
       2. ...
       
       看起來相關嗎？要繼續嗎？

用戶：很好，繼續

Agent：好的，我來逐篇確認。總共 47 篇，我會顯示每篇讓你決定納入或排除...
       
       [篩選過程...]
       
       篩選完成！
       - 納入：23 篇
       - 排除：24 篇
       
       正在儲存並下載 PDF...
       [呼叫 save_reference(...) x 23]
       
       完成！
       - 23 篇已儲存
       - 18 篇有 PDF
       - 5 篇需要手動取得
       
       正在整理文獻摘要...
       [呼叫 get_reference_details(...)]
       [呼叫 read_reference_fulltext(...)]
       
       文獻回顧完成！產出：
       - drafts/literature_review.md - 完整摘要
       - drafts/references.md - 參考文獻列表
       
       下一步建議：
       1. 查看 literature_review.md 確認內容
       2. 如果滿意，可以開始撰寫 Introduction
       3. 或者將探索轉為正式專案
```

## 常見問題

### Q: 搜尋結果太多怎麼辦？

A: 嘗試以下策略：
1. 增加 MeSH 限定詞（如 `/therapy`）
2. 限制文獻類型（如只要 RCT）
3. 縮短時間範圍
4. 增加排除條件

### Q: 找不到足夠的文獻？

A: 嘗試以下策略：
1. 使用同義詞和相關術語
2. 放寬 PICO 條件
3. 擴展時間範圍
4. 做擴展搜尋（Phase 3）

### Q: PDF 無法下載？

A: 
1. 有些期刊需要付費訂閱
2. 可以嘗試 `retry_pdf_download`
3. 手動從機構圖書館取得
4. 考慮聯繫作者

### Q: 這跟 `/mdpaper.search` prompt 有什麼不同？

A: 
- `/mdpaper.search` 是快速搜尋入口
- 這個 Skill 是完整的系統性流程
- Skill 包含篩選、下載、整理的完整知識

## 相關技能

- `concept_development.md` - 文獻回顧後發展研究概念
- `gap_analysis.md` - 從文獻中識別研究缺口
- `draft_introduction.md` - 用文獻回顧撰寫前言

---

*最後更新：2025-12-01*
