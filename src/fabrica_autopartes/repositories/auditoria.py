"""Repositorio de auditoría: única puerta de acceso a la base relacional."""

from __future__ import annotations

import json
import sqlite3
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, func, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from fabrica_autopartes.repositories.orm import (
    Base,
    EjecucionPipeline,
    EstadoSimulador,
    Evaluacion,
    EventoSimulador,
    Interaccion,
)


class RepositorioAuditoria:
    def __init__(self, url: str, crear_esquema: bool = True) -> None:
        conexion = {"check_same_thread": False} if url.startswith("sqlite") else {}
        if url.startswith("sqlite:///"):
            Path(url.removeprefix("sqlite:///")).parent.mkdir(parents=True, exist_ok=True)
        self.motor: Engine = create_engine(url, connect_args=conexion, future=True)
        self._sesiones = sessionmaker(self.motor, expire_on_commit=False)
        if crear_esquema:
            # En desarrollo se crea el esquema directamente; en despliegue se usa Alembic.
            Base.metadata.create_all(self.motor)

    @contextmanager
    def sesion(self) -> Iterator[Session]:
        s = self._sesiones()
        try:
            yield s
            s.commit()
        except Exception:
            s.rollback()
            raise
        finally:
            s.close()

    # ------------------------------------------------------------ interacciones
    def registrar_interaccion(self, **datos: Any) -> int:
        with self.sesion() as s:
            fila = Interaccion(**datos)
            s.add(fila)
            s.flush()
            return int(fila.id)

    def listar_interacciones(
        self, pagina: int = 1, tamano: int = 20, tarea: str | None = None
    ) -> tuple[list[Interaccion], int]:
        with self.sesion() as s:
            consulta = select(Interaccion)
            conteo = select(func.count(Interaccion.id))
            if tarea:
                consulta = consulta.where(Interaccion.tarea == tarea)
                conteo = conteo.where(Interaccion.tarea == tarea)
            total = int(s.scalar(conteo) or 0)
            filas = s.scalars(
                consulta.order_by(Interaccion.id.desc()).offset((pagina - 1) * tamano).limit(tamano)
            ).all()
            return list(filas), total

    # --------------------------------------------------------------- pipeline
    def iniciar_ejecucion(self, etapa: str) -> int:
        with self.sesion() as s:
            fila = EjecucionPipeline(etapa=etapa, estado="en_curso", detalle={})
            s.add(fila)
            s.flush()
            return int(fila.id)

    def finalizar_ejecucion(self, id_: int, estado: str, detalle: dict) -> None:
        with self.sesion() as s:
            fila = s.get(EjecucionPipeline, id_)
            if fila is not None:
                fila.estado = estado
                fila.detalle = detalle
                fila.fin = datetime.now(UTC)

    def listar_ejecuciones(self, limite: int = 50) -> list[EjecucionPipeline]:
        with self.sesion() as s:
            return list(
                s.scalars(select(EjecucionPipeline).order_by(EjecucionPipeline.id.desc()).limit(limite))
            )

    # ------------------------------------------------------------ evaluaciones
    def registrar_evaluacion(self, **datos: Any) -> int:
        with self.sesion() as s:
            fila = Evaluacion(**datos)
            s.add(fila)
            s.flush()
            return int(fila.id)

    def listar_evaluaciones(self, limite: int = 20) -> list[Evaluacion]:
        with self.sesion() as s:
            return list(s.scalars(select(Evaluacion).order_by(Evaluacion.id.desc()).limit(limite)))

    # ------------------------------------------------------------ simulador
    def guardar_estado(self, ensamblaje: str, nombre: str, estado: dict) -> int:
        with self.sesion() as s:
            fila = EstadoSimulador(ensamblaje=ensamblaje, nombre=nombre, estado=estado)
            s.add(fila)
            s.flush()
            return int(fila.id)

    def listar_estados(self, ensamblaje: str) -> list[EstadoSimulador]:
        with self.sesion() as s:
            return list(
                s.scalars(
                    select(EstadoSimulador)
                    .where(EstadoSimulador.ensamblaje == ensamblaje)
                    .order_by(EstadoSimulador.id.desc())
                )
            )

    def obtener_estado(self, id_: int) -> EstadoSimulador | None:
        with self.sesion() as s:
            return s.get(EstadoSimulador, id_)

    def registrar_evento(self, ensamblaje: str, tipo: str, pieza_id: str | None, detalle: dict) -> int:
        with self.sesion() as s:
            fila = EventoSimulador(ensamblaje=ensamblaje, tipo=tipo, pieza_id=pieza_id, detalle=detalle)
            s.add(fila)
            s.flush()
            return int(fila.id)

    def listar_eventos(self, ensamblaje: str, limite: int = 100) -> list[EventoSimulador]:
        with self.sesion() as s:
            return list(
                s.scalars(
                    select(EventoSimulador)
                    .where(EventoSimulador.ensamblaje == ensamblaje)
                    .order_by(EventoSimulador.id.desc())
                    .limit(limite)
                )
            )


