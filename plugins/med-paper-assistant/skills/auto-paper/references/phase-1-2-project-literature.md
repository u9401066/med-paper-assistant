# Phase 1-2: PROJECT SETUP + LITERATURE SEARCH

> auto-paper 的 reference 檔（progressive disclosure）；入口與 hard gate 見 [../SKILL.md](../SKILL.md)。
> **Read this when**: creating the project skeleton, running literature searches, or saving references (`save_reference_mcp`).
> 相關：[phase-2-1-fulltext-appraisal.md](phase-2-1-fulltext-appraisal.md)、[phase-0-pre-planning.md](phase-0-pre-planning.md)

---

### Phase 1: PROJECT SETUP

**Skill**: `project-management`

1. `project_action(action="current")` → 有專案就切換，沒有就建立
2. `project_action(action="create", name, paper_type)` 或 `project_action(action="switch", slug)`
3. `project_action(action="setup")`
4. 載入 `journal-profile.yaml` → 驗證 paper_type 一致
5. `project_action(action="update", target_journal=journal.name)`
6. `workspace_state_action(action="sync", doing="phase 1 setup", next_action="phase 2 literature")`

**Code hard gate**: `drafts/`、`references/`、`data/`、`results/`、`.audit/`、`.memory/` 存在。paper type 對齊是 setup workflow 要求；Phase 2 起另以 `project.json` 作前置條件。

---

### Phase 2: LITERATURE SEARCH

**Skill**: `literature-review`, `parallel-search`
**外部 MCP**: `pubmed-search`, `zotero-keeper`（optional）

1. `generate_search_queries(topic, strategy="comprehensive")`
2. 並行 `unified_search()` × 3-5 組
3. 以 `read_session(action="pmids")` 取回 PMID，並以 PMID/DOI 去重
4. `get_citation_metrics(sort_by="relative_citation_ratio")`
5. 選前 15-20 篇 → `save_reference_mcp(pmid, agent_notes)`
6. [Optional] Zotero: `search_items(query)` → 取 PMID → `save_reference_mcp()`

**Code hard gate**: Paper-type-aware 最低文獻數 + 每筆 reference 有穩定 identity 與誠實 trust provenance。搜尋策略／選文紀錄缺失只警告。

| Paper Type        | 最低文獻數 |
| ----------------- | ---------- |
| original-research | 20         |
| review-article    | 30         |
| systematic-review | 40         |
| meta-analysis     | 40         |
| case-report       | 8          |
| letter            | 5          |
| fallback          | 15         |

解析優先序：`journal-profile.yaml references.minimum_reference_limits` → `DEFAULT_MINIMUM_REFERENCES` → `DEFAULT_MIN_REFERENCES (15)`

自動決策：< minimum → `expand_search_queries`；>500 → 加 MeSH 限縮；用戶有 Zotero → 主動問匯入。
