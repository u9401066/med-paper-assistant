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
list_templates → read_template → read_draft → start_document_session
→ insert_section × N → verify_document → check_word_limits → save_document
```

## MCP Tools

| Tool                     | 用途                              | 關鍵參數                                        |
| ------------------------ | --------------------------------- | ----------------------------------------------- |
| `list_templates`         | 列出可用模板                      | 無                                              |
| `read_template`          | 讀取模板結構（必先呼叫！）        | `template_name`                                 |
| `start_document_session` | 開啟編輯 session                  | `template_name`, `session_id`                   |
| `insert_section`         | 插入章節內容（自動修復 wikilink） | `session_id`, `section_name`, `content`, `mode` |
| `verify_document`        | 驗證文件狀態                      | `session_id`                                    |
| `check_word_limits`      | 檢查字數限制                      | `session_id`, `limits_json`(optional)           |
| `save_document`          | 儲存並關閉 session                | `session_id`, `output_filename`                 |

`export_word`（Legacy）：簡易匯出，建議改用 session 流程。

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

- 字數超標 → `insert_section(mode="replace")` 重新插入修改後內容
- Session 存在記憶體中，MCP 重啟會遺失 → 分批 `save_document`
- `insert_section` 自動修復 wikilink 格式問題
