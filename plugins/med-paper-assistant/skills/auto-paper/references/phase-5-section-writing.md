# Phase 5: SECTION WRITING（核心 + Cascading Audit Loop）

> auto-paper 的 reference 檔（progressive disclosure）；入口與 hard gate 見 [../SKILL.md](../SKILL.md)。
> **Read this when**: running, resuming or debugging Phase 5 section writing and its per-section Hook A/B loop.
> 相關：[hooks-a-b-post-write-section.md](hooks-a-b-post-write-section.md)、[phase-5-asset-generation.md](phase-5-asset-generation.md)、[phase-4-writing-templates.md](phase-4-writing-templates.md)

---

### Phase 5: SECTION WRITING（核心 + Cascading Audit Loop）

**Skill**: `draft-writing`
**外部 MCP**: `drawio`（diagrams）, `cgu`（Discussion）, `data-tools`（圖表）
**輸入**: `manuscript-plan.yaml`（Phase 4 產出）

```
plan = load("manuscript-plan.yaml")

FOR section IN plan.writing_order:

  brief = plan.sections[section]

  ── Step 1: 準備 ──
  1a. 讀取 brief.paragraphs + 已完成 sections + draft_action(action="available_citations")()
  1b. 讀取 plan.asset_plan[section] → 確認需要哪些圖表

  ── Step 2: Asset 生成（先於寫作，見 phase-5-asset-generation.md 的 Asset Sub-Pipeline）──
  2a. IF plan.asset_plan 有該 section 的 asset:
      → 執行 Asset Generation Sub-Pipeline
      → 產出 asset manifest entries（圖表路徑 + caption）

  ── Step 3: 撰寫（段落級 Brief 引導） ──
  3a. IF Methods + asset_plan 有 diagram:
      → drawio.create_diagram → XML
      → drawio.export_diagram → PNG/SVG
      → project_action(action="save_diagram", project=..., content=..., rendered_content=..., rendered_format=...)
      → draft_action(action="insert_figure", filename=..., caption=..., draft_filename=..., after_section=...)
  3b. FOR paragraph IN brief.paragraphs:
      → 依據 paragraph.topic + key_claims + must_cite 撰寫
      → 尊重 paragraph.word_target
      → 若 paragraph.protected = true → 確保 🔒 內容完整
      → 若 paragraph.checklist_items → 逐條涵蓋
      → ✍️ 每段開始前呼叫 `workspace_state_action(action="checkpoint", section=..., plan=..., notes=..., references_in_use=...)`
        → 儲存寫作大綱與推理狀態，防止 compaction 遺失
  3c. draft_action(action="section") 或 draft_action(action="write")
      → 撰寫時整合 Step 2 產出的 asset references
      → ✅ 成功後自動 checkpoint 至 .mdpaper-state.json（無需手動）
  3d. IF Discussion + 論點弱:
      → cgu.deep_think → 強化邏輯鏈

  ── Step 4: Cascading Audit Loop（最多 3 rounds） ──
  4a. 🔔 HOOK A: post-write audit
      → Round 1: run A1-A4 → collect issues
        A1: 字數 vs brief.word_budget
        IF issues → draft_action(action="patch") 修正 → re-run A1-A4
      → Round 2: IF still issues → draft_action(action="patch")（不同策略）→ re-run
      → Round 3: IF still issues → LOG to .audit/ + FLAG for Phase 6

  4b. 🔔 HOOK B: post-section audit
      → run B1-B7 → collect issues
      → B7: Section Brief 合規（段落級比對 + caption_requirements，見 hooks-a-b-post-write-section.md 的 Hook B7 定義）
      → IF critical (B1 concept 不一致 / B2 🔒 缺失 / B5 <5):
        → targeted draft_action(action="patch") → re-run Hook A on patched areas (1 round)
        → re-run Hook B → IF still critical → FLAG for Phase 6
      → IF advisory only → LOG + continue

  ── Step 5: Agent 自主審閱 + 即時修正（Autopilot 預設行為）──

  **核心原則**：Agent 在寫完 section 後立即自我評估，發現問題就地修正，
  不需等到 Phase 7 Review 才回頭改。這才是真正的 autopilot。

  5a. Agent 自行評估 section 品質：
      - Hook A/B 結果 → 有無未解 CRITICAL/WARNING
      - 與 concept.md 的一致性
      - 與已完成 sections 的邏輯連貫性
      - 段落是否完整涵蓋 manuscript-plan.yaml 的 key_claims
  5b. IF 發現問題 → Agent 立即修正：
      - 針對性 draft_action(action="patch") → re-run 相關 Hook
      - 修正直到 0 CRITICAL，或達 cascading 上限後 FLAG for Phase 6
      - 決策和修正記入 `.audit/pipeline-run-{ts}.md`
  5c. 自我評估通過 → Agent 呼叫 `pipeline_action(action="approve_section", section=section, decision="approve")`
      → 自動標記 approved → 繼續下一個 section
  5d. **用戶可隨時介入**：
      - 用戶說「我要看一下」→ Agent 暫停，呈現 section 摘要
      - 用戶說「每個 section 都讓我看」→ Agent 對後續 section 切換為手動審閱模式

  **手動審閱模式**（`pipeline.autopilot: false` 或 `autopilot_pause_at` 含 `"phase5_section"`）：
  5e. 呈現 section 內容摘要（字數、主要論點、Hook A/B 結果）
  5f. 🗣️ 詢問用戶：「approve / 請修改（附具體意見）」
  5g. Agent 呼叫 `pipeline_action(action="approve_section", section=section, decision=action, feedback=feedback)`
  5h. IF action == "revise":
      → 根據 feedback 執行 draft_action(action="patch") / draft_action(action="write") 修正
      → re-run Hook A/B on modified content
      → 回到 5e 再次呈現（最多 3 輪修改）
  5i. IF action == "approve":
      → 繼續到下一個 section

    ⏸️ 暫停點：用戶可隨時說「暫停」→ Agent 呼叫 `pipeline_action(action="pause")`
     → 用戶自由編輯草稿
      → 用戶說「繼續」→ Agent 呼叫 `pipeline_action(action="resume")`
     → 根據修改偵測結果重新跑相關 Hook

  ── Step 6: 記錄 ──
  6a. Log section audit results 到 .audit/pipeline-run-{ts}.md
  6b. Log 到 .memory/progress.md
  6c. 更新 checkpoint.json: { last_section: section, audit_status }
  6d. IF plan 需修改 → 寫入 plan.metadata.changelog + 存檔
```
