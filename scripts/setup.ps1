# Med Paper Assistant - Windows Setup Script (PowerShell)
# Usage: .\scripts\setup.ps1

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectDir = Split-Path -Parent $ScriptDir

Write-Host "Med Paper Assistant Setup..." -ForegroundColor Cyan

# 1. Check Python
Write-Host "Checking Python..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version 2>&1
    Write-Host "  Found $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "ERROR: Python not found. Please install Python 3.10+" -ForegroundColor Red
    Write-Host "  Download: https://www.python.org/downloads/" -ForegroundColor Yellow
    exit 1
}

# 2. Create virtual environment
Write-Host "Creating Python virtual environment..." -ForegroundColor Yellow
Set-Location $ProjectDir

if (Test-Path ".venv") {
    Write-Host "  Virtual environment already exists, skipping creation" -ForegroundColor Gray
} else {
    python -m venv .venv
    Write-Host "  Virtual environment created" -ForegroundColor Green
}

# 3. Activate virtual environment
Write-Host "Activating virtual environment..." -ForegroundColor Yellow
& "$ProjectDir\.venv\Scripts\Activate.ps1"

# 4. Install dependencies
Write-Host "Installing dependencies..." -ForegroundColor Yellow
pip install --upgrade pip --quiet
pip install -e . --quiet
Write-Host "  Dependencies installed" -ForegroundColor Green

# 5. Update .vscode/mcp.json (cross-platform)
Write-Host "Configuring VS Code MCP (cross-platform)..." -ForegroundColor Yellow

if (-not (Test-Path ".vscode")) {
    New-Item -ItemType Directory -Path ".vscode" | Out-Null
}

$mcpConfig = @'
{
  "inputs": [],
  "servers": {
    "mdpaper": {
      "type": "stdio",
      "command": "${workspaceFolder}/.venv/Scripts/python.exe",
      "args": ["-m", "med_paper_assistant.interfaces.mcp"],
      "env": {
        "PYTHONPATH": "${workspaceFolder}/src"
      },
      "platforms": {
        "win32": {
          "command": "${workspaceFolder}/.venv/Scripts/python.exe"
        },
        "linux": {
          "command": "${workspaceFolder}/.venv/bin/python"
        },
        "darwin": {
          "command": "${workspaceFolder}/.venv/bin/python"
        }
      }
    }
  }
}
'@

$mcpConfig | Out-File -FilePath ".vscode\mcp.json" -Encoding UTF8
Write-Host "  mcp.json created (cross-platform)" -ForegroundColor Green

# 6. Verify installation
Write-Host "Verifying installation..." -ForegroundColor Yellow
$verifyResult = python -c "from med_paper_assistant.interfaces.mcp.server import mcp; print(f'  MCP Server loaded: {len(mcp._tool_manager._tools)} tools')"
Write-Host $verifyResult -ForegroundColor Green

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Setup Complete!" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next Steps:" -ForegroundColor White
Write-Host "  1. In VS Code, press Ctrl+Shift+P" -ForegroundColor Gray
Write-Host "  2. Type 'Developer: Reload Window'" -ForegroundColor Gray
Write-Host "  3. In Copilot Chat, type / to see mdpaper commands" -ForegroundColor Gray
Write-Host ""
Write-Host "Available Commands:" -ForegroundColor White
Write-Host "  /mdpaper.project  - Setup research project" -ForegroundColor Gray
Write-Host "  /mdpaper.concept  - Develop research concept" -ForegroundColor Gray
Write-Host "  /mdpaper.strategy - Configure search strategy" -ForegroundColor Gray
Write-Host "  /mdpaper.draft    - Write paper draft" -ForegroundColor Gray
Write-Host "  /mdpaper.analysis - Data analysis" -ForegroundColor Gray
Write-Host "  /mdpaper.clarify  - Improve content" -ForegroundColor Gray
Write-Host "  /mdpaper.format   - Export to Word" -ForegroundColor Gray
Write-Host ""
