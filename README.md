# Medical Paper Assistant (醫學論文寫作助手)

這是一個專為醫學研究人員設計的 AI 輔助寫作工具，基於 Model Context Protocol (MCP) 構建。它能夠與 VSCode (透過 Copilot 或 Antigravity) 整合，提供從文獻檢索、數據分析、草稿生成到格式化輸出的完整工作流。

## ✨ 主要功能 (Features)

*   **文獻檢索與管理**: 連接 PubMed API 搜尋文獻，並建立本地端文獻庫。
*   **數據分析**: 自動讀取 CSV 數據，執行統計檢定 (T-test, Correlation 等) 並繪製圖表。
*   **智慧草稿生成**: 根據您的研究構想 (`concept.md`) 與分析結果，自動撰寫論文草稿。
*   **自動引用**: 在草稿中自動插入引用標記 `[1]` 並生成參考文獻列表。
*   **互動式修正**: 透過對話微調特定段落的內容與語氣。
*   **Word 匯出**: 支援將 Markdown 草稿與圖表匯出為符合期刊格式的 `.docx` 文件。

## 🚀 安裝與設定 (Installation)

### 前置需求
*   Python 3.10+
*   Git
*   VSCode + GitHub Copilot

### 快速安裝 (推薦)

```bash
git clone https://github.com/u9401066/med-paper-assistant.git
cd med-paper-assistant
./scripts/setup.sh
```

設定完成後，在 VS Code 中按 `Ctrl+Shift+P` → `Developer: Reload Window`

### 手動安裝

1.  **複製專案**
    ```bash
    git clone https://github.com/u9401066/med-paper-assistant.git
    cd med-paper-assistant
    ```

2.  **建立虛擬環境**
    ```bash
    python3 -m venv .venv
    source .venv/bin/activate  # Linux/Mac
    # .venv\Scripts\activate   # Windows
    ```

3.  **安裝依賴**
    ```bash
    pip install -e .
    ```

4.  **配置 VS Code MCP**
    
    在專案根目錄建立 `.vscode/mcp.json`（如果不存在）：
    
    ```json
    {
      "inputs": [],
      "servers": {
        "mdpaper": {
          "command": "/absolute/path/to/med-paper-assistant/.venv/bin/python",
          "args": ["-m", "med_paper_assistant.mcp_server.server"],
          "env": {
            "PYTHONPATH": "/absolute/path/to/med-paper-assistant/src"
          }
        }
      }
    }
    ```

    > ⚠️ **重要設定說明**: 
    > 
    > | 項目 | 說明 |
    > |------|------|
    > | `"mdpaper"` | MCP 伺服器名稱，決定指令前綴為 `/mcp.mdpaper.*` |
    > | `"command"` | **必須使用絕對路徑**，指向虛擬環境的 Python |
    > | `"PYTHONPATH"` | **必須使用絕對路徑**，指向 `src/` 目錄 |
    > 
    > **設定完成後：**
    > 1. 按 `Ctrl+Shift+P` → 輸入 `Developer: Reload Window` 重新載入
    > 2. VS Code 會**自動啟動** MCP 伺服器，無需手動執行
    > 3. 在 Copilot Chat 中輸入 `/mcp` 可查看所有可用的 MCP 指令
    > 4. 使用 `/mcp.mdpaper.concept` 等指令開始使用

    **驗證 MCP 是否正常運作：**
    ```
    在 Copilot Chat 中輸入: /mcp
    應該會看到: mdpaper (16 tools)
    ```

## 📖 使用指南 (Usage Guide)

本助手透過 MCP (Model Context Protocol) 與 GitHub Copilot 整合。在 Copilot Chat 中使用 `/mcp.mdpaper.*` 指令：

### 1. 準備階段
*   將您的原始數據 (CSV) 放入 `data/` 目錄。
*   (選用) 準備您的期刊 Word 範本 (`.docx`)。

### 2. 發展構想 (`/mcp.mdpaper.concept`)
協助您釐清研究思路。
*   **指令**: `/mcp.mdpaper.concept`
*   **功能**: Agent 會引導您填寫 `concept.md`，定義假說、方法、關鍵結果與預期引用的文獻 (PMID)。

### 3. 搜尋策略 (`/mcp.mdpaper.strategy`)
設定文獻搜尋條件。
*   **指令**: `/mcp.mdpaper.strategy`
*   **功能**: 設定搜尋關鍵字、排除條件、文章類型、日期範圍等。

### 4. 資料分析 (`/mcp.mdpaper.analysis`)
自動執行統計與繪圖。
*   **指令**: `/mcp.mdpaper.analysis`
*   **功能**: 
    1. 選擇 `data/` 中的檔案。
    2. 指定分組變數與結果變數。
    3. Agent 執行統計檢定並將圖表存入 `results/figures/`。

### 5. 撰寫草稿 (`/mcp.mdpaper.draft`)
生成論文初稿。
*   **指令**: `/mcp.mdpaper.draft`
*   **功能**: 
    1. 讀取 `concept.md` 與 `results/`。
    2. 詢問是否使用特定範本。
    3. 生成 Markdown 草稿，自動嵌入圖表與引用。

### 6. 內容修正 (`/mcp.mdpaper.clarify`)
微調文章內容。
*   **指令**: `/mcp.mdpaper.clarify`
*   **功能**: 指定要修改的檔案與章節，透過對話方式讓 Agent 進行精確修訂 (例如：「把 Introduction 寫得更保守一點」)。

### 7. 格式匯出 (`/mcp.mdpaper.format`)
產出最終文件。
*   **指令**: `/mcp.mdpaper.format`
*   **功能**: 將 Markdown 草稿與圖片匯出為 `.docx` 檔，並套用您指定的期刊範本格式。

## 📂 專案結構 (Project Structure)

```
.
├── data/                   # 存放原始數據 (CSV)
├── results/                # 存放分析結果 (圖表/表格)
├── drafts/                 # 存放生成的 Markdown 草稿
├── references/             # 本地文獻庫
├── templates/              # 期刊 Word 範本
├── src/
│   └── med_paper_assistant/
│       ├── core/           # 核心邏輯 (Search, Analyzer, Drafter, Exporter, Formatter)
│       ├── mcp_server/     # MCP 伺服器入口
└── .agent/workflows/       # Agent 工作流程定義
```

## 🛠️ 開發與測試

執行測試：
```bash
pytest tests/
```

## 授權 (License)

本專案採用 MIT 授權。
