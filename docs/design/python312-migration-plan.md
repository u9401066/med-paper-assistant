# Python 3.12 + UV 遷移計畫

> **目標**：將專案從 Python 3.11 升級到 3.12，並完全採用 UV 管理

---

## 📊 現況

| 項目             | 現況                    | 目標          |
| ---------------- | ----------------------- | ------------- |
| Python 版本      | 3.11                    | **3.12**      |
| 套件管理         | uv (部分)               | **uv (完全)** |
| requires-python  | `>=3.11`                | `>=3.12`      |
| submodule 相容性 | pubmed-search 要求 3.12 | ✅            |

---

## 🔧 變更內容

### 1. pyproject.toml 更新

```toml
[project]
requires-python = ">=3.12"

[tool.ruff]
target-version = "py312"

[tool.mypy]
python_version = "3.12"
```

### 2. 虛擬環境重建

```bash
# 移除舊環境
rm -rf .venv

# 使用 UV 建立 Python 3.12 環境
uv venv --python 3.12

# 同步依賴
uv sync --all-extras
```

### 3. Submodule Python 版本對齊

| Submodule         | 最低 Python | 備註      |
| ----------------- | ----------- | --------- |
| pubmed-search-mcp | 3.12        | ✅ 已滿足 |
| cgu               | 3.10        | ✅ 相容   |

---

## 📋 執行步驟

### Step 1：更新 pyproject.toml

```bash
# 自動執行
sed -i 's/requires-python = ">=3.11"/requires-python = ">=3.12"/' pyproject.toml
sed -i 's/target-version = "py310"/target-version = "py312"/' pyproject.toml
sed -i 's/python_version = "3.11"/python_version = "3.12"/' pyproject.toml
```

### Step 2：重建環境

```bash
# 清除舊環境
rm -rf .venv uv.lock

# 建立新環境
uv venv --python 3.12

# 同步所有依賴
uv sync --all-extras --all-groups

# 驗證
uv run python --version
# Expected: Python 3.12.x
```

### Step 3：更新 CI/CD

`.github/workflows/` 中的 Python 版本：

```yaml
# Before
python-version: ['3.11', '3.12']

# After
python-version: ['3.12', '3.13']
```

### Step 4：測試

```bash
# 執行測試
uv run pytest tests/ -v

# 類型檢查
uv run mypy src/

# 程式碼品質
uv run ruff check src/
```

---

## 📦 依賴更新

### 需要更新的套件

| 套件     | 原因             |
| -------- | ---------------- |
| mcp      | 確保 3.12 支援   |
| pydantic | 使用 3.12 新特性 |
| pandas   | 效能優化         |

### 新增 3.12 特性可用

| 特性           | 說明               | 使用場景     |
| -------------- | ------------------ | ------------ |
| `type` 關鍵字  | Type alias 語法糖  | 簡化類型定義 |
| `@override`    | 明確覆寫標記       | 增強可讀性   |
| 更好的錯誤訊息 | 更精確的 traceback | 除錯         |
| f-string 改進  | 可嵌套 quote       | 字串處理     |

---

## ⚠️ 風險評估

### 低風險

- 大多數套件已支援 3.12
- 無使用 deprecated 3.11 特性

### 需注意

| 項目           | 風險            | 緩解措施      |
| -------------- | --------------- | ------------- |
| CI 執行時間    | 需下載 3.12     | 使用 uv cache |
| Submodule 依賴 | 版本衝突        | 統一使用 3.12 |
| 開發環境       | 本地需安裝 3.12 | 文檔說明      |

---

## 🔄 回滾計畫

如果遇到嚴重問題：

```bash
# 還原 pyproject.toml
git checkout pyproject.toml

# 重建 3.11 環境
rm -rf .venv
uv venv --python 3.11
uv sync --all-extras
```

---

## 📅 時程

| 日期  | 任務                |
| ----- | ------------------- |
| Day 1 | 更新 pyproject.toml |
| Day 1 | 重建環境            |
| Day 2 | 執行測試            |
| Day 2 | 修復問題            |
| Day 3 | 更新文檔            |
| Day 3 | 合併到 main         |

---

## ✅ 驗收標準

- [ ] `uv run python --version` 顯示 3.12.x
- [ ] `uv run pytest` 全部通過
- [ ] `uv run mypy src/` 無錯誤
- [ ] `uv run ruff check src/` 無錯誤
- [ ] MCP server 可正常啟動
- [ ] 所有工具可正常運作
