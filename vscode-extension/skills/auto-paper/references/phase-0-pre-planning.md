# Phase 0: PRE-PLANNING（Source Materials + Journal Profile + Pipeline Config）

> auto-paper 的 reference 檔（progressive disclosure）；入口與 hard gate 見 [../SKILL.md](../SKILL.md)。
> **Read this when**: starting a project, scanning workspace source materials, generating `journal-profile.yaml`, or looking up which `pipeline.*` thresholds apply.
> 相關：[phase-1-2-project-literature.md](phase-1-2-project-literature.md)、[cross-tool-orchestration.md](cross-tool-orchestration.md)

---

### Phase 0: PRE-PLANNING（Source Materials + Journal Profile + Pipeline Config）🆕

**目的**：在任何寫作開始前，先登記用戶提供的原始素材，再建立結構化的期刊約束 + Pipeline 行為設定。
**產出**：`projects/{slug}/journal-profile.yaml` + `projects/{slug}/.audit/source-materials.yaml`

```
── Step 0: 掃描用戶原始素材（不可略過）──
  1. 呼叫 `project_action(action="source_materials")`
     - 預設掃描 workspace root，排除 projects/src/tests/node_modules 等 generated/code trees
     - 偵測 `.docx`, `.xlsx`, `.xls`, `.csv`, `.tsv`, `.pdf`, `.rtf`, `.pptx`, `.txt`
     - 產出 `.audit/source-materials.yaml` 和 `.audit/source-materials.md`
  2. 若 manifest 有 `pending_asset_aware > 0`：
     - 對 `agent_next_steps.asset_aware_file_paths` 呼叫 asset-aware `ingest_documents`
     - 表格型 DOCX/XLSX 必須先轉成 context，不能只根據摘要腦補
     - 後續 Phase 4/5 的 asset plan / results drafting 必須以這些 primary_user_material 為優先證據
  3. 即使沒有找到素材，也必須保留 0-candidate manifest，證明 agent 已掃描過 workspace。

── Step 1: 資訊來源 ──
Agent 按優先順序取得期刊要求：
  a) 用戶提供 submission guide / for-authors PDF/URL
     → 解析文件 → 自動填入 YAML（需用戶確認）
  b) 用戶口頭說明（例：「BJA, original research, 3000字」）
     → Agent 先查 templates/journal-profiles/ 內建期刊庫（麻醉學 Top 20）
     → 有匹配 → 讀取 YAML → 複製到專案 → 用戶確認
     → 無匹配 → 從 template 建立 + 補全欄位
  c) 無明確期刊 → 使用 paper_type 預設值
     → 產出 YAML 後提醒用戶日後補充

  💡 提醒用戶：可直接請 Copilot 讀取內建期刊設定（templates/journal-profiles/），
     例如「幫我套用 BJA 的設定」即可自動產生 journal-profile.yaml。
     用 read_file 閱讀 _index.yaml 可查看所有 20 個可用期刊。

── Step 2: 產生 journal-profile.yaml ──
  1. 從 templates/journal-profile.template.yaml 複製模板
  2. 填入期刊資訊、字數限制、圖表上限
  3. 設定 pipeline 行為（loop 上限、review 輪數）
  4. 設定 reporting guidelines checklist
  5. 🗣️ 呈現 YAML 摘要給用戶確認
     → 特別強調：字數上限、圖表上限、必要文件、loop 設定

── Step 3: 解析 submission guide（如有）──
  IF 用戶提供 submission guide 文件：
    a) 讀取文件內容（PDF/URL）
    b) 提取結構化資訊：
       - 字數限制（total + per section）
       - 圖表限制（數量 + 格式 + DPI）
       - 引用格式 + 上限
       - 必要文件清單
       - 報告指引要求
    c) 填入 YAML 對應欄位
    d) 標註 ⚠️ 不確定的欄位 → 請用戶確認
```

#### journal-profile.yaml 對全 Pipeline 的約束

| YAML 欄位                        | 影響的 Phase / Hook                         |
| -------------------------------- | ------------------------------------------- |
| `paper.type`                     | Phase 1 專案設定, Phase 4 寫作順序          |
| `paper.sections`                 | Phase 4 大綱, Phase 5 寫作順序              |
| `word_limits.*`                  | Hook A1 字數, Hook C6 總字數                |
| `assets.figures_max/tables_max`  | Phase 4 Asset Plan, Phase 5 Asset 生成      |
| `references.max_references`      | Phase 7 R6 / Phase 8 reference workflow     |
| `references.reference_limits`    | 按論文類型的引用上限（覆蓋 max_references） |
| `references.style`               | Phase 8 引用格式                            |
| `reporting_guidelines.checklist` | Hook B5 方法學, Hook C2 投稿清單            |
| `required_documents.*`           | Phase 9 匯出, Hook C2 投稿清單              |

#### source-materials.yaml 對全 Pipeline 的約束

| YAML 欄位                                 | 影響的 Phase / Hook                                     |
| ----------------------------------------- | ------------------------------------------------------- |
| `summary.total_candidates`                | Phase 0 是否已實際掃描用戶素材                          |
| `materials[].evidence_priority`           | Phase 3 concept、Phase 4 plan、Phase 5 results/methods  |
| `materials[].ingestion.status`            | Phase 2.1/Phase 5 是否需先用 asset-aware 解析 DOCX/XLSX |
| `agent_next_steps.asset_aware_file_paths` | Agent 必須呼叫 asset-aware 的具體 file list             |
| `agent_next_steps.asset_aware_required`   | 防止只讀摘要、漏讀正式表格/資料檔                       |

**Data Anchor Provenance Rule**：`data-artifacts.yaml` 的 `data_anchors` 不得以 `concept.md`、agent summary、inferred/estimated 值作為來源。每個數字/統計 anchor 必須引用 ready/ingested `source_material_id`、`asset_aware_doc_id`、`data_artifact_id`，或可信 data file；若來源素材仍是 `pending_asset_aware`，Hook F4 必須 CRITICAL fail。
| `pipeline.hook_*_max_rounds` | Hook A/B/C cascading 上限 |
| `pipeline.review_max_rounds` | Phase 7 Autonomous Review 輪數 |
| `pipeline.writing.anti_ai_*` | Hook A3 Anti-AI 嚴格度 |
| `pipeline.writing.citation_density` | Hook A2 引用密度標準 |
| `pipeline.assets.*` | Phase 5 Asset Sub-Pipeline 行為 |
| `pipeline.autopilot` | 全自動模式（預設 true） |

> 📌 `#### Autopilot 模式（預設開啟）`（含安全閥）與 Phase 0 的 **Code hard gate** 是全 Pipeline 的不可跳過規則，保留在 [../SKILL.md](../SKILL.md)。
