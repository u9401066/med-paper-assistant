# Med Paper Assistant - Windows Setup Script (PowerShell)
# Usage: .\scripts\setup.ps1

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectDir = Split-Path -Parent $ScriptDir

Write-Host "Med Paper Assistant Setup..." -ForegroundColor Cyan

# 1. Check uv
Write-Host "Checking uv..." -ForegroundColor Yellow
try {
    $uvVersion = uv --version 2>&1
    Write-Host "  Found $uvVersion" -ForegroundColor Green
} catch {
    Write-Host "ERROR: uv not found. Please install uv" -ForegroundColor Red
    Write-Host "  Install: powershell -c ""irm https://astral.sh/uv/install.ps1 | iex""" -ForegroundColor Yellow
    exit 1
}

# 2. Update submodules
Write-Host "Updating Git submodules..." -ForegroundColor Yellow
git submodule update --init --recursive --remote
Write-Host "  Submodules updated" -ForegroundColor Green

# 3. Create virtual environment and install dependencies
Write-Host "Setting up environment with uv..." -ForegroundColor Yellow
Set-Location $ProjectDir
uv sync --all-extras
Write-Host "  Environment ready" -ForegroundColor Green

# 4. Activate virtual environment
Write-Host "Activating virtual environment..." -ForegroundColor Yellow
& "$ProjectDir\.venv\Scripts\Activate.ps1"

# 5. Verify installation
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
