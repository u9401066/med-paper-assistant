---
name: project-management
description: |
  研究專案的建立、切換、設定管理。
  LOAD THIS SKILL WHEN: 新專案、切換專案、專案設定、paper type、start exploration、convert exploration
  CAPABILITIES: create_project, list_projects, switch_project, get_current_project, setup_project_interactive, start_exploration, convert_exploration_to_project
---

# 專案管理技能

| 觸發語           | 操作                                                                       |
| ---------------- | -------------------------------------------------------------------------- |
| 新專案、開始研究 | `create_project(name, description, paper_type)`                            |
| 切換、換專案     | `list_projects()` → `switch_project(slug)`                                 |
| 設定 paper type  | `setup_project_interactive()`                                              |
| 先瀏覽文獻       | `start_exploration()`                                                      |
| 轉成正式專案     | `convert_exploration_to_project(name, description)`                        |
| 改設定           | `update_project_settings(paper_type/target_journal/status/citation_style)` |
| 查目前專案       | `get_current_project(include_files=True)`                                  |

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
2. `create_project(name, description, paper_type)`
3. `setup_project_interactive()` — 互動式設定

### B: 切換專案

1. `list_projects()` → 用戶選擇 → `switch_project(slug)`
2. 讀 `projects/{slug}/.memory/activeContext.md`

### C: 探索模式

1. `start_exploration()` → 建立 ~exploration 臨時工作區
2. 搜尋 + 儲存文獻
3. `convert_exploration_to_project(name, description)` → 文獻自動遷移

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
| 不確定用哪個  | `list_projects()`                           |
| 先看文獻      | `start_exploration()`                       |
| 改 paper type | `update_project_settings(paper_type="...")` |
