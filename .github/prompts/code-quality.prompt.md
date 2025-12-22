---
description: "🔍 code-quality - 程式碼品質檢查流程"
---

# 程式碼品質檢查流程

📖 **Capability 類型**: 高層編排
📖 **編排 Skills**: code-reviewer → test-generator → ddd-architect

---

## 🎯 此 Capability 的目標

全面檢查程式碼品質，包含：
1. 靜態分析（ruff, mypy）
2. 測試覆蓋率
3. 架構合規性（DDD）
4. 程式碼審查

---

## Phase 1: 靜態分析 `lint`

### Step 1.1: 執行 ruff 檢查

```bash
uv run ruff check src/
uv run ruff check tests/
```

### Step 1.2: 執行 mypy 檢查

```bash
uv run mypy src/ --config-file pyproject.toml
```

### Step 1.3: 彙整問題

```
向用戶報告：
- Linting 錯誤數量
- Type 錯誤數量
- 是否有 auto-fix 可用
```

---

## Phase 2: 測試檢查 `test`

📖 Skill: `.claude/skills/test-generator/SKILL.md`

### Step 2.1: 執行現有測試

```bash
uv run pytest tests/ -v --tb=short
```

### Step 2.2: 檢查覆蓋率

```bash
uv run pytest tests/ --cov=src --cov-report=term-missing
```

### Step 2.3: 識別未測試區域

```
列出：
- 沒有測試的 function/method
- 覆蓋率低於 80% 的模組
- 建議補充的測試
```

---

## Phase 3: 架構審查 `architecture`

📖 Skill: `.claude/skills/ddd-architect/SKILL.md`

### Step 3.1: 檢查分層

```
確認：
- Domain 層不依賴 Infrastructure
- Application 層不直接存取資料庫
- DAL 是否獨立
```

### Step 3.2: 檢查依賴方向

```
Presentation → Application → Domain ← Infrastructure

任何反向依賴 = 違規
```

### Step 3.3: 檢查模組邊界

```
每個模組應該：
- 有清晰的 public interface
- 內部細節不暴露
- 依賴注入而非直接建立
```

---

## Phase 4: 程式碼審查 `review`

📖 Skill: `.claude/skills/code-reviewer/SKILL.md`

### Step 4.1: 安全性檢查

```
檢查：
- 硬編碼密碼/API key
- SQL injection 風險
- Path traversal 風險
```

### Step 4.2: 可讀性檢查

```
檢查：
- 過長的 function（> 50 行）
- 過深的巢狀（> 3 層）
- 命名是否清楚
- 註解是否充足
```

### Step 4.3: 效能檢查

```
檢查：
- N+1 查詢
- 不必要的重複計算
- 記憶體洩漏風險
```

---

## 📋 品質報告

```markdown
# 程式碼品質報告

## 摘要
- 靜態分析: ✅/❌ (N 個問題)
- 測試覆蓋: X% (目標 80%)
- 架構合規: ✅/❌
- 安全性: ✅/❌

## 詳細問題

### 必須修復
1. [問題描述] - [位置]

### 建議改善
1. [建議描述] - [位置]

## 下一步
- [ ] 修復 ruff 錯誤
- [ ] 補充測試
- [ ] 重構過長函數
```

---

## ⏸️ 快速模式

如果只需要快速檢查：

```bash
# 一行指令
uv run ruff check src/ && uv run pytest tests/ -q
```
