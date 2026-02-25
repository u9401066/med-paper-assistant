# 子法：Git 工作流規範

> 父法：CONSTITUTION.md 第三章

## 第 1 條：提交前檢查清單

依序執行以下步驟（可透過 `--skip-X` 跳過）：

| 順序 | 項目                 | Skill               | 可跳過 |
| ---- | -------------------- | ------------------- | ------ |
| 1    | Memory Bank 同步     | `memory-updater`    | ❌     |
| 2    | README 更新          | `readme-updater`    | ✅     |
| 3    | CHANGELOG 更新       | `changelog-updater` | ✅     |
| 4    | ROADMAP 標記         | `roadmap-updater`   | ✅     |
| 5    | 架構文檔（如有變更） | `arch-updater`      | ✅     |

## 第 2 條：Commit Message 格式

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Type 類型

- `feat`: 新功能
- `fix`: 修復
- `docs`: 文檔
- `refactor`: 重構
- `test`: 測試
- `chore`: 雜項

## 第 3 條：分支策略

| 分支        | 用途     | 保護 |
| ----------- | -------- | ---- |
| `main`      | 穩定版本 | ✅   |
| `develop`   | 開發整合 | ✅   |
| `feature/*` | 功能開發 | ❌   |
| `hotfix/*`  | 緊急修復 | ❌   |

## 第 4 條：Commit 粒度

一個 commit 應對應一個邏輯變更單元：

- 一個 `feat` = 一個 commit（含其測試和文檔）
- 跨功能的 `chore`（lint、docs、version bump）= 獨立 commit
- 緊急 `hotfix` 允許合併多個修復，但需在 body 說明
