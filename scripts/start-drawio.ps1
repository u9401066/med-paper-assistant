# Verify Draw.io MCP availability for diagram generation on Windows.

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
$DrawioForkDir = Join-Path $ProjectRoot "integrations/next-ai-draw-io/mcp-server"
$DrawioForkEntry = Join-Path $DrawioForkDir "src/drawio_mcp_server"
$DrawioPackageSource = "https://github.com/u9401066/next-ai-draw-io/archive/83e35303208766750ff04f2f3637c3b83fce0d0b.tar.gz#subdirectory=mcp-server"

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

if (-not (Get-Command uvx -ErrorAction SilentlyContinue)) {
    Write-Host "❌ uvx is not available. Install uv to run the pinned Draw.io SDK2 snapshot." -ForegroundColor Red
    exit 1
}

if (Test-BackgroundCommand -FilePath "uvx" -ArgumentList @("--python", "3.12", "--from", $DrawioPackageSource, "drawio-mcp-server", "--help")) {
    Write-Host "✅ Pinned Draw.io MCP 2.0.0 / SDK2 is available via uvx" -ForegroundColor Green
    Write-Host "   Commit: 83e35303208766750ff04f2f3637c3b83fce0d0b"
    exit 0
}

Write-Host "❌ Failed to launch the pinned Draw.io SDK2 snapshot" -ForegroundColor Red
exit 1
