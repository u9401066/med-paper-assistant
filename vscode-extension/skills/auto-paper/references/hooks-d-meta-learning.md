# Copilot Hooks D: meta-learning（Phase 10，閉環核心）

> auto-paper 的 reference 檔（progressive disclosure）；入口與 hard gate 見 [../SKILL.md](../SKILL.md)。
> **Read this when**: running Phase 10 meta-learning, proposing a new hook, or propagating a hook definition across SKILL / AGENTS / copilot-instructions.
> 相關：[lessons-learned.md](lessons-learned.md)、[audit-trail-and-checkpoints.md](audit-trail-and-checkpoints.md)、[phase-8-11-delivery.md](phase-8-11-delivery.md)

---

### Hook D: meta-learning（Phase 10，閉環核心）

Hook D 不只改進 SKILL — 它改進 Hook 自身（CONSTITUTION §23）。

**基礎設施**（`infrastructure/persistence/`）：

| 元件                       | 檔案                            | 用途                                                        |
| -------------------------- | ------------------------------- | ----------------------------------------------------------- |
| `HookEffectivenessTracker` | `hook_effectiveness_tracker.py` | 記錄 hook 事件、計算觸發率/修正率/誤報率、產出推薦          |
| `QualityScorecard`         | `quality_scorecard.py`          | 6 維品質評分 (0-10)、閾值檢查、弱項偵測                     |
| `MetaLearningEngine`       | `meta_learning_engine.py`       | D1-D9 編排器、`ThresholdAdjustment` (±20%)、`LessonLearned` |

**使用方式**：

```python
from med_paper_assistant.infrastructure.persistence.hook_effectiveness_tracker import HookEffectivenessTracker
from med_paper_assistant.infrastructure.persistence.quality_scorecard import QualityScorecard
from med_paper_assistant.infrastructure.persistence.meta_learning_engine import MetaLearningEngine

tracker = HookEffectivenessTracker(audit_dir)
scorecard = QualityScorecard(audit_dir)
engine = MetaLearningEngine(audit_dir, tracker, scorecard)
result = engine.analyze()  # → {adjustments, lessons, suggestions, audit_trail, summary}
```

#### D1: 效能統計

`HookEffectivenessTracker` 記錄每次 hook 評估事件（`trigger`/`pass`/`fix`/`false_positive`），持久化至 `.audit/hook-effectiveness.yaml`。

效能判斷（§23）：

- 觸發率 > 80% → Hook 太嚴格，建議放寬閾值
- 觸發率 < 5%（超過 5 次執行）→ Hook 太鬆/過時，考慮移除
- 誤報率 > 30% → 判斷標準需修正

`QualityScorecard` 追蹤 7 個標準維度的品質分數，持久化至 `.audit/quality-scorecard.yaml`。

#### D2: 品質維度分析

`MetaLearningEngine._d2_analyze_quality()` 對 QualityScorecard 的 7 維品質分數做深度分析：

- 弱項偵測：score < 6.0 的維度 → 產出 `quality_gap` lesson
- 缺項偵測：未評估的維度 → 產出 `process_gap` lesson
- 趨勢判斷：平均分 ≥ 8 → achievement，< 6 → critical review needed
- 維度 → Hook 映射：methodology → B5, text_quality → A3, equator_compliance → E1-E5

D2 的 lessons 輸入 D3（調閾值）和 D4-D5（改 SKILL），形成分析鏈。

#### D3: Hook 自我改進

`MetaLearningEngine._d1_d3_analyze_hooks()` 根據 tracker 推薦產生 `ThresholdAdjustment`：

**自動調整**（`auto_apply=True`，變動幅度 ≤ ±20%）：

- 觸發率過高 → 放寬閾值 +15%
- 觸發率過低 → 收緊閾值 -15%

**需用戶確認**（`auto_apply=False`）：邏輯修正、新增/移除 Hook

**禁止修改**：CONSTITUTION 原則、🔒 規則、save_reference_mcp 優先、Hook D 自身邏輯

##### Hook 傳播程序（用戶確認後自動執行）

當 D3 提出新增 Hook 且用戶確認後，依以下 spec 自動同步所有檔案：

**Hook Spec 格式**（D3 產出）：

```yaml
hook_id: C7 # 類型字母 + 編號
category: C # A/B/C/D
name: 時間一致性 # 簡短中文名
description: 逆向掃描修正因寫作順序造成的過時引用
check_tool: "`draft_action(action="read")` × N + Agent 掃描"
fix_action: "`draft_action(action="patch")` 更新過時描述"
detailed_definition: |
  #### Hook C7: 時間一致性
  C1-C6 完成後，逆向掃描每個 section...
```

**傳播清單**（5 個檔案，按順序更新）：

