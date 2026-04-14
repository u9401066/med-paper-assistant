---
name: word-export
description: |
  Word 匯出技能 - 將草稿匯出為符合期刊格式的 Word 文件。
  LOAD THIS SKILL WHEN: 匯出 Word、export、template、word count、轉成 docx
---

# Word Export

## 匯出前必須完成

1. Concept 驗證通過（novelty ≥ 75）
2. 草稿已完成所有必要章節
3. 引用文獻格式正確

## 工作流程（必須按順序）

```
inspect_export(action="list_templates")
→ inspect_export(action="read_template")
→ read_draft
→ export_document(action="session_start")
→ export_document(action="session_insert") × N
→ inspect_export(action="verify_document")
→ export_document(action="session_save")
→ export_document(action="docx") / export_document(action="pdf")
```

## MCP Tools

| Facade Call                                                        | 用途                              | 關鍵參數                                        |
| ------------------------------------------------------------------ | --------------------------------- | ----------------------------------------------- |
| `inspect_export(action="list_templates")`                          | 列出可用模板                      | 無                                              |
| `inspect_export(action="read_template")`                           | 讀取模板結構（必先呼叫）          | `template_name`                                 |
| `export_document(action="session_start")`                          | 開啟編輯 session                  | `template_name`, `session_id`                   |
| `export_document(action="session_insert")`                         | 插入章節內容（自動修復 wikilink） | `session_id`, `section_name`, `content`, `mode` |
| `inspect_export(action="verify_document")`                         | 驗證文件狀態與字數限制            | `session_id`, `limits_json`                     |
| `export_document(action="session_save")`                           | 儲存並關閉 session                | `session_id`, `output_filename`                 |
| `export_document(action="docx")` / `export_document(action="pdf")` | 直接產出 DOCX / PDF               | `draft_filename`, `output_filename`, `project`  |

> Legacy export verbs `list_templates`, `read_template`, `start_document_session`,
> `insert_section`, `verify_document`, `save_document`, `export_docx`, `export_pdf`
> 保留相容性；first-party orchestration 一律優先走 `inspect_export` / `export_document`。

## 預設字數限制

| 章節         | 上限 |
| ------------ | ---- |
| Abstract     | 250  |
| Introduction | 800  |
| Methods      | 1500 |
| Results      | 1500 |
| Discussion   | 1500 |
| Conclusions  | 300  |

## 注意事項

- 字數超標 → `export_document(action="session_insert", mode="replace")` 重新插入修改後內容
- Session 存在記憶體中，MCP 重啟會遺失 → 分批 `export_document(action="session_save")`
- `export_document(action="session_insert")` 自動修復 wikilink 格式問題
