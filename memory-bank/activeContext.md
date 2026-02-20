# Active Context

## User Preferences
- **Git Identity**: u9401066 <u9401066@gap.kmu.edu.tw>

## 當前焦點
Infrastructure & Quality Cleanup 大整理完成 ✅
架構方向已確定：**Direction C: Full VSX + Foam + Pandoc**

## 最近變更 (2026-02-20)

### Infrastructure & Quality Cleanup 大整理 🆕

1. **Pre-commit Hooks** — 13 hooks 全部通過 (ruff, mypy, bandit, pytest, whitespace…)
2. **DDD Import 遷移** — 19 個測試檔從 `core.*` 遷移到 DDD 路徑
3. **Test Isolation** — 所有測試改用 `tmp_path` fixture
4. **ARCHITECTURE.md 重寫** — 448 行過時文檔 → ~240 行精確 DDD 架構
5. **Legacy Cleanup** — 刪除空的 `core/` 目錄、多餘腳本
6. **Copilot Hook 修復** — AGENTS.md 補齊 7 skills + 8 prompts
7. **Coverage Baseline** — 17 passed / 1 skipped / 26 integration (27%)
8. **ROADMAP 更新** — 新增 Phase 3.5 (cleanup) + Phase 5c (Full VSX + Pandoc)

### 架構方向決策

| 方向 | 結果 |
|------|------|
| A. Lightweight (純 MCP + Shell Prompts) | ❌ |
| B. Slim MCP | ❌ |
| **C. Full VSX + Foam + Pandoc** | **✅ 選定** |

- VS Code Extension → TreeView / CodeLens / Diagnostics
- 保留 Foam 做文獻知識圖譜
- 新增 Pandoc 支援 LaTeX + Word 雙輸出

## 工具統計
- 目前工具數：~87 個
- Python 3.12.12 / uv 0.10.0
- pre-commit 13 hooks 全部通過

## 下一步
- [ ] Phase 5c: Full VSX Extension 升級（TreeView, CodeLens, Diagnostics）
- [ ] Pandoc 整合（取代 python-docx）
- [ ] Citation Intelligence MVP 實作

## 更新時間
2026-02-20
