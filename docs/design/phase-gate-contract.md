# Phase gate：設計與程式契約

> 本文件回答「程式現在真正檢查什麼」。使用者導向的說明見[每階段檢查與修正](../wiki/research-pipeline.md)，實作權威是 `PipelineGateValidator.validate_phase()`。

## 契約層級

同一個 Phase 可能同時有三種規則，不可混為一談：

| 層級              | 意義                                                                                       | 能否宣稱 hard gate |
| ----------------- | ------------------------------------------------------------------------------------------ | ------------------ |
| Code hard gate    | `validate_phase()` 產生的 `CRITICAL` check；任一失敗即 `passed=false`                      | 可以               |
| Workflow contract | Auto-Paper skill 規定 Agent 應執行的搜尋、審閱、修稿或人工確認；可能尚未由 phase gate 重算 | 不可以             |
| Advisory          | `WARNING` / `INFO`，用來提醒覆蓋率、Memory 或 Git provenance                               | 不可以             |

`get_pipeline_status()` 只是快速 heartbeat，只看少量檔案，不能取代 `validate_phase()`。後者會重算前置條件、內容完整性與部分 hooks，並把結果寫入 `.audit/gate-validations.jsonl`。

## Phase-by-phase code contract

<!-- phase-gate:0 -->

### Phase 0 — 素材與投稿限制

- **Code hard gate**：`journal-profile.yaml` 與 `.audit/source-materials.yaml` 都存在。
- **Workflow contract**：掃描 DOCX、XLSX、PDF、PPTX、CSV 等使用者素材，整理期刊字數、圖表、引用與投稿文件限制。
- **修正路徑**：執行 `project_action(action="source_materials")`；缺 profile 時執行 `project_action(action="journal_profile", ...)`。

<!-- phase-gate:1 -->

### Phase 1 — 專案骨架

- **Code hard gate**：`drafts/`、`references/`、`data/`、`results/`、`.audit/`、`.memory/` 六個目錄存在。
- **修正路徑**：建立或修復專案結構；後續 Phase 2 起另要求 `project.json`。

<!-- phase-gate:2 -->

### Phase 2 — 文獻集合

- **Code hard gate**：依 paper type 達到最低文獻數；每筆 reference 具穩定識別，且 trust provenance 沒有偽造或矛盾。
- **Advisory**：`search-strategy.md`、`reference-selection.md` 缺失只警告。
- **修正路徑**：補搜尋與篩選；PubMed 優先用 `save_reference_mcp`；遷移 legacy reference 或修復無法驗證的 metadata。

<!-- phase-gate:21 -->

### Phase 2.1 — 全文與原始素材解析

- **Code hard gate**：文獻數仍達 Phase 2 下限；`fulltext-ingestion-status.md` 非空；每筆 reference 都有可驗證的全文 receipt 或明確 fallback；每筆都有綁定目前 source revision 的完整分析；primary user material 不得仍為 `pending_asset_aware`。
- **Advisory**：沒有任何全文、過半文獻只有 metadata，或非主要素材尚未解析時提出警告。
- **修正路徑**：取得可用全文或記錄不可取得原因；重做過期分析；主要 DOCX/XLSX/PDF 等先交給 asset-aware，再寫回 ingestion receipt。

<!-- phase-gate:3 -->

### Phase 3 — 研究概念

- **Code hard gate**：`concept.md` 存在並含 `NOVELTY`、`KEY SELLING POINTS`；`.audit/concept-review.yaml` 結構完整；結論為可進行，或有可信 host/UI 簽發且綁定目前內容的外部 approval receipt。
- **Advisory**：`concept-validation.md` 缺失只警告。
- **修正路徑**：補齊研究問題、必要 claims、evidence obligations 與風險；修改後重跑 concept review。Agent/MCP 不能自行鑄造 human approval。

<!-- phase-gate:4 -->

### Phase 4 — 稿件計畫

- **Code hard gate**：Phase 3 concept review 仍可採用；`manuscript-plan.yaml` 或 legacy `drafts/manuscript-plan.md` 存在。
- **Workflow contract**：Section Brief、evidence coverage、字數／引用／圖表預算、寫作順序、manual approval 或 autopilot 自審紀錄。
- **重要邊界**：目前 phase validator **沒有重算** approver、reason、coverage 或圖表上限；網站不得把這些說成已 code-enforced。
- **修正路徑**：補建計畫；由研究者或 autopilot 依模式檢查內容。圖表與引用限制會在後續 hooks／review 再檢查。

<!-- phase-gate:5 -->

### Phase 5 — 分節寫作與資產

- **Code hard gate**：`manuscript.md` 與 Abstract、Introduction、Methods、Results、Discussion 存在；出現圖表或統計 claim 時有 data provenance；每個 required planned asset 已登記、放入指定 section、圖檔可匯出且 caption 有 review receipt；每個必需 section 在 `checkpoint.json` 有 recorded approval。
- **Workflow contract**：執行 A-series 即時檢查與 B-series section 檢查；approval 可以來自 manual review 或按設定留下的 autopilot 審閱紀錄，不等同於一律由使用者親自核准。
- **修正路徑**：只重寫失敗 section；補 provenance；重新產生、登記、審閱或插入資產；完成 section approval 後重跑 gate。

