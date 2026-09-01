---
description: "🚢 release-prep - 發布準備流程"
---

# 發布準備流程

編排：code-quality → changelog-updater → readme-updater → git-precommit

## Phase 1: 品質確認

`uv run ruff check src/ tests/` → `uv run ruff format --check src/ tests/` → `uv run mypy src/` → `uv run pytest tests/ -q -m "not integration and not slow"`

必須通過：lint/type/security/authority 無 error、fast tests 全過、compact/full MCP 與 release integration smokes 無 unexpected error。Coverage 必須產生報告並追蹤基線，但未由 `pyproject.toml` 或 CI 設定的全 repo 百分比不能臨時當作發布 gate，也不能為提高數字加入只測常數、自建 fake 或 implementation detail 的低價值測試；本次變更的關鍵 production path 應有直接行為或整合覆蓋。

## Phase 2: 更新文件

1. CHANGELOG（changelog-updater）— 分類 git log 為 Added/Changed/Fixed/etc
2. README（readme-updater）— 安裝指令、功能、範例、版本號
3. ROADMAP（roadmap-updater）— 標記完成項

## Phase 3: 版本更新（SemVer）

| Breaking | New features | Bug fixes |
| -------- | ------------ | --------- |
| Major    | Minor        | Patch     |

同步：`pyproject.toml` + `CHANGELOG.md` 標題 + `__version__`

## Phase 4: 提交與標籤

依邏輯範圍精確 stage 並分段 commit，保留不屬於本次 release 的既有 dirty worktree；最後以 release-prep commit 收斂版本與文件。確認 `master` CI 對 release SHA 全綠後，建立 annotated `vX.Y.Z` tag 並 push。

## Phase 5: 發布後

tag-triggered Release workflow 負責 reproducible build、PyPI trusted publishing、GitHub Release 與 VSIX；不得在 workflow 尚未完成時宣告發布成功。核對公開 artifact SHA/attestation 與 release 狀態後更新 Memory Bank。Marketplace 外部授權失敗必須明示 degraded channel，不得掩蓋。

## 回滾

`git tag -d vX.Y.Z` → `git push origin :refs/tags/vX.Y.Z` → `git revert HEAD && git push`
