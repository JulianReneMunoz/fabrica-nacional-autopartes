"""Usuarios seudónimos e hilos de cada usuario (ADR-033).

- ``usuarios`` guarda solo el ``user_id`` seudónimo (HMAC del alias) y fechas: **no hay columna de alias**. El
  alias solo viaja en la cookie cifrada del propio usuario.
- ``hilos`` liga cada ``thread_id`` a su dueño, con un título anonimizado, el número de turnos y la última
  ruta.

Una conexión por operación (válida desde cualquier hilo del servidor, sin archivos abiertos entre
peticiones) y un lock para las escrituras, como ``RepositorioMemoriaIgnis``.
"""

from __future__ import annotations

import sqlite3
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path


@dataclass(frozen=True)
class Hilo:
    thread_id: str
    titulo: str
    turnos: int
    ultima_ruta: str
    creado: str
    actualizado: str


def _ahora() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


class RepositorioSesiones:
    def __init__(self, ruta: Path) -> None:
        self.ruta = ruta
        self.ruta.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._inicializar()

    @contextmanager
    def _conectar(self) -> Iterator[sqlite3.Connection]:
        """Abre, confirma y cierra la conexión (``with sqlite3.connect`` no la cierra)."""
        conn = sqlite3.connect(self.ruta, timeout=10)
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    def _inicializar(self) -> None:
        with self._lock, self._conectar() as conn:
            conn.execute(
                """CREATE TABLE IF NOT EXISTS usuarios (
                    user_id TEXT PRIMARY KEY,
                    creado TEXT NOT NULL,
                    ultimo_acceso TEXT NOT NULL
                )"""
            )
            conn.execute(
                """CREATE TABLE IF NOT EXISTS hilos (
                    thread_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    titulo TEXT NOT NULL DEFAULT '',
                    turnos INTEGER NOT NULL DEFAULT 0,
                    ultima_ruta TEXT NOT NULL DEFAULT '',
                    creado TEXT NOT NULL,
                    actualizado TEXT NOT NULL
                )"""
            )
            conn.execute("CREATE INDEX IF NOT EXISTS hilos_por_usuario ON hilos (user_id, actualizado)")

    # ------------------------------------------------------------ usuarios
    def registrar_acceso(self, user_id: str) -> None:
        """Crea el usuario si no existe y actualiza su último acceso."""
        ahora = _ahora()
        with self._lock, self._conectar() as conn:
            conn.execute(
                "INSERT INTO usuarios (user_id, creado, ultimo_acceso) VALUES (?, ?, ?) "
                "ON CONFLICT(user_id) DO UPDATE SET ultimo_acceso = excluded.ultimo_acceso",
                (user_id, ahora, ahora),
            )

    # ------------------------------------------------------------ hilos
    def dueno_de(self, thread_id: str) -> str | None:
        with self._conectar() as conn:
            fila = conn.execute("SELECT user_id FROM hilos WHERE thread_id = ?", (thread_id,)).fetchone()
        return str(fila[0]) if fila else None

    def crear_hilo(self, thread_id: str, user_id: str) -> bool:
        """Liga un ``thread_id`` nuevo al usuario. ``False`` si el hilo ya tenía dueño."""
        ahora = _ahora()
        with self._lock, self._conectar() as conn:
            cur = conn.execute(
                "INSERT OR IGNORE INTO hilos (thread_id, user_id, creado, actualizado) VALUES (?, ?, ?, ?)",
                (thread_id, user_id, ahora, ahora),
            )
            return cur.rowcount == 1

    def listar_hilos(self, user_id: str, limite: int = 100) -> list[Hilo]:
        with self._conectar() as conn:
            filas = conn.execute(
                "SELECT thread_id, titulo, turnos, ultima_ruta, creado, actualizado FROM hilos "
                "WHERE user_id = ? ORDER BY actualizado DESC, creado DESC LIMIT ?",
                (user_id, limite),
            ).fetchall()
        return [Hilo(*fila) for fila in filas]

    def registrar_turno(self, thread_id: str, user_id: str, titulo: str, ruta: str) -> None:
        """Suma un turno, guarda la última ruta y fija el título solo si el hilo aún no tenía."""
        with self._lock, self._conectar() as conn:
            conn.execute(
                "UPDATE hilos SET turnos = turnos + 1, ultima_ruta = ?, actualizado = ?, "
                "titulo = CASE WHEN titulo = '' THEN ? ELSE titulo END "
                "WHERE thread_id = ? AND user_id = ?",
                (ruta, _ahora(), titulo, thread_id, user_id),
            )
