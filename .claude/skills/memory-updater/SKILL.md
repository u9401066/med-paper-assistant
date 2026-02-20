---
name: memory-updater
description: 更新 Memory Bank 檔案。觸發：memory、記憶、進度、存檔、sync、做到哪。
---

# Memory Bank 更新技能

觸發：更新 memory、記錄進度、存檔、sync、工作階段結束時自動觸發

---

## MCP Tools

| 工具                          | 用途                                |
| ----------------------------- | ----------------------------------- |
| `memory_bank_update_progress` | progress.md (done/doing/next)       |
| `memory_bank_update_context`  | activeContext.md                    |
| `memory_bank_log_decision`    | decisionLog.md（重大決策）          |
| `memory_bank_show_memory`     | 顯示記憶內容                        |
| `memory_bank_switch_mode`     | 切換模式 (architect/code/ask/debug) |

## 檔案與時機

| 檔案              | 更新時機        |
| ----------------- | --------------- |
| activeContext.md  | 每次切換任務    |
| progress.md       | 完成任務時      |
| decisionLog.md    | 架構/技術決策時 |
| productContext.md | 專案設定變更時  |
| systemPatterns.md | 發現新模式時    |

## 原則

增量更新、保持簡潔、重要項目加日期、標記相關檔案和決策
