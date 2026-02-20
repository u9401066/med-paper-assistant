---
name: draft-writing
description: |
  論文草稿的撰寫、讀取、引用管理。
  LOAD THIS SKILL WHEN: 寫草稿、draft、撰寫、Introduction、Methods、Results、Discussion、引用、citation、字數、patch、編輯草稿
  CAPABILITIES: write_draft, draft_section, read_draft, list_drafts, insert_citation, sync_references, count_words, get_available_citations, patch_draft
---

# 草稿撰寫技能

觸發：寫草稿、draft、section、引用、citation、字數、patch、寫作順序

## 前置條件
1. `get_current_project()` 確認專案
2. concept.md 存在且 🔒 區塊非空（寫 concept.md 本身除外）

---

## MCP Tools

### 撰寫

| 工具 | 說明 |
|------|------|
| `write_draft` | 建立/覆寫草稿（`filename`, `content`, `project`）|
| `draft_section` | 根據 notes 產出 section（`topic`, `notes`）|
| `read_draft` | 讀取草稿 |
| `list_drafts` | 列出所有草稿 |
| `check_writing_order` | ⭐ 檢查寫作順序與進度（advisory, 不阻止）|

### 引用（⚠️ 修改引用必須用 `patch_draft`，禁止 `replace_string_in_file`）

| 工具 | 說明 |
|------|------|
| `get_available_citations` | ⚠️ 編輯前必呼叫！列出可用 `[[citation_key]]` |
| `patch_draft` | 部分編輯草稿，自動驗證 wikilinks |
| `insert_citation` | 定點插入引用（`filename`, `target_text`, `pmid`）|
| `sync_references` | 掃描 [[wikilinks]] 生成 References |
| `count_words` | 計算字數 |

**patch_draft vs replace_string_in_file**：patch_draft 驗證引用、自動修復格式、拒絕不存在的引用。

---

## 寫作順序（Advisory）

| Paper Type | 順序 |
|------------|------|
| original-research | Methods → Results → Introduction → Discussion → Conclusion → Abstract |
| systematic-review | Methods → Results → Discussion → Introduction → Conclusion → Abstract |
| case-report | Case Presentation → Discussion → Introduction → Conclusion → Abstract |
| review-article | Introduction → Body → Conclusion → Abstract |

前置：Results 需 Methods、Discussion 需 Results+Intro、Conclusion 需 Discussion、Abstract 需全部。
`check_writing_order()` 產生警告，不阻止。警告出現時詢問用戶是否繼續。

---

## Flow A: 撰寫新 Section

1. `check_writing_order()` → 確認前置
2. `validate_for_section(section)` → ✅/❌
3. `read_draft("concept.md")` → 提取 🔒 NOVELTY + 🔒 SELLING POINTS
4. 參考下方 Section 指南撰寫
5. `count_words()`

## Flow B: Citation-Aware 編輯

1. `get_available_citations()` → 取得可用 citation keys
2. `patch_draft(filename, old_text, new_text)` → 自動驗證 wikilinks
3. `sync_references(filename)` → 生成 References

---

## 🔒 受保護內容

- Introduction 開頭/結尾必須呼應 🔒 NOVELTY
- Discussion 必須逐條強調 🔒 SELLING POINTS
- 不可刪除或弱化 🔒 區塊。修改前必須詢問用戶

---

## Section 寫作指南

### Introduction (400-600 words)
結構：Clinical Reality → Evidence Base (with [[wikilinks]]) → Knowledge Gap (對應 🔒 NOVELTY) → Objective
🚫 禁止 "In recent years..." / 每段 "Furthermore"。必須有具體數字。

### Methods (800-1200 words)
Study Design → Participants → Intervention → Outcomes → Statistics

### Results (600-1000 words)
Participants → Primary Outcome → Secondary Outcomes → Tables/Figures

### Discussion (1000-1500 words)
Main Findings (含 🔒 SELLING POINTS) → Comparison → Implications → Limitations → Conclusion

### Abstract (250-350 words)
Structured: Background / Methods / Results / Conclusions

---

## Wikilink 格式
✅ `[[author2024_12345678]]` → 自動修復 `[[12345678]]` → `[[author2024_12345678]]`
