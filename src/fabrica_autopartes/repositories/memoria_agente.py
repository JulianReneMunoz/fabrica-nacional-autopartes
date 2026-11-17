"""Memoria persistente de los agentes (ADR-033): checkpointer y Store de LangGraph sobre SQLite.

- ``crear_checkpointer``: ``SqliteSaver`` para la memoria de corto plazo por ``thread_id``. El historial de
  un hilo sobrevive al reinicio del proceso (R03).
- ``crear_store``: ``SqliteStore`` para la memoria de largo plazo por namespace, con ``search()`` (R05).
  Las preferencias de un usuario viven en ``("preferencias", user_id)``.

Es, junto con ``auditoria.py``, el único módulo que abre conexiones SQL (AGENTS.md, ADR-033). Las
bases van en ``Configuracion.dir_datos`` (``data/*.sqlite`` está ignorado por git porque puede contener
mensajes de usuarios).
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.store.base import BaseStore
from langgraph.store.sqlite import SqliteStore


def _conectar(ruta: Path, autocommit: bool = False) -> sqlite3.Connection:
    """Conexión utilizable desde los hilos del servidor.

    ``SqliteSaver`` y ``SqliteStore`` serializan el acceso a la conexión.
    """
    ruta.parent.mkdir(parents=True, exist_ok=True)
    if autocommit:
        return sqlite3.connect(ruta, check_same_thread=False, isolation_level=None)
    return sqlite3.connect(ruta, check_same_thread=False)


def crear_checkpointer(ruta: Path) -> SqliteSaver:
    """Checkpointer persistente de LangGraph en ``ruta`` (crea el archivo y las tablas si no existen)."""
    saver = SqliteSaver(_conectar(ruta))
    saver.setup()
    return saver


def crear_store(ruta: Path) -> SqliteStore:
    """Store persistente de LangGraph en ``ruta`` (crea el archivo y aplica las migraciones si hace falta)."""
    store = SqliteStore(_conectar(ruta, autocommit=True))
    store.setup()
    return store


def cerrar_checkpointer(saver: SqliteSaver) -> None:
    """Cierra la conexión del checkpointer (libera el archivo; necesario en Windows antes de borrarlo)."""
    saver.conn.close()


def cerrar_store(store: BaseStore) -> None:
    """Cierra la conexión del Store si es un ``SqliteStore``; otros Store (en memoria, simulados) no tienen
    archivo que liberar. Recibe ``BaseStore`` para que los servicios no importen el tipo concreto."""
    if isinstance(store, SqliteStore):
        store.conn.close()
