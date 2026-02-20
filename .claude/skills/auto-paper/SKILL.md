---
name: auto-paper
description: |
  全自動論文撰寫 + 閉環自我改進系統。
  LOAD THIS SKILL WHEN: 全自動寫論文、auto write、自動撰寫、幫我寫完整篇、autopilot、從頭到尾、一鍵寫論文
  CAPABILITIES: 編排所有研究 Skills + 3 層 Audit Hooks + Meta-Learning 自我改進
---

# 全自動論文撰寫 + 閉環自我改進

## 閉環架構

Instructions (AGENTS.md) → Skill (auto-paper) → Writing (drafts/) → Hooks (audit) → 回頭更新 Skill/Instructions

核心理念（CONSTITUTION §22）：可審計、可拆解、可重組。詳見 AGENTS.md。

四個審計維度：

| 維度        | 檢查                   | 更新對象               |
| ----------- | ---------------------- | ---------------------- |
| Paper       | 引用、字數、Anti-AI    | `patch_draft` 修正論文 |
| Methodology | 方法學可再現性         | 補充方法學細節         |
| Compliance  | Agent 是否遵循流程     | `.memory/` 記錄偏差    |
| Meta        | Skill/Hook/Instruction | 更新 SKILL/Hook/AGENTS |

---

## 執行審計軌跡（Audit Trail）

每次執行在 `projects/{slug}/.audit/` 產出：

| 檔案                     | 內容                                              |
| ------------------------ | ------------------------------------------------- |
| `pipeline-run-{ts}.md`   | Phase 摘要 + Hook 統計 + Decision Log             |
| `search-strategy.md`     | 搜尋策略和結果                                    |
| `reference-selection.md` | 文獻篩選決策                                      |
| `concept-validation.md`  | Novelty 驗證過程                                  |
| `hook-effectiveness.md`  | Hook 觸發率/通過率/誤報率                         |
| `quality-scorecard.md`   | 方法學 + 文字品質（0-10 分）                      |
| `checkpoint.json`        | 斷點恢復：`last_completed_phase`, `phase_outputs` |

恢復邏輯：偵測 checkpoint.json → 詢問從 Phase N+1 繼續或重來。

---

## 雙重 Hook 系統

Copilot Hooks（A-D，寫作時即時修正）定義於本檔。
Pre-Commit Hooks（P1-P8 + G1-G7）定義於 `git-precommit/SKILL.md`。
兩者互補：Copilot 處理細節，Pre-Commit 處理全局。

---

## 9-Phase Pipeline

### Phase 1: PROJECT SETUP

**Skill**: `project-management`

1. `get_current_project()` → 有專案就切換，沒有就建立
2. `create_project(name, paper_type)` 或 `switch_project(slug)`
3. `setup_project_interactive()`

**Gate**: 專案存在 + paper_type 已設定

---

### Phase 2: LITERATURE SEARCH

**Skill**: `literature-review`, `parallel-search`
**外部 MCP**: `pubmed-search`, `zotero-keeper`（optional）

1. `generate_search_queries(topic, strategy="comprehensive")`
2. 並行 `search_literature()` × 3-5 組
3. `merge_search_results()`
4. `get_citation_metrics(sort_by="relative_citation_ratio")`
5. 選前 15-20 篇 → `save_reference_mcp(pmid, agent_notes)`
6. [Optional] Zotero: `search_items(query)` → 取 PMID → `save_reference_mcp()`

**Gate**: ≥10 篇文獻已儲存

自動決策：<20 → `expand_search_queries`；>500 → 加 MeSH 限縮；用戶有 Zotero → 主動問匯入。

---

### Phase 3: CONCEPT DEVELOPMENT

**Skill**: `concept-development`
**外部 MCP**: `cgu`（when novelty needs boost）

1. 分析 saved references → 識別 Gap
2. 撰寫 concept.md（含 🔒 NOVELTY + 🔒 SELLING POINTS）
3. `write_draft(filename="concept.md", content=..., skip_validation=True)`
4. `validate_concept(project=...)`
5. IF score < 75:
   - 自動修正 1 次 → 再驗證
   - 仍 < 75 → CGU: `deep_think` / `spark_collision` / `generate_ideas` → 修正 → 再驗證
   - 仍 < 75 → STOP，回報用戶（附 CGU 建議）

