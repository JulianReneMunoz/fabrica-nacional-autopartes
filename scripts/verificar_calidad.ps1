<# Ejecuta la misma batería que la integración continua y guarda evidencias en docs/evidencias #>
param([switch]$ConE2E)
$ErrorActionPreference = 'Stop'
$raiz = Split-Path -Parent $PSScriptRoot
Set-Location $raiz
$sello = Get-Date -Format 'yyyyMMdd-HHmmss'
$salida = "docs/evidencias/calidad_$sello.txt"
& {
    uv run ruff check .
    uv run ruff format --check .
    uv run mypy
    uv run python scripts/verificar_capas.py
    uv run pytest -q --cov --cov-report=term
    if (Get-Command npm -ErrorAction SilentlyContinue) {
        Push-Location web
        npm ci --no-audit --no-fund
        npm run typecheck
        npm test
        npm run build
        if ($ConE2E) { npx playwright test }   # requiere la API activa o la inicia con uvicorn
        Pop-Location
    } else {
        Write-Warning "Node.js no está instalado: se omiten las pruebas del visor web."
    }
} *>&1 | Tee-Object -FilePath $salida
Write-Host "Evidencia guardada en $salida"
