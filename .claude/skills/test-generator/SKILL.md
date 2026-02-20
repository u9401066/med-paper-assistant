---
name: test-generator
description: 生成測試套件。觸發：test、測試、寫測試、coverage、覆蓋率、pytest、unittest、驗證、TG、unit test、整合測試、e2e、static、ruff、mypy、lint。
---

# 測試生成技能

## 靜態分析

| 工具    | 用途               | 命令                                                      |
| ------- | ------------------ | --------------------------------------------------------- |
| ruff    | Linter + Formatter | `uv run ruff check src/ --fix && uv run ruff format src/` |
| mypy    | 類型檢查           | `uv run mypy src/ --ignore-missing-imports`               |
| bandit  | 安全掃描           | `uv run bandit -r src/ -ll`                               |
| vulture | 死代碼檢測         | `uv run vulture src/ --min-confidence 80`                 |

完整：`uv run ruff check src/; uv run mypy src/ --ignore-missing-imports; uv run bandit -r src/ -ll`

---

## 測試金字塔

| 層級        | 工具           | 目錄               |
| ----------- | -------------- | ------------------ |
| Unit        | pytest         | tests/unit/        |
| Integration | pytest + httpx | tests/integration/ |
| E2E         | playwright     | tests/e2e/         |
| Coverage    | pytest-cov     | 目標 ≥80%          |

---

## 單元測試必涵蓋

1. Happy Path — 正常流程
2. Edge Cases — 邊界條件
3. Error Handling — `pytest.raises`
4. Parametrize — `@pytest.mark.parametrize`

---

## 執行命令

```bash
pytest tests/unit -v                          # 單元
pytest tests/integration -v -m integration    # 整合
pytest --cov=src --cov-report=term-missing --cov-fail-under=80  # 覆蓋率
```

---

## Checklist

- [ ] Happy path + edge cases + error handling
- [ ] Fixtures 設定（conftest.py）
- [ ] 覆蓋率 ≥ 80%
- [ ] CI workflow 整合
