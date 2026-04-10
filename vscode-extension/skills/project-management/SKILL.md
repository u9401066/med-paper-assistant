---
name: project-management
description: |
  研究專案的建立、切換、設定管理。
  LOAD THIS SKILL WHEN: 新專案、切換專案、專案設定、paper type、start exploration、convert exploration
  CAPABILITIES: project_action, workspace_state_action
---

# 專案管理技能

| 觸發語           | 操作                                                                                         |
| ---------------- | -------------------------------------------------------------------------------------------- |
| 新專案、開始研究 | `project_action(action="create", name, description, paper_type)`                           |
| 切換、換專案     | `project_action(action="list")` → `project_action(action="switch", slug)`               |
| 設定 paper type  | `project_action(action="setup")`                                                           |
| 先瀏覽文獻       | `project_action(action="start_exploration")`                                               |
| 轉成正式專案     | `project_action(action="convert_exploration", name, description, paper_type)`             |
| 改設定           | `project_action(action="update", paper_type/target_journal/status/citation_style)`        |
| 查目前專案       | `project_action(action="current", include_files=True)`                                     |
| 查 workspace 狀態 | `workspace_state_action(action="get")`                                                     |

> Legacy verbs `create_project`, `list_projects`, `switch_project`, `get_current_project`,
> `setup_project_interactive`, `start_exploration`, `convert_exploration_to_project`,
> `sync_workspace_state` 僅保留相容性；first-party orchestration 一律優先走 façade。

---

## Paper Types

| 代碼                | 名稱       | 結構            |
| ------------------- | ---------- | --------------- |
| `original-research` | 原創研究   | IMRAD           |
| `systematic-review` | 系統性回顧 | PRISMA          |
| `meta-analysis`     | 統合分析   | PRISMA + Forest |
| `case-report`       | 病例報告   | CARE            |
| `review-article`    | 回顧文章   | 敘事結構        |
| `letter`            | 讀者來函   | 精簡結構        |

---

## 工作流

### A: 建立新專案

1. 問用戶：專案名稱（**必須英文**，中文 → 翻譯）、描述、論文類型
2. `project_action(action="create", name, description, paper_type)`
3. `project_action(action="setup")` — 互動式設定
4. `workspace_state_action(action="sync", doing="project setup", next_action="concept development")`

### B: 切換專案

1. `project_action(action="list")` → 用戶選擇 → `project_action(action="switch", slug)`
2. 讀 `projects/{slug}/.memory/activeContext.md`

### C: 探索模式

1. `project_action(action="start_exploration")` → 建立 ~exploration 臨時工作區
2. 搜尋 + 儲存文獻
3. `project_action(action="convert_exploration", name, description)` → 文獻自動遷移

---

## Project Memory

| 時機   | 動作                                                |
| ------ | --------------------------------------------------- |
| 切換後 | 讀 `.memory/activeContext.md`                       |
| 離開前 | 寫 `.memory/activeContext.md`（進度 + 文獻 + 筆記） |

## 常見問題

| 問題          | 解法                                        |
| ------------- | ------------------------------------------- |
| 中文名稱      | Agent 翻成英文                              |
| 不確定用哪個  | `project_action(action="list")`           |
| 先看文獻      | `project_action(action="start_exploration")` |
| 改 paper type | `project_action(action="update", paper_type="...")` |

---

## Journal Profile（期刊設定）

系統內建麻醉學前 20 大期刊的投稿設定檔（`templates/journal-profiles/`），包含字數限制、圖表上限、引用格式等。

**使用方式**：

- 用戶只需告訴 Copilot 目標期刊名稱（如「我要投 BJA」）
- Agent 讀取對應 YAML → 複製到 `projects/{slug}/journal-profile.yaml`
- 所有 Writing Hooks 自動套用該期刊的約束

**可用指令**：

```
# 查看所有可用期刊
read_file templates/journal-profiles/_index.yaml

# 讀取特定期刊設定
read_file templates/journal-profiles/bja.yaml

# 套用到專案
cp templates/journal-profiles/bja.yaml projects/{slug}/journal-profile.yaml
```

💡 **提醒用戶**：可以直接請 Copilot 讀取期刊的設定資料來建立 journal-profile.yaml，不需手動操作。
