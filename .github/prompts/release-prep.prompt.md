---
description: "🚢 release-prep - 發布準備流程"
---

# 發布準備流程

編排：code-quality → changelog-updater → readme-updater → git-precommit

## Phase 1: 品質確認

`uv run ruff check src/ tests/` → `uv run mypy src/` → `uv run pytest tests/ -v --cov=src`

必須通過：lint 無 error、測試全過、覆蓋率 ≥ 80%

## Phase 2: 更新文件

1. CHANGELOG（changelog-updater）— 分類 git log 為 Added/Changed/Fixed/etc
2. README（readme-updater）— 安裝指令、功能、範例、版本號
3. ROADMAP（roadmap-updater）— 標記完成項

## Phase 3: 版本更新（SemVer）

| Breaking | New features | Bug fixes |
|----------|-------------|-----------|
| Major | Minor | Patch |

同步：`pyproject.toml` + `CHANGELOG.md` 標題 + `__version__`

## Phase 4: 提交與標籤

`git add -A && git commit -m "chore: release vX.Y.Z"` → `git tag -a vX.Y.Z` → `git push origin master && git push origin vX.Y.Z`

## Phase 5: 發布後

`uv build && uv publish`（如適用）→ GitHub Release（CHANGELOG 內容）→ Memory Bank 更新

## 回滾

`git tag -d vX.Y.Z` → `git push origin :refs/tags/vX.Y.Z` → `git revert HEAD && git push`
