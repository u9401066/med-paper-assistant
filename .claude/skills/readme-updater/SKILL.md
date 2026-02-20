---
name: readme-updater
description: 更新 README.md。觸發：readme、說明、文檔、怎麼用、安裝說明。
---

# README 更新技能

觸發：更新 README、文檔、怎麼用、安裝說明、被 git-precommit 自動調用

工具：`read_file("README.md")`、`replace_string_in_file`、`list_dir`、`get_changed_files`

---

## 更新對應

| 變更類型 | 更新區塊 |
|----------|----------|
| 新功能 | 功能列表 |
| 新依賴 | 安裝說明 |
| API 變更 | 使用範例 |
| 目錄變更 | 專案結構 |
| 新設定 | 配置說明 |

## 保護區塊（不自動修改）

授權資訊、貢獻指南、致謝

## 工作流

1. `read_file("README.md")` + `get_changed_files()`
2. 分析變更 → 對應更新區塊
3. `replace_string_in_file` 更新對應區塊
