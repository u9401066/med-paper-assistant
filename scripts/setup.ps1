# Med Paper Assistant - Windows 自動設定腳本 (PowerShell)
# 使用方式: 在 PowerShell 中執行 .\scripts\setup.ps1

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectDir = Split-Path -Parent $ScriptDir

Write-Host "🚀 Med Paper Assistant 設定中..." -ForegroundColor Cyan

# 1. 檢查 Python
Write-Host "🔍 檢查 Python..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version 2>&1
    Write-Host "   找到 $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ 找不到 Python，請先安裝 Python 3.10+" -ForegroundColor Red
    Write-Host "   下載: https://www.python.org/downloads/" -ForegroundColor Yellow
    exit 1
}

# 2. 創建虛擬環境
Write-Host "📦 創建 Python 虛擬環境..." -ForegroundColor Yellow
Set-Location $ProjectDir

if (Test-Path ".venv") {
    Write-Host "   虛擬環境已存在，跳過創建" -ForegroundColor Gray
} else {
    python -m venv .venv
    Write-Host "   ✅ 虛擬環境已創建" -ForegroundColor Green
}

# 3. 啟動虛擬環境
Write-Host "🔌 啟動虛擬環境..." -ForegroundColor Yellow
& "$ProjectDir\.venv\Scripts\Activate.ps1"

# 4. 安裝依賴
Write-Host "📥 安裝依賴套件..." -ForegroundColor Yellow
pip install --upgrade pip --quiet
pip install -e . --quiet
Write-Host "   ✅ 依賴套件已安裝" -ForegroundColor Green

# 5. 創建 .vscode/mcp.json
Write-Host "⚙️  配置 VS Code MCP..." -ForegroundColor Yellow

if (-not (Test-Path ".vscode")) {
    New-Item -ItemType Directory -Path ".vscode" | Out-Null
}

$mcpConfig = @"
{
  "inputs": [],
  "servers": {
    "mdpaper": {
      "command": "`${workspaceFolder}/.venv/Scripts/python.exe",
      "args": ["-m", "med_paper_assistant.interfaces.mcp.server"],
      "env": {
        "PYTHONPATH": "`${workspaceFolder}/src"
      }
    }
  }
}
"@

$mcpConfig | Out-File -FilePath ".vscode\mcp.json" -Encoding UTF8
Write-Host "   ✅ mcp.json 已創建" -ForegroundColor Green

# 6. 驗證安裝
Write-Host "✅ 驗證安裝..." -ForegroundColor Yellow
$verifyResult = python -c "from med_paper_assistant.interfaces.mcp.server import mcp; print(f'  MCP Server 載入成功: {len(mcp._tool_manager._tools)} 個工具')"
Write-Host $verifyResult -ForegroundColor Green

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "✅ 設定完成！" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "📋 下一步:" -ForegroundColor White
Write-Host "  1. 在 VS Code 中按 Ctrl+Shift+P" -ForegroundColor Gray
Write-Host "  2. 輸入 'Developer: Reload Window'" -ForegroundColor Gray
Write-Host "  3. 在 Copilot Chat 中輸入 / 即可看到 mdpaper 指令" -ForegroundColor Gray
Write-Host ""
Write-Host "🔧 可用指令:" -ForegroundColor White
Write-Host "  /mdpaper.project - 設定研究專案" -ForegroundColor Gray
Write-Host "  /mdpaper.concept - 發展研究概念" -ForegroundColor Gray
Write-Host "  /mdpaper.strategy - 配置搜尋策略" -ForegroundColor Gray
Write-Host "  /mdpaper.draft    - 撰寫論文草稿" -ForegroundColor Gray
Write-Host "  /mdpaper.analysis - 資料分析" -ForegroundColor Gray
Write-Host "  /mdpaper.clarify  - 改進內容" -ForegroundColor Gray
Write-Host "  /mdpaper.format   - 導出 Word" -ForegroundColor Gray
Write-Host ""