# --- Memoria del agente IGNIS (tabla SQLite propia por hilo; SqliteSaver y Store llegan en #28 y #29) ---
class RepositorioMemoriaIgnis:
    """Tablas SQLite propias: turnos por hilo (thread_id) y pares clave-valor por namespace."""

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        # Una conexión por operación (válida desde cualquier hilo) y un lock para las escrituras: evita que
        # dos turnos simultáneos del mismo hilo calculen el mismo número de turno.
        self._lock_escritura = threading.Lock()
        self._inicializar_tablas()

    @contextmanager
    def _conectar(self) -> Iterator[sqlite3.Connection]:
        """Abre, confirma y cierra la conexión (``with sqlite3.connect`` no la cierra)."""
        conn = sqlite3.connect(self.db_path, timeout=10)
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    def _inicializar_tablas(self) -> None:
        with self._lock_escritura, self._conectar() as conn:
            conn.execute(
                """CREATE TABLE IF NOT EXISTS checkpoints_hilos (
                    thread_id TEXT,
                    turno INTEGER,
                    rol TEXT,
                    contenido TEXT,
                    metadatos TEXT,
                    PRIMARY KEY (thread_id, turno)
                )"""
            )
            conn.execute(
                """CREATE TABLE IF NOT EXISTS store_largo_plazo (
                    namespace TEXT,
                    clave TEXT,
                    valor TEXT,
                    PRIMARY KEY (namespace, clave)
                )"""
            )

    def guardar_turno(
        self, thread_id: str, rol: str, contenido: str, metadatos: dict[str, Any] | None = None
    ) -> None:
        with self._lock_escritura, self._conectar() as conn:
            cur = conn.execute(
                "SELECT COALESCE(MAX(turno), 0) + 1 FROM checkpoints_hilos WHERE thread_id = ?", (thread_id,)
            )
            sig_turno = cur.fetchone()[0]
            conn.execute(
                "INSERT INTO checkpoints_hilos VALUES (?, ?, ?, ?, ?)",
                (thread_id, sig_turno, rol, contenido, json.dumps(metadatos or {}, ensure_ascii=False)),
            )

    def obtener_historial_recortado(self, thread_id: str, max_turnos: int = 8) -> list[dict[str, str]]:
        """Devuelve los últimos N turnos del hilo con un LIMIT de SQL."""
        with self._conectar() as conn:
            filas = conn.execute(
                "SELECT rol, contenido FROM checkpoints_hilos WHERE thread_id = ? "
                "ORDER BY turno DESC LIMIT ?",
                (thread_id, max_turnos),
            ).fetchall()
        return [{"role": r, "content": c} for r, c in reversed(filas)]

    def obtener_historial(self, thread_id: str, limite: int = 200) -> list[dict[str, Any]]:
        """Historial completo del hilo, del más antiguo al más reciente, con los metadatos de cada turno
        (ruta y citas de las respuestas). Se usa para reabrir un hilo en la interfaz."""
        with self._conectar() as conn:
            filas = conn.execute(
                "SELECT rol, contenido, metadatos FROM checkpoints_hilos WHERE thread_id = ? "
                "ORDER BY turno ASC LIMIT ?",
                (thread_id, limite),
            ).fetchall()
        return [{"role": r, "content": c, "metadatos": json.loads(m or "{}")} for r, c, m in filas]

    def tiene_historial(self, thread_id: str) -> bool:
        """Verdadero si el hilo ya tiene turnos guardados (por ejemplo, hilos anteriores a las sesiones)."""
        with self._conectar() as conn:
            fila = conn.execute(
                "SELECT 1 FROM checkpoints_hilos WHERE thread_id = ? LIMIT 1", (thread_id,)
            ).fetchone()
        return fila is not None

    def guardar_en_store(self, namespace: str, clave: str, valor: str) -> None:
        with self._lock_escritura, self._conectar() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO store_largo_plazo VALUES (?, ?, ?)",
                (namespace, clave, valor),
            )

    def buscar_en_store(self, namespace: str) -> dict[str, str]:
        with self._conectar() as conn:
            filas = conn.execute(
                "SELECT clave, valor FROM store_largo_plazo WHERE namespace = ?",
                (namespace,),
            ).fetchall()
        return {k: v for k, v in filas}
