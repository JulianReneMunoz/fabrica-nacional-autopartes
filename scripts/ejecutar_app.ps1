<# Inicia la interfaz Streamlit en http://localhost:8501 #>
$raiz = Split-Path -Parent $PSScriptRoot
Set-Location $raiz
uv run streamlit run frontend/app.py
