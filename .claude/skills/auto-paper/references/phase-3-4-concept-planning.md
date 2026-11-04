# Phase 3-4: CONCEPT DEVELOPMENT + MANUSCRIPT PLANNING

> auto-paper 的 reference 檔（progressive disclosure）；入口與 hard gate 見 [../SKILL.md](../SKILL.md)。
> **Read this when**: validating concept novelty (score < 75, CGU escalation), approving the outline, or generating / editing `manuscript-plan.yaml`.
> 相關：[phase-4-writing-templates.md](phase-4-writing-templates.md)、[phase-5-section-writing.md](phase-5-section-writing.md)

---

### Phase 3: CONCEPT DEVELOPMENT

**Skill**: `concept-development`
**外部 MCP**: `cgu`（when novelty needs boost）

1. 分析 saved references → 識別 Gap
2. 撰寫 concept.md（含 🔒 NOVELTY + 🔒 SELLING POINTS）
3. `draft_action(action="write", filename="concept.md", content=..., skip_validation=True)`
4. `validation_action(action="concept")(project=...)`
5. IF score < 75:
   - 自動修正 1 次 → 再驗證
   - 仍 < 75 → CGU: `deep_think` / `spark_collision` / `generate_ideas` → 修正 → 再驗證
   - 仍 < 75 → STOP，回報用戶（附 CGU 建議）

**Code hard gate**: `concept.md` 含 NOVELTY / KEY SELLING POINTS、structured concept review 完整，且 decision 可採用（通常為 `readiness=ready`），或可信 host/UI 依用戶明確決定簽發
`mdpaper.concept_review_override.v3` Ed25519 receipt。MCP/Agent 只能查詢或撤銷 receipt，
不得以 `approved_by="human"` 或直接寫 YAML 冒充人類核准。

CGU 工具對應：

| 問題     | CGU 工具                 | 產出                |
| -------- | ------------------------ | ------------------- |
| 找弱點   | `deep_think`             | Reviewer 攻擊角度   |
| 找論點   | `spark_collision`        | 碰撞新穎角度        |
| 廣泛發想 | `generate_ideas`         | 3-5 個 novelty 候選 |
| 多觀點   | `multi_agent_brainstorm` | 多角色辯論          |

---

### Phase 4: MANUSCRIPT PLANNING

**產出物：`manuscript-plan.yaml`**（存在 `projects/{slug}/` 下）

1. 讀取 concept.md + saved references + **journal-profile.yaml**
2. 產出 `manuscript-plan.yaml`（段落級 Section Brief）：
   - `writing_order`: 依 `journal-profile.paper.sections`，fallback 到 paper type 預設
   - `sections`: 每個 section 包含 `word_budget` + `paragraphs[]`
     - 每段：`id`, `function`, `topic`, `key_claims`, `must_cite`, `word_target`
     - 🔒 保護段落標記 `protected: true`（Novelty Statement / Selling Points）
     - Methods 段落可含 `checklist_items`（對應 B5 方法學）
   - `asset_plan`: 圖/表/流程圖（含 `tool`, `tool_args`, `caption`, `caption_requirements`）
     - ⚠️ 驗證總數 ≤ `assets.figures_max` + `assets.tables_max`
     - ⚠️ 驗證 ≤ `assets.total_display_items_max`
   - `submission_checklist`: 依 `required_documents.*` 列出需準備項目
   - `metadata`: `generated_at`, `based_on`, `changelog[]`
3. Plan 修改規則：
   - Agent 可新增段落 / 修改 claims / 調字數 → **需寫入 `metadata.changelog`**
   - Agent **禁止**刪除 `protected: true` 段落
   - 用戶自由修改，changelog 自動追蹤
4. **Autopilot 模式**（`pipeline.autopilot: true`，預設）：
   - Agent 自行驗證 plan 的完整性（圖表數量、字數預算、section 涵蓋度）
   - 驗證通過 → 直接存入 `projects/{slug}/manuscript-plan.yaml` → 繼續 Phase 5
   - 驗證失敗 → Agent 自行修正 → 重新驗證（最多 2 輪）→ 仍失敗才詢問用戶
   - Plan 摘要記入 `.audit/pipeline-run-{ts}.md`，用戶可事後查閱
5. **手動模式**（`pipeline.autopilot: false` 或 `autopilot_pause_at` 含 `"phase4"`）：
   - 🗣️ 呈現 manuscript-plan.yaml 摘要給用戶確認
   - 用戶調整 → 確認 → 存入

**Code hard gate**: Phase 3 concept review 仍可採用 + `manuscript-plan.yaml`（或 legacy `drafts/manuscript-plan.md`）存在。圖表數量、coverage、approval reason 是本 workflow 的自審／人工審閱要求；目前 Phase 4 validator 未逐欄重算。

寫作順序（依 journal-profile.paper.sections，fallback 到 paper type 預設）：

| Paper Type        | 建議順序                                                 |
| ----------------- | -------------------------------------------------------- |
| original-research | Methods → Results → Introduction → Discussion → Abstract |
| systematic-review | Methods → Results → Discussion → Introduction → Abstract |
| case-report       | Case Presentation → Discussion → Introduction → Abstract |

---

### Phase 4 advisory task: SUPPLEMENTARY PLANNING

**輸入**: `manuscript-plan.yaml`（Phase 4 產出）
**輸出**: `manuscript-plan.yaml` 更新（新增 `supplementary` 區段）

目的：在撰寫前規劃補充材料（Supplementary Materials），避免主稿完成後才回頭補。

1. 根據期刊 profile 判斷是否需要補充材料
2. 規劃補充內容：

   - Supplementary Tables（大型數據表、子群分析）
   - Supplementary Figures（額外結果圖）
   - Supplementary Methods（詳細方法學、程式碼）
   - 敏感度分析結果
   - EQUATOR checklist 完整版（如 CONSORT flow diagram）

3. 在 `manuscript-plan.yaml` 加入 `supplementary` 區段：

```yaml
supplementary:
  - id: S1
    type: table
    title: "Baseline characteristics by subgroup"
    linked_section: Results
  - id: S2
    type: figure
    title: "Sensitivity analysis forest plot"
    linked_section: Results
```

4. 建立 `supplementary/` 目錄結構

**Advisory checkpoint**: manuscript-plan.yaml 含 supplementary 區段（可為空 = 無需補充材料）；正式 gate 仍是 Phase 4。
