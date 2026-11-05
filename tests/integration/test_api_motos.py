"""Rutas /api/v1/motos* (fichas curadas y cálculo didáctico)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from fabrica_autopartes.api.main import crear_app


@pytest.fixture
def cliente() -> TestClient:
    return TestClient(crear_app())


def test_listar_y_ficha(cliente: TestClient) -> None:
    lista = cliente.get("/api/v1/motos").json()
    assert [m["id"] for m in lista] == ["cb160f"]
    ficha = cliente.get("/api/v1/motos/cb160f").json()
    assert ficha["ensamblaje_id"] == "moto_honda"
    assert ficha["grupos"]["llantas"]["trasera"]["valor"] == "140/70-17"
    assert ficha["grupos"]["motor"]["cilindrada"]["estado"] == "no_publicado"
    assert all(s["estado"] == "supuesto" for s in ficha["supuestos"])
    assert cliente.get("/api/v1/motos/otra").status_code == 404


def test_faq_determinista_con_fuente(cliente: TestClient) -> None:
    faq = cliente.get("/api/v1/motos/cb160f/faq").json()
    ids = {p["id"] for p in faq}
    assert {"potencia", "std_vs_dlx", "cbs", "llanta_trasera"} <= ids
    llanta = next(p for p in faq if p["id"] == "llanta_trasera")
    assert llanta["campos"] == ["llantas.trasera"] and llanta["fuentes"]
    assert faq == cliente.get("/api/v1/motos/cb160f/faq").json()


def test_calculo(cliente: TestClient) -> None:
    r = cliente.post("/api/v1/motos/cb160f/calculo", json={"rpm": 8000, "marcha": 3})
    assert r.status_code == 200
    cuerpo = r.json()
    assert cuerpo["resultado"]["medida_llanta"] == "140/70-17"
    assert cuerpo["ficha_aplicada"]["modelo"] == "cb160f"
    gen = cliente.post("/api/v1/motos/cb160f/calculo?con_ficha=false", json={"rpm": 8000, "marcha": 3}).json()
    assert gen["ficha_aplicada"] is None and gen["resultado"]["medida_llanta"] == "130/70-17"


@pytest.mark.parametrize(
    "cuerpo",
    [
        {"rpm": -5},
        {"rpm": 99999},
        {"marcha": 9},
        {"marcha": 6},
        {"fuerza_palanca_n": -1},
        {"fuerza_palanca_n": 5000},
        {"palanca": "pie"},
        {"version": "STD", "cbs": True},
        {"rpm": "abc"},
    ],
)
def test_calculo_422(cliente: TestClient, cuerpo: dict) -> None:
    assert cliente.post("/api/v1/motos/cb160f/calculo", json=cuerpo).status_code == 422


def test_calculo_ficha_inexistente(cliente: TestClient) -> None:
    assert cliente.post("/api/v1/motos/otra/calculo", json={}).status_code == 404
