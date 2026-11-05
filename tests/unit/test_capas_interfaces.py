"""Regla de capas para las interfaces: solo importan de ``services`` (no de ``llm.salvaguardas``)."""

from __future__ import annotations

import ast
from pathlib import Path

from fabrica_autopartes.llm import salvaguardas
from fabrica_autopartes.services import asistente

RAIZ = Path(__file__).resolve().parents[2]
PROHIBIDOS = ("fabrica_autopartes.llm.cadenas", "fabrica_autopartes.llm.salvaguardas")


def _importaciones(ruta: Path) -> list[str]:
    arbol = ast.parse(ruta.read_text(encoding="utf-8"))
    modulos: list[str] = []
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.ImportFrom) and nodo.module:
            modulos.append(nodo.module)
        elif isinstance(nodo, ast.Import):
            modulos.extend(a.name for a in nodo.names)
    return modulos


def test_es_rechazo_se_reexporta_desde_services() -> None:
    assert asistente.es_rechazo is salvaguardas.es_rechazo
    assert asistente.es_rechazo(
        "La información solicitada no se encuentra en la base de conocimiento de Fanalca."
    )
    assert not asistente.es_rechazo("Fanalca fue fundada en 1958.")


def test_streamlit_no_importa_llm_cadenas_ni_salvaguardas() -> None:
    modulos = _importaciones(RAIZ / "frontend" / "app.py")
    assert not [m for m in modulos if m in PROHIBIDOS]
    # y obtiene la función desde la capa de servicios
    arbol = ast.parse((RAIZ / "frontend" / "app.py").read_text(encoding="utf-8"))
    nombres = {
        a.name
        for n in ast.walk(arbol)
        if isinstance(n, ast.ImportFrom) and n.module == "fabrica_autopartes.services.asistente"
        for a in n.names
    }
    assert "es_rechazo" in nombres
