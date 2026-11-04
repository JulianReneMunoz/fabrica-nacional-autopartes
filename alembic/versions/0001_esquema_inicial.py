"""Esquema inicial de auditoría: interacciones, ejecuciones_pipeline y evaluaciones.

Revision ID: 0001
Revises:
Create Date: 2026-11-04
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "interacciones",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("fecha", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("tarea", sa.String(20), nullable=False),
        sa.Column("canal", sa.String(20), nullable=False),
        sa.Column("entrada", sa.Text(), nullable=False),
        sa.Column("salida", sa.Text(), nullable=False),
        sa.Column("proveedor", sa.String(30), nullable=False),
        sa.Column("modelo", sa.String(80), nullable=False),
        sa.Column("version_prompt", sa.String(10), nullable=False),
        sa.Column("modo_contexto", sa.String(20), nullable=False),
        sa.Column("fuentes", sa.JSON(), nullable=False),
        sa.Column("fundamentada", sa.Boolean(), nullable=True),
        sa.Column("latencia_ms", sa.Integer(), nullable=False),
    )
    op.create_index("ix_interacciones_tarea_fecha", "interacciones", ["tarea", "fecha"])
    op.create_table(
        "ejecuciones_pipeline",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("inicio", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("fin", sa.DateTime(timezone=True), nullable=True),
        sa.Column("etapa", sa.String(20), nullable=False),
        sa.Column("estado", sa.String(20), nullable=False),
        sa.Column("detalle", sa.JSON(), nullable=False),
    )
    op.create_table(
        "evaluaciones",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("fecha", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("proveedor", sa.String(30), nullable=False),
        sa.Column("modelo", sa.String(80), nullable=False),
        sa.Column("version_prompt", sa.String(10), nullable=False),
        sa.Column("metricas", sa.JSON(), nullable=False),
        sa.Column("detalle", sa.JSON(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("evaluaciones")
    op.drop_table("ejecuciones_pipeline")
    op.drop_index("ix_interacciones_tarea_fecha", table_name="interacciones")
    op.drop_table("interacciones")
