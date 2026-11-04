# Copilot Hooks A-B: post-write + post-section

> auto-paper 的 reference 檔（progressive disclosure）；入口與 hard gate 見 [../SKILL.md](../SKILL.md)。
> **Read this when**: tuning or debugging per-write / per-section hook checks (word count, citations, Anti-AI, 🔒 protected content, tense, effect size …).
> 相關：[hooks-c-post-manuscript.md](hooks-c-post-manuscript.md)、[phase-5-section-writing.md](phase-5-section-writing.md)

---

## Copilot Hooks 定義（寫作時觸發）

### Hook A: post-write（每次寫完立即，最多 N rounds，N = `pipeline.hook_a_max_rounds`）

| #   | 檢查項                | MCP Tool                                                  | 失敗行為                                             | 閾值來源                              |
| --- | --------------------- | --------------------------------------------------------- | ---------------------------------------------------- | ------------------------------------- |
| A1  | 字數在 target ±20%    | `draft_action(action="count_words")`                      | `draft_action(action="patch")` 精簡/擴充             | `paper.sections[].word_limit`         |
| A2  | 引用密度達標          | `draft_action(action="available_citations")`              | `suggest_citations` + `draft_action(action="patch")` | `pipeline.writing.citation_density.*` |
| A3  | 無 Anti-AI 模式       | `run_quality_checks(action="writing_hooks", hooks="A3")`  | `draft_action(action="patch")` 改寫                  | `pipeline.writing.anti_ai_strictness` |
| A3b | AI 結構信號偵測 🆕    | `run_quality_checks(action="writing_hooks", hooks="A3B")` | `draft_action(action="patch")` 改寫                  | Code-Enforced（5 項結構分析）         |
| A3c | 語音一致性偵測 🆕     | `run_quality_checks(action="writing_hooks", hooks="A3C")` | `draft_action(action="patch")` 改寫                  | Code-Enforced（z-score 離群值）       |
| A4  | Wikilink 格式正確     | `validate_wikilinks`                                      | 自動修復                                             | —                                     |
| A5  | 語言一致性（BrE/AmE） | `run_quality_checks(action="writing_hooks", hooks="A5")`  | `draft_action(action="patch")` 統一拼法              | `pipeline.writing.prefer_language`    |
| A6  | 段落重複偵測          | `run_quality_checks(action="writing_hooks", hooks="A6")`  | `draft_action(action="patch")` 改寫重複段            | `pipeline.writing.overlap_threshold`  |
| A7  | 文獻數量充足性 🆕     | `run_quality_checks(action="writing_hooks", hooks="A7")`  | BLOCK 寫作，提示擴大搜尋                             | `DEFAULT_MINIMUM_REFERENCES` per type |

#### Hook A Cascading Protocol

```
Round 1: 執行 A1-A4 → 收集所有 issues
  → IF issues:
    → batch draft_action(action="patch")（一次修正多個問題）
    → 記錄：哪些問題、修正策略

Round 2: re-run A1-A4
  → IF same issues persist:
    → 改變策略（例：A1 字數超標 → Round 1 精簡句子 → Round 2 刪除次要段落）
    → draft_action(action="patch")
    → 記錄：策略變更原因

Round 3: re-run A1-A4
  → IF still issues:
    → LOG to audit trail（不阻擋）
    → FLAG issue type + section → 帶入 Phase 6 Cascading Audit
    → 繼續下一步（Hook B）

每 round 的修正策略升級：
  A1 字數: trim sentences → remove paragraphs → restructure section
  A2 引用: suggest_citations → search more refs → flag for user
  A3 Anti-AI: rephrase → rewrite paragraph → flag specific phrases
  A3b AI結構信號: 句長CV/轉折詞密度/句首多樣性/三連列舉/段落CV → draft_action(action="patch")
  A3c 語音一致性: 段落風格離群值 → draft_action(action="patch") 改寫風格斷裂段落
  A4 Wikilink: auto-fix → manual check → flag broken refs
```

A2 引用密度標準：Introduction ≥1/100w, Methods ≥0, Results ≥0, Discussion ≥1/150w

A3 Anti-AI 禁止詞（~75 個）：涵蓋 Classic AI filler、Grandiose/buzzword、Metaphorical cliché、Vague academic padding、Formulaic conclusion/transition、AI-specific phrasing 六大類。常見如 `In recent years`, `plays a crucial role`, `has garnered significant attention`, `a comprehensive understanding`, `This groundbreaking` → 替換為具體內容。

