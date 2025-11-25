# Medical Paper Assistant (醫學論文寫作助手)

這是一個專為醫學研究人員設計的寫作輔助工具，整合了 VSCode 與 MCP (Model Context Protocol)，旨在簡化文獻檢索、草稿生成與期刊格式化的流程。

## 功能特色

- **智能文獻檢索 (Literature Search)**: 直接在編輯器中搜尋醫學文獻，支援自定義檢索參數。
- **草稿生成 (Draft Generation)**: 類似 Speckit 的功能，協助將零散的想法與筆記轉化為結構化的論文草稿。
- **期刊格式化 (Journal Formatting)**: 自動套用不同期刊的格式範本 (Templates)，確保引用與排版正確。
- **VSCode 整合**: 透過 MCP 協議，可與 VSCode Copilot 或 Antigravity 等 Agent 無縫協作。

## 安裝說明

本專案使用 Python 開發。

1.  複製專案：
    ```bash
    git clone https://github.com/yourusername/med-paper-assistant.git
    cd med-paper-assistant
    ```

2.  建立虛擬環境並安裝依賴：
    ```bash
    python3 -m venv .venv
    source .venv/bin/activate  # Linux/macOS
    pip install .
    ```

## 使用方法

### 啟動 MCP Server

```bash
python src/med_paper_assistant/mcp_server/server.py
```

### 在 VSCode 中使用

設定您的 MCP Client (如 VSCode Extension) 連接至此 Server，即可在對話中使用以下工具：
- `search_literature(query, limit)`
- `draft_section(topic, notes)`
- `apply_template(content, journal_name)`

## 專案結構

- `src/med_paper_assistant/mcp_server`: MCP Server 實作
- `src/med_paper_assistant/core`: 核心邏輯 (搜尋、草稿、格式化)
- `src/med_paper_assistant/templates`: 期刊範本

## 貢獻

歡迎提交 Issue 或 Pull Request！詳情請見 [CONTRIBUTING.md](CONTRIBUTING.md)。

## 使用指南 (Usage Guide)

本助手透過一系列的 Agent Workflows 來協助您完成論文寫作：

### 1. 準備階段 (Preparation)
- **上傳資料**: 將您的原始數據 (CSV) 放入 `data/` 目錄。
- **準備範本**: (選用) 如果您有特定的期刊格式，請準備好 Markdown 範本檔。

### 2. 發展構想 (Concept Development)
- **指令**: `/mdpaper.concept`
- **流程**: Agent 會協助您填寫 `concept.md`，釐清研究假說、方法與預期結果。

### 3. 資料分析 (Data Analysis)
- **指令**: `/mdpaper.data_analysis`
- **流程**: Agent 會讀取 `data/` 中的檔案，根據您的指示執行統計檢定 (T-test, Chi-square 等) 並繪製圖表。結果會存於 `results/`。

### 4. 撰寫草稿 (Drafting)
- **指令**: `/mdpaper.draft`
- **流程**: Agent 會讀取 `concept.md`、分析結果與期刊範本，自動生成論文草稿。圖表會自動嵌入，引用文獻也會自動格式化。

### 5. 內容修正 (Refinement)
- **指令**: `/mdpaper.clarify`
- **流程**: 針對草稿的特定段落進行互動式修改，例如「請改寫 Introduction 讓語氣更強烈」。

### 6. 文獻檢索 (Literature Search)
- 您也可以隨時要求 Agent 搜尋文獻：
  - "幫我找 2024 年關於氣喘的 Review 文章"
  - "搜尋 remifentanil 相關的臨床試驗"

## 授權 (License)

本專案採用 MIT 授權。
License](LICENSE)。
