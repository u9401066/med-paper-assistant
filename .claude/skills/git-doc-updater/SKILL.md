---
name: git-doc-updater
description: Git 提交前文檔同步。觸發：docs、文檔、sync docs、發布。
---

# Git 文檔自動更新技能

觸發：更新文檔、sync docs、準備發布、被 git-precommit 自動調用

工具：`read_file`、`replace_string_in_file`、`get_changed_files`、`memory_bank_update_progress`

---

## 更新對應

| 文檔         | 更新條件        | 調用 Skill        |
| ------------ | --------------- | ----------------- |
| README.md    | 新功能/依賴變更 | readme-updater    |
| CHANGELOG.md | 任何代碼變更    | changelog-updater |
| ROADMAP.md   | 完成里程碑      | roadmap-updater   |
| memory-bank/ | 每次提交        | memory-updater    |

## 工作流

1. `get_changed_files()` 分析變更
2. 判斷更新：src/ 新檔→README、pyproject.toml→README 安裝、任何變更→CHANGELOG、ROADMAP 項目→ROADMAP
3. 依序呼叫對應 Skill
4. `memory_bank_update_progress()` 同步
