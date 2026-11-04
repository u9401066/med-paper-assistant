# Phase 2.1: FULLTEXT INGESTION + Phase 2 advisory: CRITICAL APPRAISAL

> auto-paper 的 reference 檔（progressive disclosure）；入口與 hard gate 見 [../SKILL.md](../SKILL.md)。
> **Read this when**: ingesting full texts or PDFs with asset-aware-mcp, writing `fulltext-ingestion-status.md`, or building `appraisal-matrix.md`.
> 相關：[phase-1-2-project-literature.md](phase-1-2-project-literature.md)、[phase-3-4-concept-planning.md](phase-3-4-concept-planning.md)

---

### Phase 2.1: FULLTEXT INGESTION & ASSET EXTRACTION

**Skill**: `literature-review`
**外部 MCP**: `asset-aware-mcp`, `pubmed-search`
**輸入**: Phase 2 儲存的文獻（須達 paper-type-specific 最低數量）
**輸出**: 每篇文獻的全文解析結果 + `analysis.json` + `references/fulltext-ingestion-status.md`

**核心原則**: 引用文獻前必須閱讀全文並完成結構化分析。僅依據 abstract/metadata 不足以支撐 Methods/Results/Discussion 的引用。

**Context Isolation**: 每篇論文由獨立 subagent 閱讀分析，避免 20+ 篇全文汙染主 agent context。

流程：

1. `list_saved_references()` → 取得所有已儲存文獻清單
2. 對每篇文獻：
   a. 查詢 PDF 來源：`get_fulltext(pmcid)` （pubmed-search MCP）或 `analyze_fulltext_access(pmids)` 確認 Open Access 狀態
   b. IF 全文可取得：
   - 取得全文：pubmed-search `get_fulltext(pmcid, sections="all")` 或下載 PDF
   - 解析全文：asset-aware `ingest_documents(file_paths=[pdf_path], use_marker=true)`
   - 等候處理：`get_job_status(job_id)` 直到完成
   - 建立索引：`inspect_document_manifest(doc_id)` 取得完整資產清單
   - 提取關鍵段落：`get_section_content(doc_id, section_path)` → Methods, Results, Discussion
   - 更新 metadata.json：加入 `fulltext_ingested: true`, `asset_aware_doc_id`, `fulltext_sections`
     c. IF 全文不可取得：
   - 記錄原因：metadata.json 加入 `fulltext_ingested: false`, `fulltext_unavailable_reason: "..."`
   - ⚠️ 此文獻在寫作時僅能引用其 abstract 中的結論性資訊，不可引用具體方法或數據
3. **Subagent 閱讀分析（CRITICAL — 每篇一個 subagent）**：
   a. 主 Agent 呼叫 `get_reference_for_analysis(pmid)` → 取得結構化全文包（≤30K 字元）
   b. 用 `runSubagent` 啟動獨立 subagent，prompt 包含：
   - 全文內容（步驟 a 的結果）
   - 分析指令：摘要、方法學評估、關鍵發現、限制、可用於文章哪些章節
   - 要求 subagent 呼叫 `save_reference_analysis(pmid, summary, methodology, key_findings, limitations, usage_sections, relevance_score)`
     c. Subagent 完成後，`analysis.json` 已寫入 reference 目錄，`metadata.json` 標記 `analysis_completed: true`
     d. 主 Agent 後續寫作時只使用 `analysis_summary`，不再重讀全文 → **零 context 汙染**
4. 產出 `references/fulltext-ingestion-status.md`：

| PMID | 標題 | 全文狀態 | Asset-Aware | 分析狀態 | 可用章節 | 備註  |
| ---- | ---- | -------- | ----------- | -------- | -------- | ----- |
| ...  | ...  | ✅       | doc_abc     | ✅       | I/M/R/D  |       |
| ...  | ...  | ❌       | —           | ⚠️       | I only   | 非 OA |

**Code hard gate**: `fulltext-ingestion-status.md` 非空；每篇文獻都有可驗證 ingestion evidence 或明確 fallback；`analysis_completed: true` 必須對得上目前 source revision 的 analysis artifact；primary user materials 不得仍為 `pending_asset_aware`。
**WARNING Gate**: 若 >50% 文獻無全文 → 提醒用戶考慮補充 OA 文獻

---

### Phase 2 advisory task: CRITICAL APPRAISAL

**輸入**: Phase 2 + 2.1 完成的文獻（含全文解析結果）
**輸出**: `references/appraisal-matrix.md`

目的：在進入概念階段前，對核心文獻做品質評估，避免在低品質證據上建構研究。
**requires**: Phase 2.1 完成（全文解析結果可用時，品質評估更精確）

1. 對每篇核心文獻（≥5 篇）評估：

   - 研究設計品質（RCT > cohort > case series > case report > expert opinion）
   - 偏差風險（selection, performance, detection, attrition, reporting）
   - 樣本量適足性
   - 統計方法適當性
   - 結論是否有資料支持
   - **[NEW] 全文驗證狀態**：是否已透過 asset-aware 閱讀全文？未讀全文的文獻標記 ⚠️

2. 產出品質矩陣（appraisal-matrix.md）：

| PMID | 1st Author | Design | Quality | Bias Risk | Key Limitation |
| ---- | ---------- | ------ | ------- | --------- | -------------- |
| ...  | ...        | RCT    | High    | Low       | ...            |

3. 標記低品質文獻（Quality = Low），概念階段不應過度依賴

**Advisory checkpoint**: appraisal-matrix.md 已建立，至少 5 篇已評估；正式 gate 仍是 Phase 2 / Phase 2.1 / Phase 3。