**Gate**: concept score ≥ 75 OR 用戶明確說「繼續」

CGU 工具對應：

| 問題     | CGU 工具                 | 產出                |
| -------- | ------------------------ | ------------------- |
| 找弱點   | `deep_think`             | Reviewer 攻擊角度   |
| 找論點   | `spark_collision`        | 碰撞新穎角度        |
| 廣泛發想 | `generate_ideas`         | 3-5 個 novelty 候選 |
| 多觀點   | `multi_agent_brainstorm` | 多角色辯論          |

---

### Phase 4: MANUSCRIPT PLANNING（唯一人工確認點）

1. 讀取 concept.md + saved references + paper_type
2. 產出段落級大綱（每段：topic, words, refs, claims）
3. Asset Planning（表格/圖/流程圖清單，含 tool + data_source）
4. 🗣️ 呈現大綱 + Asset Plan 給用戶確認
5. 用戶調整 → 確認 → 儲存到 .memory/

**Gate**: 大綱 + Asset Plan 已確認

寫作順序（依 paper type）：

| Paper Type        | 建議順序                                                 |
| ----------------- | -------------------------------------------------------- |
| original-research | Methods → Results → Introduction → Discussion → Abstract |
| systematic-review | Methods → Results → Discussion → Introduction → Abstract |
| case-report       | Case Presentation → Discussion → Introduction → Abstract |

---

### Phase 5: SECTION WRITING（核心 + Audit Loop）

**Skill**: `draft-writing`
**外部 MCP**: `drawio`（diagrams）, `cgu`（Discussion）

```
FOR section IN writing_order:
  1. 讀取 outline[section] + 已完成 sections + get_available_citations()
  2. IF Methods + asset_plan 有 diagram:
     → drawio.create_diagram → save_diagram(project, content)
  3. draft_section() 或 write_draft()
  4. IF Results + asset_plan:
     → generate_table_one / create_plot / run_statistical_test → 整合
  5. IF Discussion + 論點弱:
     → cgu.deep_think → 強化邏輯鏈
  6. 🔔 HOOK A: post-write → IF issues → patch_draft（最多 2 rounds）
  7. 🔔 HOOK B: post-section
  8. Log 到 .memory/progress.md
```

---

### Phase 6: CROSS-SECTION AUDIT

1. 🔔 HOOK C: post-manuscript
2. IF critical issues → `patch_draft` 定點修正（最多 2 rounds）

**Gate**: 0 critical issues（warnings 可接受）

---

### Phase 7: REFERENCE SYNC

1. `sync_references(filename=manuscript)` → 生成 References section
2. 確認所有 `[[wikilinks]]` 已解析
3. `format_references(style=journal_style)`

**Gate**: 0 broken links

---

### Phase 8: EXPORT

**Skill**: `word-export`

1. `list_templates()` → 選擇 template
2. `start_document_session()` → `insert_section()` × N
3. `verify_document()` → `save_document()`

**Gate**: Word 已匯出

---

### Phase 9: RETROSPECTIVE（閉環核心）

🔔 HOOK D: meta-learning（見下方定義）

1. 回顧執行紀錄 + Hook 觸發統計
2. 更新 SKILL.md Lessons Learned
3. 更新 AGENTS.md（如適用）
4. 更新 .memory/ 完整紀錄

---

## Copilot Hooks 定義（寫作時觸發）

### Hook A: post-write（每次寫完立即）

| #   | 檢查項             | MCP Tool                  | 失敗行為                            |
| --- | ------------------ | ------------------------- | ----------------------------------- |
| A1  | 字數在 target ±20% | `count_words`             | `patch_draft` 精簡/擴充             |
| A2  | 引用密度達標       | `get_available_citations` | `suggest_citations` + `patch_draft` |
| A3  | 無 Anti-AI 模式    | `read_draft` + Agent 掃描 | `patch_draft` 改寫                  |
| A4  | Wikilink 格式正確  | `validate_wikilinks`      | 自動修復                            |

