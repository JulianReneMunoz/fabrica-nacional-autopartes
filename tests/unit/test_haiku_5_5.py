"""Compatibilidad con Claude Haiku 5.5 (ADR-028), sin red ni clave real.

- No se envían temperature, top_p ni top_k a los modelos Claude 5.x (ni en el cuerpo ni en ``extra_body``).
- Un 400 de Anthropic llega como ``ErrorProveedorLLM`` con un mensaje claro (agente y Q&A).
- ``stop_reason: "refusal"`` se muestra como rechazo, solo en el turno en que ocurre.
"""

from __future__ import annotations

import httpx
import pytest
from langchain_core.messages import AIMessage, HumanMessage
from pydantic import SecretStr

from fabrica_autopartes.core.config import Configuracion
from fabrica_autopartes.core.excepciones import ErrorProveedorLLM
from fabrica_autopartes.knowledge.base import BaseConocimiento
from fabrica_autopartes.llm import proveedores as pv
from fabrica_autopartes.repositories.auditoria import RepositorioAuditoria
from fabrica_autopartes.services import agente as ag
from fabrica_autopartes.services.asistente import ServicioAsistente
from tests.simulados import ModeloSimulado, llamada, responder_citando_primera_url

MUESTREO = ("temperature", "top_p", "top_k")
ID_SOLICITUD = "req_011CgrZ1YPt63B8jXatHpBYJ"  # el de la prueba real en Streamlit


def _parametros_enviados(modelo: object) -> dict:
    """Cuerpo de la solicitud que ChatAnthropic enviaría (sin red), incluido ``extra_body``."""
    cuerpo = modelo._get_request_payload([HumanMessage("hola")])  # type: ignore[attr-defined]
    return {**cuerpo, **(cuerpo.get("extra_body") or {})}


def error_400_como_en_streamlit() -> Exception:
    """``AnthropicInvalidRequestError`` real, encadenado a un ``BadRequestError`` (``raise ... from ...``)."""
    import anthropic
    from langchain_anthropic.chat_models import AnthropicInvalidRequestError

    respuesta = httpx.Response(
        400,
        request=httpx.Request("POST", "https://api.anthropic.com/v1/messages"),
        headers={"request-id": ID_SOLICITUD},
    )
    cuerpo = {
        "type": "error",
        "error": {"type": "invalid_request_error", "message": "temperature: Extra inputs are not permitted"},
    }
    original = anthropic.BadRequestError(
        "temperature: Extra inputs are not permitted", response=respuesta, body=cuerpo
    )
    try:
        try:
            raise original
        except anthropic.BadRequestError as e:
            raise AnthropicInvalidRequestError(message=e.message, response=e.response, body=e.body) from e
    except AnthropicInvalidRequestError as envuelto:
        return envuelto


# ------------------------------------------------------------------ parámetros de muestreo
@pytest.mark.parametrize(
    ("modelo", "esperado"),
    [
        ("claude-haiku-5-5", True),
        ("claude-sonnet-5-5", True),
        ("claude-opus-5-5", True),
        ("claude-sonnet-5", True),
        ("claude-fable-5-1", True),
        ("claude-haiku-4-5", False),
        ("claude-sonnet-4-6", False),
        ("llama3.2:3b", False),
    ],
)
def test_familia_claude_5_sin_muestreo(modelo: str, esperado: bool) -> None:
    assert pv.modelo_sin_parametros_de_muestreo(modelo) is esperado


def test_agente_con_haiku_5_5_no_envia_parametros_de_muestreo(config_con_base: Configuracion) -> None:
    config = config_con_base.model_copy(
        update={"proveedor_agente": "anthropic", "anthropic_api_key": SecretStr("clave-de-prueba")}
    )
    enviados = _parametros_enviados(pv.crear_modelo_agente(config))
    assert enviados["model"] == "claude-haiku-5-5"
    assert not set(MUESTREO) & set(enviados), enviados


def test_qa_con_haiku_5_5_no_envia_parametros_de_muestreo(config_con_base: Configuracion) -> None:
    config = config_con_base.model_copy(update={"anthropic_api_key": SecretStr("clave-de-prueba")})
    enviados = _parametros_enviados(pv.crear_modelo(config, "anthropic", "claude-haiku-5-5"))
    assert not set(MUESTREO) & set(enviados), enviados


def test_modelos_anteriores_conservan_la_temperatura(config_con_base: Configuracion) -> None:
    """FNA_TEMPERATURA sigue llegando a los modelos que la aceptan (no se cambia para los demás)."""
    config = config_con_base.model_copy(update={"anthropic_api_key": SecretStr("clave-de-prueba")})
    enviados = _parametros_enviados(pv.crear_modelo(config, "anthropic", "claude-haiku-4-5"))
    assert enviados.get("temperature") == config.temperatura


# ------------------------------------------------------------------------ errores 400
def test_traducir_el_400_real_de_langchain_anthropic() -> None:
    exc = error_400_como_en_streamlit()
    assert (
        type(exc).__name__ == "AnthropicInvalidRequestError"
        and type(exc.__cause__).__name__ == "BadRequestError"
    )
    traducido = pv.traducir_error_anthropic(exc)
    assert isinstance(traducido, ErrorProveedorLLM) and traducido.estado_http == 503
    mensaje = str(traducido)
    assert "rechazó la solicitud (400)" in mensaje and "Extra inputs are not permitted" in mensaje
    assert ID_SOLICITUD in mensaje and "ADR-028" in mensaje
    assert pv.MENSAJE_CREDENCIALES not in mensaje  # separado de credenciales
    assert pv.traducir_error_anthropic(ValueError("otro")) is None  # lo demás no se toca


