# MCP Server Internal Templates
# MCP 伺服器內部範本

## Purpose | 用途

This directory contains **internal templates** used by the MCP server and AI Agent for structured content generation.

此目錄包含 MCP 伺服器和 AI Agent 用於結構化內容生成的**內部範本**。

## ⚠️ Important Distinction | 重要區別

| Directory | Purpose | Format |
|-----------|---------|--------|
| `/templates/` (root) | Word document templates for export | `.docx` |
| `/src/.../mcp_server/templates/` (here) | Internal templates for Agent guidance | `.md` |

| 目錄 | 用途 | 格式 |
|------|------|------|
| `/templates/` (根目錄) | Word 文件輸出範本 | `.docx` |
| `/src/.../mcp_server/templates/` (此處) | Agent 引導用內部範本 | `.md` |

## Available Templates | 可用範本

### `concept_template.md`
**Research Concept Template | 研究概念範本**

A structured template for developing research concepts with:
- 🔒 **Protected sections**: Novelty Statement, Key Selling Points, Author Notes
- 📝 **Editable sections**: Background, Research Gap, Methods, Expected Outcomes
- ⚠️ **Required markers**: Fields that must be completed before drafting

用於開發研究概念的結構化範本，包含：
- 🔒 **受保護區塊**：創新性聲明、核心賣點、作者備註
- 📝 **可編輯區塊**：背景、研究缺口、方法、預期結果
- ⚠️ **必填標記**：撰寫草稿前必須完成的欄位

## Section Markers | 區塊標記

| Marker | Meaning | Agent Behavior |
|--------|---------|----------------|
| 🔒 PROTECTED | Content requires user confirmation before modification | Must ask user before changing |
| 📝 EDITABLE | Content can be freely improved | Can modify without asking |
| ⚠️ REQUIRED | Must be filled before proceeding | Validation will fail if empty |

| 標記 | 含義 | Agent 行為 |
|------|------|-----------|
| 🔒 受保護 | 修改前需用戶確認 | 必須先詢問用戶 |
| 📝 可編輯 | 可自由改進 | 可直接修改 |
| ⚠️ 必填 | 繼續前必須填寫 | 空白時驗證失敗 |

## Usage | 使用方式

These templates are used internally by:
1. **`/mdpaper.concept` prompt**: Guides concept development
2. **`validate_concept` tool**: Checks template completeness
3. **`/mdpaper.draft` prompt**: References protected sections

這些範本由以下內部使用：
1. **`/mdpaper.concept` 提示**：引導概念開發
2. **`validate_concept` 工具**：檢查範本完整性
3. **`/mdpaper.draft` 提示**：參照受保護區塊
