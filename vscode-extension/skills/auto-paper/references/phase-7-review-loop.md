# Phase 7: AUTONOMOUS REVIEW（結構化 Review Loop — MANDATORY）

> auto-paper 的 reference 檔（progressive disclosure）；入口與 hard gate 見 [../SKILL.md](../SKILL.md)。
> **Read this when**: running any Phase 7 review round, writing the Author Response, fixing Anti-AI findings, or deciding to roll back to Phase 5.
> 相關：[phase-7-equator-hook-e.md](phase-7-equator-hook-e.md)、[audit-trail-and-checkpoints.md](audit-trail-and-checkpoints.md)、[hooks-d-meta-learning.md](hooks-d-meta-learning.md)

---

### Phase 7: AUTONOMOUS REVIEW（結構化 Review Loop — MANDATORY）🆕

**目的**：模擬同行審查，產出結構化 Review Report + Author Response，確保每個 issue 都被回應。
**觸發**：**ALWAYS**（Phase 6.5 強制進入，不可跳過）。即使 Hook A-C 全過、quality 已達標，仍必須至少執行 2 rounds（code-enforced `min_rounds=2`）。
**上限**：`pipeline.review_max_rounds`（預設 3）。
**最低輪數**：`min_rounds=2`（**Code-Enforced**：`AutonomousAuditLoop._determine_verdict()` 在 round < min_rounds 時強制返回 CONTINUE，不允許提前結束）。
**Hard Gate**：每輪 MUST call `pipeline_action(action="start_review", min_rounds=2)` 開始 + `pipeline_action(action="submit_review", scores=...)` 結束。Phase 7 固定安全下限為 `min_rounds >= 2`、`quality_threshold >= 7.0`、`max_rounds <= 10`，序列化狀態或專案設定都不能降低。Loop 結束後 `pipeline_action(action="validate_phase", phase=7)` 必須 PASS：除了驗證 rounds、artifact、hash chain、R1-R6 與重算分數，只有 `quality_met` 可在自主模式解鎖 Phase 8。`max_rounds`／`stagnated`／`user_needed` 是升級條件；若人類明確接受低於門檻的結果，可信 host/UI 必須簽發 `mdpaper.review_completion_override.v3` Ed25519 receipt，綁定專案、當前稿件與 loop state。MCP/Agent 只能查詢或撤銷，不能鑄造核准。

#### Multi-Reviewer 設計（模擬 2-3 位獨立審稿人）🆕

人類同行審查通常由 2-3 位獨立審稿人進行，每位審稿人有不同的知識背景和思考模式。為模擬此過程：

**每輪 Review 啟動 2-3 個 subagent**，每個 subagent 使用**不同的 top-tier 模型**（避免思考模式雷同）：

| Reviewer | 模型             | 角色                              |
| -------- | ---------------- | --------------------------------- |
| R1       | Claude Opus 4.6  | Methodology Expert + Statistician |
| R2       | OpenAI Codex 5.3 | Domain Specialist + Editor        |
| R3       | Gemini Pro 3.1   | Independent Critical Reviewer     |

**每位 Reviewer 必須**：

1. **搜尋文獻驗證**：使用 `unified_search` / `find_related_articles` 搜尋相關文獻，比對稿件引用是否充分、結論是否與現有證據一致
2. **獨立閱讀全稿**：不參考其他 Reviewer 的意見
3. **提出 5-10 個結構化問題**：每個問題必須包含 section、paragraph、category、issue、suggestion
4. **文獻比對**：至少引用 2-3 篇搜尋到的文獻來支持或挑戰稿件觀點
5. **給出獨立評分**：6 個品質維度各自評分

**合併流程**：

- 所有 Reviewer 獨立完成後，合併為統一的 `review-report-{round}.md`
- 重複 issue 去重，保留最嚴格的 severity
- Author Response 必須回應所有 Reviewer 的所有 issue

