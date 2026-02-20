# MCP Tool 精簡規劃 v2.2

> **目標**：精簡工具數量、減少 token、保持 Agent 友善
> **原則**：參考 pubmed-search MCP 的設計 - 工具獨立但描述精簡
> **限制**：MCP 無法分段載入，所有工具必須一次暴露

---

## 📊 現況分析

### 問題

| 問題                | 影響                                  |
| ------------------- | ------------------------------------- |
| 工具數量過多 (76個) | 小模型 tool list 爆 token             |
| CRUD 操作分散       | 每個 CRUD 都是獨立工具                |
| 描述過長            | 每個工具 description 平均 300+ tokens |

### ❌ 為什麼不用 Action 參數合併？

```python
# 這種設計對 Agent 不友善！
reference(action="save", pmid="123")
reference(action="delete", pmid="123", confirm=True)
```

**問題**：

1. Agent 需要記住每個工具有哪些 action
2. 每個 action 需要不同參數組合，容易錯
3. Tool description 還是要列出所有 action，token 沒省多少

### ❌ 為什麼不用分層載入？

**MCP 限制**：無法動態啟用/停用工具，`@mcp.tool()` 在啟動時全部註冊

### ❌ 職責分開會破壞功能嗎？

**不會！** 因為現有設計已經是分工的：

```
┌─────────────────────────────────────────────────────────────┐
│  pubmed-search MCP                                          │
│  └── search_literature, fetch_details, get_fulltext...     │
├─────────────────────────────────────────────────────────────┤
│  mdpaper MCP                                                │
│  └── save_reference_mcp(pmid) ─────┐                        │
│      ↓                              │ HTTP API 取得 metadata │
│      呼叫 pubmed-search API ←───────┘                        │
│      ↓                                                      │
│      存入 projects/{slug}/references/                       │
└─────────────────────────────────────────────────────────────┘
```

mdpaper 從未重複實作 `search_literature`，它只做「專案相關」操作。

---

## ✅ 可行的精簡策略

### 唯一有效方案：描述精簡

| 策略                 | 可行性          | 效果               |
| -------------------- | --------------- | ------------------ |
| ~~Action 參數合併~~  | ❌ Agent 不友善 | -                  |
| ~~分層載入~~         | ❌ MCP 不支援   | -                  |
| ~~職責分開到子模組~~ | ⚠️ 已經分開了   | -                  |
| **描述精簡**         | ✅ 可行         | **-77% tokens**    |
| **合併相似工具**     | ✅ 可行         | **-10~20% 工具數** |

---

## 🎯 精簡策略

### 策略 1：描述精簡（主力）

**Before** (350+ tokens):

```python
def create_project(name: str, description: str = "", ...) -> str:
    """
    Create a new research paper project with isolated workspace.

    Each project gets its own:
    - concept.md (research concept with type-specific template)
    - .memory/ (project-specific AI memory)
    - drafts/ (paper drafts)
    - references/ (saved literature by PMID)
    - data/ (analysis data files)
    - results/ (exported Word documents)

    IMPORTANT: The 'name' parameter MUST be in English for proper slug generation.
    If user provides a non-English name (e.g., Chinese, Japanese, Korean),
    YOU (the Agent) must translate it to English before calling this tool.

    Examples:
    - "死亡率預測" → "Mortality Prediction"
    - "鼻腔氣管插管比較" → "Nasotracheal Intubation Comparison"

    Args:
        name: Project name in ENGLISH...
        [更多說明...]
    """
```

**After** (~80 tokens):

```python
def create_project(name: str, description: str = "", paper_type: str = "") -> str:
    """
    Create new research project. Name must be English.

    Args:
        name: English project name (translate if needed)
        description: Brief description
        paper_type: original-research|systematic-review|meta-analysis|case-report|letter
    """
```

**Token 節省**：350 → 80 = **-77%**

### 策略 2：合併相似工具（輔助）