A2 引用密度標準：Introduction ≥1/100w, Methods ≥0, Results ≥0, Discussion ≥1/150w

A3 Anti-AI 禁止詞：`In recent years`, `It is worth noting`, `Furthermore`(段首), `plays a crucial role`, `has garnered significant attention`, `a comprehensive understanding`, `This groundbreaking` → 替換為具體內容。

---

### Hook B: post-section（section 完成後）

| #   | 檢查項                          | MCP Tool                                | 失敗行為              |
| --- | ------------------------------- | --------------------------------------- | --------------------- |
| B1  | 與 concept.md 一致              | `read_draft("concept.md")` + Agent 比對 | 重寫不一致段落        |
| B2  | 🔒 NOVELTY 在 Intro 體現        | `read_draft` 檢查                       | `patch_draft` 加入    |
| B3  | 🔒 SELLING POINTS 在 Discussion | 逐條比對                                | `patch_draft` 補充    |
| B4  | 與已寫 sections 不矛盾          | `read_draft` 交叉比對                   | 修正矛盾處            |
| B5  | 方法學可再現性                  | Agent 依 paper_type 評估                | `patch_draft` 補細節  |
| B6  | 寫作順序驗證                    | `check_writing_order`                   | ⚠️ Advisory（不阻擋） |

#### B5 方法學 Checklist

| 檢查項        |    Original    | Case | Systematic |
| ------------- | :------------: | :--: | :--------: |
| 研究設計描述  |       ✅       |  ✅  |     ✅     |
| 主要/次要結局 |       ✅       |  ⬜  |     ✅     |
| 樣本量/power  |       ✅       |  ⬜  |     ⬜     |
| 納入/排除標準 |       ✅       |  ⬜  |     ✅     |
| 統計方法匹配  |       ✅       |  ⬜  |     ✅     |
| 變項定義      |       ✅       |  ✅  |     ⬜     |
| 倫理聲明      |       ✅       |  ✅  |     ⬜     |
| 收集期間      |       ✅       |  ✅  |     ✅     |
| EQUATOR       | CONSORT/STROBE | CARE |   PRISMA   |

任何必選項 < 5 分 → patch_draft → 2 rounds 後仍 < 5 → 人工介入。

#### B6 前置條件

| Target     | 前置            | 原因                    |
| ---------- | --------------- | ----------------------- |
| Results    | Methods         | Results 依 Methods 定義 |
| Discussion | Results + Intro | 討論 Results 回應 Intro |
| Conclusion | Discussion      | 總結 Discussion         |
| Abstract   | 所有主體        | 摘錄精華                |

Advisory only（§22 可重組），審計軌跡記錄跳過。

---

### Hook C: post-manuscript（全稿完成後）

| #   | 檢查項              | MCP Tool                          | 失敗行為                  |
| --- | ------------------- | --------------------------------- | ------------------------- |
| C1  | 稿件一致性          | `check_formatting("consistency")` | `patch_draft`             |
| C2  | 投稿清單            | `check_formatting("submission")`  | 定點修正                  |
| C3  | N 值跨 section 一致 | `read_draft` × N + 數字比對       | `patch_draft` 統一        |
| C4  | 縮寫首次定義        | `read_draft` + 全文掃描           | `patch_draft` 補定義      |
| C5  | Wikilinks 可解析    | `scan_draft_citations`            | `save_reference_mcp` 補存 |
| C6  | 總字數合規          | `count_words`                     | 精簡超長 section          |

---

### Hook D: meta-learning（Phase 9，閉環核心）

Hook D 不只改進 SKILL — 它改進 Hook 自身（CONSTITUTION §23）。

#### D1: 效能統計

讀取 `.audit/pipeline-run-{latest}.md`，統計各 Hook 觸發率/通過率/修正率/誤報率。

效能判斷（§23）：

