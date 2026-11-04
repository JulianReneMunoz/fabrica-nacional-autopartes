"""Entorno de migraciones Alembic."""

from __future__ import annotations

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from fabrica_autopartes.core.config import obtener_configuracion
from fabrica_autopartes.repositories.orm import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

url = context.get_x_argument(as_dictionary=True).get("url") or obtener_configuracion().url_base_datos
config.set_main_option("sqlalchemy.url", url)
target_metadata = Base.metadata


def ejecutar_fuera_de_linea() -> None:
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True, render_as_batch=True)
    with context.begin_transaction():
        context.run_migrations()


def ejecutar_en_linea() -> None:
    motor = engine_from_config(
        config.get_section(config.config_ini_section, {}), prefix="sqlalchemy.", poolclass=pool.NullPool
    )
    with motor.connect() as conexion:
        context.configure(connection=conexion, target_metadata=target_metadata, render_as_batch=True)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    ejecutar_fuera_de_linea()
else:
    ejecutar_en_linea()
