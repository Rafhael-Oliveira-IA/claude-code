# run.ps1 — inicia o Claude Code apontando para o Llama local
# Uso: .\run.ps1 [argumentos do claude]
# Ex:  .\run.ps1
# Ex:  .\run.ps1 "revise meu código"

# Carrega variáveis do .env.local se existir
$envFile = Join-Path $PSScriptRoot ".env.local"
if (Test-Path $envFile) {
    Get-Content $envFile | Where-Object { $_ -match '^\s*[^#]\S+=.+' } | ForEach-Object {
        $parts = $_ -split '=', 2
        $name  = $parts[0].Trim()
        $value = $parts[1].Trim()
        [System.Environment]::SetEnvironmentVariable($name, $value, 'Process')
        Write-Host "  $name=$value" -ForegroundColor DarkGray
    }
    Write-Host ""
}

# Verifica se bun está instalado
if (-not (Get-Command bun -ErrorAction SilentlyContinue)) {
    Write-Error "Bun não encontrado. Instale em: https://bun.sh"
    exit 1
}

Write-Host "Iniciando Claude Code..." -ForegroundColor Cyan
Write-Host "  Base URL : $env:ANTHROPIC_BASE_URL" -ForegroundColor Green
Write-Host "  Modelo   : $env:ANTHROPIC_MODEL" -ForegroundColor Green
Write-Host ""

bun run --preload "$PSScriptRoot\preload.js" "$PSScriptRoot\src\entrypoints\cli.tsx" @args
