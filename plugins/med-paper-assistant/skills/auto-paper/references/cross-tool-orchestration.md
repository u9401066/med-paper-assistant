# Cross-Tool Orchestration Map

> auto-paper 的 reference 檔（progressive disclosure）；入口與 hard gate 見 [../SKILL.md](../SKILL.md)。
> **Read this when**: deciding which internal / external MCP tool to call in a phase, or whether an optional MCP (zotero, cgu, drawio, asset-aware) can be skipped.
> 相關：[phase-5-asset-generation.md](phase-5-asset-generation.md)、[phase-2-1-fulltext-appraisal.md](phase-2-1-fulltext-appraisal.md)

---

## Cross-Tool Orchestration Map

核心原則：Pipeline 定義「何時」→ Skill 定義「如何」→ Hook 定義「品質」→ Review 定義「完成度」。

### Phase × 工具矩陣

| Phase               | 內部 MCP Tools                                                                       | 外部 MCP                              | journal-profile 欄位           |
| ------------------- | ------------------------------------------------------------------------------------ | ------------------------------------- | ------------------------------ |
| 0 Pre-Planning      | —                                                                                    | `fetch_webpage` 🔸                    | 產出所有欄位                   |
| 1 Project Setup     | `project_action(action="create")`, `project_action(action="update")`                 | —                                     | `paper.type`, `journal.*`      |
| 2 Literature Search | `save_reference_mcp`                                                                 | `pubmed-search`, `zotero`             | `references.max_references`    |
| 2.1 Fulltext Ingest | `list_saved_references`                                                              | `asset-aware-mcp` 🔸, `pubmed-search` | —                              |
| 3 Concept Dev       | `draft_action(action="write")`, `validation_action(action="concept")`                | `cgu` 🔸                              | —                              |
| 4 Planning          | `draft_action(action="read")`                                                        | —                                     | `paper.sections`, `assets.*`   |
| 5 Writing           | `draft_action(action="section")`, `draft_action(action="patch")`, etc.               | `drawio` 🔸, `cgu` 🔸                 | `word_limits.*`, `assets.*`    |
| 6 Audit             | `run_quality_checks(action="writing_hooks")`, `draft_action(action="count_words")`   | —                                     | 所有 `pipeline.*` 閾值         |
| 7 Review            | `draft_action(action="read")`, `draft_action(action="patch")`                        | `cgu` 🔸                              | `pipeline.autonomous_review.*` |
| 8 Ref Sync          | `draft_action(action="sync_references")`, `format_references`                        | —                                     | `references.*`                 |
| 9 Export            | `export_document(action="session_save")`, `inspect_export(action="verify_document")` | —                                     | `required_documents.*`         |
| 10 Retrospective    | —                                                                                    | —                                     | 分析所有欄位合理性             |

### 跨 MCP 傳遞規則

| 來源          | 目標        | 傳遞物        | 規則                                                              |
| ------------- | ----------- | ------------- | ----------------------------------------------------------------- |
| pubmed-search | mdpaper     | PMID          | `save_reference_mcp(pmid)` 只傳 PMID                              |
| pubmed-search | asset-aware | 全文 / PMC ID | `get_fulltext(pmcid)` → PDF/text                                  |
| asset-aware   | mdpaper     | doc_id + 段落 | 解析後更新 metadata.json                                          |
| zotero-keeper | mdpaper     | PMID/DOI      | 取 PMID → `save_reference_mcp()`                                  |
| cgu           | concept.md  | 文字建議      | Agent 整合到 `draft_action(action="write")`                       |
| drawio        | mdpaper     | XML           | `project_action(action="save_diagram", project=..., content=...)` |
| data tools    | drafts      | 表格/圖       | Agent 整合到 draft 文字                                           |

### 何時跳過外部 MCP

| 情境                         | 跳過                                    |
| ---------------------------- | --------------------------------------- |
| 無 Zotero                    | zotero-keeper                           |
| Concept ≥ 75 首次通過        | CGU                                     |
| 無資料集                     | table_one / plot                        |
| 純 review（無 Methods flow） | drawio                                  |
| 全文均不可取得（非 OA）      | asset-aware（但必須在 metadata 記錄⚠️） |
