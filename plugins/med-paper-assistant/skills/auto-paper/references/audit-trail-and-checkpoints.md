# Audit Trail 生成 + Checkpoint 恢復機制

> auto-paper 的 reference 檔（progressive disclosure）；入口與 hard gate 見 [../SKILL.md](../SKILL.md)。
> **Read this when**: writing or verifying `.audit/` artifacts at the end of a phase or review round, or resuming a pipeline from `checkpoint.json`.
> 相關：[phase-7-review-loop.md](phase-7-review-loop.md)、[phase-7-equator-hook-e.md](phase-7-equator-hook-e.md)

---

## Audit Trail 生成（每個 Phase 完成時自動執行）

Agent 必須在 `projects/{slug}/.audit/` 維護以下檔案：

### 增量更新（每個 Phase 結束時）

```
Phase 完成 → 更新以下檔案：

1. pipeline-run-{YYYYMMDD-HHmm}.md（增量 append）
   格式：
   ## Phase {N}: {名稱}
   - 開始時間 / 結束時間
   - 輸入：{files read}
   - 輸出：{files written}
   - Hook 結果：
     | Hook | 觸發 | 通過 | 修正次數 | 最終結果 |
   - 決策紀錄：{任何自動決策 + 理由}
   - Issues flagged for later: {list}

2. checkpoint.json（覆寫更新）
   {
     "last_completed_phase": N,
     "current_section": "Methods",
     "phase_outputs": { "P1": "project_created", "P2": "15_refs_saved", ... },
     "flagged_issues": [...],
     "audit_stats": { "hook_a_triggers": 5, "hook_a_passes": 3, ... },
     "timestamp": "ISO-8601"
   }
```

### Phase 6 完成後生成

```
3. quality-scorecard.md
   | 維度 | 分數 (0-10) | 說明 |
   | 引用品質 | | |
   | 方法學再現性 | | |
   | 文字品質 | | |
   | 概念一致性 | | |
   | 格式合規 | | |
   | 圖表品質 | | |
   | 總分 | | |

4. hook-effectiveness.md
   | Hook | 觸發次數 | 通過次數 | 修正次數 | 誤報次數 | 有效率 |
   → 供 Hook D 分析用
```

### Phase 7 每輪生成

```
5. review-round-{N}.md
   ## Round {N} Summary
   | 角色 | MAJOR issues | MINOR issues | OPTIONAL |
   | Issue | 角色 | 嚴重度 | 修正策略 | 修正後狀態 |

   ## Quality Score Trend
   | 維度 | Round 0 | Round 1 | Round 2 | ... | 變化趨勢 |
   | 總分 | 6.2 | 7.1 | 7.8 | ... | ↑ |

6. equator-compliance-{N}.md  🆕
   ## EQUATOR Compliance Report — Round {N}
   ## Detected Guidelines: {auto-detected or specified}
   | # | Item | Section | Status | Notes |
   → 見 phase-7-equator-hook-e.md 的 Hook E4 格式定義
```

### Evolution Tracing（Phase 6.5 → 7 → 10）🆕

```
7. evolution-log.jsonl（append-only，每事件一行 JSON）

   ## 事件類型：
   - baseline: Phase 6.5 建立的基線快照
   - review_round: Phase 7 每輪 review 結果
   - equator_check: Hook E 每輪 compliance 結果
   - hook_correction: Hook A-C 修正事件
   - meta_learning: Phase 10 自我改進事件

   ## Schema:
   {"event": "baseline", "round": 0, "timestamp": "ISO-8601",
    "scorecard": {"citation": 7, "methodology": 8, "text": 6, ...},
    "word_count": 3200,
    "instruction_version": "abc1234"}

   {"event": "review_round", "round": 1, "timestamp": "...",
    "scorecard": {"citation": 7.5, "methodology": 8, "text": 7, ...},
    "scorecard_delta": {"text": +1, "total": +0.8},
    "review_issues": {"major": 3, "minor": 5, "accepted": 7, "declined": 1},
    "patches_applied": [{"section": "Methods", "issue_id": "R1-M1", "words_changed": 45}],
    "instruction_version": "abc1234"}

   {"event": "equator_check", "round": 1, "timestamp": "...",
    "guideline": "TRIPOD+AI", "compliance_rate": 0.85,
    "essential_complete": false, "missing_essential": ["Item 10d", "Item 4b"],
    "action_items": 3}

   {"event": "meta_learning", "phase": 10, "timestamp": "...",
    "skill_updates": ["Lessons Learned +1"],
    "hook_adjustments": [{"hook": "B5", "param": "threshold", "old": 5, "new": 6}],
    "total_rounds": 2, "final_score": 7.8}

   ## 用途：
   - Phase 10 D1-D9 分析 → 產出 evolution summary
   - 跨 run 比較（如有多次執行）
   - 論文自身的 Fig 1 / Table 2（框架效果量化證據）
```

### Phase 2 完成後生成

```
5. search-strategy.md
   - 搜尋策略 + MeSH terms
   - 每組搜尋的結果數量
   - 篩選標準 + 排除原因

6. reference-selection.md
   - 最終選擇的文獻列表 + 選擇理由
   - 排除的重要文獻 + 排除原因
```

### Phase 3 完成後生成

```
7. concept-validation.md
   - 驗證分數 (每輪)
   - 修正歷史
   - CGU 使用紀錄（如有）
```

---

## Checkpoint 恢復機制

**實作**：`CheckpointManager`（`infrastructure/persistence/checkpoint_manager/`）

```
Pipeline 啟動時：
1. 檢查 projects/{slug}/.audit/checkpoint.json
2. IF exists:
   → ckpt = CheckpointManager(audit_dir)
   → summary = ckpt.get_recovery_summary()  # 顯示上次進度
   → 詢問：
     a) 從 Phase {N+1} 繼續
     b) 從當前 section 繼續
     c) 重新開始（保留文獻和 concept）
     d) 完全重來 → ckpt.clear()
3. IF 選擇繼續：
   → state = ckpt.load()
   → 載入 phase_outputs
   → 載入 flagged_issues（帶入 Phase 6）
   → 跳到對應 Phase/Section

Phase 轉換時：
  ckpt.save_phase_start(phase, name)
  ... 執行 ...
  ckpt.save_phase_completion(phase, name, outputs, flagged_issues)
```
