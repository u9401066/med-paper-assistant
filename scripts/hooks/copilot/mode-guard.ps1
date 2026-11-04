# Fail-open PreToolUse launcher for scripts/copilot_hook_guard.py (Windows).
# Never use `uv run` here: it can re-resolve uv.lock or block on locked .venv
# files, which turns every hook invocation into an error and blocks all tools.
$ErrorActionPreference = 'Stop'
$stdin = [Console]::In.ReadToEnd()
try {
    $root = Resolve-Path (Join-Path $PSScriptRoot '..\..\..')
    $script = Join-Path $root 'scripts\copilot_hook_guard.py'
    $candidates = @(
        (Join-Path $root '.venv\Scripts\python.exe'),
        'py',
        'python'
    )
    foreach ($candidate in $candidates) {
        if (-not (Get-Command $candidate -ErrorAction SilentlyContinue)) { continue }
        $output = $stdin | & $candidate $script 2>$null
        if ($LASTEXITCODE -eq 0 -and $output) {
            Write-Output ($output -join "`n")
            exit 0
        }
    }
} catch {
    # fall through to fail-open
}
Write-Output '{"continue": true}'
exit 0
