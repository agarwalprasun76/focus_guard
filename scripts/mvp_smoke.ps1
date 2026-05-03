#Requires -Version 5.1
<#
.SYNOPSIS
  Minimal MVP smoke: tab server + admin gateway HTTP probes (non-destructive).

.EXAMPLE
  pwsh -File scripts/mvp_smoke.ps1
  pwsh -File scripts/mvp_smoke.ps1 -TabBase "http://127.0.0.1:58392" -AdminBase "http://127.0.0.1:58393"
#>
param(
    [string]$TabBase = "http://127.0.0.1:58392",
    [string]$AdminBase = "http://127.0.0.1:58393"
)

$ErrorActionPreference = "Stop"

function Join-Url {
    param([string]$Base, [string]$Path)
    $b = $Base.TrimEnd("/")
    $p = $Path.TrimStart("/")
    return "$b/$p"
}

function Test-GetJson {
    param([string]$Name, [string]$Uri)
    Write-Host "==> $Name" -ForegroundColor Cyan
    Write-Host "    GET $Uri"
    try {
        $r = Invoke-WebRequest -Uri $Uri -UseBasicParsing -TimeoutSec 8
        if ($r.StatusCode -lt 200 -or $r.StatusCode -ge 300) {
            throw "HTTP $($r.StatusCode)"
        }
        $snippet = if ($r.Content.Length -gt 240) { $r.Content.Substring(0, 240) + "..." } else { $r.Content }
        Write-Host "    OK ($($r.StatusCode)) body: $snippet" -ForegroundColor Green
    } catch {
        Write-Host "    FAIL: $_" -ForegroundColor Red
        throw
    }
}

Write-Host "Focus Guard MVP smoke (read-only GETs)" -ForegroundColor Yellow
Write-Host ""

Test-GetJson "Tab server health" (Join-Url $TabBase "/api/health")
Test-GetJson "Tab server auth status" (Join-Url $TabBase "/api/auth/status")

# Admin gateway: health and meta are common patterns in this repo
Test-GetJson "Admin gateway health" (Join-Url $AdminBase "/admin/health")
Test-GetJson "Admin gateway meta" (Join-Url $AdminBase "/admin/api/v1/meta")

Write-Host ""
Write-Host "All MVP smoke probes passed." -ForegroundColor Green
