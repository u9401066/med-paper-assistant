# Active Context

## User Preferences
- **Git Identity**: u9401066 <u9401066@gap.kmu.edu.tw>

## Current Goals
- Phase 5c: Full VSX Extension 升級（TreeView, CodeLens, Diagnostics）
- Pandoc 整合（取代 python-docx）
- Citation Intelligence MVP 實作

## 當前焦點
本 Session 完成 6 大功能，專案已達生產級別 ✅

### Session 成果 (2026-02-22)

| # | 功能 | Commit |
|---|------|--------|
| 1 | Auto-Paper 9-Phase Pipeline + 閉環自我改進 | af887f0 |
| 2 | Dual-Hook Architecture (Copilot + Pre-Commit + General) | e754489 |
| 3 | VSX Extension v0.2.0 (388KB, 14 skills, 12 prompts) | 81427d0 |
| 4 | Production-Grade Audit: CONSTITUTION v1.3.0 Ch.8 (§20-§23) | 56e79b1 |
| 5 | Cross-Reference Integrity + G6 Project Health Hook | 96e3770 |
| 6 | Code Review Infrastructure Audit（結構已完整，無需新增） | — |

### 關鍵數字（已跨文件統一）
- MCP Tools: **53**
- Skills: **26**
- Prompts: **15**
- Total tools (含 external MCP): **~116**
- Hooks: **36 checks** (Copilot A1-4 + B1-5 + C1-6 + D1-6 + P1-8 + G1-7)
- Constitution: **v1.3.0** (Chapter 8: §20-§23)
- Tests: 35 pass / 21 pre-existing / 0 regressions

### Code Review Infrastructure（完整）

| 層級 | 工具 | 觸發 | 自動修正 |
|------|------|------|----------|
| Git Hook | pre-commit (ruff+mypy+bandit+pytest) | 自動 | ✅ ruff |
| Agent Hook | G6 project-integrity | commit 時 | ❌ report |
| Skill | code-reviewer | 手動 | ❌ report |
| Skill | code-refactor | 手動 | ✅ auto-fix |
| Capability | code-quality.prompt.md | 手動 | 混合 |

## 工具統計
- 目前工具數：**53 個**（MCP tools across 7 modules）
- Python 3.12.12 / uv 0.10.0
- 測試：35 passed / 21 pre-existing failures / 0 regressions
- pre-commit 13 hooks 全部通過

## 下一步
- [ ] Phase 5c: Full VSX Extension 升級（TreeView, CodeLens, Diagnostics）
- [ ] Pandoc 整合（取代 python-docx）
- [ ] Citation Intelligence MVP 實作

## 更新時間
2026-02-22
