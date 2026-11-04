# Phase 5: ASSET GENERATION SUB-PIPELINES

> auto-paper 的 reference 檔（progressive disclosure）；入口與 hard gate 見 [../SKILL.md](../SKILL.md)。
> **Read this when**: generating tables / figures / diagrams, handling missing asset data, or applying asset-tool fallbacks.
> 相關：[phase-5-section-writing.md](phase-5-section-writing.md)、[cross-tool-orchestration.md](cross-tool-orchestration.md)

---

#### Asset Generation Sub-Pipeline（Phase 5 Step 2）

每個 section 寫作前，依 asset_plan 生成所需資產：

```
FOR asset IN asset_plan[section]:
  SWITCH asset.type:

    CASE "table_one":
      1. analysis_action(action="list_data") → 確認資料存在
      2. analysis_action(action="detect_variables", filename=file) → 自動分類
      3. analysis_action(action="table_one", filename=file, groups=..., variables=...) → 產出表格
      4. draft_action(action="insert_table", filename=..., table_content=..., caption=...) → 插入草稿
      → ❌ 無資料檔 → 提示用戶提供，SKIP asset

    CASE "statistical_test":
      1. analysis_action(action="summary", filename=file) → 了解資料分佈
      2. analysis_action(action="test", filename=file, test_type=...) → 執行檢定
      3. 結果整合到 section 文字中
      → ❌ 不確定檢定方法 → 詢問用戶

    CASE "plot":
      1. analysis_action(action="plot", filename=file, plot_type=...) → 產生圖片
      2. draft_action(action="insert_figure", filename=..., image_path=..., caption=...) → 插入草稿
      → ❌ 圖表不合理 → 提供替代建議

    CASE "flow_diagram":  (CONSORT, PRISMA, study flow)
      1. IF drawio MCP 可用:
         → drawio.create_diagram(type, data) → XML
        → drawio.export_diagram(format="png" or "svg") → rendered asset
        → project_action(action="save_diagram", project=..., content=..., filename=name, rendered_content=..., rendered_format=...)
        → draft_action(action="insert_figure", filename=..., caption=..., draft_filename=..., after_section=...)
      2. ELSE:
         → 產生 Mermaid 文字描述 → 存入 results/diagrams/
         → FLAG: 建議用戶手動轉換
      3. reference 在草稿中，確保導出的 Word/PDF 可見圖像而不只是 `.drawio` 原始檔

    CASE "custom_figure":
      1. Agent 依 asset_plan 說明 → analysis_action(action="plot") 或手動描述
      2. draft_action(action="insert_figure") 或 FLAG 需外部工具
```

| Asset Type       | 必要 MCP Tool                                                                    | 外部 MCP           | Fallback        |
| ---------------- | -------------------------------------------------------------------------------- | ------------------ | --------------- |
| table_one        | `analysis_action(action="table_one")`                                            | —                  | 手動提供表格    |
| statistical_test | `analysis_action(action="test")`                                                 | —                  | 描述預期分析    |
| plot             | `analysis_action(action="plot")`                                                 | —                  | 描述圖表需求    |
| flow_diagram     | `project_action(action="save_diagram")` + `draft_action(action="insert_figure")` | `drawio` 🔸        | Mermaid 文字    |
| forest_plot      | ❌ 缺少                                                                          | `meta-analysis` 🔸 | R/Python script |
| funnel_plot      | ❌ 缺少                                                                          | `meta-analysis` 🔸 | R/Python script |
| PRISMA_diagram   | `project_action(action="save_diagram")` + `draft_action(action="insert_figure")` | `drawio` 🔸        | Mermaid 文字    |

#### Agent-Initiated Asset Generation（寫作中自主新增圖表）

Phase 4 的 asset_plan 無法預見所有需求。寫作過程中 Agent 可能發現需要 **文獻比較表**、**方法對照表** 等。

```
觸發條件（Phase 5 Step 3 寫作中）：
  - 引用 ≥3 篇文獻做比較 → 考慮 literature_summary_table
  - 描述多種方法/技術差異 → 考慮 comparison_table
  - 概念或架構複雜 → 考慮 concept_diagram

流程：
  1. 檢查 journal-profile.yaml → pipeline.assets.agent_initiated.enabled
  2. 檢查類型是否在 allowed_types 中
  3. 檢查目前圖/表數量是否已達 assets.figures_max / tables_max
  4. IF 可新增:
     a. 用 Markdown 表格撰寫（文獻比較表、方法對照表等）
     b. 或 analysis_action(action="plot") / project_action(action="save_diagram")（如需圖形）
     c. 附 caption + 標記來源為 "agent-initiated"
     d. draft_action(action="insert_table") 或 draft_action(action="insert_figure") → 插入草稿
     e. 更新 asset_plan（追加到 plan.metadata.changelog）
     f. 記錄到 .audit/: 為何新增、依據哪些文獻
  5. IF 已達上限:
     → 評估是否替換低優先級 asset
     → 或以文字描述替代，不生成實際圖表

常見 Agent-Initiated Assets：
  - 「Table X. Comparison of [topic] across studies」 → 文獻整理表
  - 「Table X. Characteristics of included studies」 → SR/Review 常見
  - 「Figure X. Conceptual framework of [approach]」 → 架構圖
```
