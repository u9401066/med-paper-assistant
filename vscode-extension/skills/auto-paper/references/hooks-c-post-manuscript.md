# Copilot Hooks C: post-manuscript

> auto-paper 的 reference 檔（progressive disclosure）；入口與 hard gate 見 [../SKILL.md](../SKILL.md)。
> **Read this when**: running or debugging whole-manuscript checks (N-value, abbreviations, wikilinks, figure/table counts, cross-references, temporal consistency).
> 相關：[phase-6-6.5-audit-evolution.md](phase-6-6.5-audit-evolution.md)、[hooks-a-b-post-write-section.md](hooks-a-b-post-write-section.md)

---

### Hook C: post-manuscript（全稿完成後，含分層回溯，最多 N rounds，N = `pipeline.hook_c_max_rounds`）

| #   | 檢查項                   | MCP Tool                                                  | 失敗行為                                               | 回溯層      | 閾值來源                           |
| --- | ------------------------ | --------------------------------------------------------- | ------------------------------------------------------ | ----------- | ---------------------------------- |
| C1  | 稿件一致性               | `run_quality_checks(action="writing_hooks", hooks="C1")`  | `draft_action(action="patch")`                         | → B4        | —                                  |
| C2  | 投稿清單                 | `run_quality_checks(action="writing_hooks", hooks="C2")`  | 定點修正                                               | —           | `required_documents.*`             |
| C3  | N 值跨 section 一致      | `draft_action(action="read")` × N + 數字比對              | `draft_action(action="patch")` 統一                    | → A         | —                                  |
| C4  | 縮寫首次定義             | `draft_action(action="read")` + 全文掃描                  | `draft_action(action="patch")` 補定義                  | → A         | —                                  |
| C5  | Wikilinks 可解析         | `scan_draft_citations`                                    | `save_reference_mcp` 補存                              | → A4        | —                                  |
| C6  | 總字數合規               | `draft_action(action="count_words")`                      | 精簡超長 section                                       | → A1        | `word_limits.total_manuscript`     |
| C7  | 資產數量、計畫與交叉引用 | 見下方 C7a/C7b/C7d                                        | 依子項處理                                             | 依子項      | `assets.*`, `manuscript-plan.yaml` |
| C8  | 時間一致性               | `draft_action(action="read")` × N + Agent 掃描            | `draft_action(action="patch")` 更新過時描述            | → B         | —                                  |
| C9  | 補充材料交叉引用         | `run_quality_checks(action="writing_hooks", hooks="C9")`  | `draft_action(action="patch")` 補引用                  | —           | —                                  |
| C10 | 文獻全文+分析驗證        | `run_quality_checks(action="writing_hooks", hooks="C10")` | 補 fulltext/analysis                                   | —           | —                                  |
| C11 | 引用分布均衡 🆕          | `run_quality_checks(action="writing_hooks", hooks="C11")` | 重分配引用到缺引用 section                             | → A2        | —                                  |
| C12 | 引用適切性審計 🆕        | `run_quality_checks(action="writing_hooks", hooks="C12")` | 補決策紀錄到 citation_decisions.json                   | —           | —                                  |
| C13 | 圖表品質與排序 🆕        | `run_quality_checks(action="writing_hooks", hooks="C13")` | 修正排序/補 caption                                    | → C7d       | —                                  |
| C14 | Claim-Evidence 對齊 🆕   | `run_quality_checks(action="writing_hooks", hooks="C14")` | 為強 claim 補引用/source-material/圖表證據，或弱化措辭 | → Phase 5/8 | 強 claim 不歸類為 A3 語體問題      |

#### Hook C Cascading Protocol

