<#
.SYNOPSIS
  Instala en Windows 11 las herramientas base del proyecto mediante winget y los instaladores oficiales.
.DESCRIPTION
  Ejecutar en PowerShell (no requiere administrador salvo Docker Desktop y WSL2):
    Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
    .\scripts\instalar_herramientas.ps1            # herramientas obligatorias
    .\scripts\instalar_herramientas.ps1 -Opcionales # agrega Docker Desktop, MiKTeX y GitHub CLI
  Cada paso es idempotente: si la herramienta existe, se omite.
#>
[CmdletBinding()]
param([switch]$Opcionales)

$ErrorActionPreference = 'Stop'

function Test-Comando([string]$Nombre) { [bool](Get-Command $Nombre -ErrorAction SilentlyContinue) }

function Install-Winget([string]$Id, [string]$Comando) {
    if ($Comando -and (Test-Comando $Comando)) { Write-Host "[omitido] $Id ya disponible ($Comando)"; return }
    Write-Host "[winget] Instalando $Id ..."
    winget install --id $Id --exact --source winget --accept-package-agreements --accept-source-agreements
}

function Update-RutaSesion {
    $env:Path = [Environment]::GetEnvironmentVariable('Path', 'Machine') + ';' +
                [Environment]::GetEnvironmentVariable('Path', 'User')
}

if (-not (Test-Comando 'winget')) { throw 'winget no disponible: instalar "App Installer" desde Microsoft Store.' }

Install-Winget 'Git.Git' 'git'
Install-Winget 'Microsoft.VisualStudioCode' 'code'
Install-Winget 'OpenJS.NodeJS.LTS' 'node'
Install-Winget 'Ollama.Ollama' 'ollama'
Update-RutaSesion

if (-not (Test-Comando 'uv')) {
    Write-Host '[uv] Instalador oficial de Astral'
    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
    Update-RutaSesion
}

if (-not (Test-Comando 'claude')) {
    Write-Host '[Claude Code] Instalador nativo oficial'
    Invoke-RestMethod https://claude.ai/install.ps1 | Invoke-Expression
    Update-RutaSesion
}

if (-not (Test-Comando 'opencode')) {
    Write-Host '[OpenCode] npm install -g opencode-ai'
    npm install -g opencode-ai
    Update-RutaSesion
}

if ($Opcionales) {
    Install-Winget 'GitHub.cli' 'gh'
    Install-Winget 'Docker.DockerDesktop' 'docker'
}

Write-Host ''
Write-Host 'Instalación finalizada. Cerrar y abrir la terminal, luego ejecutar: .\scripts\verificar_entorno.ps1'
