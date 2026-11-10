"""faq-visor con proveedor simulado (modelo extractivo inyectado): sin red ni llamadas a Claude."""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from fabrica_autopartes.api.dependencias import obtener_servicio
from fabrica_autopartes.api.main import crear_app
from fabrica_autopartes.services.evaluacion import cargar_preguntas
from fabrica_autopartes.services.faq_visor import (
    NOMBRE_ARCHIVO,
    TIPOS_INCLUIDOS,
    generar_faq_visor,
)

OP = {"proveedor": "extractivo", "modelo": "extractivo"}


def test_solo_preguntas_respondibles_y_guarda_json(servicio) -> None:  # type: ignore[no-untyped-def]
    datos = generar_faq_visor(servicio, OP, maximo=4)
    esperadas = [p for p in cargar_preguntas("v1") if p["tipo"] in TIPOS_INCLUIDOS][:4]
    assert [i["id"] for i in datos["items"]] == [p["id"] for p in esperadas]
    ruta = servicio.config.dir_gold / NOMBRE_ARCHIVO
    guardado = json.loads(ruta.read_text(encoding="utf-8"))
    assert guardado["total"] == 4 and guardado["version_prompt"] == "v3"
    for item in guardado["items"]:
        assert {"id", "pregunta", "respuesta", "rechazo", "fuentes", "fundamentada"} <= item.keys()
        assert all({"fragmento_id", "url"} <= f.keys() for f in item["fuentes"])


def test_nunca_incluye_inyeccion_ni_fuera_de_alcance(servicio) -> None:  # type: ignore[no-untyped-def]
    datos = generar_faq_visor(servicio, OP, guardar=False)
    ids_excluidos = {p["id"] for p in cargar_preguntas("v1") if p["tipo"] != "respondible"}
    assert ids_excluidos and not ids_excluidos & {i["id"] for i in datos["items"]}
    assert "archivo" not in datos


def test_valores_predeterminados_claude_code_sonnet_v3(servicio) -> None:  # type: ignore[no-untyped-def]
    datos = generar_faq_visor(servicio, {}, maximo=1, guardar=False)
    assert (datos["proveedor"], datos["modelo"], datos["version_prompt"]) == ("claude_code", "sonnet", "v3")


@pytest.fixture
def cliente(servicio) -> TestClient:  # type: ignore[no-untyped-def]
    app = crear_app()
    app.dependency_overrides[obtener_servicio] = lambda: servicio
    return TestClient(app)


def test_ruta_faq_visor_404_y_luego_200(cliente: TestClient, servicio) -> None:  # type: ignore[no-untyped-def]
    assert cliente.get("/api/v1/faq-visor").status_code == 404
    generar_faq_visor(servicio, OP, maximo=2)
    r = cliente.get("/api/v1/faq-visor")
    assert r.status_code == 200 and r.json()["total"] == 2
