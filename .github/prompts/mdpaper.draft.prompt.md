---
description: "✍️ mdpaper.draft - 撰寫論文草稿"
---

# 撰寫論文草稿

## ⚠️ 前置條件

**必須先通過 concept 驗證才能撰寫 draft！**

```
mcp_mdpaper_validate_concept(filename="concept.md")
→ Novelty Score ≥ 75 (3/3 rounds)
→ 如果失敗 → 停止並要求用戶修正 concept
```

---

## Step 1: 確認專案與驗證狀態 `validate`

📖 技能參考: `.claude/skills/concept-development/SKILL.md`

**任務：**
```
mcp_mdpaper_get_current_project()
mcp_mdpaper_validate_for_section(section="Introduction")
```

**驗證結果：**
- ✅ CAN WRITE → 繼續
- ❌ CANNOT WRITE → 顯示缺少的區塊，請用戶補充

---

## Step 2: 讀取 Concept 與受保護內容 `read-concept`

```
mcp_mdpaper_read_draft(filename="concept.md")
```

**提取 🔒 受保護內容：**
- `🔒 NOVELTY STATEMENT` → 必須在 Introduction 體現
- `🔒 KEY SELLING POINTS` → 必須在 Discussion 強調

---

## Step 3: 取得寫作指南 `get-template`

```
mcp_mdpaper_get_section_template(section="Introduction")
```

**各 section 要點：**

| Section | 重點 |
|---------|------|
| Introduction | 背景 → Gap → 研究目的（含 🔒 NOVELTY）|
| Methods | 研究設計 → 樣本 → 分析方法 |
| Results | 主要發現 → 次要發現 → 表格/圖 |
| Discussion | 主要發現討論 → 與文獻比較（含 🔒 SELLING POINTS）→ 限制 → 結論 |
| Abstract | 依期刊格式（structured/unstructured）|

---

## Step 4: 撰寫草稿 `write-draft`

**方式一：逐段撰寫**
```
mcp_mdpaper_draft_section(topic="Introduction", notes="...")
```

**方式二：完整檔案**
```
mcp_mdpaper_write_draft(filename="drafts/introduction.md", content="...")
```

**🔒 受保護內容規則：**
- Introduction 必須體現 NOVELTY STATEMENT
- Discussion 必須強調所有 KEY SELLING POINTS
- 修改 🔒 區塊前必須詢問用戶

---

## Step 5: 確認字數 `word-count`

```
mcp_mdpaper_count_words(filename="drafts/introduction.md")
```

**常見期刊字數限制：**
| Section | 一般限制 |
|---------|----------|
| Abstract | 250-350 words |
| Introduction | 400-600 words |
| Methods | 800-1200 words |
| Results | 600-1000 words |
| Discussion | 1000-1500 words |

---

## Step 6: 同步引用 `sync-citations`

```
mcp_mdpaper_sync_references(filename="drafts/introduction.md")
```

**功能：**
- 掃描 `[[wikilinks]]` 格式的引用
- 自動生成 References 區塊
- 確保引用格式一致

---

## 📋 完成檢查

- [ ] Step 1: Concept 驗證通過
- [ ] Step 2: 🔒 受保護內容已提取
- [ ] Step 3: 寫作指南已取得
- [ ] Step 4: 草稿已撰寫（保留 🔒 內容）
- [ ] Step 5: 字數符合限制
- [ ] Step 6: 引用已同步
