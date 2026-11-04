"""Versión 2.0: tablas del simulador 3D (estados guardados y eventos).

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-04
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "estados_simulador",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("fecha", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("ensamblaje", sa.String(60), nullable=False),
        sa.Column("nombre", sa.String(120), nullable=False),
        sa.Column("estado", sa.JSON(), nullable=False),
    )
    op.create_index("ix_estados_ensamblaje", "estados_simulador", ["ensamblaje"])
    op.create_table(
        "eventos_simulador",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("fecha", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("ensamblaje", sa.String(60), nullable=False),
        sa.Column("tipo", sa.String(40), nullable=False),
        sa.Column("pieza_id", sa.String(60), nullable=True),
        sa.Column("detalle", sa.JSON(), nullable=False),
    )
    op.create_index("ix_eventos_ensamblaje_fecha", "eventos_simulador", ["ensamblaje", "fecha"])


def downgrade() -> None:
    op.drop_index("ix_eventos_ensamblaje_fecha", table_name="eventos_simulador")
    op.drop_table("eventos_simulador")
    op.drop_index("ix_estados_ensamblaje", table_name="estados_simulador")
    op.drop_table("estados_simulador")
