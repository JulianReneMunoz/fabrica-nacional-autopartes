"""Verifica los enlaces relativos y las anclas de los Markdown del repositorio (sin red).

Uso: ``uv run python scripts/verificar_enlaces.py [archivos.md ...]`` (por omisión, README.md y docs/**/*.md
versionados). Sale con código 1 si encuentra un enlace roto. Los enlaces http(s) y mailto no se comprueban.
"""

from __future__ import annotations

import re
import subprocess
import sys
import unicodedata
from pathlib import Path
from urllib.parse import unquote

RAIZ = Path(__file__).resolve().parent.parent
ENLACE = re.compile(r"(?<!!)\[[^\]]*\]\(([^)\s]+)\)|!\[[^\]]*\]\(([^)\s]+)\)|<a\s[^>]*href=\"([^\"]+)\"")
ENCABEZADO = re.compile(r"^#{1,6}\s+(.+?)\s*#*\s*$")


def ancla_github(texto: str) -> str:
    """Ancla que GitHub genera para un encabezado: minúsculas, sin puntuación, espacios a guiones."""
    texto = re.sub(r"`([^`]*)`", r"\1", texto)
    texto = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", texto)
    texto = unicodedata.normalize("NFC", texto.strip().lower())
    texto = re.sub(r"[^\w\- ]", "", texto)
    return texto.replace(" ", "-")


def anclas(archivo: Path) -> set[str]:
    vistas: dict[str, int] = {}
    salida: set[str] = set()
    en_codigo = False
    for linea in archivo.read_text(encoding="utf-8").splitlines():
        if linea.lstrip().startswith("```"):
            en_codigo = not en_codigo
            continue
        m = None if en_codigo else ENCABEZADO.match(linea)
        if m:
            base = ancla_github(m.group(1))
            n = vistas.get(base, 0)
            salida.add(base if n == 0 else f"{base}-{n}")
            vistas[base] = n + 1
    return salida


def _rel(archivo: Path) -> str:
    try:
        return str(archivo.relative_to(RAIZ))
    except ValueError:
        return str(archivo)


def revisar(archivo: Path) -> list[str]:
    errores: list[str] = []
    texto = archivo.read_text(encoding="utf-8")
    texto = re.sub(r"```.*?```", "", texto, flags=re.S)  # los bloques de código no contienen enlaces reales
    for m in ENLACE.finditer(texto):
        destino = next(g for g in m.groups() if g)
        if re.match(r"^(https?:|mailto:)", destino):
            continue
        ruta, _, fragmento = destino.partition("#")
        objetivo = archivo if not ruta else (archivo.parent / unquote(ruta)).resolve()
        if not objetivo.exists():
            errores.append(f"{_rel(archivo)}: no existe {destino}")
            continue
        if fragmento and objetivo.suffix == ".md" and unquote(fragmento) not in anclas(objetivo):
            errores.append(f"{_rel(archivo)}: ancla inexistente {destino}")
    return errores


def main(argv: list[str]) -> int:
    if argv:
        archivos = [Path(a).resolve() for a in argv]
    else:
        versionados = subprocess.run(
            ["git", "ls-files", "README.md", "docs/*.md", "docs/**/*.md"],
            cwd=RAIZ,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.split()
        archivos = [RAIZ / a for a in versionados]
    errores = [e for a in archivos for e in revisar(a)]
    for e in errores:
        print(e)
    print(f"{len(archivos)} archivos revisados, {len(errores)} enlaces rotos")
    return 1 if errores else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