```
載入 journal-profile.yaml → 取得 reviewer_perspectives + quality_threshold

── Review Loop（最少 min_rounds 輪，最多 max_rounds 輪）──

FOR round = 1 TO N:

  ── Stage A: Multi-Reviewer Review（獨立 subagent） ──
  LAUNCH 2-3 subagents in parallel (each using different model):

  FOR each reviewer subagent:
    1. 搜尋文獻：unified_search() 搜尋與稿件主題相關的最新文獻（至少 5 篇）
    2. 比對文獻：find_related_articles() / find_citing_articles() 驗證稿件引用
    3. 獨立審查全稿，提出 5-10 個結構化問題
    4. 以搜尋到的文獻為依據，標記稿件中的不足或錯誤
    5. 獨立評分（6 維度）

    Reviewer 角色覆蓋：
    "methodology_expert":
      - 研究設計是否嚴謹？統計方法是否恰當？
      - 方法是否可再現？偏差控制是否充分？
      - 搜尋同類方法學文獻 → 比對是否有遺漏的 best practice

    "domain_specialist":
      - 文獻引用是否全面且最新？
      - 對領域 gap 的理解是否準確？臨床意義是否明確？
      - 搜尋最新系統性回顧 → 驗證稿件是否與當前共識一致

    "statistician":
      - 統計假設是否合理？結果呈現是否清晰？
      - 圖表是否有效傳達數據？
      - 搜尋統計方法指引 → 驗證分析方法的恰當性

    "editor":
      - 寫作品質（清晰度、邏輯流、語法）
      - 是否符合期刊風格？圖表品質與必要性

  MERGE all reviewer outputs → 統一 review-report-{round}.md

  產出 .audit/review-report-{round}.md：
  ┌─────────────────────────────────────────────────┐
  │ ---                                             │
  │ round: 1                                        │
  │ date: "YYYY-MM-DD"                              │
  │ reviewers:                                      │
  │   - role: "Methodology Expert"                  │
  │     issues_major: 2                             │
  │     issues_minor: 1                             │
  │   - role: "Domain Specialist"                   │
  │     issues_major: 1                             │
  │     issues_minor: 3                             │
  │ total:                                          │
  │   major: 3                                      │
  │   minor: 5                                      │
  │   optional: 2                                   │
  │ ---                                             │
  │                                                 │
  │ # Review Report — Round {round}                 │
  │                                                 │
  │ ## Reviewer 1: Methodology Expert               │
  │ ### MAJOR                                       │
  │ - id: R1-M1                                     │
  │   section: Methods                              │
  │   paragraph: methods-p3                         │
  │   category: methodology                         │
  │   issue: 缺少 sample size justification         │
  │   suggestion: 加入 power analysis               │
  │ ### MINOR                                       │
  │ - id: R1-m1                                     │
  │   section: Results                              │
  │   ...                                           │
  └─────────────────────────────────────────────────┘

  ── Stage B: Author Response（全 issue 須回應） ──
  產出 .audit/author-response-{round}.md：
  ┌─────────────────────────────────────────────────┐
  │ ---                                             │
  │ round: 1                                        │
  │ response_to: "review-report-1.md"               │
  │ actions:                                        │
  │   accepted: 6                                   │
  │   accepted_modified: 2                          │
  │   declined: 2                                   │
  │ ---                                             │
  │                                                 │
  │ # Author Response — Round {round}               │
  │                                                 │
  │ ### R1-M1: Sample size justification            │
  │ - **Action**: ACCEPT                            │
  │ - **Response**: Added power analysis...         │
  │ - **Change**: methods-p3 (+45 words)            │
  │ - **Verified**: Hook A re-run ✅               │
  │                                                 │
  │ ## Completeness Check                           │
  │ | Issue ID | Addressed | Action      |          │
  │ | R1-M1    | ✅       | ACCEPT      |          │
  │ | R2-o1    | ✅       | DECLINE     |          │
  │ ALL issues addressed: ✅                        │
  └─────────────────────────────────────────────────┘

  ── Completeness Check（每輪必過）──
  FOR issue IN review_report.all_issues:
    IF issue.id NOT IN author_response → FAIL（禁止忽略 issue）
  → 未回應的 issue 必須標記 DECLINE + 理由

  ── Stage C: 執行修正（MANDATORY — 稿件必須被修改） ──
  ⚠️ HARD ENFORCEMENT: `pipeline_action(action="submit_review", ...)` 會比對稿件 hash。
  若稿件未修改 → 提交會被 REJECT。

  FOR each ACCEPTED issue:
    1. 定位 paragraph ID（from manuscript-plan.yaml）
    2. draft_action(action="patch") 修正
    3. re-run Hook A on patched section
    4. 記錄到 author-response

  FOR each MINOR ACCEPTED issue:
    1. batch draft_action(action="patch") 修正
    2. 快速 Hook A 驗證

  OPTIONAL + DECLINED issues → LOG only（不自動修正）

  ── Stage C2: 敘事強化（MANDATORY — 即使無結構問題） ──
  人類 reviewer 即使不要求結構修改，也會提升敘事品質。
  AI reviewer 必須做到至少同等標準：
    1. 選擇至少 3 段落進行「敘事強化」（tighten prose, improve transitions,
       strengthen claims, eliminate redundancy, improve word economy）
    2. 每段 draft_action(action="patch") 修正，附帶改善理由
    3. 記錄到 author-response 的 "Narrative Enhancements" section

  IF 沒有結構性 issue（全部 DECLINE 或 OPTIONAL only）：
    → Stage C2 仍然 MANDATORY（最低改 3 段落）
    → 目標：人類讀者應能看到「review 前」vs「review 後」有明顯差異

  ── Stage C3: Anti-AI 自然度審查（MANDATORY — Code-Enforced Gate） ──
  AI 生成文字常被偵測器（Gemini 3.1 等）秒辨。Stage C3 強制 Agent 自我檢測並修正。
  更關鍵的是：有經驗的人類審稿人會注意到段落間的「語體斷裂」——前段 ESL 風格突然切換到
  流暢的 corporate-academic prose，即使通過自動偵測也會引起懷疑。

  Step 1: Code-Enforced Hook Gate（三層掃描）
    → run_quality_checks(action="writing_hooks", hooks="A3,A3B,A3C")
    → A3: 禁止詞掃描（~150 個 AI 特徵用語）
    → A3b: 結構信號偵測（句長均勻度、轉折詞密度、句首多樣性、三連列舉、段落均勻度）
    → A3c: 語體一致性偵測（段落級可讀性指標 z-score 異常偵測 + 詞彙精緻度落差）
    → 任何 CRITICAL → 必須 draft_action(action="patch") 修正後重跑，直到 PASS

  Step 2: Agent 自我審閱（Anti-AI Naturalness Check）
    Agent 以下列視角重新閱讀全文：
    a) 是否有「四平八穩」的語調？（每段都同一節奏 → 改）
    b) 是否過度使用被動語態或名詞化？（nominalization → 改為動詞）
    c) 是否有 AI 特有的「禮貌性冗餘」？（"It is important to note that" → 刪）
    d) 段落是否缺乏個人學術觀點？（全是 hedging → 加 assertive claim）
    e) 是否有「假平衡」？（on the one hand... on the other hand → 取立場）
    f) **語體斷裂**：A3c 標記的 outlier 段落是否「太流暢」而脫離作者自然語體？
       → 降級過度精煉的句子、加回作者的「笨拙但真實」語法特徵
    → 每項至少修正 2 處 → draft_action(action="patch")

  Step 3: 雙 Subagent 交叉審計（RECOMMENDED — 至少最終輪必做）
    使用兩個不同模型的 subagent 分別審計，交叉比對結果：

    Subagent 1 — Surface Scanner（concept-challenger 或主 Agent）：
      → 審計目標：黑名單詞、結構信號、自動偵測器可偵測的 pattern
      → 問題：「能否通過 GPTZero？哪些具體詞/句需要替換？」

    Subagent 2 — Voice Analyst（domain-reviewer）：
      → 審計目標：語體一致性、ESL baseline vs polished prose 對比
      → 問題：「人類審稿人會不會因為語體突變而起疑？逐段評分 1-5」
      → 重點：段落級 AI 機率評分，標出 TOP 5 最可疑句子

    交叉比對規則：
      → 兩者都標 🔴 → 必須重寫該段落
      → 僅一方標 ⚠️ → Agent 判斷是否需要調整
      → 兩者都 ✅ → 安全

  Step 4: 修正後驗證
    → 重跑 run_quality_checks(action="writing_hooks", hooks="A3,A3B,A3C")
    → 必須全部 PASS 或僅 WARNING（無 CRITICAL）才能進入 Stage D
    → IF 仍有 CRITICAL → 回到 Step 2 再修，最多 3 輪

  ── Stage D: 品質重評 ──
  更新 quality-scorecard.md：
    | 維度 | Round N-1 分數 | Round N 分數 | 變化 |

  計算總分 → 比對 quality_threshold

  IF 總分 ≥ quality_threshold:
    → ✅ PASS: 結束 review loop
    → LOG: "Review completed at round {round}, score={score}"

  IF 總分 < quality_threshold AND round < N:
    → 繼續下一輪（重新審稿）
    → 分析哪些維度分數最低 → 下一輪重點關注

  IF round = N AND 總分 < quality_threshold:
    → ⚠️ PARTIAL: 呈現剩餘問題 + 分數趨勢
    → 詢問用戶：
      a) 接受當前品質：由可信 host/UI 收集具名 reviewer、rationale 與 accepted risks，簽發 state-bound `mdpaper.review_completion_override.v3` receipt；再呼叫 `pipeline_action(action="approve_review_completion", decision="status")` 驗證。不得由 MCP/Agent 簽發、改寫分數或宣稱 quality_met
      b) 繼續 N 輪（用戶延長 loop）
      c) 手動修改後重新 review
      d) 🔁 回退到 Phase 5 重寫特定 section → call `pipeline_action(action="rewrite_section", ...)`

  ── Stage D2: 回退決策（Agent 自主判斷 + 自主執行） ──
  IF Agent 判斷某些 section 的問題無法透過 draft_action(action="patch") 修正，需要整個 section 重寫：
    1. 識別需要重寫的 section（通常是 persistent critical issues 集中的 section）
    2. **Autopilot 模式**（預設）：
      → Agent 直接呼叫 `pipeline_action(action="rewrite_section", sections="Methods,Results", reason="...")`
       → 決策和理由記入 `.audit/pipeline-run-{ts}.md`
       → Pipeline 回退到 Phase 5 → 僅重寫指定 sections
    3. **手動模式**（`autopilot: false` 或 `autopilot_pause_at` 含 `"phase7_rewrite"`）：
       → 🗣️ 詢問用戶確認：「建議重寫 [section]，是否同意？」
      → 用戶確認後執行 `pipeline_action(action="rewrite_section", ...)`
    4. 重寫後走 Phase 5 → 6 → 7 完整流程
    5. ⚠️ regression_count > 2 → **安全閥：強制停下詢問用戶**（防止無限循環）

  ── Stage E: Evolution Tracing（每輪結束後） ──
  追加到 .audit/evolution-log.jsonl：
  {"event": "review_round", "round": N,
   "timestamp": "...",
   "scorecard": {6 維度分數},
   "scorecard_delta": {與 Round N-1 的差異},
   "review_issues": {"major": M, "minor": m, "accepted": A, "declined": D},
   "draft_snapshots": ["snapshot_path_1", ...],
   "patches_applied": [{"section": "...", "issue_id": "R1-M1", "words_changed": N}],
   "instruction_version": git_short_hash()}
```

