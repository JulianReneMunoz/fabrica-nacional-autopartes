"""Verifica la dirección de dependencias entre capas de la arquitectura (``ast``).

Regla: una capa solo puede importar capas de nivel igual o inferior.
Salida con código 1 si se detecta una violación.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

PAQUETE = Path(__file__).resolve().parents[1] / "src" / "fabrica_autopartes"
NIVELES = {
    "core": 0,
    "domain": 0,
    "scraping": 1,
    "pipelines": 2,
    "knowledge": 3,
    "llm": 4,
    "repositories": 4,
    "services": 5,
    "api": 6,
    "mcp_server": 6,
    "cli": 6,
}


def capa_de(ruta: Path) -> str:
    relativa = ruta.relative_to(PAQUETE)
    return relativa.parts[0].removesuffix(".py")


def main() -> int:
    violaciones = []
    for ruta in PAQUETE.rglob("*.py"):
        origen = capa_de(ruta)
        if origen not in NIVELES:
            continue
        for nodo in ast.walk(ast.parse(ruta.read_text(encoding="utf-8"))):
            if (
                isinstance(nodo, ast.ImportFrom)
                and nodo.module
                and nodo.module.startswith("fabrica_autopartes.")
            ):
                destino = nodo.module.split(".")[1]
                if destino in NIVELES and NIVELES[destino] > NIVELES[origen]:
                    violaciones.append(f"{ruta.relative_to(PAQUETE)}: {origen} -> {destino}")
    for v in violaciones:
        print("VIOLACIÓN", v)
    print(f"{len(violaciones)} violaciones de capas")
    return 1 if violaciones else 0


if __name__ == "__main__":
    sys.exit(main())
