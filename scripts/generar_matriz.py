"""Genera la matriz de trazabilidad en Markdown desde ``matriz_trazabilidad.csv``."""

from __future__ import annotations

import csv
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
CSV = RAIZ / "docs" / "requisitos" / "matriz_trazabilidad.csv"


def main() -> None:
    filas = list(csv.DictReader(CSV.open(encoding="utf-8"), delimiter=";"))
    md = [
        "# Matriz de trazabilidad de requisitos",
        "",
        "Generada desde `matriz_trazabilidad.csv` con `uv run python scripts/generar_matriz.py`.",
        "",
        "| ID | Origen | Descripción | Tipo | Prioridad | Componente | Caso de uso "
        "| Prueba de aceptación | Estado |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for f in filas:
        md.append(
            "| "
            + " | ".join(
                f[k].replace("|", "/")
                for k in (
                    "id",
                    "origen",
                    "descripcion",
                    "tipo",
                    "prioridad",
                    "componente",
                    "caso_uso",
                    "prueba",
                    "estado",
                )
            )
            + " |"
        )
    md += ["", "## Historias de usuario", ""] + [f"- **{f['id']}**: {f['historia']}." for f in filas]
    (CSV.parent / "matriz_trazabilidad.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(f"{len(filas)} requisitos → {CSV.parent / 'matriz_trazabilidad.md'}")


if __name__ == "__main__":
    main()
