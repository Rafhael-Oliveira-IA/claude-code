# start-proxy.ps1 — inicia o proxy Bun (Anthropic→OpenAI)
# Cole sua chave OpenAI quando pedido.
#
# Não precisa de Python nem LiteLLM — usa Bun direto.

param(
    [string]$Key = ""
)

$env:PATH = "C:\Users\rafha\.bun\bin;" + $env:PATH

if ($Key) {
    $env:OPENAI_API_KEY = $Key.Trim()
}

if (-not $env:OPENAI_API_KEY) {
    $k = Read-Host "Cole sua chave OpenAI (sk-proj-...)"
    $env:OPENAI_API_KEY = $k.Trim()
}

if (-not $env:OPENAI_API_KEY) {
    Write-Error "OPENAI_API_KEY não definida."
    exit 1
}

Write-Host ""
Write-Host "Iniciando proxy Anthropic→OpenAI..." -ForegroundColor Cyan
Write-Host "  Porta: 4000" -ForegroundColor Green
Write-Host ""
Write-Host "Deixe este terminal aberto e abra outro para rodar .\run.ps1" -ForegroundColor Yellow
Write-Host ""

bun run "$PSScriptRoot\proxy.js"