| 合併前                                         | 合併後                          | 說明           |
| ---------------------------------------------- | ------------------------------- | -------------- |
| `validate_concept` + `validate_concept_quick`  | `validate_concept(quick=False)` | 加參數         |
| `start_exploration` + `get_exploration_status` | `exploration(action)`           | 低頻工具可合併 |
| `archive_project` + `delete_project`           | 保持獨立                        | 危險操作不合併 |

### 策略 3：詳細說明移到 Instructions

把冗長的使用說明從 docstring 移到 `instructions.py`：

```python
# tools.py - 精簡
def save_reference_mcp(pmid: str, agent_notes: str = "") -> str:
    """Save reference by PMID. Fetches verified metadata via API."""

# instructions.py - 詳細
TOOL_GUIDE = """
## save_reference_mcp
🔒 資料完整性工具 - Agent 只傳 PMID，系統自動取得驗證資料

使用時機：
- 用戶說「存這篇」「加入參考文獻」
- 搜尋後要保存到專案

⚠️ 絕對不要用 save_reference()（可能幻覺 metadata）
"""
```

---

## 📋 mdpaper 工具完整盤點（82 個）

### 專案管理 (12 個)

| 工具                        | 說明         | 精簡策略                      |
| --------------------------- | ------------ | ----------------------------- |
| `create_project`            | 建立專案     | ✅ 保留                       |
| `list_projects`             | 列出專案     | ✅ 保留                       |
| `switch_project`            | 切換專案     | ✅ 保留                       |
| `get_current_project`       | 當前專案     | ✅ 保留                       |
| `archive_project`           | 封存專案     | ✅ 保留                       |
| `delete_project`            | 刪除專案     | ✅ 保留                       |
| `update_project_settings`   | 更新設定     | ✅ 保留                       |
| `update_project_status`     | 更新狀態     | ✅ 保留                       |
| `get_project_paths`         | 取得路徑     | 🔄 合併到 get_current_project |
| `get_project_file_paths`    | 取得檔案路徑 | 🔄 合併到 get_current_project |
| `get_paper_types`           | 論文類型列表 | ✅ 保留                       |
| `setup_project_interactive` | 互動設定     | ✅ 保留                       |

### 文獻管理 (12 個)

| 工具                      | 說明                | 精簡策略                        |
| ------------------------- | ------------------- | ------------------------------- |
| `save_reference_mcp`      | 🔒 儲存文獻 (PMID)  | ✅ 保留 (核心)                  |
| `save_reference`          | 儲存文獻 (metadata) | ⚠️ fallback                     |
| `save_reference_pdf`      | 儲存 PDF            | 🔄 合併到 save_reference        |
| `list_saved_references`   | 列出文獻            | ✅ 保留                         |
| `search_local_references` | 本地搜尋            | ✅ 保留                         |
| `get_reference_details`   | 文獻詳情            | ✅ 保留                         |
| `check_reference_exists`  | 檢查存在            | 🔄 合併到 get_reference_details |
| `read_reference_fulltext` | 讀取全文            | ✅ 保留                         |
| `delete_reference`        | 刪除文獻            | ✅ 保留                         |
| `rebuild_foam_aliases`    | 重建別名            | ✅ 保留                         |
| `format_references`       | 格式化引用          | ✅ 保留                         |
| `standardize_references`  | 標準化引用          | 🔄 合併到 format_references     |

### 草稿撰寫 (7 個)

| 工具                   | 說明     | 精簡策略 |
| ---------------------- | -------- | -------- |
| `write_draft`          | 寫入草稿 | ✅ 保留  |
| `read_draft`           | 讀取草稿 | ✅ 保留  |
| `list_drafts`          | 列出草稿 | ✅ 保留  |
| `delete_draft`         | 刪除草稿 | ✅ 保留  |
| `draft_section`        | 段落撰寫 | ✅ 保留  |
| `get_section_template` | 段落模板 | ✅ 保留  |
| `count_words`          | 字數統計 | ✅ 保留  |

### 引用管理 (6 個)

| 工具                      | 說明     | 精簡策略 |
| ------------------------- | -------- | -------- |
| `sync_references`         | 同步引用 | ✅ 保留  |
| `suggest_citations`       | 引用建議 | ✅ 保留  |
| `insert_citation`         | 插入引用 | ✅ 保留  |
| `find_citation_for_claim` | 找引用   | ✅ 保留  |
| `scan_draft_citations`    | 掃描引用 | ✅ 保留  |
| `set_citation_style`      | 設定樣式 | ✅ 保留  |

