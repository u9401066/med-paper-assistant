---
name: code-reviewer
description: 程式碼審查。觸發：review、審查、檢查、看一下、有沒有問題、安全。
---

# 程式碼審查技能

觸發：review、審查程式碼、檢查、看一下、有問題嗎、安全

工具：`read_file`、`grep_search`、`get_errors`、`run_in_terminal("ruff check .")`、`run_in_terminal("mypy .")`

---

## 審查項目

### 程式碼品質
函數長度（`grep_search("def ")`）、命名清晰度、DRY 原則（搜尋重複）、複雜度（巢狀/分支）

### 安全性

| 風險 | grep 模式 |
|------|-----------|
| SQL 注入 | `execute.*%s\|f".*SELECT` |
| XSS | `innerHTML\|dangerouslySetInnerHTML` |
| 敏感資料 | `password\|secret\|api_key` |
| 硬編碼密碼 | `password.*=.*['"]` |

### 效能
N+1 查詢（迴圈內 DB 呼叫）、不必要迴圈

## 工作流

1. `ruff check src/` + `mypy src/` + `get_errors()`
2. `read_file` 目標檔案
3. `grep_search` 安全風險模式
4. 彙整報告（優點 / 建議 / 品質+安全+效能評分 0-10）
