#!/bin/bash
# Med Paper Assistant - 自動設定腳本
# 使用方式: ./scripts/setup.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "🚀 Med Paper Assistant 設定中..."

# 1. 創建虛擬環境
echo "📦 創建 Python 虛擬環境..."
cd "$PROJECT_DIR"
python3 -m venv .venv
source .venv/bin/activate

# 2. 安裝依賴
echo "📥 安裝依賴套件..."
pip install -q --upgrade pip
pip install -q -e .

# 3. 創建 .vscode/mcp.json（使用相對路徑）
echo "⚙️  配置 VS Code MCP..."
mkdir -p .vscode

cat > .vscode/mcp.json << EOF
{
  "inputs": [],
  "servers": {
    "mdpaper": {
      "command": "${PROJECT_DIR}/.venv/bin/python",
      "args": ["-m", "med_paper_assistant.interfaces.mcp.server"],
      "env": {
        "PYTHONPATH": "${PROJECT_DIR}/src"
      }
    }
  }
}
EOF

# 4. 驗證安裝
echo "✅ 驗證安裝..."
python -c "from med_paper_assistant.interfaces.mcp.server import mcp; print(f'  MCP Server 載入成功: {len(mcp._tool_manager._tools)} 個工具, {len(mcp._prompt_manager._prompts)} 個 prompts')"

echo ""
echo "=========================================="
echo "✅ 設定完成！"
echo "=========================================="
echo ""
echo "📋 下一步:"
echo "  1. 在 VS Code 中按 Ctrl+Shift+P"
echo "  2. 輸入 'Developer: Reload Window'"
echo "  3. 在 Copilot Chat 中輸入 / 即可看到 mdpaper 指令"
echo ""
echo "🔧 可用指令:"
echo "  /mdpaper.project  - 設定研究專案"
echo "  /mdpaper.concept  - 發展研究概念"
echo "  /mdpaper.strategy - 配置搜尋策略"
echo "  /mdpaper.draft    - 撰寫論文草稿"
echo "  /mdpaper.analysis - 資料分析"
echo "  /mdpaper.clarify  - 改進內容"
echo "  /mdpaper.format   - 導出 Word"
echo ""
