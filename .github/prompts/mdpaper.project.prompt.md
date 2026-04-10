---
description: "📁 mdpaper.project - 專案建立與管理"
---

# 專案管理

技能：project-management

## 流程

1. `project_action(action="list")` → 檢查現有專案
2. 新建 → `project_action(action="create", name, description, paper_type)` / 切換 → `project_action(action="switch", slug)`
3. `project_action(action="setup")` → 設定 paper type + 偏好
4. `workspace_state_action(action="sync", doing="project setup", next_action="literature search")`

Paper types: `original-research` `systematic-review` `case-report` `letter` `meta-analysis` `narrative-review`

下一步：`/mdpaper.search` 搜尋文獻
