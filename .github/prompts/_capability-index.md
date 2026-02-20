# Capability Index

> ⚠️ **Agent 必讀**：此檔案定義所有可用 Capabilities 及其自動觸發條件。
>
> 當用戶意圖匹配任一 Capability 時，Agent 應主動載入對應的 Prompt File。

---

## 🔍 自動觸發規則

### 觸發優先級

1. **精確匹配**：用戶明確說出 `/mdpaper.xxx` → 直接執行
2. **意圖匹配**：用戶意圖符合某 Capability → 主動建議或執行
3. **情境匹配**：檢測到特定情境 → 提示可用 Capability

---

## 📚 mdpaper Capabilities（研究論文）

### write-paper / auto-paper（全自動論文 + 閉環審計）

| 項目 | 內容 |
|------|------|
| **Prompt File** | `mdpaper.write-paper.prompt.md` |
| **核心 Skill** | `.claude/skills/auto-paper/SKILL.md` |
| **觸發語** | 寫論文、寫 paper、完整流程、從頭開始寫、help me write、全自動、auto write、一鍵寫論文、autopilot |
| **情境觸發** | 用戶提到研究主題但沒有專案存在 |
| **編排 Skills** | auto-paper（編排器）→ project-management → literature-review → concept-development → draft-writing → word-export |
| **跨 MCP 工具** | `pubmed-search`（Phase 2）, `zotero-keeper`🔸（Phase 2）, `cgu`🔸（Phase 3, 5）, `drawio`🔸（Phase 5） |
| **特色** | 9-Phase Pipeline + 3 層 Audit Hooks + Meta-Learning 閉環自我改進 + Cross-Tool Orchestration |

### literature-survey（系統性文獻調查）

| 項目 | 內容 |
|------|------|
| **Prompt File** | `mdpaper.literature-survey.prompt.md` |
| **觸發語** | 文獻調查、系統性搜尋、找所有相關論文、comprehensive search、survey |
| **情境觸發** | 用戶要求「找齊」「全面搜尋」「不要漏」|
| **編排 Skills** | parallel-search → literature-review → reference-management |

### manuscript-revision（稿件修改）

| 項目 | 內容 |
|------|------|
| **Prompt File** | `mdpaper.manuscript-revision.prompt.md` |
| **觸發語** | 修改稿件、revision、reviewer comment、修訂、response to reviewer |
| **情境觸發** | 用戶提到「reviewer 說」「被退稿」「major/minor revision」|
| **編排 Skills** | draft-writing → concept-validation → word-export |

### quick-search（快速搜尋，現有）

| 項目 | 內容 |
|------|------|
| **Prompt File** | `mdpaper.search.prompt.md` |
| **觸發語** | 找論文、search、搜尋、PubMed |
| **情境觸發** | 用戶詢問特定主題的文獻 |
| **編排 Skills** | literature-review |

---

## 🛠️ 開發 Capabilities

### code-quality（程式碼品質檢查）

| 項目 | 內容 |
|------|------|
| **Prompt File** | `code-quality.prompt.md` |
| **觸發語** | 檢查程式碼、code review、品質檢查、安全檢查、有沒有 bug |
| **情境觸發** | 用戶完成功能開發、準備 PR |
| **編排 Skills** | code-reviewer → test-generator → ddd-architect |

### release-prep（發布準備）

| 項目 | 內容 |
|------|------|
| **Prompt File** | `release-prep.prompt.md` |
| **觸發語** | 準備發布、release、版本發布、上線前 |
| **情境觸發** | 用戶說「做完了」「可以上線」|
| **編排 Skills** | code-reviewer → changelog-updater → readme-updater → roadmap-updater → git-precommit |

---

---

## 🔔 Hook 系統

### 雙重 Hook 架構

| Hook 類型 | 定義位置 | 觸發時機 | 使用 MCP Tools |
|-----------|----------|----------|----------------|
| **Copilot Hooks** (A-D) | `.claude/skills/auto-paper/SKILL.md` | 寫作過程中 | mdpaper: `patch_draft`, `count_words`, `validate_wikilinks`, `read_draft` |
| **Pre-Commit Hooks** (P1-P8) | `.claude/skills/git-precommit/SKILL.md` | `git commit` 前 | mdpaper: `scan_draft_citations`, `read_draft`, `count_words`, `list_saved_references` |

