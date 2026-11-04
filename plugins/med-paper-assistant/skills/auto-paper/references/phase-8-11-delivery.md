# Phase 8-11: REFERENCE SYNC → EXPORT → RETROSPECTIVE → FINAL DELIVERY

> auto-paper 的 reference 檔（progressive disclosure）；入口與 hard gate 見 [../SKILL.md](../SKILL.md)。
> **Read this when**: syncing references, exporting DOCX/PDF, preparing submission artifacts, running the retrospective, or closing the pipeline.
> 相關：[hooks-d-meta-learning.md](hooks-d-meta-learning.md)、[closed-loop-checklist.md](closed-loop-checklist.md)、[lessons-learned.md](lessons-learned.md)

---

### Phase 8: REFERENCE SYNC

1. `draft_action(action="sync_references", filename="manuscript.md")` → 生成 References section
2. 確認所有 `[[wikilinks]]` 已解析
3. `format_references(style=journal-profile.references.style)`
4. 驗證引用數量 ≤ `references.reference_limits[paper.type]`（fallback `max_references`）
5. IF 超過上限 → 標記最少被引用的 refs → 建議刪除

**Code hard gate**: Phase 7 已完成 + References section 存在 + citation wikilinks 全部可解析。格式、引用數量／分布是本 workflow 與 C-series/R6 checks，不由 Phase 8 validator 額外重算。

---

### Phase 9: EXPORT（Code-Enforced — CRITICAL Gate）

**Skill**: `word-export`

⚠️ **Code-Enforced**: `pipeline_action(action="validate_phase", phase=9)` 對 docx 和 pdf 的檢查為 CRITICAL severity。必須同時產出 docx 和 pdf，否則 Gate 不會通過。

Facade 入口仍是 `export_document(action="docx")` / `export_document(action="pdf")`；正式呼叫時必填 `draft_filename` 與 `output_filename`。

1. `export_document(action="docx", draft_filename="manuscript.md", output_filename="paper.docx")` → 產出 DOCX
2. `export_document(action="pdf", draft_filename="manuscript.md", output_filename="paper.pdf")` → 產出 PDF
3. `inspect_export(action="list_templates")` → 選擇 template（優先匹配 journal-profile.journal.name）
4. `export_document(action="session_start")` → `export_document(action="session_insert")` × N
5. 驗證必要文件清單（from `required_documents.*`）：
   - cover_letter → 如尚未產生，提示用戶或自動草擬
   - author_contributions → 提示用戶填寫
   - ethics_statement → 提示用戶提供
6. `inspect_export(action="verify_document")` → `export_document(action="session_save")`
7. `inspect_export(action="docx_smoke")` 或 `inspect_export(action="xml_smoke")` → 驗證 DOCX zip/XML 結構、`word/document.xml`、段落與可見文字

**Code hard gate**: `pipeline_action(action="validate_phase", phase=9)` — Phase 6–8 前置條件有效，DOCX + PDF 都存在且各自通過 integrity smoke。必要投稿文件清單是下方 submission-readiness advisory task，不是 Phase 9 validator 的額外 hard check。

---

### Phase 9 advisory task: SUBMISSION READINESS

**輸入**: Phase 9 匯出的文件
**外部 MCP**: —

目的：投稿前的最終系統性檢查，確保所有投稿要件齊全。

1. **檔案清單核對**（依期刊 profile）：

   - [ ] Title page（含 author info、ORCID、corresponding author）
   - [ ] Manuscript（blinded if required）
   - [ ] Abstract（structured / unstructured）
   - [ ] Cover letter
   - [ ] Conflict of interest declarations
   - [ ] Funding statement
   - [ ] Ethics approval statement
   - [ ] Data availability statement
   - [ ] Supplementary files（if any）
   - [ ] Figure files（high-res, correct format）
   - [ ] Table files（if separate）
   - [ ] EQUATOR checklist（if required）
   - [ ] Author contributions (CRediT if applicable)

2. **格式最終確認**：

   - 字數限制（abstract + main text）
   - 圖表數量限制
   - Reference 格式（期刊 CSL style）
   - 檔案命名慣例

3. **內容一致性**：

   - Title page 作者 == manuscript 作者
   - Abstract numbers == main text numbers
   - Cover letter 提及正確期刊名

4. 產出 `exports/submission-checklist.md`（✅/❌ 清單）

**Gate**: submission-checklist.md 全部 ✅ 或用戶確認接受列外

---

### Phase 10: RETROSPECTIVE（閉環核心）

🔔 HOOK D: meta-learning（見 hooks-d-meta-learning.md 定義，含 D7 Review Retrospective、D8 EQUATOR Retrospective）

1. 回顧執行紀錄 + Hook 觸發統計 + Review 輪次統計
2. 更新 SKILL.md Lessons Learned（[lessons-learned.md](lessons-learned.md)）
3. 更新 AGENTS.md（如適用）
4. 更新 .memory/ 完整紀錄
5. 分析 journal-profile 設定是否合理 → 建議微調
6. 🆕 D7: 分析 review-report + author-response → 演化 Reviewer 指令
7. 🆕 D8: 分析 equator-compliance → 演化 EQUATOR 偵測與分類邏輯

**Code hard gate**: `pipeline-run-*.md` 含 D7/D8、hook-effectiveness report、`run_meta_learning` evolution event，以及可互相核對的 v2 audit schema、D1-D9、counts/lists/provenance。Project Memory 缺失只警告。

---

### Phase 11: FINAL DELIVERY（Code-Enforced — CRITICAL Gate）🆕

**目的**：確認 paper 交付物完整可審計。Git 僅作為 optional provenance，不可阻擋 paper-only workflow。
**觸發**：Phase 10 完成後自動進入。

⚠️ **Code-Enforced**: `pipeline_action(action="validate_phase", phase=11)` 驗證以下 CRITICAL 項目：

- Phase 9 匯出的 `.docx` + `.pdf` 存在
- Phase 10 retrospective / meta-learning artifacts 完整
- Phase 7 review loop 已完成

以下項目為 **optional provenance / WARNING or INFO**，不得阻擋 final delivery：

- Git repository 是否存在
- 工作目錄是否乾淨
- 最新 commit 是否包含專案檔案
- 是否有 remote/upstream / 是否 push

**流程**：

1. 確認 Phase 9 `.docx` + `.pdf` 已產出
2. 確認 Phase 10 `.audit/pipeline-run-*.md`、`.audit/meta-learning-audit.yaml`、`.audit/meta-learning-feedback.yaml` 完整
3. `pipeline_action(action="validate_phase", phase=11, response_format="json", compact=true)` → 驗證 PASS
4. 若專案使用 Git，可選擇 commit/push 作為 provenance；若用戶只是寫 paper，不需要 remote

**Code hard gate**: `pipeline_action(action="validate_phase", phase=11)` — DOCX/PDF 再次通過 integrity smoke且 Phase 10 仍通過；目前沒有額外 completion-marker 檔案要求。Git remote/push 不作為硬性條件。
