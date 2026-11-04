"""Repositorio de auditoría: única puerta de acceso a la base relacional."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
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
            from pathlib import Path

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
