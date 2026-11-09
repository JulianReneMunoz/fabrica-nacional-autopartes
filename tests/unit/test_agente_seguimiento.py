"""Preguntas de seguimiento en el agente (ADR-029), sin red: prompt v2 y log de diagnóstico."""

from __future__ import annotations

import ast
import logging

from langchain_core.messages import AIMessage, SystemMessage

from fabrica_autopartes.core.config import Configuracion
from fabrica_autopartes.knowledge.base import BaseConocimiento
from fabrica_autopartes.llm.catalogo_prompts import obtener_prompt
from fabrica_autopartes.services import agente as ag
from tests.simulados import ModeloSimulado, llamada, responder_citando_primera_url

PRIMERA = "¿Dónde queda la sede principal?"
SEGUIMIENTO = "¿Y cuál es su teléfono?"


def _agente(config: Configuracion, *guion: object) -> ag.ServicioAgente:
    return ag.ServicioAgente(config, BaseConocimiento(config.dir_gold), ModeloSimulado(guion=list(guion)))


def test_seguimiento_sin_busqueda_sigue_en_rechazo(config_con_base: Configuracion) -> None:
    """Reproduce la prueba real: el turno 2 responde sin llamar a la herramienta → frase de rechazo."""
    agente = _agente(
        config_con_base,
        llamada("sede principal", "c1"),
        responder_citando_primera_url("La sede"),
        AIMessage("El teléfono es (57) 2 651 5343."),  # responde desde el historial, sin buscar
    )
    agente.preguntar(PRIMERA, "real")
    r2 = agente.preguntar(SEGUIMIENTO, "real")
    assert r2.llamadas_herramienta == 0 and r2.respuesta == ag.RECHAZO and r2.fuentes == []


def test_prompt_v2_por_defecto_pide_buscar_en_cada_turno(config_con_base: Configuracion) -> None:
    modelo = ModeloSimulado(guion=[llamada("sede principal", "c1"), responder_citando_primera_url("La sede")])
    agente = ag.ServicioAgente(config_con_base, BaseConocimiento(config_con_base.dir_gold), modelo)
    r = agente.preguntar(PRIMERA, "t1")
    assert r.version_prompt == "v2"
    sistema = str(next(m for m in modelo.recibidos[0] if isinstance(m, SystemMessage)).content)
    assert "En CADA turno" in sistema and "reformúlala" in sistema
    assert "sin\n   formato Markdown" in sistema or "sin formato Markdown" in sistema.replace("\n   ", " ")


def test_seguimiento_reformulado_responde_con_fuente(config_con_base: Configuracion) -> None:
    """Con la v2, el seguimiento se reformula, se busca en el turno y la respuesta cita una fuente válida."""
    agente = _agente(
        config_con_base,
        llamada("sede principal", "c1"),
        responder_citando_primera_url("La sede"),
        llamada("teléfono de contacto de Fanalca", "c2"),
        responder_citando_primera_url("El teléfono publicado"),
    )
    agente.preguntar(PRIMERA, "real")
    r2 = agente.preguntar(SEGUIMIENTO, "real")
    assert r2.llamadas_herramienta == 1 and r2.fuentes and r2.respuesta != ag.RECHAZO
    assert r2.fuentes[0].url in r2.respuesta


def test_la_v1_del_prompt_se_conserva() -> None:
    v1 = obtener_prompt("agente", "v1")
    assert "Puedes usar la conversación previa para entender referencias" in v1.sistema
    assert "En CADA turno" not in v1.sistema


class _Registro(logging.Handler):
    """Manejador propio: funciona aunque pytest se ejecute con ``-p no:logging`` (sin ``caplog``)."""

    def __init__(self) -> None:
        super().__init__(level=logging.INFO)
        self.mensajes: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.mensajes.append(record.getMessage())


def test_log_de_diagnostico(config_con_base: Configuracion) -> None:
    """Solo en el log local: hilo, mensajes, tokens, llamadas y la respuesta original (500 caracteres)."""
    larga = "Respuesta sin búsqueda. " + "x" * 800
    agente = _agente(config_con_base, AIMessage(larga))
    registro = _Registro()
    logger = logging.getLogger("fabrica_autopartes.services.agente")
    nivel_anterior = logger.level
    logger.addHandler(registro)
    logger.setLevel(logging.INFO)
    try:
        r = agente.preguntar(SEGUIMIENTO, "hilo-diag")
    finally:
        logger.removeHandler(registro)
        logger.setLevel(nivel_anterior)
    assert r.respuesta == ag.RECHAZO
    lineas = registro.mensajes
    llamada_modelo = next(x for x in lineas if "llamada al modelo" in x)
    assert (
        "thread=hilo-diag" in llamada_modelo and "mensajes=" in llamada_modelo and "tokens≈" in llamada_modelo
    )
    turno = next(x for x in lineas if "Agente · turno" in x)
    assert "thread=hilo-diag" in turno and "llamadas=0" in turno and "reemplazada=sí" in turno
    original = turno.split("respuesta original=", 1)[1]
    assert original.startswith("'Respuesta sin búsqueda.") and len(ast.literal_eval(original)) == 500
    texto = " ".join(lineas).lower()
    for prohibido in ("api_key", "x-api-key", "authorization", "sk-" + "ant"):
        assert prohibido not in texto
