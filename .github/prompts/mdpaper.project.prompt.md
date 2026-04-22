---
description: "📁 mdpaper.project - 專案建立與管理"
---

# 專案管理

技能：project-management

## 流程

1. `project_action(action="list")` → 檢查現有專案
2. 選路徑後建立或切換專案
	- Library Wiki Path → `project_action(action="create", name, description, workflow_mode="library-wiki", paper_type="other")`
	- Manuscript Path → `project_action(action="create", name, description, workflow_mode="manuscript", paper_type="original-research")`
	- 切換 → `project_action(action="switch", slug)`
3. `project_action(action="setup")` → 設定偏好；只有 manuscript path 需要 paper type / target journal
4. `workspace_state_action(action="sync", doing="project setup", next_action="literature search or library ingestion")`

## 路徑切換

- library → manuscript：`project_action(action="update", workflow_mode="manuscript", paper_type="...")`
- manuscript → library：`project_action(action="update", workflow_mode="library-wiki")`

Paper types: `original-research` `systematic-review` `case-report` `letter` `meta-analysis` `narrative-review`

下一步：`/mdpaper.search` 搜尋文獻；library path 先做 ingest / organize，manuscript path 再進 concept / draft
