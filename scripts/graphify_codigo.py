"""Regenera el grafo del código con Graphify en el modo aprobado por la ADR-020 (sin LLM y sin red).

Uso: ``uv run --no-sync python scripts/graphify_codigo.py [--salida CARPETA]``.

Copia solo los ``.py``, ``.ts`` y ``.tsx`` de ``src/`` y ``web/src/`` (sin pruebas) a una carpeta temporal y
ejecuta ``graphify extract <copia> --code-only`` con ``GRAPHIFY_BACKEND=none``. La salida queda fuera del
repositorio; el SVG y el informe versionados se actualizan a mano después de revisarlos (ADR-020, punto 5).
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
ORIGENES = (RAIZ / "src", RAIZ / "web" / "src")
EXTENSIONES = {".py", ".ts", ".tsx"}
EXCLUIDOS = ("__tests__", "__pycache__")


def es_prueba(ruta: Path) -> bool:
    """Indica si el archivo es una prueba o una declaración de tipos, que no entran al grafo."""
    nombre = ruta.name
    return (
        any(parte in EXCLUIDOS for parte in ruta.parts)
        or nombre.startswith("test_")
        or nombre.endswith((".test.ts", ".test.tsx", ".spec.ts", ".spec.tsx", ".d.ts"))
    )


def copiar_codigo(destino: Path) -> int:
    """Copia el código de producción a ``destino`` conservando la estructura relativa a la raíz."""
    total = 0
    for origen in ORIGENES:
        for ruta in sorted(origen.rglob("*")):
            if ruta.suffix in EXTENSIONES and ruta.is_file() and not es_prueba(ruta):
                copia = destino / ruta.relative_to(RAIZ)
                copia.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(ruta, copia)
                total += 1
    return total


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--salida", type=Path, help="Carpeta de salida (por omisión, una temporal)")
    args = parser.parse_args()

    ejecutable = shutil.which("graphify")
    if ejecutable is None:
        print("graphify no está instalado (ver ADR-020: uv tool install graphifyy==0.9.102)", file=sys.stderr)
        return 1

    trabajo = Path(tempfile.mkdtemp(prefix="fna-graphify-"))
    salida = (args.salida or trabajo / "salida").resolve()
    if salida.is_relative_to(RAIZ):
        print("La salida debe quedar fuera del repositorio (ADR-020)", file=sys.stderr)
        return 1
    codigo = trabajo / "codigo"
    print(f"{copiar_codigo(codigo)} archivos copiados a {codigo}")

    entorno = {**os.environ, "GRAPHIFY_BACKEND": "none"}
    orden = [ejecutable, "extract", str(codigo), "--code-only", "--out", str(salida)]
    resultado = subprocess.run(orden, env=entorno, check=False)
    if resultado.returncode == 0:
        print(f"Grafo generado en {salida / 'graphify-out'}")
    return resultado.returncode


if __name__ == "__main__":
    sys.exit(main())
