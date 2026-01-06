# Active Context

## User Preferences
- **Git Identity**: u9401066 <u9401066@gap.kmu.edu.tw>

## 當前焦點
Phase 4 MVP 核心功能已全部完成 🎉

## 最近變更 (2026-01-06)

### 1. Phase 4 MVP 核心工具 ✅ (剛完成)

#### Analysis Tools (`tools/analysis/`)
- **generate_table_one** - Table 1 自動生成（mean±SD, t-test/chi2, p-values）
- **detect_variable_types** - 自動偵測變數類型（連續/類別/分組）
- **list_data_files** - 列出 data/ 目錄的可用檔案
- **analyze_dataset** - 描述性統計
- **run_statistical_test** - 統計檢定（t-test, ANOVA, chi2, correlation 等）
- **create_plot** - 統計圖表（histogram, boxplot, scatter, violin 等）

#### Review Tools (`tools/review/`)
- **check_manuscript_consistency** - 稿件一致性檢查
  - 引用一致性（PMID 存在、未引用文獻）
  - 數字一致性（N= 值）
  - 縮寫定義檢查（BMI, ASA, ICU 等）
  - Table/Figure 連續性
  - p 值格式一致性
- **create_reviewer_response** - Reviewer 回覆模板生成
  - structured：標準 point-by-point 格式
  - table：表格式整理
  - letter：正式信函格式
- **format_revision_changes** - 修改差異格式化

### 2. CRUD Delete 操作 ✅ (稍早完成)
- delete_reference, delete_draft, archive_project, delete_project

### 3. Citation Assistant ✅
- suggest_citations, scan_draft_citations, find_citation_for_claim

## 相關檔案
- `src/med_paper_assistant/interfaces/mcp/tools/analysis/` - Analysis 模組
  - `table_one.py` - Table 1 相關工具
  - `stats.py` - 統計分析工具
- `src/med_paper_assistant/interfaces/mcp/tools/review/` - Review 模組
  - `consistency.py` - 一致性檢查
  - `response.py` - Reviewer 回覆

## 工具統計
- 總工具數：56 → 65 個
- Phase 4 新增：9 個工具（6 analysis + 3 review）

## 待解決問題
- [ ] Dashboard → Copilot 主動通訊（VS Code Chat API 限制）

## 下一步 (Phase 4 剩餘)
- [ ] `generate_cover_letter` - Cover Letter 自動生成
- [ ] `check_submission_checklist` - 期刊投稿清單檢查
- [ ] `generate_highlights` - Bullet points highlights
- [ ] `generate_graphical_abstract` - 視覺摘要模板

## 更新時間
2026-01-06 12:20
