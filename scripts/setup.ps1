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
        Write-Host "mcp.json exists - checking for missing servers..." -ForegroundColor Yellow
        $migrationResult = uv run python "$ScriptDir\migrate_mcp_json.py" $mcpJsonPath 2>&1
        Write-Host $migrationResult
} else {
        Write-Host "Creating .vscode/mcp.json (cross-platform)..." -ForegroundColor Yellow
        @'
{
    "inputs": [],
    "servers": {
        "mdpaper": {
            "type": "stdio",
            "command": "uv",
            "args": ["run", "--directory", "${workspaceFolder}", "python", "-m", "med_paper_assistant.interfaces.mcp"],
            "env": {
                "PYTHONPATH": "${workspaceFolder}/src",
                "MEDPAPER_TOOL_SURFACE": "compact"
            }
        },
        "pubmed-search": {
            "type": "stdio",
            "command": "uvx",
            "args": ["pubmed-search-mcp"],
            "env": {
                "ENTREZ_EMAIL": "medpaper@example.com"
            }
        },
        "cgu": {
            "type": "stdio",
            "command": "uv",
            "args": ["run", "--directory", "${workspaceFolder}/integrations/cgu", "python", "-m", "cgu.server"],
            "env": {
                "CGU_THINKING_ENGINE": "simple"
            }
        },
        "zotero-keeper": {
            "type": "stdio",
            "command": "uvx",
            "args": ["zotero-keeper"]
        },
        "asset-aware": {
            "type": "stdio",
            "command": "uv",
            "args": ["run", "--directory", "${workspaceFolder}/integrations/asset-aware-mcp", "asset-aware-mcp"]
        },
        "drawio": {
            "type": "stdio",
            "command": "npx",
            "args": ["-y", "@drawio/mcp"]
        }
    }
}
'@ | Set-Content -Path $mcpJsonPath -Encoding UTF8
        Write-Host "  mcp.json created" -ForegroundColor Green
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
Write-Host "  - Draw.io requires Node.js/npm for the npx fallback." -ForegroundColor Gray
Write-Host ""
