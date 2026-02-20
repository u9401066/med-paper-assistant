---
description: "🔍 code-quality - 程式碼品質檢查流程"
---

# 程式碼品質檢查

編排：code-reviewer → test-generator → ddd-architect

## Phase 1: 靜態分析

`uv run ruff check src/ tests/` → `uv run mypy src/` → 彙整 lint/type error 數量

## Phase 2: 測試

`uv run pytest tests/ -v --tb=short` → `uv run pytest tests/ --cov=src --cov-report=term-missing`

識別：未測試 function、覆蓋率 < 80% 模組

## Phase 3: 架構審查（DDD）

✅ Presentation → Application → Domain ← Infrastructure
❌ 反向依賴 = 違規
檢查：Domain 不依賴 Infrastructure、Application 不直接存取 DB、模組邊界清晰

## Phase 4: 程式碼審查

安全：硬編碼密碼、SQL injection、Path traversal
可讀：函數 > 50 行、巢狀 > 3 層、命名
效能：N+1 查詢、重複計算

## 報告格式

摘要（靜態分析 ✅/❌、覆蓋率 X%、架構 ✅/❌、安全 ✅/❌）→ 必須修復 → 建議改善

## 快速模式

`uv run ruff check src/ && uv run pytest tests/ -q`
