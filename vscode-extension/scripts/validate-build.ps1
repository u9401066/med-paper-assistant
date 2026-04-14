$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ValidateScript = Join-Path $ScriptDir "validate-build.cjs"

& node $ValidateScript @args
exit $LASTEXITCODE
