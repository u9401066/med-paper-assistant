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

# 2. Initialize pinned submodules
Write-Host "Initializing pinned Git submodules..." -ForegroundColor Yellow
git submodule update --init --recursive
Write-Host "  Submodules initialized" -ForegroundColor Green

# 3. Create virtual environment and install dependencies
Write-Host "Setting up environment with uv..." -ForegroundColor Yellow
Set-Location $ProjectDir
uv sync --all-extras
Write-Host "  Environment ready" -ForegroundColor Green

# 4. Create .vscode/mcp.json if not exists
$vscodeDir = Join-Path $ProjectDir ".vscode"
$mcpJsonPath = Join-Path $vscodeDir "mcp.json"
New-Item -ItemType Directory -Path $vscodeDir -Force | Out-Null

if (Test-Path $mcpJsonPath) {
        Write-Host "mcp.json exists - checking the pinned MCP SDK2 contract..." -ForegroundColor Yellow
        $migrationResult = uv run python "$ScriptDir\migrate_mcp_json.py" $mcpJsonPath 2>&1
        $migrationStatus = $LASTEXITCODE
        Write-Host $migrationResult
        if ($migrationStatus -gt 1) {
            throw "mcp.json migration failed with exit code $migrationStatus"
        }
} else {
        Write-Host "Creating .vscode/mcp.json from mcp-integration-lock.json..." -ForegroundColor Yellow
        $creationResult = uv run python "$ScriptDir\migrate_mcp_json.py" --create $mcpJsonPath 2>&1
        $creationStatus = $LASTEXITCODE
        Write-Host $creationResult
        if ($creationStatus -ne 0) {
            throw "mcp.json creation failed with exit code $creationStatus"
        }
        Write-Host "  mcp.json created with pinned MCP SDK2 runtimes" -ForegroundColor Green
}

# 5. Verify installation
Write-Host "Verifying installation..." -ForegroundColor Yellow
$verifyMedPaper = uv run python -c "from med_paper_assistant.interfaces.mcp.server import create_server; create_server(); print('  MedPaper MCP server loaded')"
Write-Host $verifyMedPaper -ForegroundColor Green
$verifyCgu = uv run --directory integrations/cgu python -c "import cgu; print('  CGU import OK')"
Write-Host $verifyCgu -ForegroundColor Green

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
Write-Host "Notes:" -ForegroundColor White
Write-Host "  - Setup uses pinned submodule commits from this repository for reproducible installs." -ForegroundColor Gray
Write-Host "  - To update submodules intentionally, run: git submodule update --remote --merge" -ForegroundColor Gray
Write-Host "  - External Python MCP integrations are locked to SDK2 commits in mcp-integration-lock.json." -ForegroundColor Gray
Write-Host ""
