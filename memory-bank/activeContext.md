# Active Context

## User Preferences
- **Git Identity**: u9401066 <u9401066@gap.kmu.edu.tw>

## 當前焦點
Tool Consolidation 三階段全部完成 ✅（Phase 8→9→10: 74→83→76→53 tools）
架構方向已確定：**Direction C: Full VSX + Foam + Pandoc**

## 最近變更 (2026-02-21)

### Tool Consolidation (Phase 8+9+10) 🆕

| Phase | 內容 | 工具數變化 |
|-------|------|-----------|
| Phase 8 | 9 個佔位工具升級為完整實作 | 74→83 |
| Phase 9 | 7 個模板型工具轉為 3 Skill 檔案 | 83→76 |
| Phase 10 | 6 大策略精簡（merge/absorb/skill） | 76→53 |

**Phase 10 六大策略**：
- A: 移除無用工具（-2）
- B: 簡單合併（-3）
- C: 參數合併（-11）— validate_concept, get_current_project, update_project_settings, save_diagram, sync_workspace_state, suggest_citations, verify_document
- D: 功能吸收（-2）— consistency + submission checklist → check_formatting
- E+F: Skill 轉換（-7）— section template, cover letter, highlights, journal list, submission checklist, reviewer response, revision changes

**新增 Skill 檔案**：
- `academic-debate/SKILL.md` (Phase 9)
- `idea-validation/SKILL.md` (Phase 9)
- `manuscript-review/SKILL.md` (Phase 9)
- `submission-preparation/SKILL.md` (Phase 10)

### 架構方向決策 (2026-02-20)

| 方向 | 結果 |
|------|------|
| A. Lightweight (純 MCP + Shell Prompts) | ❌ |
| B. Slim MCP | ❌ |
| **C. Full VSX + Foam + Pandoc** | **✅ 選定** |

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
2026-02-21
