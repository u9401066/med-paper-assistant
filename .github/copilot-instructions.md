# Copilot 自定義指令

## 開發哲學 💡
> **「想要寫文件的時候，就更新 Memory Bank 吧！」**
> 
> **「想要零散測試的時候，就寫測試檔案進 tests/ 資料夾吧！」**

## 法規遵循
你必須遵守以下法規層級：
1. **憲法**：`CONSTITUTION.md` - 最高原則
2. **子法**：`.github/bylaws/*.md` - 細則規範
3. **技能**：`.claude/skills/*/SKILL.md` - 操作程序

## 架構原則
- 採用 DDD (Domain-Driven Design)
- DAL (Data Access Layer) 必須獨立
- 參見子法：`.github/bylaws/ddd-architecture.md`

## MCP 架構原則 ⚠️
**MCP 對 MCP 只要 API！**

本專案有多個 MCP Server，彼此透過 Agent 協調通訊：

| MCP Server | 職責 | 來源 |
|------------|------|------|
| **mdpaper** | 專案管理、草稿、參考文獻儲存、Word 匯出 | 本地 |
| **pubmed-search** | PubMed 文獻搜尋 | submodule |
| **cgu** | 創意生成單元 | submodule |
| **zotero-keeper** | Zotero 書目管理 | uvx |
| **drawio** | Draw.io 圖表 | uvx |

### 儲存參考文獻的正確流程
```
❌ 錯誤：mdpaper 直接 import pubmed_search
✅ 正確：Agent 協調 MCP 間資料傳遞

1. pubmed-search: search_literature("query") → PMIDs
2. pubmed-search: fetch_article_details(pmids) → metadata dict
3. mdpaper: save_reference(article=metadata) → 儲存到專案
```

## Python 環境（uv 優先）
- 新專案必須使用 uv 管理套件
- 必須建立虛擬環境（禁止全域安裝）
- 參見子法：`.github/bylaws/python-environment.md`

## Memory Bank 同步
**⚠️ 強制寫入位置：`memory-bank/`**

每次重要操作必須更新 Memory Bank：
- 參見子法：`.github/bylaws/memory-bank.md`
- 目錄：`memory-bank/`

## Git 工作流
提交前必須執行檢查清單：
- 參見子法：`.github/bylaws/git-workflow.md`
- 觸發 Skill：`git-precommit`

## 跨平台支援
本專案支援 Windows/Linux/macOS：
- Windows: `scripts/setup.ps1`
- Linux/macOS: `scripts/setup.sh`

## 回應風格
- 使用繁體中文
- 提供清晰的步驟說明
- 引用相關法規條文
