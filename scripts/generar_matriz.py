"""Genera la matriz de trazabilidad en Markdown y LaTeX desde ``matriz_trazabilidad.csv``."""

from __future__ import annotations

import csv
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
CSV = RAIZ / "docs" / "requisitos" / "matriz_trazabilidad.csv"


_MAPA = {
    "\\": r"\textbackslash{}",
    "&": r"\&",
    "%": r"\%",
    "_": r"\_\allowbreak{}",
    "#": r"\#",
    "$": r"\$",
    "{": r"\{",
    "}": r"\}",
    "~": r"\textasciitilde{}",
    "^": r"\^{}",
    "§": r"\S{}",
    "≥": r"$\geq$",
    "→": r"$\rightarrow$",
    "/": r"/\allowbreak{}",
}


def escapar_tex(texto: str) -> str:
    """Escapa caracteres especiales de LaTeX en una sola pasada."""
    return "".join(_MAPA.get(c, c) for c in texto)


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

    tex = []
    for f in filas:
        tex.append(
            " & ".join(
                escapar_tex(f[k]) for k in ("id", "origen", "descripcion", "componente", "prueba", "estado")
            )
            + r" \\ \hline"
        )
    salida = RAIZ / "docs" / "latex" / "generado" / "matriz_filas.tex"
    salida.parent.mkdir(parents=True, exist_ok=True)
    salida.write_text("\n".join(tex) + "\n", encoding="utf-8")
    print(f"{len(filas)} requisitos → {CSV.parent / 'matriz_trazabilidad.md'} y {salida}")


if __name__ == "__main__":
    main()
