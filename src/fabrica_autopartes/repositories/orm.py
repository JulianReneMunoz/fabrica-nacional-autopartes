"""Modelo relacional de auditoría (SQLAlchemy 2.0, SQLite por defecto).

Justificación (ADR-003): el Módulo 1 solo requiere registrar interacciones, ejecuciones
de pipeline y evaluaciones; SQLite no exige servidor, se versiona el esquema con Alembic
y la misma capa ORM permite migrar a PostgreSQL en la Fase 3 cambiando la URL.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, Index, Integer, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Interaccion(Base):
    __tablename__ = "interacciones"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    fecha: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    tarea: Mapped[str] = mapped_column(String(20))  # qa | faq | resumen
    canal: Mapped[str] = mapped_column(String(20), default="api")  # api | streamlit | cli | mcp
    entrada: Mapped[str] = mapped_column(Text)
    salida: Mapped[str] = mapped_column(Text)
    proveedor: Mapped[str] = mapped_column(String(30))
    modelo: Mapped[str] = mapped_column(String(80))
    version_prompt: Mapped[str] = mapped_column(String(10))
    modo_contexto: Mapped[str] = mapped_column(String(20), default="")
    fuentes: Mapped[list] = mapped_column(JSON, default=list)
    fundamentada: Mapped[bool | None] = mapped_column(default=None)
    latencia_ms: Mapped[int] = mapped_column(Integer, default=0)

    __table_args__ = (Index("ix_interacciones_tarea_fecha", "tarea", "fecha"),)


class EjecucionPipeline(Base):
    __tablename__ = "ejecuciones_pipeline"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    inicio: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    fin: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    etapa: Mapped[str] = mapped_column(String(20))  # scraping | construccion
    estado: Mapped[str] = mapped_column(String(20))  # ok | error
    detalle: Mapped[dict] = mapped_column(JSON, default=dict)


class Evaluacion(Base):
    __tablename__ = "evaluaciones"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    fecha: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    proveedor: Mapped[str] = mapped_column(String(30))
    modelo: Mapped[str] = mapped_column(String(80))
    version_prompt: Mapped[str] = mapped_column(String(10))
    metricas: Mapped[dict] = mapped_column(JSON, default=dict)
    detalle: Mapped[list] = mapped_column(JSON, default=list)


class EstadoSimulador(Base):
    """Configuración guardada del visualizador (modo, despiece, visibilidad, articulaciones)."""

    __tablename__ = "estados_simulador"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    fecha: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    ensamblaje: Mapped[str] = mapped_column(String(60))
    nombre: Mapped[str] = mapped_column(String(120))
    estado: Mapped[dict] = mapped_column(JSON, default=dict)

    __table_args__ = (Index("ix_estados_ensamblaje", "ensamblaje"),)


class EventoSimulador(Base):
    """Bitácora de interacción con el simulador (selección, despiece, preguntas...)."""

    __tablename__ = "eventos_simulador"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    fecha: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    ensamblaje: Mapped[str] = mapped_column(String(60))
    tipo: Mapped[str] = mapped_column(String(40))
    pieza_id: Mapped[str | None] = mapped_column(String(60), nullable=True)
    detalle: Mapped[dict] = mapped_column(JSON, default=dict)

    __table_args__ = (Index("ix_eventos_ensamblaje_fecha", "ensamblaje", "fecha"),)
