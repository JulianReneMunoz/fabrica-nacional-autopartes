<#
.SYNOPSIS
  Verifica herramientas y versiones requeridas. Devuelve código 1 si falta alguna obligatoria.
.EXAMPLE
  .\scripts\verificar_entorno.ps1
#>
[CmdletBinding()]
param()

$herramientas = @(
    @{ Nombre = 'git';      Args = @('--version'); Obligatoria = $true  },
    @{ Nombre = 'uv';       Args = @('--version'); Obligatoria = $true  },
    @{ Nombre = 'node';     Args = @('--version'); Obligatoria = $true  },
    @{ Nombre = 'ollama';   Args = @('--version'); Obligatoria = $true  },
    @{ Nombre = 'code';     Args = @('--version'); Obligatoria = $false },
    @{ Nombre = 'opencode'; Args = @('--version'); Obligatoria = $false },
    @{ Nombre = 'claude';   Args = @('--version'); Obligatoria = $false },
    @{ Nombre = 'docker';   Args = @('--version'); Obligatoria = $false },
    @{ Nombre = 'engram';   Args = @('version');   Obligatoria = $false }
)

$faltantes = 0
$resultado = foreach ($h in $herramientas) {
    $cmd = Get-Command $h.Nombre -ErrorAction SilentlyContinue
    if ($cmd) {
        $version = (& $h.Nombre @($h.Args) 2>$null | Select-Object -First 1)
        [pscustomobject]@{ Herramienta = $h.Nombre; Estado = 'OK'; Version = "$version" }
    } else {
        if ($h.Obligatoria) { $faltantes++ }
        $estado = if ($h.Obligatoria) { 'FALTA (obligatoria)' } else { 'no instalada (opcional)' }
        [pscustomobject]@{ Herramienta = $h.Nombre; Estado = $estado; Version = '' }
    }
}
$resultado | Format-Table -AutoSize

if (Get-Command ollama -ErrorAction SilentlyContinue) {
    try {
        $modelos = Invoke-RestMethod -Uri 'http://localhost:11434/api/tags' -TimeoutSec 3
        $nombres = ($modelos.models | ForEach-Object { $_.name }) -join ', '
        Write-Host "Ollama activo. Modelos: $nombres"
    } catch {
        Write-Host 'Ollama instalado pero el servicio no responde en http://localhost:11434 (ejecutar: ollama serve).'
    }
}

if ($faltantes -gt 0) { Write-Host "Faltan $faltantes herramientas obligatorias."; exit 1 }
Write-Host 'Entorno verificado.'
exit 0
