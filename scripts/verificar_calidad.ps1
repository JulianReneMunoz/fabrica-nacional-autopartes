<# Ejecuta la misma batería que la integración continua y guarda evidencias en docs/evidencias.
   Cada paso se valida por su código de salida: el ruido que algunas herramientas escriben en stderr
   (p. ej. el cierre de la base embebida tras pytest) no cuenta como fallo, y cualquier paso con código
   distinto de cero hace que el script termine con código 1 (antes de un commit). #>
param([switch]$ConE2E)
$ErrorActionPreference = 'Continue'
$raiz = Split-Path -Parent $PSScriptRoot
Set-Location $raiz
$sello = Get-Date -Format 'yyyyMMdd-HHmmss'
$salida = "docs/evidencias/calidad_$sello.txt"
$script:fallos = @()

function Paso([string]$nombre, [scriptblock]$comando) {
    & $comando
    if ($LASTEXITCODE -ne 0) {
        $script:fallos += $nombre
        Write-Host "FALLO en '$nombre' (código $LASTEXITCODE)"
    }
}

& {
    Paso 'ruff check' { uv run ruff check . }
    Paso 'ruff format' { uv run ruff format --check . }
    Paso 'mypy' { uv run mypy }
    Paso 'capas' { uv run python scripts/verificar_capas.py }
    Paso 'pytest' { uv run pytest -q --cov --cov-report=term }
    if (Get-Command npm -ErrorAction SilentlyContinue) {
        Push-Location web
        Paso 'npm ci' { npm ci --no-audit --no-fund }
        Paso 'typecheck' { npm run typecheck }
        Paso 'vitest' { npm test }
        Paso 'build' { npm run build }
        # Proyecto funcional (el proyecto «recorrido» graba MP4 versionados y no es una verificación).
        if ($ConE2E) { Paso 'playwright' { npx playwright test --project=funcional } }   # inicia la API con uvicorn si no está activa
        Pop-Location
    } else {
        Write-Warning "Node.js no está instalado: se omiten las pruebas del visor web."
    }
} *>&1 | Tee-Object -FilePath $salida
Write-Host "Evidencia guardada en $salida"
if ($script:fallos.Count -gt 0) {
    Write-Host ("Pasos con fallos: " + ($script:fallos -join ', '))
    exit 1
}
Write-Host "Todos los pasos pasaron."
