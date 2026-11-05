"""Genera docs/arquitectura/arbol.txt (estructura resumida del repositorio).

Uso: ``uv run python scripts/generar_arbol.py``. Omite entornos, dependencias y cachés; las carpetas
con muchos archivos de datos se resumen con un conteo.
"""

from __future__ import annotations

from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
OMITIR = {
    ".venv",
    ".git",
    "node_modules",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "dist",
    "test-results",
    "build",
    ".opencode",
    "skills_cache",
}
RESUMIR = {
    "docs/gold",
    "data/bronze/html",
    "gold/docs",
    "docs/capturas/v2",
    ".claude/skills",
    "skills",
}
DESTINO = RAIZ / "docs" / "arquitectura" / "arbol.txt"


def _lineas(carpeta: Path, prefijo: str = "") -> list[str]:
    hijos = sorted(
        (
            h
            for h in carpeta.iterdir()
            if h.name not in OMITIR and not h.name.endswith((".pyc", ".aux", ".log"))
        ),
        key=lambda h: (h.is_file(), h.name.lower()),
    )
    salida: list[str] = []
    for i, h in enumerate(hijos):
        ultimo = i == len(hijos) - 1
        rama, sig = ("└── ", "    ") if ultimo else ("├── ", "│   ")
        relativa = h.relative_to(RAIZ).as_posix()
        if h.is_dir():
            salida.append(f"{prefijo}{rama}{h.name}/")
            if any(relativa.endswith(r) for r in RESUMIR):
                n = sum(1 for x in h.rglob("*") if x.is_file())
                salida.append(f"{prefijo}{sig}└── … ({n} archivos)")
            else:
                salida.extend(_lineas(h, prefijo + sig))
        else:
            salida.append(f"{prefijo}{rama}{h.name}")
    return salida


def main() -> None:
    texto = "\n".join([f"{RAIZ.name}/", *_lineas(RAIZ)]) + "\n"
    DESTINO.write_text(texto, encoding="utf-8")
    print(f"{texto.count(chr(10))} líneas → {DESTINO.relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