def test_400_en_el_agente_llega_como_error_claro(config_con_base: Configuracion) -> None:
    agente = ag.ServicioAgente(
        config_con_base,
        BaseConocimiento(config_con_base.dir_gold),
        ModeloSimulado(guion=[error_400_como_en_streamlit()]),
    )
    with pytest.raises(ErrorProveedorLLM, match=r"rechazó la solicitud \(400\)") as error:
        agente.preguntar("¿Dónde queda la sede?", "t1")
    assert "no respondió" not in str(error.value) and ID_SOLICITUD in str(error.value)


def test_400_en_el_qa_llega_como_error_claro(config_con_base: Configuracion) -> None:
    servicio = ServicioAsistente(
        config_con_base,
        RepositorioAuditoria(config_con_base.url_base_datos),
        modelo_llm=ModeloSimulado(guion=[error_400_como_en_streamlit()]),
    )
    with pytest.raises(ErrorProveedorLLM, match=r"rechazó la solicitud \(400\)"):
        servicio.responder("¿Dónde queda la sede?", proveedor="anthropic", modo_contexto="seleccion")


# --------------------------------------------------------------------------- refusal
def _rechazo() -> AIMessage:
    return AIMessage("", response_metadata={"stop_reason": "refusal"})


def test_refusal_en_el_agente(config_con_base: Configuracion) -> None:
    agente = ag.ServicioAgente(
        config_con_base,
        BaseConocimiento(config_con_base.dir_gold),
        ModeloSimulado(guion=[llamada("sede", "c1"), _rechazo()]),
    )
    r = agente.preguntar("¿Dónde queda la sede?", "t1")
    assert r.rechazada_por_seguridad and r.respuesta == pv.MENSAJE_RECHAZO_SEGURIDAD
    assert r.fuentes == [] and not r.fundamentada


def test_refusal_de_un_turno_no_marca_el_siguiente(config_con_base: Configuracion) -> None:
    agente = ag.ServicioAgente(
        config_con_base,
        BaseConocimiento(config_con_base.dir_gold),
        ModeloSimulado(
            guion=[_rechazo(), llamada("sede principal", "c2"), responder_citando_primera_url("La sede")]
        ),
    )
    assert agente.preguntar("Pregunta que el modelo declina", "t1").rechazada_por_seguridad
    r2 = agente.preguntar("¿Dónde queda la sede principal?", "t1")
    assert not r2.rechazada_por_seguridad and r2.respuesta != pv.MENSAJE_RECHAZO_SEGURIDAD and r2.fuentes
    assert any(isinstance(m, AIMessage) and pv.es_rechazo_de_seguridad(m) for m in agente.historial("t1"))


# ---------------------------------------------------------------------- max_tokens
def test_max_tokens_por_defecto_16000_con_limite_32000(monkeypatch: pytest.MonkeyPatch) -> None:
    """Haiku 5.5 razona por defecto y eso cuenta en max_tokens: 16000 (ejemplo de la guía de migración)."""
    from pydantic import ValidationError

    monkeypatch.delenv("FNA_AGENTE_MAX_TOKENS", raising=False)
    assert Configuracion(_env_file=None).agente_max_tokens == 16000  # type: ignore[call-arg]
    assert Configuracion(_env_file=None, agente_max_tokens=32000).agente_max_tokens == 32000  # type: ignore[call-arg]
    with pytest.raises(ValidationError):
        Configuracion(_env_file=None, agente_max_tokens=32001)  # type: ignore[call-arg]


def test_respuesta_cortada_por_max_tokens_tiene_mensaje_propio(config_con_base: Configuracion) -> None:
    """Si el razonamiento agota max_tokens, no se muestra la frase de rechazo («no se encuentra…»)."""
    cortada = AIMessage("", response_metadata={"stop_reason": "max_tokens"})
    agente = ag.ServicioAgente(
        config_con_base,
        BaseConocimiento(config_con_base.dir_gold),
        ModeloSimulado(guion=[llamada("sede", "c1"), cortada]),
    )
    r = agente.preguntar("¿Dónde queda la sede?", "t1")
    assert r.respuesta_truncada and r.respuesta == ag.MENSAJE_TRUNCADO and r.respuesta != ag.RECHAZO
    assert r.fuentes == [] and not r.fundamentada and not r.rechazada_por_seguridad


def test_max_tokens_de_un_turno_no_marca_el_siguiente(config_con_base: Configuracion) -> None:
    agente = ag.ServicioAgente(
        config_con_base,
        BaseConocimiento(config_con_base.dir_gold),
        ModeloSimulado(
            guion=[
                AIMessage("", response_metadata={"stop_reason": "max_tokens"}),
                llamada("sede principal", "c2"),
                responder_citando_primera_url("La sede"),
            ]
        ),
    )
    assert agente.preguntar("Pregunta larga", "t1").respuesta_truncada
    r2 = agente.preguntar("¿Dónde queda la sede principal?", "t1")
    assert not r2.respuesta_truncada and r2.fuentes and r2.respuesta != ag.MENSAJE_TRUNCADO
