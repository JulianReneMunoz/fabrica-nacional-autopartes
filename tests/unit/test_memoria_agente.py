"""Fábricas de memoria persistente (ADR-033) y regla de capas: el SQL solo vive en ``repositories/``."""

from __future__ import annotations

import ast
from pathlib import Path

from langgraph.store.memory import InMemoryStore

from fabrica_autopartes.core.config import Configuracion
from fabrica_autopartes.repositories.memoria_agente import (
    cerrar_checkpointer,
    cerrar_store,
    crear_checkpointer,
    crear_store,
)

PAQUETE = Path(__file__).resolve().parents[2] / "src" / "fabrica_autopartes"
MODULOS_SQL = ("sqlite3", "sqlalchemy", "langgraph.checkpoint.sqlite", "langgraph.store.sqlite")


def test_las_rutas_viven_en_el_directorio_de_datos(config: Configuracion) -> None:
    assert config.ruta_checkpoints.parent == config.dir_datos
    assert config.ruta_store.parent == config.dir_datos
    assert config.ruta_checkpoints.suffix == config.ruta_store.suffix == ".sqlite"


def test_el_store_persiste_al_reabrir_el_archivo(tmp_path: Path) -> None:
    ruta = tmp_path / "store.sqlite"
    store = crear_store(ruta)
    store.put(("preferencias", "u1"), "linea_producto", {"valor": "motocicletas"})
    cerrar_store(store)

    reabierto = crear_store(ruta)
    try:
        items = reabierto.search(("preferencias", "u1"))
        assert [(i.key, i.value) for i in items] == [("linea_producto", {"valor": "motocicletas"})]
    finally:
        cerrar_store(reabierto)


def test_el_checkpointer_crea_su_archivo_y_cierra(tmp_path: Path) -> None:
    ruta = tmp_path / "sub" / "checkpoints.sqlite"
    saver = crear_checkpointer(ruta)
    assert ruta.is_file()
    assert saver.get({"configurable": {"thread_id": "inexistente"}}) is None
    cerrar_checkpointer(saver)


def test_cerrar_store_acepta_un_store_sin_archivo() -> None:
    cerrar_store(InMemoryStore())  # no hay conexión que cerrar: no falla


def _importaciones(ruta: Path) -> set[str]:
    nombres: set[str] = set()
    for nodo in ast.walk(ast.parse(ruta.read_text(encoding="utf-8"))):
        if isinstance(nodo, ast.Import):
            nombres.update(a.name for a in nodo.names)
        elif isinstance(nodo, ast.ImportFrom) and nodo.module:
            nombres.add(nodo.module)
    return nombres


def test_el_sql_solo_se_importa_desde_repositories() -> None:
    """AGENTS.md y ADR-033: ningún módulo fuera de ``repositories/`` abre conexiones SQL."""
    infractores = []
    for ruta in PAQUETE.rglob("*.py"):
        if "repositories" in ruta.relative_to(PAQUETE).parts:
            continue
        for modulo in _importaciones(ruta):
            if any(modulo == m or modulo.startswith(f"{m}.") for m in MODULOS_SQL):
                infractores.append(f"{ruta.relative_to(PAQUETE)}: {modulo}")
    assert infractores == []