A3b AI 結構信號偵測（Code-Enforced）：

- 句長均勻度: CV < 0.25 = WARNING（AI 傾向產出等長句子）
- 轉折詞密度: 句首轉折詞 >20% WARNING, >35% CRITICAL
- 句首多樣性: unique ratio < 0.50 = WARNING
- 三連列舉: `X, Y, and Z` 出現 >3 次 = WARNING
- 段落長度均勻度: CV < 0.20 = WARNING

A3c 語音一致性偵測（Code-Enforced）：

- 段落級特徵：avg_sent_len、avg_word_len、type_token_ratio、punct_complexity
- 文件基線：計算全文各指標的 mean + std
- 離群偵測：任一指標 z-score > 1.8 → WARNING（風格斷裂）
- 詞彙精緻度落差：max − min avg_word_len > 1.2 → WARNING（ESL vs 精修段落）
- 典型場景：ESL 文法段落突然轉為精修企業學術文風 → 人類審稿者可察覺

---

### Hook B: post-section（section 完成後，含回溯修正）

| #   | 檢查項                          | MCP Tool                                                          | 失敗行為                              |
| --- | ------------------------------- | ----------------------------------------------------------------- | ------------------------------------- |
| B1  | 與 concept.md 一致              | `draft_action(action="read", filename="concept.md")` + Agent 比對 | 重寫不一致段落                        |
| B2  | 🔒 NOVELTY 在 Intro 體現        | `draft_action(action="read")` 檢查                                | `draft_action(action="patch")` 加入   |
| B3  | 🔒 SELLING POINTS 在 Discussion | 逐條比對                                                          | `draft_action(action="patch")` 補充   |
| B4  | 與已寫 sections 不矛盾          | `draft_action(action="read")` 交叉比對                            | 修正矛盾處                            |
| B5  | 方法學可再現性                  | Agent 依 paper_type 評估                                          | `draft_action(action="patch")` 補細節 |
| B6  | 寫作順序驗證                    | `check_writing_order`                                             | ⚠️ Advisory（不阻擋）                 |
| B7  | Section Brief 合規 🆕           | Agent 比對 `manuscript-plan.yaml`                                 | `draft_action(action="patch")` 補遺漏 |

#### Hook B Cascading Protocol

```
執行 B1-B7 → 分類 issues:
  CRITICAL: B1 concept 不一致, B2 🔒 NOVELTY 缺失, B5 方法學 <5 分
  WARNING:  B3 selling points 不完整, B4 sections 矛盾, B7a/b/d/e Brief 遺漏
  ADVISORY: B6 寫作順序, B7c 段落順序偏離

IF CRITICAL issues:
  → 針對性 draft_action(action="patch") 修正
  → re-run Hook A on patched areas（1 round，確認 patch 沒破壞品質）
  → re-run 失敗的 Hook B checks
  → IF still CRITICAL after 2 attempts:
    → FLAG for Phase 6 Cascading Audit
    → 記錄到 .audit/pipeline-run-{ts}.md

IF WARNING issues:
  → draft_action(action="patch") 修正（1 round）
  → IF still WARNING → LOG + continue（Phase 6 會再檢查）

IF ADVISORY only:
  → LOG to audit trail → continue
```

#### B5 方法學 Checklist

**基礎方法學檢查**（所有 paper type）：

| 檢查項        |    Original    | Case | Systematic | AI/ML Prediction | AI Clinical |
| ------------- | :------------: | :--: | :--------: | :--------------: | :---------: |
| 研究設計描述  |       ✅       |  ✅  |     ✅     |        ✅        |     ✅      |
| 主要/次要結局 |       ✅       |  ⬜  |     ✅     |        ✅        |     ✅      |
| 樣本量/power  |       ✅       |  ⬜  |     ⬜     |        ✅        |     ✅      |
| 納入/排除標準 |       ✅       |  ⬜  |     ✅     |        ✅        |     ✅      |
| 統計方法匹配  |       ✅       |  ⬜  |     ✅     |        ✅        |     ✅      |
| 變項定義      |       ✅       |  ✅  |     ⬜     |        ✅        |     ✅      |
| 倫理聲明      |       ✅       |  ✅  |     ⬜     |        ✅        |     ✅      |
| 收集期間      |       ✅       |  ✅  |     ✅     |        ✅        |     ✅      |
| EQUATOR       | CONSORT/STROBE | CARE |   PRISMA   |    TRIPOD+AI     |  DECIDE-AI  |