#### Review 品質維度（quality-scorecard）

| 維度            | 評分標準 (0-10)                         | 權重 |
| --------------- | --------------------------------------- | ---- |
| 引用品質        | 引用充分、最新、高影響力、格式正確      | 10%  |
| 方法學再現性    | 研究設計、統計、可再現                  | 18%  |
| 文字品質        | 清晰度、邏輯流、無 AI 痕跡、語法        | 16%  |
| 概念一致性      | NOVELTY 體現、SELLING POINTS、全稿一致  | 16%  |
| 格式合規        | 字數、圖表、引用數、期刊要求            | 7%   |
| 圖表品質        | 圖表必要性、清晰度、caption、數據呈現   | 8%   |
| EQUATOR 合規    | checklist compliance + ESSENTIAL 項完整 | 13%  |
| 再現性/資料可用 | 資料分享聲明、程式碼公開、protocol 註冊 | 12%  |

總分 = Σ(維度分數 × 權重)

#### Review vs Hook 的分工

| 面向     | Hook A-C（Phase 5-6）                    | Autonomous Review（Phase 7）            |
| -------- | ---------------------------------------- | --------------------------------------- |
| 目的     | 技術合規                                 | 學術品質 + 報告指引合規                 |
| 觸發時機 | 寫作過程中 / 全稿完成後                  | Phase 6.5 強制進入（MANDATORY）         |
| 關注點   | 格式、引用、字數、一致性                 | 內容品質、邏輯、學術說服力 + EQUATOR    |
| 修正方式 | draft_action(action="patch")（局部修正） | 可能 rewrite 段落或重組論證             |
| 角色     | 自動化 linter                            | 模擬 Reviewer + EQUATOR compliance      |
| 停止條件 | 0 CRITICAL                               | quality_threshold 達標 + ESSENTIAL 完整 |
| 產出     | audit log                                | review-report + equator-compliance      |
| 粒度     | pass/fail                                | MAJOR/MINOR/OPTIONAL + checklist 逐條   |