### Hook ↔ Skill ↔ MCP 關係

```
Capability (write-paper)
  └── Skill (auto-paper) ──→ Uses MCP: mdpaper, pubmed-search, cgu, drawio, zotero-keeper
        │
        ├── Phase 2 (Literature)
        │     ├── pubmed-search: search + metrics + citations
        │     ├── mdpaper: save_reference_mcp(pmid)
        │     └── zotero-keeper: search_items [optional]
        │
        ├── Phase 3 (Concept)
        │     ├── mdpaper: validate_concept
        │     └── cgu: deep_think, spark_collision [when novelty < 75]
        │
        ├── Phase 5 (Writing)
        │     ├── mdpaper: draft_section, generate_table_one, create_plot
        │     ├── drawio: create_diagram [Methods flow diagrams]
        │     └── cgu: deep_think [Discussion argumentation]
        │
        ├── Copilot Hook A ──→ Uses MCP: mdpaper.count_words, patch_draft
        ├── Copilot Hook B ──→ Uses MCP: mdpaper.read_draft, patch_draft, check_writing_order
        ├── Copilot Hook C ──→ Uses MCP: mdpaper.check_formatting
        └── Copilot Hook D ──→ Uses: read_file, replace_string_in_file (on SKILL.md)

Skill (git-precommit) ──→ Orchestrates: memory-updater, draft-writing, reference-management
  ├── Pre-Commit P1 ──→ Uses MCP: mdpaper.scan_draft_citations
  ├── Pre-Commit P2 ──→ Uses MCP: mdpaper.read_draft + Agent scan
  ├── Pre-Commit P3 ──→ Uses MCP: mdpaper.read_draft (concept + drafts)
  ├── Pre-Commit P4 ──→ Uses MCP: mdpaper.count_words
  ├── Pre-Commit P5 ──→ Uses MCP: mdpaper.read_draft (concept.md)
  ├── Pre-Commit P6 ──→ Uses MCP: mdpaper.sync_workspace_state
  ├── Pre-Commit P7 ──→ Uses MCP: mdpaper.list_saved_references, get_reference_details
  ├── Pre-Commit P8 ──→ Uses MCP: mdpaper.read_draft + Agent methodology check
  ├── General G1-G5 ──→ Uses: memory_bank tools, read_file, replace_string_in_file
  ├── General G6 ──→ Uses: grep_search, list_dir (project self-consistency audit)
  └── General G7 ──→ Uses: diff, npm test (VSX Extension sync verification)
```

---

## 🎯 Agent 行為指引

### 當用戶意圖明確時

```
用戶：「我想寫一篇關於 remimazolam 的論文」
Agent：
  1. 匹配 → write-paper Capability
  2. 載入 → mdpaper.write-paper.prompt.md
  3. 執行 → 按照 Prompt File 步驟進行
```

### 當用戶意圖模糊時

```
用戶：「幫我處理這個研究」
Agent：
  「您想要進行哪個步驟？
   1. 📚 文獻搜尋 → /mdpaper.search
   2. 📝 發展概念 → /mdpaper.concept  
   3. ✍️ 撰寫草稿 → /mdpaper.draft
   4. 🚀 完整流程 → /mdpaper.write-paper」
```

### 當檢測到情境時

```
情境：用戶說「reviewer 說 introduction 太弱」
Agent：
  「看起來您需要修改稿件。建議使用 manuscript-revision 流程：
   1. 先讀取 reviewer comments
   2. 分析需要修改的部分
   3. 逐項回應並修改

   要開始嗎？」
```

---

## 📋 Capability 與 Skill 的關係

```
Capability (高層編排)
    ├── 定義「做什麼」（完整任務目標）
    ├── 定義執行順序
    └── 處理 Skill 間的銜接

Skill (中層知識)
    ├── 定義「怎麼做」（工具使用方式）
    ├── 定義決策點
    └── 處理工具呼叫細節

MCP Tool (底層能力)
    └── 執行單一操作
```

---

## 🔄 更新此索引

當新增 Capability 時：
1. 在此檔案新增條目
2. 建立對應的 Prompt File
3. 確保觸發語不與現有衝突
