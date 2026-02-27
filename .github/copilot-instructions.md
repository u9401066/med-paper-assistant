# Copilot 指令（Quick Reference）

> 完整指引：[AGENTS.md](../AGENTS.md)。本檔每次對話都載入，務求精簡。

## 核心價值

**逐步多輪演進**：寫論文是人類多年累積、多輪訓練的結果。Agent + MCP 框架必須實現類似的螺旋式進步。三層架構：L1 Hook（即時品質）→ L2 Code（結構約束）→ L3 CI（長期演進）。每輪可審計，每輪更好。（CONSTITUTION §25-26）

## 模式（操作前必查 `.copilot-mode.json`）

| 模式          | 可修改檔案          | 技能範圍            |
| ------------- | ------------------- | ------------------- |
| `development` | 全部                | 全部技能 + 靜態分析 |
| `normal`      | `projects/` `docs/` | 僅研究技能          |
| `research`    | `projects/` `docs/` | 僅研究技能          |

Normal/Research 下 `.claude/` `.github/` `src/` `tests/` `integrations/` `AGENTS.md` `CONSTITUTION.md` `pyproject.toml` 皆唯讀。
用戶要改受保護檔案 → 提示切換開發模式。

## 關鍵規則

**儲存文獻**: `save_reference_mcp(pmid)` 永遠優先（MCP-to-MCP 驗證）。`save_reference()` 僅 API 不可用時 fallback。

**草稿引用**: `get_available_citations()` → `patch_draft()` → `sync_references()`。禁止直接 `replace_string_in_file` 改引用。

**Novelty Check**: 犀利回饋 + 給選項（「直接寫？修正？用 CGU？」）。禁止討好式回饋或自動改 NOVELTY。

**Workspace State**: 新對話 → `get_workspace_state()`。重要操作 → `sync_workspace_state()`。

**Memory Bank**: 重要操作後更新 `memory-bank/`。對話結束前更新 `projects/{slug}/.memory/`。

## 法規層級

CONSTITUTION.md > `.github/bylaws/*.md` > `.claude/skills/*/SKILL.md`

## 跨 MCP 編排（詳見 auto-paper SKILL.md）

Pipeline 定義「何時」、Skill 定義「如何」、Hook 定義「品質」。

| Phase   | 外部 MCP                         |
| ------- | -------------------------------- |
| 2 文獻  | pubmed-search, zotero-keeper🔸   |
| 3 概念  | cgu🔸（novelty < 75）            |
| 5 撰寫  | drawio🔸, cgu🔸, data tools      |
| 7 審查  | min_rounds=2（Code-Enforced）    |
| 9 匯出  | docx+pdf（CRITICAL Gate）        |
| 11 提交 | git commit+push（CRITICAL Gate） |

## Hook 架構（65 checks — 23 Code-Enforced / 42 Agent-Driven）

| 類型            | 時機            | Code-Enforced                                                                                                                      | Agent-Driven                                 |
| --------------- | --------------- | ---------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------- |
| Copilot A1-6    | post-write      | A5 語言一致、A6 段落重複                                                                                                           | A1 字數、A2 引用、A3 Anti-AI、A4 Wikilink    |
| Copilot B1-16   | post-section    | B8 統計對齊、B9 時態、B10 段落品質、B11 Results 客觀性、B12 Intro 結構、B13 Discussion 結構、B14 倫理聲明、B15 Hedging、B16 效果量 | B1-B7 概念一致、🔒保護、方法學、順序、Brief  |
| Copilot C1-9    | post-manuscript | C9 補充材料交叉引用                                                                                                                | C1-C8 全稿一致、投稿清單、數量交叉引用、時間 |
| Copilot D1-D9   | Phase 10        | D1-D9 全部（MetaLearningEngine）                                                                                                   | —                                            |
| Copilot E1-5    | Phase 7 每輪    | —                                                                                                                                  | E1-E5 EQUATOR 報告指引（純 Agent 評估）      |
| Copilot F1-4    | post-manuscript | F1-F4 全部（DataArtifactTracker）                                                                                                  | —                                            |
| General G9      | pre-commit      | G9 Git 狀態（WritingHooksEngine）                                                                                                  | —                                            |
| Pre-Commit P1-8 | git commit 前   | —                                                                                                                                  | P1-P8（Agent 遵循 git-precommit SKILL.md）   |
| General G1-8    | git commit 前   | —                                                                                                                                  | G1-G8（Agent 遵循 git-precommit SKILL.md）   |

**Code-Enforced** = `run_writing_hooks` / `run_meta_learning` 內有確定性程式碼邏輯。
**Agent-Driven** = 僅靠 Agent 閱讀 SKILL.md 並自行執行，無程式碼強制。

## MCP Server（81 tools, 2026-02-27）

| 模組        | 工具數 | 重點                                                        |
| ----------- | ------ | ----------------------------------------------------------- |
| project/    | 16     | CRUD + exploration + workspace state                        |
| reference/  | 10     | save_reference_mcp 優先                                     |
| draft/      | 13     | writing + citation + editing (patch_draft)                  |
| validation/ | 3      | validate_concept + wikilinks                                |
| analysis/   | 9      | table_one + stats + figures                                 |
| review/     | 20     | formatting + pipeline + audit + meta-learning + flexibility |
| export/     | 10     | word + pandoc (docx/pdf/bib)                                |

## 回應風格

繁體中文 · 清晰步驟 · 引用法規 · uv 優先
