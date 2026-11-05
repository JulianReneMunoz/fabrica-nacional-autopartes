<#
.SYNOPSIS
  Compila el manual LaTeX (docs/latex/main.tex) con pdflatex, sin necesidad de Perl ni latexmk.
.DESCRIPTION
  1. Copia los extractos de la base actual a docs/latex/generado (scripts/preparar_manual.py).
  2. Ejecuta pdflatex tres veces (índice, referencias cruzadas y bibliografía).
  3. Verifica que main.pdf se haya generado y elimina los archivos intermedios.
  Requiere MiKTeX con la instalación automática de paquetes activada.
.EXAMPLE
  .\scripts\compilar_manual.ps1
#>
$ErrorActionPreference = 'Continue'
$raiz = Split-Path -Parent $PSScriptRoot
Set-Location $raiz
if (-not (Get-Command pdflatex -ErrorAction SilentlyContinue)) {
    throw "pdflatex no está instalado: winget install --id MiKTeX.MiKTeX -e"
}
uv run python scripts/preparar_manual.py
Set-Location docs/latex
foreach ($pasada in 1..3) {
    Write-Host "pdflatex: pasada $pasada de 3"
    pdflatex -interaction=nonstopmode -halt-on-error main.tex | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-Warning "pdflatex falló en la pasada $pasada. Últimas líneas del registro:"
        Get-Content main.log -Tail 25
        Set-Location $raiz
        exit 1
    }
}
Remove-Item main.aux, main.log, main.out, main.toc, main.lof, main.lot -ErrorAction SilentlyContinue
$pdf = Get-Item main.pdf
Write-Host ("Manual generado: {0} ({1:N0} KB, {2})" -f $pdf.FullName, ($pdf.Length / 1KB), $pdf.LastWriteTime)
Set-Location $raiz