### 驗證 (6 個)

| 工具                     | 說明       | 精簡策略                               |
| ------------------------ | ---------- | -------------------------------------- |
| `validate_concept`       | 概念驗證   | ✅ 保留                                |
| `validate_concept_quick` | 快速驗證   | 🔄 合併到 validate_concept(quick=True) |
| `validate_for_section`   | 段落驗證   | ✅ 保留                                |
| `validate_hypothesis`    | 假設驗證   | ✅ 保留                                |
| `validate_wikilinks`     | 連結驗證   | ✅ 保留                                |
| `check_feasibility`      | 可行性檢查 | ✅ 保留                                |

### 分析 (5 個)

| 工具                    | 說明     | 精簡策略                  |
| ----------------------- | -------- | ------------------------- |
| `generate_table_one`    | Table 1  | ✅ 保留                   |
| `analyze_dataset`       | 描述統計 | ✅ 保留                   |
| `run_statistical_test`  | 統計檢定 | ✅ 保留                   |
| `create_plot`           | 統計圖表 | ✅ 保留                   |
| `detect_variable_types` | 變數偵測 | 🔄 合併到 analyze_dataset |

### 匯出 (8 個)

| 工具                     | 說明     | 精簡策略               |
| ------------------------ | -------- | ---------------------- |
| `list_templates`         | 模板列表 | ✅ 保留                |
| `read_template`          | 讀取模板 | ✅ 保留                |
| `start_document_session` | 開始編輯 | ✅ 保留                |
| `insert_section`         | 插入段落 | ✅ 保留                |
| `verify_document`        | 驗證文件 | ✅ 保留                |
| `check_word_limits`      | 字數限制 | ✅ 保留                |
| `save_document`          | 儲存文件 | ✅ 保留                |
| `export_word`            | 舊版匯出 | ❌ 棄用（用 workflow） |

### 投稿準備 (7 個)

| 工具                           | 說明         | 精簡策略                               |
| ------------------------------ | ------------ | -------------------------------------- |
| `generate_cover_letter`        | Cover letter | ✅ 保留                                |
| `generate_highlights`          | Highlights   | ✅ 保留                                |
| `check_submission_checklist`   | 投稿清單     | ✅ 保留                                |
| `check_manuscript_consistency` | 稿件一致性   | ✅ 保留                                |
| `check_reporting_guidelines`   | 報告規範     | ✅ 保留                                |
| `check_formatting`             | 格式檢查     | 🔄 合併到 check_manuscript_consistency |
| `list_supported_journals`      | 支援期刊     | ✅ 保留                                |

### 審稿回覆 (3 個)

| 工具                       | 說明       | 精簡策略 |
| -------------------------- | ---------- | -------- |
| `create_reviewer_response` | 審稿回覆   | ✅ 保留  |
| `format_revision_changes`  | 格式化修訂 | ✅ 保留  |
| `compare_with_literature`  | 文獻比較   | ✅ 保留  |

### Workspace 狀態 (3 個)

| 工具                   | 說明     | 精簡策略                                   |
| ---------------------- | -------- | ------------------------------------------ |
| `get_workspace_state`  | 狀態恢復 | ✅ 保留                                    |
| `sync_workspace_state` | 同步狀態 | ✅ 保留                                    |
| `clear_recovery_state` | 清除恢復 | 🔄 合併到 sync_workspace_state(clear=True) |

### 探索模式 (3 個)

| 工具                             | 說明     | 精簡策略                                      |
| -------------------------------- | -------- | --------------------------------------------- |
| `start_exploration`              | 開始探索 | ✅ 保留                                       |
| `get_exploration_status`         | 探索狀態 | 🔄 合併到 start_exploration(status_only=True) |
| `convert_exploration_to_project` | 轉換專案 | ✅ 保留                                       |

### 圖表管理 (3 個)