<!-- phase-gate:6 -->

### Phase 6 — 全稿品質稽核

- **Code hard gate**：`quality-scorecard.md`、`hook-effectiveness.md` 存在；YAML scorecard 至少四個有值維度且平均大於零；至少一個 hook 有 trigger/pass/fix/false-positive 事件；若有 data artifacts，必須有 validation report。
- **Workflow contract**：執行 C/F checks、修正 critical findings，必要時回到 Phase 5。
- **重要邊界**：validator 驗證「稽核資料真實存在」，但不會在 Phase 6 gate 內自動重跑所有 A/B/C checks，也沒有單獨解析「0 unresolved critical」。網站不得把後者說成目前的 code hard gate。
- **修正路徑**：執行 `quality_audit`、記錄 hook events、驗證 data artifacts；依 hook 結果定點修稿，再重跑相同檢查。

<!-- phase-gate:65 -->

### Phase 6.5 — 審稿前基線

- **Code hard gate**：稿件與 Phase 6 scorecard 前置條件存在；`evolution-log.jsonl` 存在且含 `baseline` event；`quality-scorecard.md` 存在。
- **修正路徑**：對目前稿件建立 baseline event 與品質基線，不能用空檔案代替 event。

<!-- phase-gate:7 -->

### Phase 7 — 多輪獨立審稿

- **Code hard gate**：review state 可重算且符合安全設定；至少兩輪；每輪有 review report、author response、EQUATOR report 或正式 N/A；稿件 hash chain 連續；R1–R6 由目前 artifacts 重跑通過；evolution events 與 state 一致；最後 review hash 等於目前稿件；以 `quality_met` 結束，或有綁定目前 state／稿件的可信外部 acceptance receipt。
- **修正路徑**：逐條回應並修稿，再開下一輪；重大問題可帶原因回退 Phase 5。`max_rounds`、`stagnated`、`user_needed` 本身都不是通過。

<!-- phase-gate:8 -->

### Phase 8 — 引用同步

- **Code hard gate**：Phase 7 已真正完成；稿件有 References section；所有 citation wikilinks 都能解析到已儲存 reference。
- **Workflow contract**：套用期刊引用格式、檢查引用分布與預算。
- **重要邊界**：格式與預算由 workflow、C-series 或 Phase 7 R6 處理，Phase 8 validator 本身只硬擋 References section 與 wikilink resolvability。
- **修正路徑**：補存 reference、修正 citekey 或移除無依據引用，重新同步 References；格式問題另跑對應 formatting/reference checks。

<!-- phase-gate:9 -->

### Phase 9 — 匯出

- **Code hard gate**：Phase 6 scorecard、Phase 7 review、Phase 8 reference sync 均有效；`exports/` 同時有 DOCX 與 PDF；DOCX zip/XML/可見文字與 PDF header/trailer 結構 smoke 通過。
- **修正路徑**：先修復上游稿件或引用，再重新產生損壞／缺失的 DOCX、PDF；不能只建立同副檔名空檔。

<!-- phase-gate:10 -->

### Phase 10 — 回顧與學習

- **Code hard gate**：存在正確命名的 `pipeline-run-*.md` 且含 D7、D8 headings；有 hook-effectiveness report；evolution log 有 `run_meta_learning` 事件；meta-learning audit 使用 v2 schema、source tool 正確、D1–D9 完整、count/list 相符，且能對上 evolution event。
- **Advisory**：project `.memory/activeContext.md`、`progress.md` 缺失只警告。
- **修正路徑**：執行正式 meta-learning 工具並補完整 retrospective；重新命名的手寫空檔或只填 counts 不能過關。

<!-- phase-gate:11 -->

### Phase 11 — 最終交付確認

- **Code hard gate**：Phase 9 的 DOCX/PDF 仍存在且再次通過 integrity smoke；Phase 10 gate 仍通過。
- **Advisory**：是否位於 Git repo、工作樹是否乾淨、最新 commit 是否含專案、remote 是否同步。
- **重要邊界**：目前沒有額外要求 `pipeline-completed` 或 final-delivery marker；Git 也不阻擋只需要論文檔案的使用者。
- **修正路徑**：hard failure 回到 Phase 9 或 10；Git warning 只需在使用者確實需要版本 provenance 時處理。

## 目前刻意不冒充 code enforcement 的項目

| 設計／workflow 目標                             | 目前落點                                                 |
| ----------------------------------------------- | -------------------------------------------------------- |
| Phase 4 approver、reason、coverage、budget      | Auto-Paper workflow contract；非 Phase 4 hard gate       |
| Phase 6 所有 hooks 重跑且 0 unresolved critical | workflow 執行責任；Phase 6 hard gate 驗 audit evidence   |
| Phase 8 citation style、distribution、budget    | C-series、R6 與 reference workflow；非 Phase 8 validator |
| Phase 11 completion marker                      | 未由 code 要求；交付以 valid exports + Phase 10 為準     |

未來若把上述項目升級為 code hard gate，必須同時更新 validator、行為測試、本文件與網站；只改設計文字不算完成。
