"""tool_use sin tool_result en el historial del agente (ADR-030), sin red y con clave ficticia.

Prueba real (Haiku 5.5): tras un turno con 2 llamadas, el turno siguiente recibió un 400 «tool_use ids were
found without tool_result blocks immediately after». La causa exacta sigue sin confirmar. El único mecanismo
reproducido dentro del agente: un ``AIMessage`` con un bloque ``tool_use`` en ``content`` que no está ni en
``tool_calls`` ni en ``invalid_tool_calls``. Los ``invalid_tool_calls`` ya los responde LangChain
(``_patch_invalid_tool_calls`` en ``langchain.agents.factory``) antes del middleware.
"""

from __future__ import annotations

import logging

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from fabrica_autopartes.core.config import Configuracion
from fabrica_autopartes.knowledge.base import BaseConocimiento
from fabrica_autopartes.services import agente as ag
from tests.simulados import ModeloSimulado, llamada, responder_citando_primera_url

FIRMA = "EqQBCkgIARABGAIiQ" * 20  # firma de un bloque de razonamiento (forma de Haiku 5.5)
PENSAMIENTO = {"type": "thinking", "thinking": "", "signature": FIRMA}


def _con_herramientas(*llamadas: tuple[str, dict]) -> AIMessage:
    """AIMessage como el de ChatAnthropic: razonamiento + bloques tool_use en content, y tool_calls."""
    bloques = [PENSAMIENTO] + [
        {"type": "tool_use", "id": i, "name": "buscar_fragmentos", "input": a} for i, a in llamadas
    ]
    calls = [{"name": "buscar_fragmentos", "args": a, "id": i, "type": "tool_call"} for i, a in llamadas]
    return AIMessage(bloques, tool_calls=calls, response_metadata={"stop_reason": "tool_use"})


def _respuesta_con_tool_use_huerfano(texto: str, id_: str, *, invalida: bool = False) -> AIMessage:
    """Respuesta final con texto y tool_use fuera de tool_calls; con ``invalida``, en invalid_tool_calls."""
    uso = {"type": "tool_use", "id": id_, "name": "buscar_fragmentos", "input": {}}
    llamada_invalida = {"name": "buscar_fragmentos", "args": '{"consulta": ', "id": id_, "error": "JSON"}
    return AIMessage(
        [PENSAMIENTO, {"type": "text", "text": texto}, uso],
        tool_calls=[],
        invalid_tool_calls=[{**llamada_invalida, "type": "invalid_tool_call"}] if invalida else [],
        response_metadata={"stop_reason": "end_turn"},
    )


def _huerfanos_en_la_api(mensajes: list) -> list[str]:
    """Ids de tool_use sin tool_result inmediatamente después, en el formato que recibe la API (sin red)."""
    chat = ChatAnthropic(model="claude-haiku-5-5", api_key="clave-ficticia", max_tokens=1024)
    cuerpo = chat._get_request_payload(mensajes)["messages"]
    faltan: list[str] = []
    for i, m in enumerate(cuerpo):
        if m["role"] != "assistant" or not isinstance(m["content"], list):
            continue
        ids = [b["id"] for b in m["content"] if isinstance(b, dict) and b.get("type") == "tool_use"]
        sig = cuerpo[i + 1]["content"] if i + 1 < len(cuerpo) else []
        resultados = []
        for b in sig if isinstance(sig, list) else []:
            if not (isinstance(b, dict) and b.get("type") == "tool_result"):
                break  # los tool_result deben ir primero
            resultados.append(b["tool_use_id"])
        faltan += [x for x in ids if x not in resultados]
    return faltan


def test_historial_con_tool_use_huerfano_produce_el_400_y_la_reparacion_lo_evita() -> None:
    historial = [
        HumanMessage("¿Dónde queda la sede?"),
        _respuesta_con_tool_use_huerfano("La sede queda en Yumbo.", "toolu_01SctqjrSKm1bpSnwu5AQEWM"),
        HumanMessage("¿Y su teléfono?"),
    ]
    assert _huerfanos_en_la_api(historial) == ["toolu_01SctqjrSKm1bpSnwu5AQEWM"]  # el 400 de la prueba real
    reparados, ids = ag.reparar_resultados_de_herramientas(historial)
    assert ids == ["toolu_01SctqjrSKm1bpSnwu5AQEWM"] and _huerfanos_en_la_api(reparados) == []
    sintetico = reparados[2]
    assert isinstance(sintetico, ToolMessage) and sintetico.content == ag.RESULTADO_SINTETICO
    assert sintetico.tool_call_id == "toolu_01SctqjrSKm1bpSnwu5AQEWM" and sintetico.status == "error"
    assert reparados[1] is historial[1]  # el AIMessage (con su razonamiento firmado) no se modifica
    assert len(historial) == 3  # la lista original no cambia


