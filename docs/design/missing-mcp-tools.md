# Missing MCP Tools Inventory

> 追蹤 auto-paper Pipeline 需要但尚未實作的 MCP 工具。
> 用途：評估哪些需要內部開發、哪些可作為外部 MCP 協作。

## 狀態定義

| 狀態    | 說明                    |
| ------- | ----------------------- |
| ❌ 缺少 | 未實作且無替代          |
| ⚠️ 部分 | 有功能但缺 alias 或參數 |
| 🔸 外部 | 需外部 MCP Server       |

---

## 內部工具（需開發或補全）

### ⚠️ validate_concept_quick

- **用途**: 快速結構檢查（不跑完整 novelty 驗證）
- **Phase**: 3 Concept, 5 Writing（section pre-check）
- **現狀**: `validate_concept(structure_only=True)` 參數已存在，但無 alias
- **建議**: 註冊為獨立 tool alias，方便 Agent 直接呼叫
- **Priority**: LOW

### ❌ validate_for_section

- **用途**: 針對特定 section 驗證 concept 覆蓋度
- **Phase**: 5 Writing（每個 section 開始前）
- **現狀**: `draft-writing/SKILL.md` 引用但未實作
- **建議**: 加入 `validate_concept(section="Methods")` 參數
- **Priority**: MEDIUM

### ❌ parse_journal_profile

- **用途**: 解析期刊 submission guide → 結構化 YAML
- **Phase**: 0 Pre-Planning
- **現狀**: 完全缺少
- **建議**: 新增 tool，輸入 PDF/URL/text → 輸出 journal-profile.yaml 草稿
- **依賴**: 需要 `fetch_webpage` MCP 或 PDF parser
- **Priority**: HIGH（Phase 0 核心）

### ❌ load_journal_profile

- **用途**: 載入並解析 journal-profile.yaml，供所有 Hook 讀取約束條件
- **Phase**: 所有 Phase 和 Hook
- **現狀**: 目前只能用 `read_file` 手動讀取 YAML
- **建議**: 新增 tool，自動解析並驗證 YAML schema
- **Priority**: HIGH

### ❌ generate_review_report

- **用途**: Phase 7 Autonomous Review 的審查報告生成
- **Phase**: 7 Autonomous Review
- **現狀**: 完全缺少
- **建議**: 可整合到 `check_formatting` 或獨立 tool
- **Priority**: MEDIUM

### ❌ generate_cover_letter

- **用途**: 自動草擬 cover letter
- **Phase**: 9 Export
- **現狀**: 完全缺少
- **建議**: 基於 concept.md + journal-profile 自動生成
- **Priority**: LOW

### ❌ list_assets

- **用途**: 列出 project 中所有已生成的 assets（圖表）
- **Phase**: 6 Audit（Hook C7）
- **現狀**: 完全缺少
- **建議**: 掃描 `projects/{slug}/results/` 目錄
- **Priority**: MEDIUM

### ⚠️ save_diagram_standalone

- **用途**: 儲存 Mermaid/drawio 圖表為獨立檔案
- **Phase**: 5 Writing（Asset Sub-Pipeline）
- **現狀**: `save_diagram(project, content, name)` 參數在 SKILL 引用但工具可能不完整
- **建議**: 確認 `save_diagram` tool 是否已完整實作
- **Priority**: MEDIUM

---

## 外部 MCP Server（需找或開發）

### 🔸 fetch_webpage / PDF Parser

- **用途**: Phase 0 解析期刊 submission guide（URL 或 PDF）
- **Phase**: 0 Pre-Planning
- **候選**: VS Code 內建 `fetch_webpage`（deferred tool），或專用 PDF parser MCP
- **Priority**: ⭐ HIGH
- **Notes**: `fetch_webpage` 已在 deferred tools 列表中，可直接使用

### 🔸 meta-analysis MCP

- **用途**: forest plot, funnel plot, I² heterogeneity, meta-regression
- **Phase**: 5 Writing（Asset Sub-Pipeline，meta-analysis paper type）
- **候選**: 需自建或找社區 MCP
- **Fallback**: R/Python script 描述 + 用戶手動執行
- **Priority**: ⭐ HIGH（meta-analysis paper type 核心需求）