**AI/ML 特定檢查項**（僅 AI/ML paper types）：

| 檢查項                 | Prediction | Diagnostic | Imaging | Decision  |
| ---------------------- | :--------: | :--------: | :-----: | :-------: |
| Data split 策略        |     ✅     |     ✅     |   ✅    |    ✅     |
| 模型架構/超參數        |     ✅     |     ✅     |   ✅    |    ✅     |
| 訓練/驗證/測試集比例   |     ✅     |     ✅     |   ✅    |    ⬜     |
| 外部驗證               |     ✅     |     ✅     |   ✅    |    ✅     |
| 缺失值處理             |     ✅     |     ✅     |   ⬜    |    ✅     |
| 校準 (calibration)     |     ✅     |     ⬜     |   ⬜    |    ⬜     |
| Bias/Fairness 分析     |     ✅     |     ✅     |   ✅    |    ✅     |
| 可解釋性/可解讀性      |     ⬜     |     ⬜     |   ✅    |    ✅     |
| 人機比較 (human vs AI) |     ⬜     |     ✅     |   ✅    |    ✅     |
| 適用指引               | TRIPOD+AI  |  STARD-AI  |  CLAIM  | DECIDE-AI |

**B5 ↔ Hook E 的分工**：B5 在 Phase 5-6 做「快速方法學掃描」（10 項以內），Hook E 在 Phase 7 做「完整 EQUATOR checklist 逐條驗證」（20-42 項）。兩者互補不重複。

任何必選項 < 5 分 → draft_action(action="patch") → 2 rounds 後仍 < 5 → 人工介入。

#### B6 前置條件

| Target     | 前置            | 原因                    |
| ---------- | --------------- | ----------------------- |
| Results    | Methods         | Results 依 Methods 定義 |
| Discussion | Results + Intro | 討論 Results 回應 Intro |
| Conclusion | Discussion      | 總結 Discussion         |
| Abstract   | 所有主體        | 摘錄精華                |

Advisory only（§22 可重組），審計軌跡記錄跳過。

#### B7 Section Brief 合規 🆕

依據 `manuscript-plan.yaml` 逐段比對，確保 Section Brief 被正確實現。

| 子項 | 檢查內容                                     | 失敗行為                                |
| ---- | -------------------------------------------- | --------------------------------------- |
| B7a  | 每段 `key_claims` 是否在文中涵蓋             | `draft_action(action="patch")` 加入論點 |
| B7b  | 每段 `must_cite` 是否出現                    | `draft_action(action="patch")` 加入引用 |
| B7c  | 段落順序/數量 vs plan                        | ⚠️ Advisory（不阻擋）                   |
| B7d  | 該 section 的 `asset_plan` 項目是否已插入    | WARNING + 提示插入圖表                  |
| B7e  | 已插入圖表的 `caption_requirements` 是否滿足 | `draft_action(action="patch")` 補充圖說 |

```
FOR paragraph IN plan.sections[section].paragraphs:
  content = extract_paragraph(draft, paragraph.id)
  FOR claim IN paragraph.key_claims:
    IF claim NOT conveyed in content → ISSUE (B7a)
  FOR ref IN paragraph.must_cite:
    IF ref NOT in content → ISSUE (B7b)

FOR asset IN plan.asset_plan WHERE asset.section == section:
  IF asset NOT inserted in draft → ISSUE (B7d)
  IF asset inserted AND caption_requirements NOT met → ISSUE (B7e)
```

B7a/B7b 遺漏為 WARNING（1 round `draft_action(action="patch")` 修正），B7d 為 WARNING，B7e 為 WARNING。
B7c 為 ADVISORY（順序偏離可接受）。

#### Hook B8: Data-Claim Alignment

在 Results 完成後觸發。驗證統計宣稱與 Methods 一致：

- 統計方法：Results 中使用的檢定必須在 Methods 中宣告
- P-value 閾值：Results 的 p < X 須與 Methods 宣告的 α 一致
- CI 寬度：Results 的 95% CI 須與 Methods 一致
- 軟體：Results 提及的統計軟體須在 Methods 中宣告

| #   | 檢查項             | MCP Tool                                                 | 失敗行為                                            | 閾值來源                          |
| --- | ------------------ | -------------------------------------------------------- | --------------------------------------------------- | --------------------------------- |
| B8  | 統計宣稱↔方法對齊 | `run_quality_checks(action="writing_hooks", hooks="B8")` | `draft_action(action="patch")` Methods/Results 補齊 | `pipeline.writing.stat_alignment` |
