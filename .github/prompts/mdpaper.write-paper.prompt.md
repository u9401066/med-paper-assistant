---
description: "🚀 write-paper - 完整論文撰寫流程（全自動 + 閉環審計）"
---

# 完整論文撰寫流程

📖 **Capability 類型**: 高層編排
📖 **核心 Skill**: `.claude/skills/auto-paper/SKILL.md`（9-Phase 閉環系統）
📖 **編排 Sub-Skills**: project-management → literature-review → concept-development → draft-writing → word-export

---

## 🎯 此 Capability 的目標

從零開始**全自動**完成一篇研究論文，內建 3 層 Audit Hooks 自動檢查品質，
並在完成後透過 Meta-Learning 更新 Skill 本身，形成**閉環自我改進**。

---

## 🔄 閉環架構

```
Instructions (AGENTS.md) ──→ Skill (auto-paper) ──→ Writing (drafts)
       ▲                           ▲                      │
       │                           │                      │
       └───── Hooks (audit paper + skill + instructions) ─┘
```

---

## 🗺️ 外部 MCP 工具使用時機

> **Pipeline 定義「何時」用哪個 MCP — 不是每個 Phase 都需要所有工具。**

| Phase | mdpaper | pubmed-search | CGU | Draw.io | Zotero |
|-------|---------|---------------|-----|---------|--------|
| 1 專案設置 | ✅ create/switch | - | - | - | - |
| 2 文獻搜尋 | ✅ save_ref | ✅ search + metrics | - | - | 🔸 import |
| 3 概念發展 | ✅ validate | - | 🔸 novelty boost | - | - |
| 4 大綱規劃 | ✅ read_draft | - | - | - | - |
| 5 章節撰寫 | ✅ draft/patch | - | 🔸 Discussion | 🔸 flow diagram | - |
| 6 全稿審計 | ✅ hooks | - | - | - | - |
| 7 引用同步 | ✅ sync_refs | - | - | - | - |
| 8 匯出 | ✅ export | - | - | - | - |
| 9 回顧改進 | ✅ meta | - | - | - | - |

🔸 = 條件觸發（非每次都需要）

---

## 📋 執行方式

**載入並遵循**：`.claude/skills/auto-paper/SKILL.md`

### 9-Phase Pipeline

| Phase | 名稱 | Skill | 外部 MCP | Gate |
|-------|------|-------|----------|------|
| 1 | 專案設置 | project-management | - | 專案存在 + paper_type |
| 2 | 文獻搜尋 | literature-review, parallel-search | pubmed-search, zotero🔸 | ≥10 篇已儲存 |
| 3 | 概念發展 | concept-development | cgu🔸 | score ≥ 75 |
| 4 | 大綱規劃 | draft-writing | - | **🗣️ 用戶確認大綱 + Asset Plan** |
| 5 | 章節撰寫 | draft-writing + **Hook A/B** | drawio🔸, cgu🔸, data tools | 所有 section 通過 |
| 6 | 全稿審計 | **Hook C** | - | 0 critical issues |
| 7 | 引用同步 | reference-management | - | 0 broken links |
| 8 | 匯出 | word-export | - | Word 已匯出 |
| 9 | 回顧改進 | **Hook D (meta-learning)** | - | SKILL 已更新 |

🔸 = 條件觸發（見 auto-paper SKILL.md Cross-Tool Orchestration Map）

### 3 層 Audit Hooks

| Hook | 觸發時機 | 檢查對象 | 更新對象 |
|------|----------|----------|----------|
| **A: post-write** | 每次寫完 | 字數、引用密度、Anti-AI | patch_draft 修正 |
| **B: post-section** | section 完成 | concept 一致性、🔒 保護內容 | patch_draft 補充 |
| **C: post-manuscript** | 全稿完成 | 一致性、投稿清單、wikilinks | 定點修正 |
| **D: meta-learning** | Phase 9 | SKILL 本身 + Instructions | 更新 SKILL + AGENTS |

### 人工介入點（最小化）

Pipeline **絕大部分自動執行**，僅在以下情況暫停：
- Phase 4 大綱需用戶確認（唯一確認點）
- Concept score < 60（兩次修正後仍低）
- 3 rounds 修正後 Hook 仍失敗
- 研究方向需要改變

---

## ⏸️ 中斷與恢復

如果用戶中途離開：
1. `sync_workspace_state(doing="...", next_action="...")`
2. 更新專案 `.memory/activeContext.md`（含 execution log）
3. 下次對話：`get_workspace_state()` → 從斷點繼續
