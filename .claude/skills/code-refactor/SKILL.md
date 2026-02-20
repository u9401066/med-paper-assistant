---
name: code-refactor
description: Proactively detect and execute code refactoring to maintain DDD architecture and code quality. Triggers: RF, refactor, 重構, 拆分, split, 模組化, modularize, 太長, cleanup, 整理, 優化, optimize, 抽出, extract, 簡化, simplify, 太亂, 難讀.
---

# 程式碼重構技能

主動偵測並執行程式碼重構，維持 DDD 架構和程式碼品質。

觸發：「重構」「refactor」「太長了」「模組化」「拆分」，或偵測到超過閾值時主動觸發。

---

## 閾值設定

| 類型 | 警告 | 強制重構 |
|------|------|----------|
| 檔案 | > 200 行 | > 400 行 |
| 類別 | > 150 行 | > 300 行 |
| 函數 | > 30 行 | > 50 行 |
| 目錄檔案數 | > 10 | > 15 |
| 圈複雜度 | > 10 | > 15 |
| 巢狀深度 | > 3 層 | > 4 層 |
| 參數數量 | > 4 | > 6 |
| 依賴數量 | > 5 | > 8 |

---

## 重構模式庫

| # | 模式 | 觸發條件 |
|---|------|----------|
| 1 | Extract Method | 函數過長、重複邏輯 |
| 2 | Extract Class | 類別職責過多、>150 行 |
| 3 | Replace Conditional with Polymorphism | 大量 if-elif-else |
| 4 | Introduce Parameter Object | 參數 >4 個 |
| 5 | Split Module | 目錄 >10 檔案 → 按子領域拆分 |

---

## DDD 架構守護

依賴方向：`Presentation → Application → Domain ← Infrastructure`

禁止：Domain 依賴 Infrastructure、Presentation 直接存取 Domain、Entity 包含持久化邏輯。

---

## 重構流程

1. **偵測**：報告檔案/函數/複雜度超標情況
2. **分析**：識別重複邏輯、隱藏 Value Object、職責分離點
3. **規劃**：列出重構步驟（新檔案、遷移、測試）
4. **執行**：逐步重構，每步確認測試通過
5. **驗證**：全部測試通過、覆蓋率、複雜度、DDD 合規

---

## 與其他 Skills 整合

| Skill | 整合 |
|-------|------|
| code-reviewer | 審查時觸發重構建議 |
| test-generator | 重構前先生成測試 |
| ddd-architect | 確保重構符合 DDD |
| memory-updater | 記錄重構決策 |
