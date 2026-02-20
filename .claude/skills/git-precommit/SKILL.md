---
name: git-precommit
description: |
  提交前編排器 + Paper-Aware Pre-Commit Hooks。
  LOAD THIS SKILL WHEN: commit、提交、推送、做完了、收工
  CAPABILITIES: 記憶同步、文檔更新、Paper 品質把關、Git 操作
---

# Git 提交前工作流（編排器 + Pre-Commit Hooks）

Copilot Hooks（寫作時即時修正）定義於 `auto-paper/SKILL.md`。
Pre-Commit Hooks（本檔，git commit 前最終把關）只報告不自動修改。

觸發：「commit」「推送」「做完了」「收工」「快速 commit」

---

## Step 0: 偵測變更範圍

`get_changed_files()` 或 `git diff --cached --name-only`。
論文檔案模式：`projects/*/drafts/*`, `projects/*/concept.md`, `projects/*/references/*`, `projects/*/.memory/*`
→ 匹配時觸發 Paper Hooks。

---

## 通用 Hooks（每次觸發）

| Hook                     | 條件                    | 動作                               | MCP Tools                                             |
| ------------------------ | ----------------------- | ---------------------------------- | ----------------------------------------------------- |
| **G1** memory-sync       | 必要                    | 更新 Memory Bank + workspace state | `memory_bank_update_progress`, `sync_workspace_state` |
| **G2** readme-update     | 新功能/API 變更         | 更新 README                        | `read_file`, `replace_string_in_file`                 |
| **G3** changelog-update  | 版本/重要修改           | 更新 CHANGELOG                     | 同上                                                  |
| **G4** roadmap-update    | 里程碑完成              | 更新 ROADMAP                       | 同上                                                  |
| **G5** arch-check        | 結構性變更              | 檢查架構文檔                       | `grep_search`, `list_dir`                             |
| **G6** project-integrity | SKILL/AGENTS/src 變更   | 專案一致性審計                     | 見下方                                                |
| **G7** vsx-integrity     | skills/prompts/vsx 變更 | VSX Extension 同步                 | 見下方                                                |

### G6 專案一致性審計

| #    | 檢查           | 方法                                        | 失敗    |
| ---- | -------------- | ------------------------------------------- | ------- |
| G6.1 | Tool 數量      | `grep -c "mcp.tool"` vs README/ARCHITECTURE | ⚠️ WARN |
| G6.2 | Skill 數量     | `ls -d .claude/skills/*/` vs AGENTS.md      | ⚠️ WARN |
| G6.3 | Prompt 數量    | `ls .github/prompts/*.prompt.md` vs 文檔    | ⚠️ WARN |
| G6.4 | Hook 工具存在  | SKILL.md 中 `mcp_mdpaper_*` → 已註冊        | ❌ FAIL |
| G6.5 | 跨文件數字一致 | README vs ARCHITECTURE vs AGENTS            | ⚠️ WARN |

### G7 VSX Extension 同步

| #    | 檢查            | 方法                          | 失敗    |
| ---- | --------------- | ----------------------------- | ------- |
| G7.1 | Skills 同步     | `diff` source vs bundled      | ⚠️ WARN |
| G7.2 | Prompts 同步    | `diff` source vs bundled      | ⚠️ WARN |
| G7.3 | Chat commands   | package.json chatParticipants | ❌ FAIL |
| G7.4 | Version semver  | 格式驗證                      | ❌ FAIL |
| G7.5 | TypeScript 編譯 | `tsc --noEmit`                | ⚠️ WARN |

快速修復：`cd vscode-extension && ./scripts/build.sh`

---

## Paper Hooks（偵測到論文變更時）

| Hook                       | 檢查                        | MCP Tools                                        | 判定                                  |
| -------------------------- | --------------------------- | ------------------------------------------------ | ------------------------------------- |
| **P1** citation-integrity  | `[[wikilinks]]` 可解析      | `scan_draft_citations`, `validate_wikilinks`     | 0 unresolved = ✅, unknown = ❌       |
| **P2** anti-ai-scan        | AI 痕跡用詞                 | `read_draft` + Agent 掃描                        | 0 = ✅, 1-2 = ⚠️, ≥3 = ❌             |
| **P3** concept-alignment   | NOVELTY/SELLING POINTS 體現 | `read_draft("concept.md")` + drafts              | 完整 = ✅, 部分 = ⚠️, NOVELTY 缺 = ❌ |
| **P4** word-count          | 各 section ±20%             | `count_words`                                    | 超 50% = ❌                           |
| **P5** protected-content   | 🔒 區塊存在且非空           | `read_draft("concept.md")`                       | 缺失 = ❌                             |
| **P6** memory-sync         | `.memory/` 已更新           | `sync_workspace_state`                           | 未更新 = AUTO-FIX                     |
| **P7** reference-integrity | 文獻 metadata 完整          | `list_saved_references`, `get_reference_details` | 非 VERIFIED = ⚠️                      |
| **P8** methodology         | Methods 可再現              | `read_draft` + Agent checklist                   | 項目 <3 = ❌                          |

P2 Anti-AI 禁止詞：`In recent years`, `It is worth noting`, `plays a crucial role`, `has garnered significant attention`, `a comprehensive understanding`, `This groundbreaking`, `delve into`, `shed light on`, `pave the way`, `a myriad of`

P8 與 Copilot Hook B5 互補：B5 寫作時即時修正，P8 提交時最終確認（safety net）。

---

## Hook 效能追蹤（§23 Self-Improving）

每次執行後記錄 `projects/{slug}/.audit/precommit-stats.md`：觸發率/通過率/警告率/阻止率。

- 通過率 >95%（5次+）→ 可能太鬆
- 阻止率 >50%（5次+）→ 可能太嚴
- 記錄供 auto-paper Hook D 分析

---

## 執行模式

| 模式 | 觸發            | 執行                                    |
| ---- | --------------- | --------------------------------------- |
| 標準 | 「準備 commit」 | Step 0 → G1-G7 → P1-P8（如適用）→ Final |
| 快速 | 「快速 commit」 | G1 + P1 + P5（如適用）→ Final           |
| 開發 | 「commit code」 | G1-G7（跳過 Paper Hooks）→ Final        |

---

## Git 操作

Commit Message 格式：`type(scope): description`

- Types: feat, fix, docs, refactor, style, test, chore
- Scope: paper, concept, refs, export, core

---

## Skill 依賴

| Hook     | 編排 Skill                       | 工具                                              |
| -------- | -------------------------------- | ------------------------------------------------- |
| G1       | memory-updater                   | `memory_bank_update_progress`                     |
| G2-G4    | readme/changelog/roadmap-updater | `read_file`, `replace_string_in_file`             |
| G5       | ddd-architect                    | `grep_search`, `list_dir`                         |
| P1-P4    | draft-writing                    | `read_draft`, `count_words`, `validate_wikilinks` |
| P3,P5,P8 | concept-development              | `read_draft("concept.md")`                        |
| P7       | reference-management             | `list_saved_references`, `get_reference_details`  |
