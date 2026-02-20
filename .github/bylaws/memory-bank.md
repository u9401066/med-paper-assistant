# 子法：Memory Bank 操作規範

> 父法：CONSTITUTION.md 第二章

---

## 第 0 條：強制寫入位置

**⚠️ 重要：所有記憶檔案必須寫入 `memory-bank/` 目錄**

```
memory-bank/                    # ✅ 唯一合法位置
├── activeContext.md           # 當前工作焦點
├── progress.md                # 進度追蹤
├── decisionLog.md             # 決策日誌
├── productContext.md          # 產品/專案背景
├── projectBrief.md            # 專案簡介
├── architect.md               # 架構設計
├── systemPatterns.md          # 系統模式
└── techContext.md             # 技術背景 (可選)
```

**禁止寫入的位置：**

- ❌ `.memory/` - 已廢棄
- ❌ 根目錄的任何 `.md` 檔案
- ❌ 其他自定義目錄

**原因：**

1. 統一管理，便於版本控制
2. 與 Skills 和 Bylaws 整合
3. 跨對話持久化

---

## 第 1 條：必要更新矩陣

| 操作       | activeContext | progress | decisionLog | productContext | architect |
| ---------- | :-----------: | :------: | :---------: | :------------: | :-------: |
| 開始新任務 |      ✅       |    ✅    |      -      |       -        |     -     |
| 完成任務   |      ✅       |    ✅    |      -      |       -        |     -     |
| 技術決策   |       -       |    -     |     ✅      |       -        |    ⚪     |
| 架構變更   |       -       |    -     |     ✅      |       -        |    ✅     |
| 新增依賴   |       -       |    -     |     ⚪      |       ✅       |     -     |
| 修 Bug     |      ⚪       |    ✅    |      -      |       -        |     -     |

✅ = 必須 ⚪ = 建議 - = 不需要

## 第 2 條：activeContext.md 格式

```markdown
# Active Context

## 當前焦點

[正在處理的主要任務]

## 相關檔案

- `path/to/file.py` - 用途說明

## 待解決問題

- [ ] 問題 1
- [ ] 問題 2

## 上下文

[任何對當前工作有幫助的背景資訊]

## 更新時間

YYYY-MM-DD HH:mm
```

## 第 3 條：progress.md 格式

```markdown
# Progress

## Done

- [x] 任務 (YYYY-MM-DD)

## Doing

- [ ] 當前任務

## Next

- [ ] 計劃任務

## Blocked

- [ ] 被阻塞的任務 - 原因
```

## 第 4 條：decisionLog.md 格式

```markdown
# Decision Log

## [YYYY-MM-DD] 決策標題

### 背景

為什麼需要做這個決策？

### 選項

1. 選項 A - 優缺點
2. 選項 B - 優缺點

### 決定

選擇了什麼？

### 理由

為什麼選這個？

### 影響

這個決定會影響什麼？
```
