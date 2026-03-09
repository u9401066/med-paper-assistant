# Verify Draw.io MCP availability for diagram generation on Windows.

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
$DrawioForkDir = Join-Path $ProjectRoot "integrations/next-ai-draw-io/mcp-server"
$DrawioForkEntry = Join-Path $DrawioForkDir "src/drawio_mcp_server"
$DrawioWorkspaceDir = Join-Path $ProjectRoot "integrations/drawio-mcp"
$DrawioWorkspaceEntry = Join-Path $DrawioWorkspaceDir "src/index.js"

function Test-BackgroundCommand {
    param(
        [Parameter(Mandatory = $true)] [string] $FilePath,
        [string[]] $ArgumentList = @(),
        [string] $WorkingDirectory = $ProjectRoot,
        [int] $WaitSeconds = 8
    )

    $process = Start-Process -FilePath $FilePath -ArgumentList $ArgumentList -WorkingDirectory $WorkingDirectory -PassThru -WindowStyle Hidden
    Start-Sleep -Seconds $WaitSeconds

    if (-not $process.HasExited) {
        Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
        return $true
    }

    return ($process.ExitCode -eq 0)
}

Write-Host "🎨 Verifying Draw.io MCP..." -ForegroundColor Cyan
Write-Host ""

if (Test-Path $DrawioForkEntry) {
    if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
        Write-Host "❌ Found forked Draw.io MCP at $DrawioForkDir, but uv is not available." -ForegroundColor Red
        exit 1
    }

    if (Test-BackgroundCommand -FilePath "uv" -ArgumentList @("run", "--directory", $DrawioForkDir, "python", "-m", "drawio_mcp_server", "--help")) {
        Write-Host "✅ Forked workspace Draw.io MCP is reachable" -ForegroundColor Green
        Write-Host "   MCP command: uv run --directory integrations/next-ai-draw-io/mcp-server python -m drawio_mcp_server"
        exit 0
    }

    Write-Host "❌ Failed to launch forked workspace Draw.io MCP from $DrawioForkDir" -ForegroundColor Red
    exit 1
}

if (Test-Path $DrawioWorkspaceEntry) {
    if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
        Write-Host "❌ Found workspace Draw.io MCP at $DrawioWorkspaceDir, but node is not available." -ForegroundColor Red
        exit 1
    }

    if (Test-BackgroundCommand -FilePath "node" -ArgumentList @($DrawioWorkspaceEntry)) {
        Write-Host "✅ Workspace Draw.io MCP is reachable" -ForegroundColor Green
        Write-Host "   MCP command: node integrations/drawio-mcp/src/index.js"
        exit 0
    }

    Write-Host "❌ Failed to launch workspace Draw.io MCP from $DrawioWorkspaceDir" -ForegroundColor Red
    exit 1
}

if (Get-Command drawio-mcp -ErrorAction SilentlyContinue) {
    Write-Host "✅ drawio-mcp binary is already installed" -ForegroundColor Green
    Write-Host "   MCP command: drawio-mcp"
    exit 0
}

if (-not (Get-Command npx -ErrorAction SilentlyContinue)) {
    Write-Host "❌ npx is not available. Install Node.js/npm first, or install drawio-mcp globally." -ForegroundColor Red
    exit 1
}

if (Test-BackgroundCommand -FilePath "npx" -ArgumentList @("-y", "@drawio/mcp", "--help")) {
    Write-Host "✅ Official Draw.io MCP is available via npx" -ForegroundColor Green
    Write-Host "   MCP command: npx -y @drawio/mcp"
    exit 0
}

Write-Host "❌ Failed to launch @drawio/mcp via npx" -ForegroundColor Red
Write-Host "   Try: npm install -g @drawio/mcp"
exit 1
