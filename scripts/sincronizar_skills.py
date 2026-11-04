"""Copia las skills canónicas de ``skills/`` a ``.opencode/skills/`` y ``.claude/skills/``.

Uso: ``uv run python scripts/sincronizar_skills.py``. Se usa copia (no enlaces simbólicos)
porque los enlaces simbólicos en Windows requieren privilegios o modo desarrollador.
"""

from __future__ import annotations

import shutil
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
ORIGEN = RAIZ / "skills"
DESTINOS = [RAIZ / ".opencode" / "skills", RAIZ / ".claude" / "skills"]


def main() -> None:
    for destino in DESTINOS:
        if destino.exists():
            shutil.rmtree(destino)
        shutil.copytree(ORIGEN, destino)
        print(f"Skills sincronizadas en {destino.relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
