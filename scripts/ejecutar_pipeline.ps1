<#
.SYNOPSIS
  Ejecuta el proceso real de datos: scraping de autopartesfanalca.com.co y fanalca.com → Bronze →
  Silver/Gold → validación → gráficas por etapa. Ejecutar en Windows 11 desde la carpeta del proyecto
  (PowerShell o la terminal de Claude Code). Requiere acceso a Internet.
.DESCRIPTION
  Con -Publicar, al terminar guarda las evidencias (data/bronze, data/silver, data/gold, docs/graficas)
  en un commit y las publica en GitHub (requiere haber ejecutado antes scripts/publicar_github.ps1).
.EXAMPLE
  .\scripts\ejecutar_pipeline.ps1 -MaxPaginas 60
  .\scripts\ejecutar_pipeline.ps1 -MaxPaginas 60 -Publicar
#>
param([int]$MaxPaginas = 60, [switch]$SinSitemap, [switch]$Publicar)
$ErrorActionPreference = 'Stop'
$raiz = Split-Path -Parent $PSScriptRoot
Set-Location $raiz
uv sync
$argumentos = @('run', 'fabrica', 'pipeline', '--max-paginas', "$MaxPaginas")
if ($SinSitemap) { $argumentos += '--sin-sitemap' }
& uv @argumentos
if ($LASTEXITCODE -ne 0) {
    Write-Warning "El pipeline terminó con código $LASTEXITCODE. Revisar data/bronze/errores.jsonl y la conexión."
    exit $LASTEXITCODE
}
uv run fabrica stats
Write-Host "Evidencias: data/bronze/manifiesto.jsonl, data/bronze/resumen_rastreo.json, data/gold/metricas_etapas.json, docs/graficas/*.png"

if ($Publicar) {
    if (-not (Test-Path '.git')) { throw 'Repositorio no inicializado: ejecutar primero .\scripts\publicar_github.ps1' }
    git add data/bronze data/silver data/gold docs/graficas
    git diff --cached --quiet
    if ($LASTEXITCODE -ne 0) {
        $fecha = Get-Date -Format 'yyyy-MM-dd'
        git commit -m "datos: scraping real de autopartesfanalca.com.co y fanalca.com ($fecha)" | Out-Null
        git push
        if ($LASTEXITCODE -ne 0) { throw 'No fue posible publicar las evidencias.' }
        Write-Host 'Evidencias del scraping publicadas en GitHub.'
    } else { Write-Host 'Sin cambios en los datos para publicar.' }
}
