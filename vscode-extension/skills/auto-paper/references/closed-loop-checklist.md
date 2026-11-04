# 閉環檢查清單

> auto-paper 的 reference 檔（progressive disclosure）；入口與 hard gate 見 [../SKILL.md](../SKILL.md)。
> **Read this when**: about to claim the pipeline is complete (always pair with `pipeline_action(action="heartbeat")`).
> 相關：[phase-8-11-delivery.md](phase-8-11-delivery.md)、[lessons-learned.md](lessons-learned.md)

---

## 閉環檢查清單

- [ ] Phase 0: source-materials.yaml 已產生；所有 pending_asset_aware 檔案已交給 asset-aware 或有明確 fallback reason
- [ ] Phase 0: journal-profile.yaml 已產生 + 用戶確認
- [ ] Phase 2.1: fulltext-ingestion-status.md 已建立，每篇文獻標記全文狀態 + analysis_completed
- [ ] 所有 section 通過 Hook A（cascading）
- [ ] 所有 section 通過 Hook B（含回溯修正）
- [ ] 所有 Phase 5 FLAG 已在 Phase 6 處理
- [ ] 全稿通過 Hook C（cascading fix）
- [ ] Phase 6.5: Evolution Gate baseline snapshot 已建立
- [ ] Phase 7: Autonomous Review 達到 quality_threshold（MANDATORY；安全下限至少 2 rounds、threshold ≥ 7.0，不可由 pipeline config 調低）
- [ ] Hook E: EQUATOR compliance rate ≥ 80% + 所有 ESSENTIAL items reported
- [ ] quality-scorecard.md 已生成（所有維度 ≥ 6 分，含 EQUATOR 維度）
- [ ] review-round-\*.md 已生成（每輪完整記錄）
- [ ] equator-compliance-\*.md 已生成（每輪 checklist 報告）
- [ ] evolution-log.jsonl 包含 baseline + 所有 round 事件
- [ ] hook-effectiveness.md 已生成
- [ ] .audit/pipeline-run-{YYYYMMDD-HHmm}.md 涵蓋所有 Phase，且含 `## D7 retrospective:` + `## D8 retrospective:`
- [ ] meta-learning-feedback.yaml 已生成，pending evolutions 已回灌到 workspace state
- [ ] checkpoint.json 標記完成
- [ ] Asset Plan 所有項目已生成或有 fallback 記錄
- [ ] 引用數量 ≤ journal-profile.references.max_references
- [ ] 圖表數量 ≤ journal-profile.assets limits
- [ ] 必要文件清單（required_documents）完成
- [ ] .memory/ 已更新
- [ ] Hook D meta-learning 已執行（含 D7 Review + D8 EQUATOR + D9 Tool Telemetry Retrospective）
- [ ] SKILL.md Lessons Learned 已更新（[lessons-learned.md](lessons-learned.md)）
- [ ] Word 已匯出
