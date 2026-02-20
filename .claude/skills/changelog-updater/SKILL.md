---
name: changelog-updater
description: 更新 CHANGELOG.md。觸發：changelog、變更、版本、發布、改了什麼。
---

# CHANGELOG 更新技能

觸發：更新 changelog、發布、新版本、被 git-precommit 自動調用

工具：`read_file("CHANGELOG.md")`、`replace_string_in_file`、`get_changed_files`

---

## 格式（Keep a Changelog）

`## [Unreleased]` → `### Added/Changed/Deprecated/Removed/Fixed/Security`

## 分類規則

| 類型 | 關鍵字 |
|------|--------|
| Added | feat, 新增, add |
| Changed | change, update, 變更 |
| Deprecated | deprecate, 棄用 |
| Removed | remove, delete, 移除 |
| Fixed | fix, bug, 修復 |
| Security | security, 安全 |

## 版本號（SemVer）

MAJOR：Breaking Changes | MINOR：新功能（向下相容）| PATCH：Bug 修復

## 工作流

1. `read_file("CHANGELOG.md")` + `get_changed_files()`
2. 分類：新檔案→Added、修改→Changed/Fixed、刪除→Removed
3. 更新 `[Unreleased]` 區塊
