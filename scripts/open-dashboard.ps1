# MedPaper Dashboard Launcher for VS Code
# Usage: Run this script to start dashboard and open in VS Code Simple Browser

param(
    [int]$Port = 3000,
    [switch]$SkipBrowser
)

$ErrorActionPreference = "Stop"
$DashboardPath = Join-Path $PSScriptRoot "..\dashboard"

Write-Host "🚀 Starting MedPaper Dashboard..." -ForegroundColor Cyan

# Check if port is already in use
$portInUse = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue
if ($portInUse) {
    Write-Host "✅ Dashboard already running on port $Port" -ForegroundColor Green
} else {
    # Start dashboard in background
    Write-Host "📦 Starting Next.js development server..." -ForegroundColor Yellow
    
    $job = Start-Job -ScriptBlock {
        param($path)
        Set-Location $path
        npm run dev
    } -ArgumentList $DashboardPath
    
    # Wait for server to be ready
    Write-Host "⏳ Waiting for server to be ready..." -ForegroundColor Yellow
    $maxAttempts = 30
    $attempt = 0
    
    while ($attempt -lt $maxAttempts) {
        try {
            $response = Invoke-WebRequest -Uri "http://localhost:$Port" -TimeoutSec 1 -ErrorAction SilentlyContinue
            if ($response.StatusCode -eq 200) {
                break
            }
        } catch {
            # Server not ready yet
        }
        Start-Sleep -Seconds 1
        $attempt++
        Write-Host "." -NoNewline
    }
    Write-Host ""
    
    if ($attempt -ge $maxAttempts) {
        Write-Host "❌ Server failed to start within 30 seconds" -ForegroundColor Red
        exit 1
    }
    
    Write-Host "✅ Dashboard server started!" -ForegroundColor Green
}

# Open in VS Code Simple Browser
if (-not $SkipBrowser) {
    Write-Host "🌐 Opening in VS Code Simple Browser..." -ForegroundColor Cyan
    
    # Use VS Code CLI to open Simple Browser
    $url = "http://localhost:$Port"
    
    # Try to use VS Code command
    try {
        code --command "simpleBrowser.show" --args "$url"
    } catch {
        Write-Host "💡 Tip: Open VS Code, press Ctrl+Shift+P, type 'Simple Browser: Show' and enter:" -ForegroundColor Yellow
        Write-Host "   $url" -ForegroundColor White
    }
}

Write-Host ""
Write-Host "📊 Dashboard URL: http://localhost:$Port" -ForegroundColor Green
Write-Host "💡 To stop: Close the terminal or run 'Stop-Job *'" -ForegroundColor Gray
