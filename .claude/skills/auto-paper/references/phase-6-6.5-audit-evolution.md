# Phase 6-6.5: CROSS-SECTION CASCADING AUDIT + EVOLUTION GATE

> auto-paper 的 reference 檔（progressive disclosure）；入口與 hard gate 見 [../SKILL.md](../SKILL.md)。
> **Read this when**: running the whole-manuscript Hook C audit, handling Phase 5 FLAGs, or creating the pre-review baseline.
> 相關：[hooks-c-post-manuscript.md](hooks-c-post-manuscript.md)、[phase-7-review-loop.md](phase-7-review-loop.md)

---

### Phase 6: CROSS-SECTION CASCADING AUDIT

三階段審計：先全稿檢查 → 再回溯修正 → 最終驗證。

```
── Stage 1: 全稿掃描 ──
1. 🔔 HOOK C: post-manuscript (C1-C8, C9-C14)
2. 收集所有 issues → 分類為 CRITICAL / WARNING / INFO
3. 收集 Phase 5 FLAG（未解決的 Hook A/B issues）

── Stage 2: 分層回溯修正（Cascading Fix，最多 3 rounds）──
Round 1:
  FOR each CRITICAL issue:
    a. 定位到具體 section + 段落
    b. draft_action(action="patch") 修正
    c. re-run 該 section 的 Hook A（確認 patch 沒破壞原有品質）
  → re-run Hook C (C1-C8, C14 where strong claims changed)

Round 2 (IF still CRITICAL):
  FOR each remaining CRITICAL:
    a. 分析 Round 1 修正為什麼失敗
    b. 嘗試不同修正策略（重寫段落 vs 微調）
    c. draft_action(action="patch")
  → re-run Hook C

Round 3 (IF still CRITICAL):
  → LOG all remaining issues to .audit/quality-scorecard.md
  → 呈現給用戶，附具體修改建議
  → 等待用戶決定（修改 / 接受 / 回到 Phase 5 重寫）

── Stage 3: 最終驗證 ──
4. re-run Hook C → 確認 0 CRITICAL
5. 生成 quality-scorecard.md（量化分數）
6. 更新 checkpoint.json
```

**Workflow exit target**: Hook C/F 已處理至沒有未解決 CRITICAL（warnings 記錄但可接受）。**Code hard gate** 另驗證 quality-scorecard / hook-effectiveness 的有效資料與 data-artifact report；目前 validator 不在 Phase 6 內重跑全部 A/B/C hooks，也不單獨解析 unresolved-critical count。

#### Cascading 回溯規則

| Hook C Issue              | 回溯到              | 觸發的 Hook                  |
| ------------------------- | ------------------- | ---------------------------- |
| C1 稿件不一致             | 較弱 section        | Hook B4 → Hook A             |
| C3 N 值跨 section 不一致  | 所有含 N 的 section | Hook A → patch               |
| C4 縮寫未定義             | 首次出現的 section  | Hook A4 → patch              |
| C5 Wikilinks 不可解析     | 對應 section        | Hook A2 → A4                 |
| C6 總字數超標             | 最長 section        | Hook A1 → patch              |
| C7a 圖表超限              | —                   | 合併或移至 supplementary     |
| C7b asset-plan 未覆蓋     | 對應 section/asset  | 補登記、放置或可匯出資產     |
| C7d phantom 引用          | 對應 section        | 插入缺漏圖表或移除引用       |
| C11 引用分布不均          | 缺引用的 section    | Hook A2 → 補引用             |
| C12 引用缺決策紀錄        | —                   | 生成 citation_decisions.json |
| C13 圖表順序/caption 問題 | 對應 section        | Hook C7d → patch             |

---

### Phase 6.5: EVOLUTION GATE（強制進入 Review）🆕

**目的**：建立 revision baseline，確保 Phase 7 Review **永遠執行**（不因 Hook A-C 全過而跳過）。
**觸發**：Phase 6 完成後 **MANDATORY**（無跳過條件）。

```
── Step 1: Snapshot Baseline ──
1. DraftSnapshotManager.snapshot_all(reason="pre-review-baseline")
   → 快照所有 section 的當前版本
2. 記錄 quality-scorecard Round 0 分數
3. 記錄到 .audit/evolution-log.jsonl:
   {"event": "baseline", "round": 0, "timestamp": "...",
    "scorecard": {6 維度分數}, "word_count": N,
    "instruction_version": git_short_hash()}

── Step 2: Force Review Entry ──
4. 無論 Hook C 結果如何 → 設定 review_required = true
5. 載入 journal-profile.yaml → reviewer_perspectives + quality_threshold
6. IF journal-profile.yaml 不存在:
   → 從 templates/ 生成預設值 → 存入專案
   → LOG: "Auto-generated journal-profile.yaml with defaults"
```

**Gate**: baseline snapshot 完成 → `pipeline_action(action="validate_phase", phase=65)` 必須 PASS → 進入 Phase 7
