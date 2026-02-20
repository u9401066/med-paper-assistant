# Project Brief

## 專案名稱

Medical Paper Assistant (醫學論文寫作助手)

## 專案目標

為醫學研究人員提供 AI 輔助的論文寫作工具，整合文獻搜尋、參考文獻管理、草稿撰寫、數據分析到格式化匯出的完整工作流程。

## 核心功能

| 功能             | 說明                              |
| ---------------- | --------------------------------- |
| **文獻搜尋**     | PubMed API 整合，支援並行搜尋     |
| **參考文獻管理** | 本地儲存、Foam 整合、多種引用格式 |
| **草稿撰寫**     | 結構化範本、自動引用插入          |
| **數據分析**     | CSV 分析、統計檢定、圖表生成      |
| **Word 匯出**    | 符合期刊格式的 .docx 輸出         |
| **圖表生成**     | Draw.io 整合，支援 CONSORT/PRISMA |

## 技術棧

- **後端**: Python 3.10+ (MCP Server)
- **介面**: VS Code + GitHub Copilot
- **協定**: Model Context Protocol (MCP)
- **文獻 API**: NCBI Entrez (BioPython)

## 目標用戶

- 醫學研究人員
- 臨床醫師撰寫論文
- 系統性回顧作者

## 專案約束

- 跨平台支援 (Windows/Linux/macOS)
- 本地優先 (無需雲端服務)
- 隱私保護 (資料不離開本機)
