<#
.SYNOPSIS
  Prepara el repositorio tras clonarlo: entorno uv, .env, base de conocimiento, pruebas y visor 3D.
.EXAMPLE
  .\scripts\preparar_proyecto.ps1            # usa el corpus semilla
  .\scripts\preparar_proyecto.ps1 -Scraping  # ejecuta el pipeline real (scraping → gráficas)
#>
[CmdletBinding()]
param([switch]$Scraping, [string]$Modelo = 'llama3.2:3b')

$ErrorActionPreference = 'Stop'
$raiz = Split-Path -Parent $PSScriptRoot
Set-Location $raiz

Write-Host '1/7 uv sync (entorno reproducible desde uv.lock)'
uv sync
if ($LASTEXITCODE -ne 0) { throw 'uv sync falló' }

if (-not (Test-Path '.env')) {
    Write-Host '2/7 Creando .env desde .env.example'
    Copy-Item '.env.example' '.env'
} else { Write-Host '2/7 .env existente: se conserva' }

if ($Scraping) {
    Write-Host '3/7 Scraping de autopartesfanalca.com.co y fanalca.com (pipeline completo)'
    Write-Host '4/7 Silver/Gold, validación y gráficas por etapa (incluidos en el pipeline)'
    uv run fabrica pipeline
    if ($LASTEXITCODE -ne 0) { throw 'El pipeline falló: revisar data/bronze/errores.jsonl' }
} else {
    Write-Host '3/7 Scraping omitido (usar -Scraping o .\scripts\ejecutar_pipeline.ps1)'
    Write-Host '4/7 Construcción Silver/Gold con la base de demostración'
    uv run fabrica build --fuente auto
    uv run fabrica validate
    if ($LASTEXITCODE -ne 0) { throw 'La validación del corpus falló' }
}

Write-Host '5/7 Pruebas automatizadas'
uv run pytest -q
if ($LASTEXITCODE -ne 0) { throw 'Hay pruebas fallidas' }

if (Get-Command ollama -ErrorAction SilentlyContinue) {
    Write-Host "6/7 Descargando modelo $Modelo en Ollama"
    ollama pull $Modelo
} else { Write-Host '6/7 Ollama no encontrado: omitido' }

if (Get-Command npm -ErrorAction SilentlyContinue) {
    Write-Host '7/7 Visor 3D: npm ci y compilación (web/dist, servido por la API en /app)'
    Push-Location web
    npm ci --no-audit --no-fund
    npm run build
    Pop-Location
} else { Write-Host '7/7 Node.js no encontrado: visor 3D omitido' }

Write-Host 'Listo. Interfaz: .\scripts\ejecutar_app.ps1 · API y visor: .\scripts\ejecutar_api.ps1 → http://127.0.0.1:8000/app/'
