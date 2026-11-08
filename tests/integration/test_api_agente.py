"""POST /api/v1/agente (ADR-024): contrato, memoria por thread_id, 422 y 503, con un modelo simulado."""

from __future__ import annotations

import argparse

import pytest
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage, HumanMessage

from fabrica_autopartes.api.dependencias import obtener_servicio
from fabrica_autopartes.api.main import crear_app
from fabrica_autopartes.cli import _comando_agente
from fabrica_autopartes.core.config import Configuracion
from fabrica_autopartes.repositories.auditoria import RepositorioAuditoria
from fabrica_autopartes.services.asistente import ServicioAsistente
from tests.simulados import ModeloSimulado, llamada, responder_citando_primera_url


def _cliente(servicio: ServicioAsistente) -> TestClient:
    app = crear_app()
    app.dependency_overrides[obtener_servicio] = lambda: servicio
    return TestClient(app)


@pytest.fixture
def modelo() -> ModeloSimulado:
    return ModeloSimulado(
        guion=[
            llamada("sede principal", "c1"),
            responder_citando_primera_url("La sede"),
            AIMessage("Se preguntó por la sede."),
        ]
    )


@pytest.fixture
def servicio_simulado(config_con_base: Configuracion, modelo: ModeloSimulado) -> ServicioAsistente:
    return ServicioAsistente(
        config_con_base, RepositorioAuditoria(config_con_base.url_base_datos), modelo_agente=modelo
    )


def test_agente_responde_con_fuentes_y_recuerda(
    servicio_simulado: ServicioAsistente, modelo: ModeloSimulado
) -> None:
    cliente = _cliente(servicio_simulado)
    r = cliente.post(
        "/api/v1/agente", json={"pregunta": "¿Dónde queda la sede principal?", "thread_id": "demo-1"}
    )
    assert r.status_code == 200
    datos = r.json()
    assert (
        datos["thread_id"] == "demo-1"
        and datos["proveedor"] == "simulado"
        and datos["llamadas_herramienta"] == 1
    )
    assert datos["fuentes"] and set(datos["fuentes"][0]) == {"fragmento_id", "titulo", "url"}
    assert datos["fuentes"][0]["url"] in datos["respuesta"]
    r2 = cliente.post("/api/v1/agente", json={"pregunta": "¿Qué pregunté antes?", "thread_id": "demo-1"})
    assert r2.status_code == 200
    humanos = [m.content for m in modelo.recibidos[-1] if isinstance(m, HumanMessage)]
    assert humanos == ["¿Dónde queda la sede principal?", "¿Qué pregunté antes?"]
    _, total = servicio_simulado.repo.listar_interacciones(tarea="agente")
    assert total == 2


@pytest.mark.parametrize(
    "cuerpo",
    [
        {"pregunta": "¿Dónde queda la sede?", "thread_id": "con espacios"},
        {"pregunta": "¿Dónde queda la sede?", "thread_id": ""},
        {"pregunta": "¿Dónde queda la sede?", "thread_id": "x" * 65},
        {"pregunta": "no", "thread_id": "demo"},
        {"pregunta": "¿Dónde queda la sede?"},
    ],
)
def test_agente_valida_la_solicitud_422(servicio_simulado: ServicioAsistente, cuerpo: dict) -> None:
    assert _cliente(servicio_simulado).post("/api/v1/agente", json=cuerpo).status_code == 422


def test_agente_sin_proveedor_503(config_con_base: Configuracion) -> None:
    config = config_con_base.model_copy(update={"proveedor_agente": "anthropic", "anthropic_api_key": None})
    servicio = ServicioAsistente(config, RepositorioAuditoria(config.url_base_datos))
    r = _cliente(servicio).post(
        "/api/v1/agente", json={"pregunta": "¿Dónde queda la sede?", "thread_id": "demo"}
    )
    assert r.status_code == 503
    cuerpo = r.json()
    assert cuerpo["codigo"] == "proveedor_llm_no_disponible"
    assert "FNA_ANTHROPIC_API_KEY" in cuerpo["mensaje"] and "nunca ANTHROPIC_API_KEY" in cuerpo["mensaje"]


def test_agente_ollama_remoto_503(config_con_base: Configuracion) -> None:
    config = config_con_base.model_copy(
        update={"proveedor_agente": "ollama", "ollama_url": "http://192.0.2.10:11434"}
    )
    servicio = ServicioAsistente(config, RepositorioAuditoria(config.url_base_datos))
    r = _cliente(servicio).post(
        "/api/v1/agente", json={"pregunta": "¿Dónde queda la sede?", "thread_id": "demo"}
    )
    assert r.status_code == 503 and "host local" in r.json()["mensaje"]


# ------------------------------------------------------------------------ CLI
def _args(**campos: object) -> argparse.Namespace:
    return argparse.Namespace(**{"pregunta": None, "thread": "cli", "verificar": False, **campos})


def test_cli_verificar_sin_clave(config_con_base: Configuracion, capsys: pytest.CaptureFixture[str]) -> None:
    config = config_con_base.model_copy(update={"proveedor_agente": "anthropic", "anthropic_api_key": None})
    servicio = ServicioAsistente(config, RepositorioAuditoria(config.url_base_datos))
    assert _comando_agente(servicio, _args(verificar=True)) == 1
    salida = capsys.readouterr().out
    assert "Proveedor: anthropic · modelo: claude-haiku-5-5" in salida and "No disponible" in salida


def test_cli_pregunta_e_interactivo(
    servicio_simulado: ServicioAsistente, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    assert (
        _comando_agente(servicio_simulado, _args(pregunta="¿Dónde queda la sede principal?", thread="t-1"))
        == 0
    )
    assert "thread=t-1" in capsys.readouterr().out
    entradas = iter(["¿Qué pregunté antes?", "salir"])
    monkeypatch.setattr("builtins.input", lambda _: next(entradas))
    assert _comando_agente(servicio_simulado, _args(thread="t-1")) == 0
    # El segundo turno no consulta la herramienta: sin evidencia, el código responde con la frase de rechazo.
    assert "no se encuentra en la base de conocimiento" in capsys.readouterr().out
    humanos = [
        m.content for m in servicio_simulado.agente._modelo.recibidos[-1] if isinstance(m, HumanMessage)
    ]  # type: ignore[union-attr]
    assert humanos == ["¿Dónde queda la sede principal?", "¿Qué pregunté antes?"]
    assert _comando_agente(servicio_simulado, _args(pregunta="hola hola", thread="mal hilo")) == 2


def test_cli_error_de_proveedor(config_con_base: Configuracion, capsys: pytest.CaptureFixture[str]) -> None:
    config = config_con_base.model_copy(update={"proveedor_agente": "anthropic", "anthropic_api_key": None})
    servicio = ServicioAsistente(config, RepositorioAuditoria(config.url_base_datos))
    assert _comando_agente(servicio, _args(pregunta="¿Dónde queda la sede?")) == 1
    assert "proveedor_llm_no_disponible" in capsys.readouterr().err
