---
description: "📄 mdpaper.format - 匯出為 Word 文件"
---

# 匯出為 Word 文件

📖 **技能參考**: `.claude/skills/word-export/SKILL.md`

## Step 1: 選擇模板

```
mcp_mdpaper_list_templates()
```

**常用模板：**
- `Type of the Paper.docx` - 標準論文格式
- `Review Article.docx` - 回顧性文章
- `Case Report.docx` - 病例報告

---

## Step 2: 讀取模板結構

```
mcp_mdpaper_read_template(template_name="Type of the Paper.docx")
```

**輸出：**
- 可用的 sections
- 每個 section 的 styles
- 字數限制（如有）

---

## Step 3: 讀取草稿

```
mcp_mdpaper_read_draft(filename="drafts/full_manuscript.md")
```

或列出所有草稿選擇：
```
mcp_mdpaper_list_drafts()
```

---

## Step 4: 開始文件 Session

```
mcp_mdpaper_start_document_session(
    template_name="Type of the Paper.docx",
    output_name="manuscript_v1.docx"
)
```

---

## Step 5: 插入各 Section

依序插入每個區塊：

```
mcp_mdpaper_insert_section(
    session_id="...",
    section_name="Abstract",
    content="..."
)

mcp_mdpaper_insert_section(
    session_id="...",
    section_name="Introduction",
    content="..."
)

# ... 其他 sections
```

---

## Step 6: 驗證文件

```
mcp_mdpaper_verify_document(session_id="...")
```

確認：
- 所有 section 已插入
- 格式正確
- 無遺漏

---

## Step 7: 檢查字數限制

```
mcp_mdpaper_check_word_limits(session_id="...")
```

---

## Step 8: 儲存文件

```
mcp_mdpaper_save_document(
    session_id="...",
    output_path="output/manuscript_v1.docx"
)
```

---

## 📋 完成檢查

- [ ] 模板已選擇
- [ ] 模板結構已了解
- [ ] Session 已建立
- [ ] 所有 sections 已插入
- [ ] 文件已驗證
- [ ] 字數符合限制
- [ ] Word 檔已儲存
