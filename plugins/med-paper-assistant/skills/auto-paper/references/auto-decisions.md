# 自動決策邏輯

> auto-paper 的 reference 檔（progressive disclosure）；入口與 hard gate 見 [../SKILL.md](../SKILL.md)。
> **Read this when**: deciding whether the agent may continue autonomously or must stop and ask the user.
> 相關：[phase-5-asset-generation.md](phase-5-asset-generation.md)、[hooks-a-b-post-write-section.md](hooks-a-b-post-write-section.md)

---

## 自動決策邏輯

| 情境               | 自動行為                                                | 停下條件            |
| ------------------ | ------------------------------------------------------- | ------------------- |
| Phase 0 無期刊資訊 | 用 paper_type 預設值                                    | 用戶提供後覆蓋      |
| Phase 0 有 PDF/URL | 解析 + 自動填 YAML                                      | ⚠️ 欄位需確認       |
| 搜尋不足           | 擴展搜尋                                                | 3 輪後仍 <10 篇     |
| Concept 65-74      | 自動修正 1 次                                           | 仍 <75              |
| Hook A 字數超標    | Round 1-N 逐級修正                                      | N rounds 後 FLAG    |
| Hook A 引用不足    | suggest + patch, N rds                                  | 無可用引用          |
| Hook B 🔒 缺失     | patch 加入                                              | 需改研究方向        |
| Hook B5 <5 分      | patch 補細節, 2 rounds                                  | 2 rounds 仍 <5      |
| Hook C CRITICAL    | cascading fix, N rds                                    | N rounds 後問用戶   |
| Hook C WARNING     | patch 1 round                                           | LOG + continue      |
| Hook C7 圖表超限   | 移至 supplementary                                      | 用戶決定刪哪個      |
| Hook C7d phantom   | 插入缺漏圖表或移除引用                                  | 用戶決定            |
| C11 引用分布不均   | 補引用到缺引用 section                                  | LOG + continue      |
| C12 引用缺決策紀錄 | 生成 citation_decisions.json                            | LOG + continue      |
| C13 圖表品質問題   | 修正排序/補 caption                                     | LOG + continue      |
| Hook B7 Brief 遺漏 | draft_action(action="patch") 補遺漏                     | 1 round 後 LOG      |
| Phase 6 FLAG       | 回溯 Hook B → A                                         | 2 cascades 後問用戶 |
| Review MAJOR issue | patch/rewrite                                           | quality ≥ threshold |
| Review 分數停滯    | 改變策略或問用戶                                        | 連續 2 輪無改善     |
| Asset 缺資料       | 提示用戶提供                                            | 跳過該 asset        |
| Asset 工具不可用   | Fallback（見 phase-5-asset-generation.md Sub-Pipeline） | LOG + 替代方案      |
| 引用超過上限       | 標記低引用 refs                                         | 用戶決定刪哪些      |
| Hook D 閾值微調    | ±20%                                                    | 超出範圍            |
| Hook D 新增/移除   | 提出建議                                                | 永遠需確認          |

**必須停下**：Concept < 60（兩次仍低）、Phase 4 大綱 approve、研究方向改變、Phase 6 N 輪 cascading 仍 CRITICAL、Review 連續 2 輪無分數改善、修改 AGENTS.md 核心原則。

**自動繼續**：Hook A/B WARNING → LOG → 下一步。Hook C WARNING → LOG → Phase 7。Review MINOR → batch fix → 下一輪。Asset fallback 成功 → 繼續。
