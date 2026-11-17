"""Memoria persistente (ADR-033): casos 2A y 2B del OpenSpec ``casos-validacion-ignis``, Ley 1581,
enrutamiento de la memoria, Store por usuario y checkpointer SqliteSaver que sobrevive al reinicio
(R03 y R05)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import textwrap
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage, HumanMessage

from fabrica_autopartes.api.dependencias import obtener_servicio
from fabrica_autopartes.api.main import crear_app
from fabrica_autopartes.core.config import Configuracion
from fabrica_autopartes.domain.modelos import Fragmento
from fabrica_autopartes.knowledge.base import BaseConocimiento
from fabrica_autopartes.knowledge.recuperacion import Resultado
from fabrica_autopartes.llm.extractivo import ModeloExtractivo
from fabrica_autopartes.repositories.auditoria import RepositorioAuditoria, RepositorioMemoriaIgnis
from fabrica_autopartes.repositories.memoria_agente import cerrar_store, crear_store
from fabrica_autopartes.services import agente as ag
from fabrica_autopartes.services.agente_ignis_m2 import AVISO_DATO_PERSONAL, AgenteIgnisM2
from fabrica_autopartes.services.asistente import ServicioAsistente
from tests.simulados import ModeloSimulado

CASO_2A = (
    "Trabajo en compras de repuestos, prefiero respuestas breves y me interesan las motocicletas. Recuérdalo."
)
CASO_2B = "¿Qué preferencias tengo guardadas?"
VALORES_2A = ("compras de repuestos", "breve", "motocicletas")


class _Base:
    """Base con un fragmento fijo (la memoria no busca; las rutas RAG sí)."""

    def __init__(self) -> None:
        self.fragmento = Fragmento(
            id="frag-0",
            documento_id="doc-0",
            url="https://ejemplo-fna.test/doc-0",
            titulo="Documento 0",
            seccion="empresa",
            texto="Fanalca fabrica autopartes y distribuye motocicletas Honda en Colombia.",
            tokens_aprox=10,
            orden=0,
        )

    def buscar(self, consulta: str, k: int = 5, recuperador: str | None = None) -> list[Resultado]:
        return [Resultado(fragmento=self.fragmento, puntaje=1.0)][:k]


@pytest.fixture
def agente(tmp_path: Path) -> Any:
    store = crear_store(tmp_path / "store.sqlite")
    yield AgenteIgnisM2(_Base(), RepositorioMemoriaIgnis(tmp_path / "memoria.sqlite"), store)  # type: ignore[arg-type]
    cerrar_store(store)


def _contiene_2a(texto: str) -> bool:
    return all(valor in texto for valor in VALORES_2A)


# ------------------------------------------------------------------ casos 2A y 2B
def test_caso_2a_guarda_tres_preferencias_del_usuario(agente: AgenteIgnisM2) -> None:
    r = agente.ejecutar_turno(CASO_2A, "h1", "u1")
    assert r["ruta_router"] == "memoria_store"
    assert _contiene_2a(r["respuesta"])
    assert agente.store is not None
    guardado = {i.key: i.value["valor"] for i in agente.store.search(("preferencias", "u1"))}
    assert guardado == {
        "area_laboral": "compras de repuestos",
        "formato_respuesta": "breve",
        "linea_producto": "motocicletas",
    }


def test_caso_2b_en_el_mismo_hilo_y_en_un_hilo_nuevo(agente: AgenteIgnisM2) -> None:
    agente.ejecutar_turno(CASO_2A, "h1", "u1")
    mismo_hilo = agente.ejecutar_turno(CASO_2B, "h1", "u1")
    hilo_nuevo = agente.ejecutar_turno(CASO_2B, "h2", "u1")
    for r in (mismo_hilo, hilo_nuevo):
        assert r["ruta_router"] == "memoria_store"
        assert _contiene_2a(r["respuesta"])
    # En el hilo nuevo las preferencias salen del Store, no del historial del hilo.
    assert len(agente.memoria.obtener_historial_recortado("h2")) == 2


def test_caso_2b_otro_usuario_no_ve_las_preferencias(agente: AgenteIgnisM2) -> None:
    agente.ejecutar_turno(CASO_2A, "h1", "u1")
    r = agente.ejecutar_turno(CASO_2B, "h9", "u2")
    assert r["respuesta"] == "No hay preferencias guardadas para este usuario."
    assert not any(valor in r["respuesta"] for valor in VALORES_2A)


_PROCESO = textwrap.dedent(
    """
    import json, os, sys
    from pathlib import Path
    from fabrica_autopartes.repositories.auditoria import RepositorioMemoriaIgnis
    from fabrica_autopartes.repositories.memoria_agente import cerrar_store, crear_store
    from fabrica_autopartes.services.agente_ignis_m2 import AgenteIgnisM2

    datos, mensaje, hilo, usuario = Path(sys.argv[1]), sys.argv[2], sys.argv[3], sys.argv[4]
    store = crear_store(datos / "store.sqlite")
    agente = AgenteIgnisM2(None, RepositorioMemoriaIgnis(datos / "memoria.sqlite"), store)
    r = agente.ejecutar_turno(mensaje, hilo, usuario)
    turnos = len(agente.memoria.obtener_historial_recortado(hilo))
    cerrar_store(store)
    salida = {"pid": os.getpid(), "ruta": r["ruta_router"], "respuesta": r["respuesta"], "turnos": turnos}
    print(json.dumps(salida))
    """
)


def _en_otro_proceso(datos: Path, mensaje: str, hilo: str, usuario: str) -> dict[str, Any]:
    entorno = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    salida = subprocess.run(
        [sys.executable, "-c", _PROCESO, str(datos), mensaje, hilo, usuario],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=entorno,
        check=True,
        timeout=120,
    )
    return json.loads(salida.stdout.strip().splitlines()[-1])


def test_caso_2b_tras_reiniciar_el_backend_con_otro_pid(tmp_path: Path) -> None:
    """Tres procesos distintos sobre los mismos archivos: guardar (2A), recuperar en un hilo nuevo y
    recuperar en el hilo original, cuyo historial también sobrevivió."""
    guardar = _en_otro_proceso(tmp_path, CASO_2A, "h1", "u1")
    hilo_nuevo = _en_otro_proceso(tmp_path, CASO_2B, "h2", "u1")
    hilo_original = _en_otro_proceso(tmp_path, CASO_2B, "h1", "u1")

    assert len({guardar["pid"], hilo_nuevo["pid"], hilo_original["pid"], os.getpid()}) == 4
    assert guardar["ruta"] == hilo_nuevo["ruta"] == "memoria_store"
    assert _contiene_2a(hilo_nuevo["respuesta"])
    assert _contiene_2a(hilo_original["respuesta"])
    assert hilo_original["turnos"] == 4  # 2 turnos del primer proceso + 2 del tercero


# ------------------------------------------------------------------ Ley 1581
def test_autopresentacion_con_orden_no_guarda_nada_y_lo_explica(agente: AgenteIgnisM2) -> None:
    r = agente.ejecutar_turno("Me llamo Ana y trabajo en Empresa X. Recuérdalo.", "h1", "u1")
    assert r["ruta_router"] == "memoria_store"
    assert "Ley 1581" in r["respuesta"]
    assert "Ana" not in r["respuesta"] and "Empresa X" not in r["respuesta"]
    assert agente.store is not None
    assert agente.store.search(("preferencias", "u1")) == []


def test_nombre_descartado_junto_a_un_area_valida_se_avisa(agente: AgenteIgnisM2) -> None:
    r = agente.ejecutar_turno("Me llamo Ana y trabajo en ventas. Recuérdalo.", "h1", "u1")
    assert "área laboral: ventas" in r["respuesta"]
    assert "No se guardan nombres, empresas ni datos de contacto" in r["respuesta"]
    assert "Ana" not in r["respuesta"]


# ------------------------------------------------------------------ enrutamiento de la memoria
@pytest.mark.parametrize(
    "mensaje",
    [
        "Me interesan las motocicletas, ¿qué modelos hay?",
        "¿Fanalca guarda relación con Honda?",
        "Recuerda que la garantía cubre motores, ¿cuánto dura?",
    ],
)
def test_sin_orden_valida_la_pregunta_sigue_por_rag(agente: AgenteIgnisM2, mensaje: str) -> None:
    r = agente.ejecutar_turno(mensaje, "h1", "u1")
    assert r["ruta_router"] == "rag_documental"
    assert agente.store is not None
    assert agente.store.search(("preferencias", "u1")) == []


@pytest.mark.parametrize(
    "mensaje", ["¿Dónde trabajo?", "¿Dónde trabajo yo?", "¿Cómo me llamo?", "¿Cuál es mi nombre?"]
)
def test_preguntas_por_datos_personales_responden_el_aviso(agente: AgenteIgnisM2, mensaje: str) -> None:
    r = agente.ejecutar_turno(mensaje, "h1", "u1")
    assert r["ruta_router"] == "directo"
    assert r["respuesta"] == AVISO_DATO_PERSONAL
    assert r["citas"] == []


@pytest.mark.parametrize(
    "mensaje", ["¿Dónde trabajó el fundador de Fanalca?", "¿Cómo se llamaba antes la empresa?"]
)
def test_preguntas_sobre_fanalca_siguen_por_rag(agente: AgenteIgnisM2, mensaje: str) -> None:
    r = agente.ejecutar_turno(mensaje, "h1", "u1")
    assert r["ruta_router"] == "rag_documental"
    assert r["respuesta"] != AVISO_DATO_PERSONAL


def test_el_saludo_sigue_respondiendo_el_saludo(agente: AgenteIgnisM2) -> None:
    r = agente.ejecutar_turno("Hola", "h1", "u1")
    assert r["ruta_router"] == "directo"
    assert r["respuesta"].startswith("Hola. Soy IGNIS")
    assert r["respuesta"] != AVISO_DATO_PERSONAL


# ------------------------------------------------------------------ servicio y API
def _servicio(config: Configuracion) -> ServicioAsistente:
    return ServicioAsistente(
        config, RepositorioAuditoria(config.url_base_datos), modelo_llm=ModeloExtractivo()
    )


def _texto_sse(cliente: TestClient, mensaje: str, hilo: str) -> str:
    r = cliente.post("/api/v1/ignis/stream", json={"mensaje": mensaje, "thread_id": hilo})
    assert r.status_code == 200
    textos = []
    for linea in r.text.splitlines():
        if linea.startswith("data: ") and linea != "data: [DONE]":
            evento = json.loads(linea.removeprefix("data: "))
            if evento.get("tipo") == "oracion":
                textos.append(evento["texto"])
    return " ".join(textos)


def test_api_y_reinicio_del_servicio_conservan_las_preferencias(config_con_base: Configuracion) -> None:
    """Por la API con una sesión real: 2A en un hilo, 2B en otro, y 2B otra vez con un servicio nuevo sobre el
    mismo directorio de datos."""
    servicio = _servicio(config_con_base)
    app = crear_app()
    app.dependency_overrides[obtener_servicio] = lambda: servicio
    with TestClient(app) as cliente:  # el lifespan cierra la memoria al salir
        assert cliente.post("/api/v1/sesiones", json={"alias": "compras-01"}).status_code == 201
        assert _contiene_2a(_texto_sse(cliente, CASO_2A, "hilo-a"))
        assert _contiene_2a(_texto_sse(cliente, CASO_2B, "hilo-b"))
        user_id = servicio.sesiones.user_id_de("compras-01")

    reiniciado = _servicio(config_con_base)
    try:
        r = reiniciado.responder_ignis(CASO_2B, "hilo-c", user_id)
        assert _contiene_2a(r["respuesta"])
    finally:
        reiniciado.cerrar()


# ------------------------------------------------------------------ checkpointer SqliteSaver (R03)
def test_el_historial_del_agente_sobrevive_al_reiniciar_el_servicio(config_con_base: Configuracion) -> None:
    base = BaseConocimiento(config_con_base.dir_gold)
    primero = ag.ServicioAgente(
        config_con_base, base, ModeloSimulado(guion=[AIMessage(content="Respuesta.")])
    )
    primero.preguntar("¿Dónde queda la sede principal?", "t-persistente")
    antes = primero.historial("t-persistente")
    primero.cerrar()

    segundo = ag.ServicioAgente(config_con_base, base, ModeloSimulado(guion=[]))
    try:
        despues = segundo.historial("t-persistente")
        assert len(despues) == len(antes) > 0
        assert any(isinstance(m, HumanMessage) and "sede principal" in str(m.content) for m in despues)
        assert segundo.historial("otro-hilo") == []
    finally:
        segundo.cerrar()