| 工具                      | 說明     | 精簡策略               |
| ------------------------- | -------- | ---------------------- |
| `save_diagram`            | 儲存圖表 | ✅ 保留                |
| `save_diagram_standalone` | 獨立儲存 | 🔄 合併到 save_diagram |
| `list_diagrams`           | 列出圖表 | ✅ 保留                |

### VS Code 整合 (2 個)

| 工具                        | 說明     | 精簡策略 |
| --------------------------- | -------- | -------- |
| `open_project_files`        | 開啟檔案 | ✅ 保留  |
| `close_other_project_files` | 關閉其他 | ✅ 保留  |

### 資料檔案 (1 個)

| 工具              | 說明     | 精簡策略 |
| ----------------- | -------- | -------- |
| `list_data_files` | 列出資料 | ✅ 保留  |

### 創意/辯論 (4 個)

| 工具                 | 說明       | 精簡策略 |
| -------------------- | ---------- | -------- |
| `peer_review`        | 同儕審查   | ✅ 保留  |
| `devils_advocate`    | 魔鬼代言人 | ✅ 保留  |
| `debate_topic`       | 辯論主題   | ✅ 保留  |
| `compare_viewpoints` | 比較觀點   | ✅ 保留  |

---

## 📊 精簡統計

| 類別      | 現有   | 保留   | 合併   | 棄用  |
| --------- | ------ | ------ | ------ | ----- |
| 專案管理  | 12     | 10     | 2      | 0     |
| 文獻管理  | 12     | 9      | 3      | 0     |
| 草稿撰寫  | 7      | 7      | 0      | 0     |
| 引用管理  | 6      | 6      | 0      | 0     |
| 驗證      | 6      | 5      | 1      | 0     |
| 分析      | 5      | 4      | 1      | 0     |
| 匯出      | 8      | 7      | 0      | 1     |
| 投稿準備  | 7      | 6      | 1      | 0     |
| 審稿回覆  | 3      | 3      | 0      | 0     |
| Workspace | 3      | 2      | 1      | 0     |
| 探索模式  | 3      | 2      | 1      | 0     |
| 圖表管理  | 3      | 2      | 1      | 0     |
| VS Code   | 2      | 2      | 0      | 0     |
| 資料檔案  | 1      | 1      | 0      | 0     |
| 創意/辯論 | 4      | 4      | 0      | 0     |
| **總計**  | **82** | **70** | **11** | **1** |

### 精簡結果

```
Before: 82 tools
After:  70 tools (-15%)

主要精簡來源：
- 合併重複功能 (11 個)
- 棄用舊版 export_word (1 個)
```

---

## 📉 Token 節省預估（修正版）

| 項目             | Before     | After     | 節省     |
| ---------------- | ---------- | --------- | -------- |
| mdpaper 工具數   | 82         | 70        | -15%     |
| 平均 description | 350 tokens | 80 tokens | -77%     |
| **總 tokens**    | ~28,700    | ~5,600    | **-80%** |

**主要節省來源**：描述精簡（-77%），不是減少工具數

---

## 🚀 實作計畫

### Phase 1：描述精簡 (本週)

- [ ] 精簡所有工具的 docstring（350→80 tokens）
- [ ] 把詳細說明移到 instructions.py

### Phase 2：合併相似工具 (下週)

- [ ] `validate_concept` + `validate_concept_quick`
- [ ] `get_exploration_status` → `start_exploration`
- [ ] `clear_recovery_state` → `sync_workspace_state`

### Phase 3：測試驗證

- [ ] 確認 Agent 仍能正確使用工具
- [ ] Token 計數驗證
- [ ] 更新文檔

---

## 🔗 現有分工（不需修改）

```
pubmed-search MCP          mdpaper MCP
─────────────────          ────────────────
search_literature    →     (Agent 中介)
fetch_article_details →    (Agent 中介)
get_fulltext         →     (Agent 中介)
                           save_reference_mcp ← 呼叫 pubmed API
                           專案管理
                           草稿撰寫
                           驗證
                           匯出
```

**結論**：職責已經分開，不需要再調整。專注在描述精簡即可。
