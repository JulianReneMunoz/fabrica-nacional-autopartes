<#
.SYNOPSIS
  Crea el repositorio en GitHub (cuenta JulianReneMunoz) y publica todo el proyecto.
.DESCRIPTION
  Ejecutar en Windows 11 desde C:\fabrica-nacional-autopartes, después de descomprimir el proyecto.
  1. Verifica Git y GitHub CLI; inicia sesión con 'gh auth login' si hace falta.
  2. Verifica la identidad de Git (user.name y user.email).
  3. Inicializa el repositorio local (rama main) y crea el primer commit.
  4. Crea el repositorio remoto con 'gh repo create' y publica la rama main.
  El archivo .env, .venv, node_modules y la base local data/app.db quedan excluidos por .gitignore.
.EXAMPLE
  .\scripts\publicar_github.ps1                 # repositorio público JulianReneMunoz/fabrica-nacional-autopartes
  .\scripts\publicar_github.ps1 -Privado        # repositorio privado
#>
[CmdletBinding()]
param(
    [string]$Usuario = 'JulianReneMunoz',
    [string]$Repositorio = 'fabrica-nacional-autopartes',
    [switch]$Privado
)
$ErrorActionPreference = 'Continue'   # los errores se controlan con $LASTEXITCODE y throw
$raiz = Split-Path -Parent $PSScriptRoot
Set-Location $raiz

foreach ($herramienta in 'git', 'gh') {
    if (-not (Get-Command $herramienta -ErrorAction SilentlyContinue)) {
        throw "No se encontró '$herramienta'. Instalar con: winget install --id Git.Git -e ; winget install --id GitHub.cli -e"
    }
}

Write-Host '1/5 Autenticación en GitHub'
gh auth status 2>$null
if ($LASTEXITCODE -ne 0) {
    gh auth login --hostname github.com --git-protocol https --web
    if ($LASTEXITCODE -ne 0) { throw 'No fue posible iniciar sesión en GitHub.' }
}
$cuenta = (gh api user --jq .login).Trim()
if ($cuenta -ne $Usuario) {
    throw "La sesión de gh corresponde a '$cuenta', no a '$Usuario'. Ejecutar 'gh auth logout' y repetir."
}

Write-Host '2/5 Identidad de Git'
if (-not (git config user.name)) { git config --global user.name (Read-Host 'Nombre para los commits') }
if (-not (git config user.email)) { git config --global user.email (Read-Host 'Correo para los commits') }

Write-Host '3/5 Repositorio local'
if (-not (Test-Path '.git')) { git init -b main | Out-Null }
if (Test-Path '.env') {
    git check-ignore -q .env
    if ($LASTEXITCODE -ne 0) { throw '.env no está excluido por .gitignore: revisar antes de publicar.' }
}

Write-Host '4/5 Commit del proyecto'
git add -A
git diff --cached --quiet
if ($LASTEXITCODE -ne 0) {
    git commit -m "feat: Fábrica Nacional de Autopartes v2.0 (scraping, base de conocimiento, Q&A, simulador 3D)" | Out-Null
} else { Write-Host '   Sin cambios pendientes.' }

Write-Host '5/5 Publicación en GitHub'
$remoto = git remote 2>$null
if ($remoto -notcontains 'origin') {
    $visibilidad = if ($Privado) { '--private' } else { '--public' }
    gh repo create "$Usuario/$Repositorio" $visibilidad --source . --remote origin --push `
        --description 'Base de conocimiento semántico, sistema Q&A y simulador 3D — Fábrica Nacional de Autopartes'
} else {
    git push -u origin main
}
if ($LASTEXITCODE -ne 0) { throw 'La publicación falló.' }
Write-Host "Repositorio publicado: https://github.com/$Usuario/$Repositorio"
Write-Host 'Siguiente paso: .\scripts\ejecutar_pipeline.ps1 -Publicar  (scraping real + evidencias en GitHub)'
