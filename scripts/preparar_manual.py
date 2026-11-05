"""Prepara los extractos de datos que el manual LaTeX incluye (docs/latex/generado/).

El manual no lee directamente data/gold/: los nombres de los documentos cambian según la última
construcción (semilla, scraping o mixta). Este script copia un documento Gold de ejemplo y el
inicio del archivo consolidado a nombres fijos, de modo que la compilación nunca falla.

Uso: ``uv run python scripts/preparar_manual.py`` (lo ejecuta scripts/compilar_manual.ps1).
"""

from __future__ import annotations

from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
GOLD = RAIZ / "data" / "gold"
DESTINO = RAIZ / "docs" / "latex" / "generado"
PREFERIDOS = (
    "autopartes-inicio",
    "nosotros",
    "inicio",
    "negocios-autopartes",
    "autopartes-productos",
    "contacto",
)


def _primeras_lineas(ruta: Path, n: int) -> str:
    lineas = ruta.read_text(encoding="utf-8", errors="replace").splitlines()[:n]
    return "\n".join(lineas) + "\n"


def main() -> None:
    DESTINO.mkdir(parents=True, exist_ok=True)
    docs = GOLD / "docs"
    candidatos = [docs / f"{nombre}.md" for nombre in PREFERIDOS] + sorted(docs.glob("*.md"))
    ejemplo = next((c for c in candidatos if c.exists()), None)
    salida_doc = DESTINO / "ejemplo_gold.md"
    if ejemplo:
        salida_doc.write_text(_primeras_lineas(ejemplo, 16), encoding="utf-8", newline="\n")
        print(f"Documento Gold de ejemplo: {ejemplo.relative_to(RAIZ)}")
    elif salida_doc.exists():
        salida_doc.unlink()
    base = GOLD / "base_conocimiento.txt"
    salida_base = DESTINO / "base_extracto.txt"
    if base.exists():
        salida_base.write_text(_primeras_lineas(base, 14), encoding="utf-8", newline="\n")
        print(f"Extracto del archivo consolidado: {base.relative_to(RAIZ)}")
    elif salida_base.exists():
        salida_base.unlink()


if __name__ == "__main__":
    main()
