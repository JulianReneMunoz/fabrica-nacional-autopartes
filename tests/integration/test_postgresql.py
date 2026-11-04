"""Persistencia sobre PostgreSQL real (servidor embebido ``pgserver``, sin Docker).

Se omite si el servidor no puede iniciarse en la plataforma (p. ej. Windows sin binarios).
"""

from __future__ import annotations

import subprocess
import sys

import pytest

from fabrica_autopartes.core.config import RAIZ_PROYECTO
from fabrica_autopartes.repositories.auditoria import RepositorioAuditoria

pgserver = pytest.importorskip("pgserver")


@pytest.fixture(scope="module")
def url_pg(tmp_path_factory):  # type: ignore[no-untyped-def]
    try:
        servidor = pgserver.get_server(str(tmp_path_factory.mktemp("pg")), cleanup_mode="stop")
    except Exception as exc:  # pragma: no cover - depende de la plataforma
        pytest.skip(f"PostgreSQL embebido no disponible: {exc}")
    uri = servidor.get_uri()  # postgresql://postgres:@/postgres?host=/tmp/...
    yield uri.replace("postgresql://", "postgresql+psycopg://", 1)
    servidor.cleanup()


def test_migraciones_alembic_en_postgresql(url_pg) -> None:  # type: ignore[no-untyped-def]
    for accion in (["upgrade", "head"], ["downgrade", "base"], ["upgrade", "head"]):
        r = subprocess.run(
            [sys.executable, "-m", "alembic", "-x", f"url={url_pg}", *accion],
            cwd=RAIZ_PROYECTO,
            capture_output=True,
            text=True,
            check=False,
        )
        assert r.returncode == 0, r.stderr


def test_repositorio_en_postgresql(url_pg) -> None:  # type: ignore[no-untyped-def]
    repo = RepositorioAuditoria(url_pg, crear_esquema=False)
    id_ = repo.guardar_estado("freno_disco", "pg", {"modo": "despiece", "factor_despiece": 1.0})
    assert repo.obtener_estado(id_).estado["modo"] == "despiece"  # type: ignore[union-attr]
    repo.registrar_evento("freno_disco", "seleccion", "disco", {"origen": "prueba"})
    assert repo.listar_eventos("freno_disco")[0].pieza_id == "disco"
    repo.registrar_interaccion(
        tarea="qa",
        entrada="p",
        salida="r",
        proveedor="x",
        modelo="m",
        version_prompt="v3",
        fuentes=["a#000"],
        fundamentada=True,
    )
    assert repo.listar_interacciones()[1] == 1
