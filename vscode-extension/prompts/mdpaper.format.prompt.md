---
description: "📄 mdpaper.format - 匯出 Word 文件"
---

# 匯出 Word

技能：word-export

## Pipeline

1. `inspect_export(action="list_templates")` → 選擇模板
2. `inspect_export(action="read_template", template_name=name)` → 確認結構
3. `read_draft("manuscript.md")` → 取得內容
4. `export_document(action="session_start", template_name=template, session_id="main")` → 建立 session
5. `export_document(action="session_insert", session_id="main", section_name=section, content=content)` — 依序插入每個 section
6. `inspect_export(action="verify_document", session_id="main")` → 確認完整
7. `export_document(action="session_save", session_id="main", output_filename=filename)` → 輸出 .docx
8. 需要直接產出 Pandoc 匯出時：`export_document(action="docx")` / `export_document(action="pdf")`

## 規則

- 每個 section 獨立 `export_document(action="session_insert")`，不合併
- `inspect_export(action="verify_document")` 失敗 → 修正後重試
- 🔒 NOVELTY / SELLING POINTS → 必完整保留
- References → `format_references()` 先格式化
