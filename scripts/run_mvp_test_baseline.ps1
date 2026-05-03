#Requires -Version 5.1
<#
.SYNOPSIS
  Tier A MVP baseline: HTTP smoke + focused pytest slices.

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run_mvp_test_baseline.ps1
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run_mvp_test_baseline.ps1 -SkipHttpSmoke
#>
param(
    [switch]$SkipHttpSmoke
)
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $root

function Invoke-Step {
    param([string]$Title, [scriptblock]$Action)
    Write-Host ""
    Write-Host "=== $Title ===" -ForegroundColor Yellow
    & $Action
    $code = $LASTEXITCODE
    if ($null -ne $code -and $code -ne 0) {
        throw "Step failed: $Title (exit $code)"
    }
}

if (-not $SkipHttpSmoke) {
    # Use nested powershell -File so $LASTEXITCODE is set (calling .ps1 with & does not always propagate).
    Invoke-Step "A1: HTTP smoke (tab + admin)" {
        $smoke = Join-Path $root "scripts\mvp_smoke.ps1"
        & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $smoke
    }
} else {
    Write-Host "Skipping A1 HTTP smoke (-SkipHttpSmoke)." -ForegroundColor DarkYellow
}

Invoke-Step "A2: tab_server tests" {
    python -m pytest focus_guard/core/browser_v2/tab_server/tests -q
}

Invoke-Step "A3: admin_gateway service tests (package-local)" {
    python -m pytest focus_guard/core/admin_gateway/tests -q
}

Invoke-Step "A4: reporting + override regressions" {
    python -m pytest focus_guard/tests/core/test_reporting_and_override_regressions.py -q
}

Invoke-Step "A5: admin_gateway tests (tests/core tree, legacy overlap slice)" {
    python -m pytest `
        focus_guard/tests/core/admin_gateway/test_dashboard_service.py `
        focus_guard/tests/core/admin_gateway/test_devices_service.py -q
}

Write-Host ""
Write-Host "MVP baseline test run completed successfully." -ForegroundColor Green
