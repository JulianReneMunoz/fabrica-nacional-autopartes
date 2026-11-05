<# Inicia la API FastAPI en http://127.0.0.1:8000 (Swagger en /docs) #>
param([int]$Puerto = 8000)
$raiz = Split-Path -Parent $PSScriptRoot
Set-Location $raiz
uv run uvicorn fabrica_autopartes.api.main:app --reload --reload-dir src --host 127.0.0.1 --port $Puerto
