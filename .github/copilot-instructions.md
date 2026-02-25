# Copilot 指令（Quick Reference）

> 完整指引：[AGENTS.md](../AGENTS.md)。本檔每次對話都載入，務求精簡。

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

| Phase  | 外部 MCP                       |
| ------ | ------------------------------ |
| 2 文獻 | pubmed-search, zotero-keeper🔸 |
| 3 概念 | cgu🔸（novelty < 75）          |
| 5 撰寫 | drawio🔸, cgu🔸, data tools    |

## Hook 架構（42 checks）

| 類型            | 時機            | 重點                                           |
| --------------- | --------------- | ---------------------------------------------- |
| Copilot A1-4    | post-write      | 字數、引用、Anti-AI、Wikilink                  |
| Copilot B1-7    | post-section    | 概念一致、🔒保護、方法學、寫作順序、Brief合規  |
| Copilot C1-8    | post-manuscript | 全稿一致、投稿清單、數量與交叉引用、時間一致性 |
| Copilot D1-7    | Phase 10        | SKILL/Hook 自我改進 + Review Retrospective     |
| Pre-Commit P1-8 | git commit 前   | 最終品質把關                                   |
| General G1-8    | git commit 前   | Memory、文檔、架構、VSX、文檔更新提醒          |

## 回應風格

繁體中文 · 清晰步驟 · 引用法規 · uv 優先
