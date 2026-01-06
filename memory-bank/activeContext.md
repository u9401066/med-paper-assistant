# Active Context

## User Preferences
- **Git Identity**: u9401066 <u9401066@gap.kmu.edu.tw>

## 當前焦點
Artifact-Centric Architecture 設計文件完成 ✅

## 最近變更 (2025-01-22)

### 1. Artifact-Centric Architecture 設計 🆕

**完成文件**：
- `docs/design/artifact-centric-architecture.md` - 完整設計（480+ 行）
- ROADMAP.md - 新增 Phase 5a
- Memory Bank - 更新 decisionLog, progress, architect
- README (EN/ZH) - Coming Soon 預告
- AGENTS.md - 新架構 Agent 指引

**設計決策**：
| 問題 | 決策 | 理由 |
|------|------|------|
| 成品歸屬 | Reference（多對多） | 彈性最高 |
| 強制專案時機 | Export 時 | 探索零阻力 |
| 向後相容 | Keep Both | 最小影響 |

**新工具預告**（+6）：
- `start_exploration` - 啟動探索模式
- `get_exploration_status` - 查看 staging 狀態
- `list_staged_artifacts` - 列出暫存成品
- `tag_artifact` - 標記成品
- `link_artifact_to_project` - 連結成品到專案
- `convert_exploration_to_project` - 探索轉專案

### 2. Workspace State 跨 Session 持久化 ✅ (稍早)
- `WorkspaceStateManager` singleton
- `.mdpaper-state.json` 狀態檔案
- 3 個新工具：get/sync/clear workspace state
- 工具數：69 → 72

## 工具統計
- 目前工具數：72 個
- 設計中新工具：+6 個（Exploration）

## 下一步
- [ ] Git commit + push 設計文件
- [ ] 實作 Phase 1: Foundation（_workspace/ + ArtifactRegistry）
- [ ] 或處理其他優先事項

## 更新時間
2025-01-22
