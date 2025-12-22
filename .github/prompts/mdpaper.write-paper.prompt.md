---
description: "🚀 write-paper - 完整論文撰寫流程"
---

# 完整論文撰寫流程

📖 **Capability 類型**: 高層編排
📖 **編排 Skills**: project-management → literature-review → concept-development → draft-writing → word-export

---

## 🎯 此 Capability 的目標

從零開始完成一篇研究論文，包含：
1. 建立專案
2. 文獻搜尋與整理
3. 發展研究概念
4. 撰寫各章節草稿
5. 匯出為 Word 文件

---

## Phase 1: 專案設置 `project`

📖 Skill: `.claude/skills/project-management/SKILL.md`

```
mcp_mdpaper_list_projects()
→ 如果無專案 → mcp_mdpaper_create_project(name="...")
→ 如果有專案 → mcp_mdpaper_switch_project(slug="...")

mcp_mdpaper_setup_project_interactive()
→ 選擇 paper_type（original-research / systematic-review / ...）
```

**完成條件**: ✅ 專案已建立，paper_type 已設定

---

## Phase 2: 文獻搜尋 `literature`

📖 Skill: `.claude/skills/literature-review/SKILL.md`

### Step 2.1: 確定搜尋策略

```
詢問用戶：
- 研究主題是什麼？
- PICO 元素（如適用）？
- 年份範圍？
- 排除條件？
```

### Step 2.2: 執行搜尋

```
mcp_pubmed-search_generate_search_queries(topic="...", strategy="comprehensive")
→ 並行執行多組搜尋
mcp_pubmed-search_merge_search_results(...)
```

### Step 2.3: 儲存關鍵文獻

```
# ⚠️ 使用 MCP-to-MCP 驗證
mcp_mdpaper_save_reference_mcp(pmid="...", agent_notes="...")
```

**完成條件**: ✅ 至少 10 篇關鍵文獻已儲存

---

## Phase 3: 發展概念 `concept`

📖 Skill: `.claude/skills/concept-development/SKILL.md`

### Step 3.1: 分析 Research Gap

```
根據搜尋結果，向用戶說明：
- 現有研究做了什麼
- 缺少什麼（Gap）
- 本研究可以填補什麼
```

### Step 3.2: 撰寫 concept.md

```
mcp_mdpaper_write_draft(
    filename="concept.md",
    content="包含 NOVELTY STATEMENT + KEY SELLING POINTS",
    skip_validation=True
)
```

### Step 3.3: 驗證概念

```
mcp_mdpaper_validate_concept(filename="concept.md")
→ Novelty Score ≥ 75 才能繼續
→ 如果失敗 → 犀利回饋 + 給用戶選項
```

**完成條件**: ✅ concept.md 驗證通過

---

## Phase 4: 撰寫草稿 `draft`

📖 Skill: `.claude/skills/draft-writing/SKILL.md`

### Step 4.1: 確認章節順序

根據 paper_type 決定撰寫順序：

| Paper Type | 建議順序 |
|------------|----------|
| original-research | Methods → Results → Introduction → Discussion → Abstract |
| systematic-review | Methods → Results → Discussion → Introduction → Abstract |
| case-report | Case → Discussion → Introduction |

### Step 4.2: 逐章節撰寫

```
# 每個章節：
mcp_mdpaper_validate_for_section(section="...")
mcp_mdpaper_get_section_template(section="...")
mcp_mdpaper_draft_section(topic="...", notes="...")
mcp_mdpaper_count_words(filename="...")
```

### Step 4.3: 同步引用

```
mcp_mdpaper_sync_references(filename="drafts/full_manuscript.md")
```

**完成條件**: ✅ 所有章節已撰寫，字數符合限制

---

## Phase 5: 匯出文件 `export`

📖 Skill: `.claude/skills/word-export/SKILL.md`

```
mcp_mdpaper_list_templates()
mcp_mdpaper_read_template(template_name="...")
mcp_mdpaper_start_document_session(template_name="...", session_id="...")

# 依序插入各章節
for section in sections:
    mcp_mdpaper_insert_section(session_id="...", section_name=section, content="...")

mcp_mdpaper_verify_document(session_id="...")
mcp_mdpaper_check_word_limits(session_id="...")
mcp_mdpaper_save_document(session_id="...", output_filename="...")
```

**完成條件**: ✅ Word 檔案已產出

---

## 📋 整體進度檢查

- [ ] Phase 1: 專案已建立
- [ ] Phase 2: 文獻已搜尋並儲存
- [ ] Phase 3: concept.md 驗證通過
- [ ] Phase 4: 所有章節草稿完成
- [ ] Phase 5: Word 檔案已匯出

---

## ⏸️ 中斷與恢復

如果用戶中途離開：
1. 更新專案 `.memory/activeContext.md`
2. 記錄目前 Phase 和進度
3. 下次對話時讀取並恢復
