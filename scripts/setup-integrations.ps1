# Setup script for med-paper-assistant integrations on Windows.

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
$DrawioForkDir = Join-Path $ProjectRoot "integrations/next-ai-draw-io/mcp-server"
$DrawioWorkspaceDir = Join-Path $ProjectRoot "integrations/drawio-mcp"
$McpJson = Join-Path $ProjectRoot ".vscode/mcp.json"

Write-Host "🔧 Setting up med-paper-assistant integrations..." -ForegroundColor Cyan
Write-Host ""

if (-not (Get-Command uvx -ErrorAction SilentlyContinue)) {
    Write-Host "❌ uvx is not available. Please install uv first:" -ForegroundColor Red
    Write-Host "   powershell -ExecutionPolicy ByPass -c \"irm https://astral.sh/uv/install.ps1 | iex\""
    exit 1
}

Write-Host "✅ uvx is available" -ForegroundColor Green

if (Test-Path (Join-Path $DrawioForkDir "src/drawio_mcp_server")) {
    Write-Host "✅ forked Draw.io MCP detected at integrations/next-ai-draw-io/mcp-server" -ForegroundColor Green
} elseif (Test-Path (Join-Path $DrawioWorkspaceDir "src/index.js")) {
    Write-Host "✅ workspace Draw.io MCP detected at integrations/drawio-mcp" -ForegroundColor Green
} elseif (Get-Command drawio-mcp -ErrorAction SilentlyContinue) {
    Write-Host "✅ drawio-mcp binary is available" -ForegroundColor Green
} elseif (Get-Command npx -ErrorAction SilentlyContinue) {
    Write-Host "✅ npx is available for official Draw.io MCP startup" -ForegroundColor Green
} else {
    Write-Host "⚠️  Draw.io MCP requires either a drawio-mcp binary or npx (Node.js/npm)." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor DarkCyan
Write-Host "📊 Verifying Draw.io MCP Server..." -ForegroundColor Cyan
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor DarkCyan
Write-Host "  Draw.io MCP prefers your forked submodule at integrations/next-ai-draw-io/mcp-server when present."
Write-Host "  Otherwise it falls back to an official checkout, installed drawio-mcp binary, or npm package @drawio/mcp."
Write-Host ""

if ((Test-Path $McpJson) -and (Select-String -Path $McpJson -Pattern '"drawio"' -Quiet)) {
    Write-Host "✅ drawio server already configured in .vscode/mcp.json" -ForegroundColor Green
} else {
    Write-Host "⚠️  drawio server not found in .vscode/mcp.json" -ForegroundColor Yellow
    Write-Host "   Add it manually or check the project documentation."
}

Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor DarkCyan
Write-Host "✅ Integration check complete!" -ForegroundColor Green
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor DarkCyan
Write-Host ""
Write-Host "📋 Available integrations:" -ForegroundColor White
Write-Host "  🎨 drawio     — CONSORT/PRISMA flowcharts (forked submodule → official checkout → package fallback)" -ForegroundColor Gray
Write-Host "  📖 zotero     — Zotero reference import (via uvx)" -ForegroundColor Gray
Write-Host ""
Write-Host "💡 Verify Draw.io MCP availability:" -ForegroundColor White
Write-Host "   .\scripts\start-drawio.ps1" -ForegroundColor Gray
