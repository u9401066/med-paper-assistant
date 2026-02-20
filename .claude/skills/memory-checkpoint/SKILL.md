---
name: memory-checkpoint
description: Externalize detailed memory to Memory Bank before conversation summarization to prevent context loss. Triggers: CP, checkpoint, save, 存檔, 記一下, 保存, sync memory, dump, 先記著, 等一下, 要離開, 暫停, pause, 儲存進度, 怕忘記.
---

# Memory Checkpoint 技能

在對話被 Summarize 前，主動將關鍵記憶寫入 `memory-bank/`，避免上下文遺失。

## 觸發時機

| 自動         | 手動                   |
| ------------ | ---------------------- |
| 對話 >10 輪  | 「checkpoint」「存檔」 |
| 修改 >5 檔案 | 「先記一下」「要離開」 |
| 完成重要功能 | 「sync memory」        |
| 從設計轉實作 |                        |

---

## 更新檔案

| 檔案               | 必要 | 內容                                 |
| ------------------ | :--: | ------------------------------------ |
| `activeContext.md` |  ✅  | 焦點、變更檔案、待解決、決策、下一步 |
| `progress.md`      |  ✅  | Done / Doing / Next                  |
| `decisionLog.md`   |  ⚪  | 新決策（背景→選項→決定→原因）        |
| `architect.md`     |  ⚪  | 架構變更（如有）                     |

---

## 品質要求

| 必須 | 說明                            |
| :--: | ------------------------------- |
|  ✅  | 當前焦點（一句話）              |
|  ✅  | 變更檔案列表（完整路徑 + 簡述） |
|  ✅  | 待解決事項                      |
|  ✅  | 下一步                          |
|  ✅  | 時間戳記                        |
|  ⚪  | 重要決策（如有）                |

---

## 整合

- **git-precommit**：commit 前 → checkpoint → 同步 → commit
- **memory-updater**：checkpoint = 批次更新，updater = 增量更新
