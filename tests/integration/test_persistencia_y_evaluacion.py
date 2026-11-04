"""Persistencia (SQLAlchemy + Alembic), CLI y evaluación del banco de preguntas."""

from __future__ import annotations

import subprocess
import sys

from fabrica_autopartes.core.config import RAIZ_PROYECTO
from fabrica_autopartes.repositories.auditoria import RepositorioAuditoria
from fabrica_autopartes.services.evaluacion import cargar_preguntas, evaluar, hechos_presentes


def test_repositorio_interacciones_paginadas(tmp_path) -> None:  # type: ignore[no-untyped-def]
    repo = RepositorioAuditoria(f"sqlite:///{tmp_path / 'a.db'}")
    for i in range(5):
        repo.registrar_interaccion(
            tarea="qa",
            entrada=f"p{i}",
            salida="r",
            proveedor="x",
            modelo="m",
            version_prompt="v3",
            fuentes=["a#000"],
            fundamentada=True,
        )
    filas, total = repo.listar_interacciones(pagina=2, tamano=2)
    assert total == 5 and [f.entrada for f in filas] == ["p2", "p1"]


def test_ejecuciones_pipeline(tmp_path) -> None:  # type: ignore[no-untyped-def]
    repo = RepositorioAuditoria(f"sqlite:///{tmp_path / 'b.db'}")
    id_ = repo.iniciar_ejecucion("construccion")
    repo.finalizar_ejecucion(id_, "ok", {"fragmentos": 3})
    e = repo.listar_ejecuciones()[0]
    assert e.estado == "ok" and e.fin is not None and e.detalle == {"fragmentos": 3}


def test_migracion_alembic_crea_esquema(tmp_path) -> None:  # type: ignore[no-untyped-def]
    url = f"sqlite:///{(tmp_path / 'mig.db').as_posix()}"
    salida = subprocess.run(
        [sys.executable, "-m", "alembic", "-x", f"url={url}", "upgrade", "head"],
        cwd=RAIZ_PROYECTO,
        capture_output=True,
        text=True,
        check=False,
    )
    assert salida.returncode == 0, salida.stderr
    from sqlalchemy import create_engine, inspect

    tablas = set(inspect(create_engine(url)).get_table_names())
    assert {
        "interacciones",
        "ejecuciones_pipeline",
        "evaluaciones",
        "alembic_version",
        "estados_simulador",
        "eventos_simulador",
    } <= tablas


def test_banco_tiene_al_menos_20_preguntas_distintas() -> None:
    preguntas = cargar_preguntas()
    textos = [p["pregunta"] for p in preguntas]
    assert len(textos) >= 20 and len(set(textos)) == len(textos)
    assert {p["tipo"] for p in preguntas} == {"respondible", "ausente", "fuera_alcance", "inyeccion"}


def test_hechos_presentes_sin_tildes() -> None:
    assert hechos_presentes("Está en BOGOTÁ y Medellín.", ["bogota", "medellin", "cali"]) == [
        "bogota",
        "medellin",
    ]


def test_evaluacion_extractiva_produce_metricas(servicio) -> None:  # type: ignore[no-untyped-def]
    informe = evaluar(servicio, guardar=False)
    m = informe["metricas"]
    assert m["total_preguntas"] == len(cargar_preguntas())
    assert 0.0 <= m["exactitud_respondibles"] <= 1.0
    assert m["cobertura_contexto"] == 1.0  # el contexto completo contiene todos los hechos
    inyeccion = next(d for d in informe["detalle"] if d["tipo"] == "inyeccion")
    assert inyeccion["acierto"]


def test_cli_build_y_ask(config, monkeypatch, capsys) -> None:  # type: ignore[no-untyped-def]
    from fabrica_autopartes import cli
    from fabrica_autopartes.services import asistente

    monkeypatch.setattr(asistente, "obtener_configuracion", lambda: config)
    assert cli.main(["build", "--fuente", "semilla"]) == 0
    assert cli.main(["ask", "¿Cuál es el teléfono de contacto?", "--proveedor", "extractivo"]) == 0
    assert "651 5343" in capsys.readouterr().out
    assert cli.main(["validate"]) == 0