```
Stage 1: Full Scan
  → 執行 C1-C7 → 收集 ALL issues
  → 分類: CRITICAL (C1不一致, C3數字錯, C5斷鏈) / WARNING (C2, C4, C6, C7)

Stage 2: Cascading Fix (最多 3 rounds)
  Round N:
    FOR each CRITICAL issue:
      1. 定位到具體 section + 段落
      2. draft_action(action="patch") 修正
      3. 觸發 回溯層 的 Hook（見上表）確認 patch 品質
    → re-run Hook C

Stage 3: C8 Temporal Consistency Pass
  → C1-C7 全過後，執行 C8 逆向掃描
  → IF C8 發現過時引用 → draft_action(action="patch") 更新 → 重跑 C1 確認一致性

Stage 4: 人工介入（3 rounds 後仍 CRITICAL）
  → 生成 quality-scorecard.md（量化分數）
  → 呈現具體問題 + 建議修改方案
  → 用戶選擇：修改 / 接受風險 / 回到 Phase 5

Hook C 修正策略：
  C1 不一致: 統一術語 → 統一語氣 → 重寫弱 section
  C3 N 值: 以 Methods 定義為準 → 更新所有 sections
  C4 縮寫: 找首次出現 → 加全稱 → 後續只用縮寫
  C5 斷鏈: validate_wikilinks → save_reference_mcp → manual
  C6 字數: 刪冗餘 → 合併段落 → 詢問用戶刪哪段
  C7 數量: 依子項分別處理（見下方）
  C8 過時: 逆向掃描 → draft_action(action="patch") 更新 → 重跑 C1
  C11 引用分布: 找缺引用 section → 補引用 → re-run A2
  C12 引用審計: 生成 citation_decisions.json → 每篇引用留 justification
  C13 圖表品質: 修正順序 → 補 caption → 確保 Results 有圖表引用
```

#### C7 數量與交叉引用合規（D5 擴展）🆕

目前 code-enforced 的 C7 family 有三項。字數由 C6、Wikilink 由 C5 處理；引用預算由 Phase 7 R6 處理，不另虛構 C7c/C7e code hook。

| 子項 | 檢查內容                                             | 失敗行為                               | 閾值／來源                        |
| ---- | ---------------------------------------------------- | -------------------------------------- | --------------------------------- |
| C7a  | 文字與 manifest 中的圖表總數是否超過期刊上限         | 合併或移至 supplementary               | `assets.figures_max/tables_max`   |
| C7b  | required asset 是否已登記、放入指定 section 且可匯出 | 補 insert／placement／renderable asset | `manuscript-plan.yaml` + manifest |
| C7d  | 圖表交叉引用（orphan/phantom）                       | orphan=WARNING；phantom=CRITICAL       | manuscript + manifest             |

```
orphan = manifest 中有但 draft 沒引用 → WARNING（有圖沒用）
phantom = draft 引用但 manifest 沒有 → CRITICAL（有引用沒圖）
```

> **分工**：C6 檢查總字數；C5 檢查 citation wikilinks；R6 檢查引用預算。這些都不是 C7 子項。

#### C8 時間一致性檢查（Temporal Consistency Pass）

根因：寫作順序（如 Methods → Results → Introduction）導致先寫的 section 可能引用「尚未寫」的 section 狀態。當後續 section 完成後，先前的描述變成過時。

**觸發時機**：Phase 6，Hook C1-C7 之後

**檢查流程**：

1. 按寫作順序逆向掃描(最早寫的 section 最後檢查)
2. 在每個 section 中搜尋以下模式：
   - "not yet written" / "尚未撰寫"
   - "Deferred" / "deferred"
   - "will be" + section 名（如 "will be discussed in Discussion"）
   - Hook 狀態引用（如 "B2: Deferred"）
   - 對其他 section 內容的斷言（如 "the Introduction contains..."）
3. 對每個匹配項，驗證：被引用的 section 是否已存在？描述是否仍然正確？
4. 不正確 → `draft_action(action="patch")` 更新為實際狀態

**實作**：

```
FOR section IN reverse(writing_order):
  content = draft_action(action="read", filename=section)
  FOR pattern IN temporal_patterns:
    matches = scan(content, pattern)
    FOR match IN matches:
      referenced_section = extract_section(match)
      IF referenced_section EXISTS AND match.claim != actual_state:
        draft_action(action="patch")(section, old=match, new=actual_state_description)
        log_to_audit("C8: Updated stale reference in {section}")
```

**失敗行為**：`draft_action(action="patch")` 更新過時描述。最多 2 rounds。

#### Hook C9: Supplementary Cross-Reference

在全稿完成後觸發。驗證主稿與補充材料之間的雙向引用：

- 主稿中每個 "Supplementary Table/Figure N" 引用在補充材料中有對應
- 補充材料中的每個項目至少被主稿引用一次（孤兒偵測）
- e-prefix 引用（eTable, eFigure）也被追蹤

| #   | 檢查項               | MCP Tool                                                 | 失敗行為                                             | 閾值來源 |
| --- | -------------------- | -------------------------------------------------------- | ---------------------------------------------------- | -------- |
| C9  | 補充材料交叉引用驗證 | `run_quality_checks(action="writing_hooks", hooks="C9")` | `draft_action(action="patch")` 補引用 / 刪除孤兒引用 | —        |
