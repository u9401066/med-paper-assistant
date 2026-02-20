---
name: roadmap-updater
description: 更新 ROADMAP.md 狀態。觸發：roadmap、路線、規劃、里程碑。
---

# ROADMAP 更新技能

觸發：更新 roadmap、完成里程碑、被 git-precommit 自動調用

工具：`read_file("ROADMAP.md")`、`replace_string_in_file`、`grep_search`

---

## 狀態標記

📋 計劃中 → 🚧 進行中 → ✅ 已完成

格式：`- [ ] 項目` → `- [x] 項目 ✅ (YYYY-MM-DD)`

## 工作流

1. `read_file("ROADMAP.md")`
2. 從 commit message / 用戶說明分析完成項目
3. `replace_string_in_file` 更新 `- [ ]` → `- [x] ✅ (date)`
