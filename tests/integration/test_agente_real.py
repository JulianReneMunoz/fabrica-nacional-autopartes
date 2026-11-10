"""Agente con el proveedor real configurado (Ollama local o Anthropic). Se omite si no está disponible.

Es opcional para no consumir la API en cada ``pytest``: se ejecuta solo con ``FNA_PRUEBAS_AGENTE_REAL=1``
y con el proveedor de ``FNA_PROVEEDOR_AGENTE`` disponible (ADR-024). No se ejecuta en CI.

Validación formal (A-08): tres turnos en un mismo ``thread_id`` con los tokens y el costo de cada turno. El
consumo se imprime (``pytest -s``) y queda en ``evaluacion/resultados/<fecha>_agente_3_turnos.json``.
"""

from __future__ import annotations

import json
import os
from collections.abc import Sequence
from datetime import UTC, datetime

import pytest
from langchain_core.messages import AnyMessage, HumanMessage

from fabrica_autopartes.core.config import Configuracion
from fabrica_autopartes.domain.modelos import RespuestaAgente
from fabrica_autopartes.knowledge.base import BaseConocimiento
from fabrica_autopartes.llm.proveedores import verificar_proveedor_agente
from fabrica_autopartes.repositories.auditoria import RepositorioAuditoria
from fabrica_autopartes.services.asistente import ServicioAsistente
from fabrica_autopartes.services.evaluacion import DIR_RESULTADOS
from fabrica_autopartes.services.evaluacion_agente import (
    ConsumoTurno,
    preguntar_con_consumo,
    urls_citadas,
    urls_fuera_de_fuentes,
)

pytestmark = [
    pytest.mark.llm,
    pytest.mark.skipif(
        os.environ.get("FNA_PRUEBAS_AGENTE_REAL") != "1",
        reason="Prueba con modelo real desactivada (definir FNA_PRUEBAS_AGENTE_REAL=1)",
    ),
]

THREAD = "real-1"
PREGUNTA_FUERA_DEL_CORPUS = "¿Cuál es el horario de atención de la sede principal?"  # P20, tipo «ausente»


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


def _comprobar_respuesta_citada(r: RespuestaAgente, turno: str, base: BaseConocimiento) -> None:
    """Busca, cita al menos una URL y toda URL citada es el campo url de una fuente citada o está en su texto
    (regla de A-09)."""
    assert r.llamadas_herramienta >= 1, f"{turno}: debe consultar la herramienta"
    assert not r.rechazo and r.fuentes, f"{turno}: debe responder con al menos una fuente"
    assert urls_citadas(r.respuesta), f"{turno}: debe citar al menos una URL"
    assert urls_fuera_de_fuentes(r, base) == [], f"{turno}: URL citadas que no permite la regla de citas"


def _registrar(consumos: list[tuple[str, RespuestaAgente, ConsumoTurno]]) -> None:
    turnos = [
        {"pregunta": p, "llamadas_herramienta": r.llamadas_herramienta, "rechazo": r.rechazo, **c.resumen()}
        for p, r, c in consumos
    ]
    total = ConsumoTurno([ll for _, _, c in consumos for ll in c.llamadas])
    informe = {
        "fecha": datetime.now(UTC).isoformat(timespec="seconds"),
        "modelo": consumos[0][1].modelo,
        "turnos": turnos,
        "total": total.resumen(),
    }
    for i, t in enumerate(turnos, 1):
        print(
            f"Turno {i}: {t['llamadas_modelo']} llamadas al modelo · entrada {t['tokens_entrada']} · "
            f"salida {t['tokens_salida']} · USD {t['costo_usd']:.5f}"
        )
    print(f"Total: entrada {total.entrada} · salida {total.salida} · USD {total.costo_usd():.5f}")
    DIR_RESULTADOS.mkdir(parents=True, exist_ok=True)
    sello = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    (DIR_RESULTADOS / f"{sello}_agente_3_turnos.json").write_text(
        json.dumps(informe, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n"
    )


def test_agente_real_tres_turnos_cita_recuerda_y_rechaza(
    servicio_real: ServicioAsistente, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Dirección, teléfono como seguimiento («su» = Fanalca) y una pregunta sin respuesta en el corpus.

    No se pregunta por la conversación misma («¿cuál fue mi pregunta anterior?»): sin llamar a la herramienta,
    el código responde con la frase de rechazo (ADR-024).
    """
    from fabrica_autopartes.services import agente as ag

    enviados: list[list[AnyMessage]] = []
    original = ag.recortar_historial

    def espia(mensajes: Sequence[AnyMessage], limite: int) -> list[AnyMessage]:
        recortados = original(mensajes, limite)
        enviados.append(recortados)  # exactamente lo que recibe el modelo real en cada llamada
        return recortados

    monkeypatch.setattr(ag, "recortar_historial", espia)
    consumos: list[tuple[str, RespuestaAgente, ConsumoTurno]] = []

    def turno(pregunta: str) -> RespuestaAgente:
        r, consumo = preguntar_con_consumo(servicio_real, pregunta, THREAD, canal="prueba")
        consumos.append((pregunta, r, consumo))
        return r

    try:
        primera = "¿Dónde queda la sede principal de Fanalca?"
        _comprobar_respuesta_citada(turno(primera), "turno 1", servicio_real.base)

        llamadas_previas = len(enviados)
        _comprobar_respuesta_citada(turno("¿Y cuál es su teléfono?"), "turno 2", servicio_real.base)
        humanos = [m.content for m in enviados[llamadas_previas] if isinstance(m, HumanMessage)]
        assert primera in humanos, "el modelo debe recibir la primera pregunta del hilo (memoria)"

        r3 = turno(PREGUNTA_FUERA_DEL_CORPUS)
        assert r3.rechazo, "turno 3: debe marcarse como rechazo"
        assert r3.fuentes == [] and not r3.fundamentada, "turno 3: un rechazo no lleva fuentes"
        assert not (
            r3.bloqueada or r3.limite_alcanzado or r3.respuesta_truncada or r3.rechazada_por_seguridad
        )
        assert r3.respuesta == ag.RECHAZO
    finally:
        if consumos:
            _registrar(consumos)  # también si una aserción falla: el gasto queda registrado