def test_llamadas_paralelas_y_secuenciales_completas_no_se_tocan() -> None:
    historial = [
        HumanMessage("¿Dónde queda la sede?"),
        _con_herramientas(("toolu_A", {"consulta": "sede"}), ("toolu_B", {"consulta": "dirección"})),
        ToolMessage("resultado A", tool_call_id="toolu_A"),
        ToolMessage("resultado B", tool_call_id="toolu_B"),
        _con_herramientas(("toolu_C", {"consulta": "dirección sede"})),
        ToolMessage("resultado C", tool_call_id="toolu_C"),
        AIMessage([PENSAMIENTO, {"type": "text", "text": "La sede (https://fanalca.com/)."}]),
        HumanMessage("¿Y su teléfono?"),
    ]
    reparados, ids = ag.reparar_resultados_de_herramientas(historial)
    assert ids == [] and reparados == historial and _huerfanos_en_la_api(reparados) == []


class _Registro(logging.Handler):
    def __init__(self) -> None:
        super().__init__(level=logging.INFO)
        self.mensajes: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.mensajes.append(record.getMessage())


ID_ROTO = "toolu_01SctqjrSKm1bpSnwu5AQEWM"


def _dos_turnos(config: Configuracion, *, invalida: bool):
    """Turno 1 con 2 llamadas y respuesta final con tool_use huérfano; turno 2 de seguimiento."""
    modelo = ModeloSimulado(
        guion=[
            _con_herramientas(("toolu_A", {"consulta": "sede"}), ("toolu_B", {"consulta": "dirección"})),
            lambda m: _respuesta_con_tool_use_huerfano(
                str(responder_citando_primera_url("La sede")(m).content), ID_ROTO, invalida=invalida
            ),
            llamada("teléfono de contacto de Fanalca", "c3"),
            responder_citando_primera_url("El teléfono publicado"),
        ]
    )
    agente = ag.ServicioAgente(config, BaseConocimiento(config.dir_gold), modelo)
    registro = _Registro()
    logger = logging.getLogger("fabrica_autopartes.services.agente")
    nivel = logger.level
    logger.addHandler(registro)
    logger.setLevel(logging.INFO)
    try:
        r1 = agente.preguntar("¿Dónde queda la sede principal?", "hilo")
        r2 = agente.preguntar("¿Y cuál es su teléfono?", "hilo")
    finally:
        logger.removeHandler(registro)
        logger.setLevel(nivel)
    return agente, modelo, registro, r1, r2


def test_agente_repara_solo_lo_enviado_y_lo_registra(config_con_base: Configuracion) -> None:
    """El turno siguiente a una respuesta con tool_use huérfano se envía reparado; la memoria no cambia."""
    agente, modelo, registro, r1, r2 = _dos_turnos(config_con_base, invalida=False)
    id_roto = ID_ROTO
    assert r1.llamadas_herramienta == 2 and r1.fuentes
    # Lo enviado al modelo en el turno 2 está reparado y es válido para la API.
    for enviados in modelo.recibidos[2:]:
        sin_sistema = [m for m in enviados if m.type != "system"]
        assert _huerfanos_en_la_api(sin_sistema) == []
        assert any(isinstance(m, ToolMessage) and m.content == ag.RESULTADO_SINTETICO for m in sin_sistema)
    # El sintético no se guarda en la memoria ni cuenta como llamada, fragmento ni fuente.
    assert not any(
        isinstance(m, ToolMessage) and m.content == ag.RESULTADO_SINTETICO for m in agente.historial("hilo")
    )
    assert r2.llamadas_herramienta == 1 and r2.fuentes and r2.respuesta != ag.RECHAZO
    assert all(ag.RESULTADO_SINTETICO not in f.titulo for f in r2.fuentes)
    # Cada reparación queda en el log local con el id; y la respuesta del modelo, con su forma.
    reparaciones = [x for x in registro.mensajes if "tool_use sin tool_result reparado" in x]
    assert reparaciones and all(f"id={id_roto}" in x and "thread=hilo" in x for x in reparaciones)
    formas = [x for x in registro.mensajes if "respuesta del modelo" in x]
    assert any(f"tool_use=['{id_roto}'] · tool_calls=[] · invalid_tool_calls=[]" in x for x in formas)
    assert any("stop_reason=tool_use" in x and "tool_calls=['toolu_A', 'toolu_B']" in x for x in formas)


def test_invalid_tool_calls_los_responde_langchain_y_no_se_reparan(config_con_base: Configuracion) -> None:
    """Con la llamada en invalid_tool_calls, LangChain ya envía su tool_result: sin sintético ni WARNING."""
    _, modelo, registro, _, r2 = _dos_turnos(config_con_base, invalida=True)
    for enviados in modelo.recibidos[2:]:
        sin_sistema = [m for m in enviados if m.type != "system"]
        assert _huerfanos_en_la_api(sin_sistema) == []
        respuestas = [m for m in sin_sistema if isinstance(m, ToolMessage) and m.tool_call_id == ID_ROTO]
        assert len(respuestas) == 1 and respuestas[0].content != ag.RESULTADO_SINTETICO
    assert not any("tool_use sin tool_result reparado" in x for x in registro.mensajes)
    formas = [x for x in registro.mensajes if "respuesta del modelo" in x]
    assert any(f"invalid_tool_calls=['{ID_ROTO}']" in x for x in formas)
    assert r2.llamadas_herramienta == 1 and r2.fuentes and r2.respuesta != ag.RECHAZO