| #   | 檔案                                                              | 更新內容                                                            | 模式   |
| --- | ----------------------------------------------------------------- | ------------------------------------------------------------------- | ------ |
| 1   | `.claude/skills/auto-paper/references/hooks-*.md`（依 Hook 類別） | Hook 表格加行 + 詳細定義 + Phase 流程                               | 插入行 |
| 2   | `AGENTS.md`                                                       | `### Hook 架構（N checks）` N+1 + 表格描述列                        | 替換   |
| 3   | `.github/copilot-instructions.md`                                 | `## Hook 架構（N checks）` N+1 + 表格列 `Copilot X1-M` → `X1-(M+1)` | 替換   |
| 4   | `vscode-extension/copilot-instructions.md`                        | 同上                                                                | 替換   |
| 5   | `vscode-extension/skills/auto-paper/references/hooks-*.md`        | 同 #1（VSX 鏡像）                                                   | 插入行 |

**自動計算**：

- `new_count` = grep 所有 `Hook 架構（(\d+) checks）` 取得舊值 + 1
- `new_range` = 解析 `Copilot {cat}1-{M}` → `{cat}1-{M+1}`
- 使用 `multi_replace_string_in_file` 一次完成所有替換

**驗證**：傳播完成後 `grep -rn "Hook 架構" AGENTS.md .github/ vscode-extension/` 確認數字一致

#### D4-D5: SKILL + Instruction 改進

`MetaLearningEngine._d4_d5_skill_suggestions()` 偵測：

- 某 Hook 觸發 >2 次且修正率 <50% → 加入 pre-check
- 弱品質維度 → 強化對應 Hook（methodology → B5, text_quality → A3）

#### D6: 記錄審計軌跡

`MetaLearningEngine._d6_build_audit_trail()` 追加寫入 `.audit/meta-learning-audit.yaml`（append-only 陣列），並由 `run_quality_checks(action="meta_learning")` 產生 `.audit/meta-learning-feedback.yaml`，把 pending evolutions 以 agent-readable 摘要回灌到專案。

其他更新：`.audit/hook-effectiveness.md`, `.audit/quality-scorecard.md`, `.memory/progress.md`, `.memory/activeContext.md`, `memory-bank/decisionLog.md`, Lessons Learned（[lessons-learned.md](lessons-learned.md)）

#### D7: Review Retrospective 🆕

分析 Phase 7 Review Loop 產出，演化 Reviewer 指令（CONSTITUTION §23 L2 級）。

**觸發**：Phase 10，D6 審計軌跡產生後，作為 D7-D9 回顧鏈的一部分

**流程**：

```
1. 讀取 review-report-*.md + author-response-*.md
2. 統計分析：
   - 哪些 reviewer 角色的 MAJOR issues 最有價值（ACCEPT 率高）？
   - 哪些 suggestions 被 DECLINE 最多？→ 可能過度嚴格
   - 哪些 issues 跨 round 反覆出現？→ 修正策略不佳
   - 各 reviewer 角色的有效問題數量分布
3. 產出建議：
   - 調整 reviewer_perspectives 的檢查重點描述（±20%）
   - 記錄到 SKILL.md Lessons Learned（[lessons-learned.md](lessons-learned.md)）
   - 更新 .audit/reviewer-effectiveness.json
4. 禁止：修改 CONSTITUTION 原則、修改 Hook D 自身邏輯
```

#### D8: EQUATOR Compliance Retrospective 🆕

分析 Hook E 在 Phase 7 的執行效果，持續改善 checklist 準確性。

**觸發**：Phase 10，D7 之後

**流程**：

```
1. 讀取 equator-compliance-*.md
2. 統計分析：
   - 哪些 checklist items 被標為 N/A 最多？→ 可能不適用該 paper type
   - 哪些 items 反覆 PARTIAL？→ 可能定義不清楚
   - compliance rate 趨勢（Round 0 → N）
   - ESSENTIAL items 的修補成功率
3. 產出建議：
   - 調整 E1 偵測邏輯的 paper_type 映射
   - 記錄到 SKILL.md Lessons Learned（[lessons-learned.md](lessons-learned.md)）
   - 建議新的 ESSENTIAL 分類（若某非 ESSENTIAL 項反覆 miss）
4. 更新 evolution-log.jsonl with meta_learning event
```

#### D9: Tool Telemetry Retrospective 🆕

分析 `.audit/tool-telemetry.yaml`、`.audit/pending-evolutions.yaml` 與 MCP tool description 使用情況，讓下一輪工具選擇更精準。

**觸發**：Phase 10，D7-D8 之後，作為 `MetaLearningEngine.analyze()` 的最後一步。

**流程**：

```
1. 讀取 tool invocation telemetry + pending evolutions
2. 統計分析：
   - 哪些工具被誤用、重試或產生 health alert？
   - 哪些 facade action 需要更清楚的 description / aliases？
   - 哪些 pending evolution 應保留到下一輪，而不是本輪自動修改？
3. 產出建議：
   - tool description / guidance 的修正候選
   - 記錄到 meta-learning-audit.yaml 的 analysis_steps.D9
   - 保留需人類確認的 L3 instruction 建議
4. 禁止：自動修改 CONSTITUTION、🔒 規則、save_reference_mcp 優先順序
```
