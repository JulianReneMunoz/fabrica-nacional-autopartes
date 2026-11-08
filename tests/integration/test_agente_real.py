"""Agente con el proveedor real configurado (Ollama local o Anthropic). Se omite si no está disponible.

Es opcional para no consumir la API en cada ``pytest``: se ejecuta solo con ``FNA_PRUEBAS_AGENTE_REAL=1``
y con el proveedor de ``FNA_PROVEEDOR_AGENTE`` disponible (ADR-024). No se ejecuta en CI.
"""

from __future__ import annotations

import os

import pytest

from fabrica_autopartes.core.config import Configuracion
from fabrica_autopartes.llm.proveedores import verificar_proveedor_agente
from fabrica_autopartes.repositories.auditoria import RepositorioAuditoria
from fabrica_autopartes.services.asistente import ServicioAsistente

pytestmark = [
    pytest.mark.llm,
    pytest.mark.skipif(
        os.environ.get("FNA_PRUEBAS_AGENTE_REAL") != "1",
        reason="Prueba con modelo real desactivada (definir FNA_PRUEBAS_AGENTE_REAL=1)",
    ),
]


@pytest.fixture
def servicio_real(config_con_base: Configuracion) -> ServicioAsistente:
    real = Configuracion()  # proveedor y claves del entorno del usuario (.env)
    config = config_con_base.model_copy(
        update={
            k: getattr(real, k)
            for k in (
                "proveedor_agente",
                "modelo_ollama",
                "modelo_anthropic",
                "ollama_url",
                "anthropic_api_key",
            )
        }
    )
    estado = verificar_proveedor_agente(config, consultar=True)
    if not estado.disponible:
        pytest.skip(f"Proveedor del agente no disponible: {estado.mensaje}")
    return ServicioAsistente(config, RepositorioAuditoria(config.url_base_datos))


def test_agente_real_cita_y_recuerda_en_un_seguimiento(
    servicio_real: ServicioAsistente, monkeypatch: pytest.MonkeyPatch
) -> None:
    """El seguimiento «¿Y cuál es su teléfono?» depende del primer turno («su» = Fanalca) y exige buscar.

    No se pregunta por la conversación misma («¿cuál fue mi pregunta anterior?»): sin llamar a la herramienta,
    el código responde con la frase de rechazo (ADR-024).
    """
    from langchain_core.messages import HumanMessage

    from fabrica_autopartes.services import agente as ag

    enviados: list[list] = []
    original = ag.recortar_historial

    def espia(mensajes, limite):  # type: ignore[no-untyped-def]
        recortados = original(mensajes, limite)
        enviados.append(recortados)  # exactamente lo que recibe el modelo real en cada llamada
        return recortados

    monkeypatch.setattr(ag, "recortar_historial", espia)
    primera = "¿Dónde queda la sede principal de Fanalca?"
    r = servicio_real.preguntar_agente(primera, "real-1", canal="prueba")
    assert r.llamadas_herramienta >= 1 and r.fuentes and any(f.url in r.respuesta for f in r.fuentes)

    llamadas_previas = len(enviados)
    r2 = servicio_real.preguntar_agente("¿Y cuál es su teléfono?", "real-1", canal="prueba")
    assert r2.llamadas_herramienta >= 1, "el seguimiento debe consultar la herramienta"
    assert r2.respuesta != ag.RECHAZO and r2.fuentes, "debe citar al menos una fuente válida"
    assert all(f.url in r2.respuesta or f.fragmento_id in r2.respuesta for f in r2.fuentes)
    humanos = [m.content for m in enviados[llamadas_previas] if isinstance(m, HumanMessage)]
    assert primera in humanos, "el modelo debe recibir la primera pregunta del hilo (memoria)"
