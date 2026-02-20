---
name: project-init
description: 初始化新專案。觸發：init、新專案、初始化、create project。
---

# 專案初始化技能

觸發：初始化新專案、create project、bootstrap、scaffold

工具：`create_directory`、`create_file`、`run_in_terminal`、`create_new_workspace`

---

## 專案結構

`.github/bylaws/` `.github/prompts/` `.claude/skills/` `memory-bank/`(activeContext + progress + decisionLog) `src/` `tests/` + `CONSTITUTION.md` `README.md` `CHANGELOG.md` `pyproject.toml`

## 互動式設定

| 項目     | 選項                        |
| -------- | --------------------------- |
| 專案名稱 | 自訂                        |
| 程式語言 | Python / TypeScript / Other |
| 授權     | MIT / Apache-2.0 / GPL-3.0  |
| Docker   | 是 / 否                     |
| CI/CD    | GitHub Actions / None       |

## 工作流

1. 取得專案資訊（名稱、語言、授權）
2. 建立目錄結構（src, tests, memory-bank, .github, .claude）
3. 建立基礎檔案（README, CHANGELOG, pyproject.toml）
4. `git init` → `uv venv && uv sync`（Python 用 uv）
