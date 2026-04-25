# run.ps1 - Claude Code launcher with provider switching
#
# Usage:
#   .\run.ps1                       # use active provider
#   .\run.ps1 -Provider openai      # switch to OpenAI (via proxy)
#   .\run.ps1 -Provider local       # switch to local LLM
#   .\run.ps1 proxy                 # start OpenAI proxy (keep terminal open)
#   .\run.ps1 proxy -Key sk-proj-.. # start proxy with key
#   .\run.ps1 status                # show active provider

param(
    [Parameter(Position = 0)]
    [string]$Command = "",
    [string]$Provider = "",
    [string]$Key = ""
)

$Root         = $PSScriptRoot
$EnvActive    = Join-Path $Root ".env.local"
$ProvidersDir = Join-Path $Root "providers"
$env:PATH     = "C:\Users\rafha\.bun\bin;" + $env:PATH

function Load-Env([string]$file) {
    if (-not (Test-Path $file)) { return }
    Get-Content $file | Where-Object { $_ -match '^\s*[A-Za-z_][^=]*=.+' } | ForEach-Object {
        $parts = $_ -split '=', 2
        $name  = $parts[0].Trim()
        $value = $parts[1].Trim()
        [System.Environment]::SetEnvironmentVariable($name, $value, 'Process')
    }
}

function Show-Status {
    Load-Env $EnvActive
    $prov = if (Test-Path (Join-Path $Root ".active-provider")) { Get-Content (Join-Path $Root ".active-provider") } else { "unknown" }
    Write-Host ""
    Write-Host "  Provider : $prov"         -ForegroundColor Cyan
    Write-Host "  URL      : $env:ANTHROPIC_BASE_URL" -ForegroundColor Green
    Write-Host "  Model    : $env:ANTHROPIC_MODEL"    -ForegroundColor Green
    Write-Host "  Fast mdl : $env:ANTHROPIC_SMALL_FAST_MODEL" -ForegroundColor Green
    Write-Host ""
}

function Switch-Provider([string]$name) {
    $src = Join-Path $ProvidersDir "$name.env"
    if (-not (Test-Path $src)) {
        $avail = (Get-ChildItem $ProvidersDir -Filter "*.env" | ForEach-Object { $_.BaseName }) -join ", "
        Write-Error "Provider '$name' not found. Available: $avail"
        exit 1
    }
    Copy-Item $src $EnvActive -Force
    Set-Content (Join-Path $Root ".active-provider") $name
    Write-Host "  Switched to: $name" -ForegroundColor Cyan
}

function Start-Proxy([string]$key) {
    if ($key) { $env:OPENAI_API_KEY = $key.Trim() }
    if (-not $env:OPENAI_API_KEY) {
        $k = Read-Host "  OpenAI API key (sk-proj-...)"
        $env:OPENAI_API_KEY = $k.Trim()
    }
    if (-not $env:OPENAI_API_KEY) { Write-Error "OPENAI_API_KEY not set."; exit 1 }
    Write-Host ""
    Write-Host "  Proxy Anthropic->OpenAI on :4000" -ForegroundColor Cyan
    Write-Host "  Keep this terminal open, then run .\run.ps1 in another." -ForegroundColor Yellow
    Write-Host ""
    bun run (Join-Path $Root "proxy.js")
}

# --- main ---

if ($Command -eq "proxy")  { Start-Proxy $Key; return }
if ($Command -eq "status") { Show-Status; return }

if ($Provider) { Switch-Provider $Provider }

if (-not (Test-Path $EnvActive)) {
    Write-Host "  No active provider - defaulting to openai" -ForegroundColor Yellow
    Switch-Provider "openai"
}

Load-Env $EnvActive

$prov = if (Test-Path (Join-Path $Root ".active-provider")) { Get-Content (Join-Path $Root ".active-provider") } else { "custom" }

Write-Host ""
Write-Host "  Claude Code  provider=$prov  model=$env:ANTHROPIC_MODEL  url=$env:ANTHROPIC_BASE_URL" -ForegroundColor DarkGray
Write-Host ""

if (-not (Get-Command bun -ErrorAction SilentlyContinue)) {
    Write-Error "Bun not found. Install at: https://bun.sh"
    exit 1
}

$extraArgs = if ($Command -and $Command -ne "") { @($Command) + $args } else { $args }
bun run --preload "$Root\preload.js" "$Root\src\entrypoints\cli.tsx" @extraArgs