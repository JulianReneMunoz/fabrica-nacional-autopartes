"""Batería de 20 preguntas de la fase 0 contra el motor de reglas de IGNIS (base Gold versionada, sin red).

Las preguntas y las palabras clave esperadas viven en ``tests/fixtures/ignis_bateria.json``; las respuestas
de referencia, antes y después de este cambio, en ``ignis_respuestas_antes.json`` e
``ignis_respuestas_despues.json``.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pytest

from fabrica_autopartes.core.config import RAIZ_PROYECTO
from fabrica_autopartes.knowledge.base import BaseConocimiento
from fabrica_autopartes.repositories.auditoria import RepositorioMemoriaIgnis
from fabrica_autopartes.repositories.memoria_agente import cerrar_store, crear_store
from fabrica_autopartes.services.agente_ignis_m2 import AgenteIgnisM2

FIXTURES = RAIZ_PROYECTO / "tests" / "fixtures"
BATERIA: list[dict[str, Any]] = json.loads((FIXTURES / "ignis_bateria.json").read_text(encoding="utf-8"))
# Restos técnicos que nunca llegan al cliente (sección «Pruebas» del documento de respuestas naturales).
PROHIBIDO = re.compile(
    r"\[[\w-]+\]|https?://|[{}`|]|Pydantic|BM25|corpus|fragmento|router|[Ee]nrutamiento|thread"
    r"|cotizaci[oó]n de ejemplo|Autor de la entrada"
)
MAX_PALABRAS = 120


@pytest.fixture(scope="module")
def respuestas(tmp_path_factory: pytest.TempPathFactory) -> list[dict[str, Any]]:
    """Las 20 preguntas en un mismo hilo y en orden, como en la fase 0 (la memoria del caso 2A va en el
    medio)."""
    tmp: Path = tmp_path_factory.mktemp("bateria")
    store = crear_store(tmp / "store.sqlite")
    agente = AgenteIgnisM2(
        BaseConocimiento(RAIZ_PROYECTO / "data" / "gold"),
        RepositorioMemoriaIgnis(tmp / "memoria.sqlite"),
        store,
    )
    try:
        return [agente.ejecutar_turno(p["pregunta"], "bateria-fase0", "usuario-bateria") for p in BATERIA]
    finally:
        cerrar_store(store)


def test_la_bateria_tiene_las_20_preguntas_de_la_fase_0() -> None:
    antes = json.loads((FIXTURES / "ignis_respuestas_antes.json").read_text(encoding="utf-8"))
    assert [p["pregunta"] for p in BATERIA] == [r["pregunta"] for r in antes]
    assert len(BATERIA) == 20


@pytest.mark.parametrize("indice", range(len(BATERIA)), ids=[p["pregunta"][:40] for p in BATERIA])
def test_cada_respuesta_es_para_el_cliente(respuestas: list[dict[str, Any]], indice: int) -> None:
    pregunta, resultado = BATERIA[indice], respuestas[indice]
    texto = resultado["respuesta"]
    assert not PROHIBIDO.search(texto), PROHIBIDO.search(texto)
    assert texto.rstrip()[-1] in ".?!"
    assert len(texto.split()) <= MAX_PALABRAS
    for clave in pregunta["claves"]:
        assert clave in texto, (clave, texto)
    assert resultado["ruta_router"] == pregunta["ruta"]
    assert resultado["bloqueada"] is (pregunta["categoria"] == "agresiva")
    assert all(a["tipo"] != "cotizacion" for a in resultado["archivos_adjuntos"])
