# MCP Server Internal Templates

# MCP 伺服器內部範本

## Purpose | 用途

This directory contains **internal templates** used by the MCP server and AI Agent for structured content generation.

此目錄包含 MCP 伺服器和 AI Agent 用於結構化內容生成的**內部範本**。

## ⚠️ Important Distinction | 重要區別

| Directory                                   | Purpose                               | Format  |
| ------------------------------------------- | ------------------------------------- | ------- |
| `/templates/` (root)                        | Word document templates for export    | `.docx` |
| `/src/.../interfaces/mcp/templates/` (here) | Internal templates for Agent guidance | `.md`   |

| 目錄                                        | 用途                 | 格式    |
| ------------------------------------------- | -------------------- | ------- |
| `/templates/` (根目錄)                      | Word 文件輸出範本    | `.docx` |
| `/src/.../interfaces/mcp/templates/` (此處) | Agent 引導用內部範本 | `.md`   |

## Template Architecture | 範本架構

The concept template system uses a **base + paper-type** architecture for
journal manuscripts and complete, output-specific contracts for formal outputs
whose requirements differ from a journal article:

```
templates/
├── concept_base.md              # Common sections (NOVELTY, SELLING POINTS, etc.)
├── concept_original_research.md # Original research specific sections
├── concept_meta_analysis.md     # Meta-analysis specific sections
├── concept_systematic_review.md # Systematic review specific sections
├── concept_case_report.md       # Case report specific sections
├── concept_review_article.md    # Review article specific sections
├── concept_research_proposal.md # Full proposal planning contract
├── concept_project_closeout_report.md # Full closeout audit contract
├── concept_student_paper.md     # Full student authorship contract
├── concept_conference_paper.md  # Full conference submission contract
├── concept_thesis_dissertation.md # Full thesis chapter contract
├── concept_arxiv_preprint.md    # Full versioned preprint contract
└── README.md                    # This file
```

### How it works | 運作方式

1. **`concept_base.md`** contains:

   - Project header with variables (`{{PROJECT_NAME}}`, `{{PAPER_TYPE}}`, etc.)
   - 🔒 Protected sections (NOVELTY STATEMENT, KEY SELLING POINTS, Author Notes)
   - 📝 Common editable sections (Background, Research Gap, Expected Outcomes)
   - `{{PAPER_TYPE_SECTIONS}}` placeholder for paper-type specific content

2. **Paper-type templates** (e.g., `concept_meta_analysis.md`) contain:

   - Sections specific to that paper type
   - Required fields for that methodology

3. **At project creation**:
   - `concept_base.md` is loaded
   - Variables are replaced
   - Paper-type sections are inserted at `{{PAPER_TYPE_SECTIONS}}`

4. **For formal non-journal outputs**:
   - The complete output-specific template is loaded directly
   - Novelty is evaluated only when that profile requires it
   - Planning, delivery, academic-integrity, or versioning claims retain their
     own auditable structure

### Variables | 變數

| Variable                  | Description                 | Example                       |
| ------------------------- | --------------------------- | ----------------------------- |
| `{{PROJECT_NAME}}`        | Project name                | "Ketamine vs Propofol Study"  |
| `{{PAPER_TYPE}}`          | Paper type display name     | "Meta-Analysis"               |
| `{{CREATED_DATE}}`        | Creation date               | "2025-01-15"                  |
| `{{PAPER_TYPE_SECTIONS}}` | Paper-type specific content | (inserted from type template) |
| `{{TARGET_JOURNAL}}`      | Target journal              | "Anesthesiology"              |
| `{{MEMO}}`                | Initial memo/notes          | User-provided notes           |

## Section Markers | 區塊標記

| Marker       | Meaning                                                | Agent Behavior                |
| ------------ | ------------------------------------------------------ | ----------------------------- |
| 🔒 PROTECTED | Content requires user confirmation before modification | Must ask user before changing |
| 📝 EDITABLE  | Content can be freely improved                         | Can modify without asking     |
| ⚠️ REQUIRED  | Must be filled before proceeding                       | Validation will fail if empty |

| 標記      | 含義             | Agent 行為     |
| --------- | ---------------- | -------------- |
| 🔒 受保護 | 修改前需用戶確認 | 必須先詢問用戶 |
| 📝 可編輯 | 可自由改進       | 可直接修改     |
| ⚠️ 必填   | 繼續前必須填寫   | 空白時驗證失敗 |

## Paper-Type Specific Sections | 論文類型專屬區塊

### Original Research

- Study Design, Participants, Intervention/Exposure, Outcomes
- Statistical Analysis, Ethical Considerations

### Meta-Analysis

- PICO Question, Eligibility Criteria, Search Strategy
- Risk of Bias Assessment, Statistical Analysis Plan
- PROSPERO Registration

### Systematic Review

- Research Question, Study Selection Process
- Quality Assessment, Data Synthesis Method

### Case Report

- Case Significance, Case Presentation, Timeline
- Discussion Points, Patient Consent, CARE Checklist

### Review Article

- Review Scope, Structure/Outline, Key Messages
- Future Directions, Visual Elements Planning

### Formal Academic Outputs

- Research proposal: objectives, methods, timeline, budget, ethics, risks, impact
- Project closeout: baseline objectives, deliverables, variance, finance, handoff
- Student paper: rubric alignment, verified reading plan, authorship and AI-use record
- Conference paper: compact venue contract plus companion presentation assets
- Thesis/dissertation: chapter dependencies, committee traceability, data governance
- arXiv/preprint: reproducibility, licenses, repository identifiers, version notes

## Usage | 使用方式

These templates are used internally by:

1. **`create_project` tool**: Generates concept.md using templates
2. **`/mdpaper.concept` prompt**: Guides concept development
3. **`validate_concept` tool**: Checks template completeness
4. **`/mdpaper.draft` prompt**: References protected sections

這些範本由以下內部使用：

1. **`create_project` 工具**：使用範本生成 concept.md
2. **`/mdpaper.concept` 提示**：引導概念開發
3. **`validate_concept` 工具**：檢查範本完整性
4. **`/mdpaper.draft` 提示**：參照受保護區塊

## Modifying Templates | 修改範本

To customize templates:

1. Edit the appropriate `.md` file
2. Restart MCP server to apply changes
3. New projects will use updated templates

⚠️ **Note**: Existing projects keep their original concept.md - templates only affect new projects.