### 🔸 drawio MCP

- **用途**: CONSORT flow diagram, PRISMA flow diagram, study flow
- **Phase**: 5 Writing（Asset Sub-Pipeline）
- **候選**: `start-drawio.sh` 已存在於 `scripts/`，可能有對應 MCP
- **Fallback**: Mermaid 文字描述
- **Priority**: ⭐ MEDIUM

### 🔸 CGU MCP

- **用途**: `cgu_frame`, `cgu_diverge`（`typical_set` / `anti_typical` / `collide`）, `cgu_ideas`, `cgu_judge`（共 11 個工具；generation / judgement 以 `work_order` 交由 agent 自己的模型完成）
- **Phase**: 3 Concept, 7 Review（論點強化）
- **候選**: `integrations/cgu/` 目錄已存在
- **Priority**: ⭐ MEDIUM

### 🔸 Grammar Checker MCP

- **用途**: 英文學術文法 + 風格檢查
- **Phase**: 7 Autonomous Review
- **候選**: LanguageTool MCP, Grammarly API
- **Fallback**: Agent 內建語法能力（品質較低）
- **Priority**: ⭐ MEDIUM

### 🔸 Plagiarism Checker MCP

- **用途**: 偵測過度相似的文字（含自引用比例）
- **Phase**: 7 Autonomous Review
- **候選**: iThenticate API（需機構授權）
- **Fallback**: Agent 自查 + 引用密度分析
- **Priority**: ⭐ LOW

### 🔸 Readability Scorer MCP

- **用途**: Flesch-Kincaid, Gunning Fog 等可讀性量化
- **Phase**: 7 Autonomous Review
- **候選**: 可用 Python library 簡單實作
- **Fallback**: Agent 主觀評估
- **Priority**: ⭐ LOW

### 🔸 Image Optimizer MCP

- **用途**: 圖片 DPI/格式轉換（TIFF, EPS for print）
- **Phase**: 9 Export
- **候選**: ImageMagick wrapper
- **Fallback**: 用戶手動轉換
- **Priority**: ⭐ LOW

### 🔸 LaTeX Renderer MCP

- **用途**: 公式 / 特殊表格渲染
- **Phase**: 9 Export
- **候選**: KaTeX, MathJax
- **Fallback**: Word 公式編輯器
- **Priority**: ⭐ LOW

---

## 未實作的基礎設施（非 Tool，但 Pipeline 引用）

| 功能                   | 說明                                               | Priority |
| ---------------------- | -------------------------------------------------- | -------- |
| `.audit/` 檔案生成     | Pipeline 定義了 audit trail 格式但無程式碼自動產出 | HIGH     |
| `checkpoint.json` 存讀 | 斷點恢復邏輯（save/restore）僅在 SKILL 描述        | HIGH     |
| Hook 效能追蹤          | `hook-effectiveness.md` 累積統計，需跨對話持久化   | MEDIUM   |
| Quality Scorecard 計算 | 0-10 分量化邏輯，目前依賴 Agent 主觀打分           | MEDIUM   |
| Review Round 持久化    | `review-round-{N}.md` 跨對話保存                   | MEDIUM   |

---

## 開發優先級排序

### P0 — Pipeline 核心（缺少會阻擋 Pipeline）

1. `load_journal_profile` — 所有 Hook 和 Phase 的約束來源
2. `parse_journal_profile` — Phase 0 核心
3. `.audit/` infra — 審計基礎
4. `checkpoint.json` infra — 斷點恢復

### P1 — 品質提升（缺少會降低品質但不阻擋）

5. `validate_for_section` — section 級 concept 檢查
6. `list_assets` — 圖表計數（Hook C7）
7. `generate_review_report` — 結構化審查報告
8. `fetch_webpage` — 已在 deferred tools，需驗證可用性

### P2 — 外部 MCP 協作

9. `meta-analysis` MCP — forest/funnel plot
10. `drawio` MCP — flow diagrams
11. `cgu` MCP — concept enhancement
12. `grammar-checker` MCP — 學術寫作品質

### P3 — Nice to Have

13. `generate_cover_letter`
14. `readability-scorer` MCP
15. `image-optimizer` MCP
16. `latex-renderer` MCP
17. `plagiarism-checker` MCP
