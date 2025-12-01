# Skills 技能系統

## 概念

Skill（技能）是一個完整的工作流程定義，告訴 AI Agent 如何組合多個 MCP 工具來完成複雜任務。

### 設計哲學

```
工具 (Tool) = 單一能力（搜尋、儲存、分析...）
技能 (Skill) = 完整知識（如何做好一件事）
```

- **工具**：`search_literature` 只負責搜尋，不知道搜完要幹嘛
- **技能**：`literature_review.md` 知道完整流程：搜尋 → 篩選 → 下載 → 整理 → 輸出

## 目錄結構

```
.skills/
├── README.md                    # 本文件
├── _template.md                 # Skill 模板
│
├── research/                    # 研究階段
│   ├── literature_review.md     # 系統性文獻回顧
│   ├── concept_development.md   # 研究概念發展
│   └── gap_analysis.md          # 研究缺口分析
│
├── writing/                     # 寫作階段
│   ├── draft_introduction.md    # 撰寫前言
│   ├── draft_methods.md         # 撰寫方法
│   ├── draft_results.md         # 撰寫結果
│   └── draft_discussion.md      # 撰寫討論
│
├── analysis/                    # 分析階段
│   ├── statistical_analysis.md  # 統計分析
│   └── figure_generation.md     # 圖表製作
│
└── publishing/                  # 發表階段
    ├── journal_selection.md     # 期刊選擇
    └── manuscript_formatting.md # 稿件格式化
```

## 如何使用

### 用戶觸發

用戶可以透過以下方式觸發 Skill：

1. **直接說**：「幫我做文獻回顧」→ Agent 載入 `literature_review.md`
2. **Prompt**：`/skill:literature_review`
3. **上下文**：Agent 判斷當前任務需要哪個 Skill

### Agent 行為

1. 識別需要的 Skill
2. 讀取 Skill 檔案
3. 按照 Skill 定義的流程執行
4. 在關鍵點詢問用戶確認
5. 產出 Skill 定義的交付物

## Skill 格式規範

每個 Skill 檔案包含：

| 區塊 | 必須 | 說明 |
|------|------|------|
| `## 概述` | ✅ | 這個技能做什麼 |
| `## 前置條件` | ✅ | 執行前需要什麼 |
| `## 使用工具` | ✅ | 會用到哪些 MCP 工具 |
| `## 工作流程` | ✅ | 詳細步驟（核心！） |
| `## 決策點` | ✅ | 需要詢問用戶的地方 |
| `## 輸出產物` | ✅ | 完成後產出什麼 |
| `## 範例對話` | ⚪ | 示範如何與用戶互動 |
| `## 常見問題` | ⚪ | FAQ 和 troubleshooting |

## 與現有系統整合

### 與 Copilot Instructions 的關係

```
copilot-instructions.md  →  告訴 Agent「有哪些工具」
.skills/*.md             →  告訴 Agent「如何組合工具完成任務」
```

### 與 MCP Prompts 的關係

Skills 可以轉換為 MCP Prompts 供程式化調用：

```python
@mcp.prompt()
def skill_literature_review():
    """載入文獻回顧技能"""
    return read_skill_file("research/literature_review.md")
```

## 新增 Skill

1. 複製 `_template.md`
2. 填入技能定義
3. 放到適當的子目錄
4. 測試工作流程