- 觸發率 > 80% → Hook 太嚴格，建議放寬閾值
- 觸發率 < 5%（超過 5 次執行）→ Hook 太鬆/過時，考慮移除
- 誤報率 > 30% → 判斷標準需修正

#### D3: Hook 自我改進

**自動調整**（不需確認）：

- Anti-AI 誤報 → 移出禁止清單
- 引用密度不合理 → 調整 ±20%
- 字數限制微調 → ±10%
- B5 持續 >8 分項目 → 降低檢查頻率

**需用戶確認**：新增/移除 Hook、修改判斷邏輯（非閾值）

**禁止修改**：CONSTITUTION 原則、🔒 規則、save_reference_mcp 優先、Hook D 自身邏輯

#### D4-D5: SKILL + Instruction 改進

- 某 Hook 觸發 >2 次同類問題 → 加入 pre-check
- 某 Phase 始終不需要 → 標記 OPTIONAL
- 觸發語不夠 → 更新 AGENTS.md
- Instruction 與 Skill 不一致 → 同步修正（記錄 decisionLog）

#### D6: 記錄審計軌跡

更新：`.audit/hook-effectiveness.md`, `.audit/quality-scorecard.md`, `.memory/progress.md`, `.memory/activeContext.md`, `memory-bank/decisionLog.md`, 本檔 Lessons Learned

---

## 自動決策邏輯

| 情境              | 自動行為         | 停下條件         |
| ----------------- | ---------------- | ---------------- |
| 搜尋不足          | 擴展搜尋         | 3 輪後仍 <10 篇  |
| Concept 65-74     | 自動修正 1 次    | 仍 <75           |
| Hook A 字數超標   | patch_draft 精簡 | 2 rounds 後仍超  |
| Hook A 引用不足   | suggest + patch  | 無可用引用       |
| Hook B 🔒 缺失    | patch 加入       | 需改研究方向     |
| Hook B5 <5 分     | patch 補細節     | 2 rounds 後仍 <5 |
| Hook C 數字不一致 | 修正到最新       | 不確定哪個正確   |
| Hook D 閾值微調   | ±20%             | 超出範圍         |
| Hook D 新增/移除  | 提出建議         | 永遠需確認       |

**必須停下**：Concept < 60（兩次仍低）、Phase 4 大綱 approve、研究方向改變、3 rounds Hook 仍失敗、修改 AGENTS.md 核心原則。

---

## Cross-Tool Orchestration Map

核心原則：Pipeline 定義「何時」→ Skill 定義「如何」→ Hook 定義「品質」。

### 跨 MCP 傳遞規則

| 來源          | 目標       | 傳遞物   | 規則                                 |
| ------------- | ---------- | -------- | ------------------------------------ |
| pubmed-search | mdpaper    | PMID     | `save_reference_mcp(pmid)` 只傳 PMID |
| zotero-keeper | mdpaper    | PMID/DOI | 取 PMID → `save_reference_mcp()`     |
| cgu           | concept.md | 文字建議 | Agent 整合到 `write_draft()`         |
| drawio        | mdpaper    | XML      | `save_diagram(project, content)`     |
| data tools    | drafts     | 表格/圖  | Agent 整合到 draft 文字              |

### 何時跳過外部 MCP

| 情境                         | 跳過             |
| ---------------------------- | ---------------- |
| 無 Zotero                    | zotero-keeper    |
| Concept ≥ 75 首次通過        | CGU              |
| 無資料集                     | table_one / plot |
| 純 review（無 Methods flow） | drawio           |

---

## Skill 依賴

auto-paper → project-management(P1) → literature-review + parallel-search(P2) → concept-development(P3) → draft-writing(P4,5) → reference-management(P7) → word-export(P8) → submission-preparation(P8)

---

## 閉環檢查清單

- [ ] 所有 section 通過 Hook A + B
- [ ] 全稿通過 Hook C
- [ ] .memory/ 已更新
- [ ] Hook D meta-learning 已執行
- [ ] SKILL.md Lessons Learned 已更新
- [ ] Word 已匯出

---

## Lessons Learned（Hook D 自動更新區）

_尚無記錄。首次全自動執行後將自動填入。_
