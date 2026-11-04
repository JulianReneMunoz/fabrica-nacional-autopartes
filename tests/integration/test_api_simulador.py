"""Contratos de la API del simulador 3D y de la biblioteca de máquinas."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from fabrica_autopartes.api.dependencias import obtener_servicio
from fabrica_autopartes.api.main import crear_app

BASE = "/api/v1/simulador/ensamblajes/freno_disco"


@pytest.fixture
def cliente(servicio):  # type: ignore[no-untyped-def]
    app = crear_app()
    app.dependency_overrides[obtener_servicio] = lambda: servicio
    return TestClient(app)


def test_consultas_basicas(cliente) -> None:  # type: ignore[no-untyped-def]
    assert cliente.get("/api/v1/simulador/ensamblajes").json()[0]["piezas"] == 15
    assert cliente.get(BASE).json()["advertencia"].startswith("Modelo de demostración")
    assert len(cliente.get(f"{BASE}/jerarquia").json()["hijos"]) == 3
    assert cliente.get(f"{BASE}/piezas/piston").json()["tipo"] == "piston"
    assert cliente.get(f"{BASE}/piezas/fantasma").status_code == 404
    assert cliente.get("/api/v1/simulador/ensamblajes/otro").status_code == 404
    assert len(cliente.get(f"{BASE}/articulaciones").json()) >= 7


def test_despiece_y_secuencias(cliente) -> None:  # type: ignore[no-untyped-def]
    assert cliente.get(f"{BASE}/despiece", params={"factor": 2}).status_code == 422
    pos = cliente.get(f"{BASE}/despiece", params={"factor": 0}).json()
    assert pos["piston"] == cliente.get(f"{BASE}/piezas/piston").json()["transformacion"]["posicion"]
    des = cliente.get(f"{BASE}/secuencia").json()
    assert cliente.get(f"{BASE}/secuencia", params={"modo": "reensamblaje"}).json() == des[::-1]


def test_cinematica_valida_limites(cliente) -> None:  # type: ignore[no-untyped-def]
    ok = cliente.post(f"{BASE}/cinematica", json={"valores": {"j_rueda": 30, "j_piston": 0.001}})
    assert ok.status_code == 200 and "disco" in ok.json()
    assert cliente.post(f"{BASE}/cinematica", json={"valores": {"j_piston": 1.0}}).status_code == 422
    assert cliente.post(f"{BASE}/cinematica", json={"valores": {"j_soporte": 1.0}}).status_code == 422


def test_calculo_freno(cliente) -> None:  # type: ignore[no-untyped-def]
    r = cliente.post(f"{BASE}/calculo-freno", json={"presion_bar": 20})
    assert r.status_code == 200 and r.json()["par_frenado_nm"] > 0
    assert cliente.post(f"{BASE}/calculo-freno", json={"presion_bar": -1}).status_code == 422


def test_estados_validados_y_persistidos(cliente) -> None:  # type: ignore[no-untyped-def]
    estado = {
        "modo": "despiece",
        "factor_despiece": 0.6,
        "ocultas": ["disco"],
        "seleccionada": "piston",
        "valores_articulacion": {"j_rueda": 15},
    }
    r = cliente.post(f"{BASE}/estados", json={"nombre": "vista pinza", "estado": estado})
    assert r.status_code == 201
    id_ = r.json()["id"]
    assert cliente.get(f"/api/v1/simulador/estados/{id_}").json()["estado"]["factor_despiece"] == 0.6
    assert cliente.get(f"{BASE}/estados").json()[0]["nombre"] == "vista pinza"
    malo = {**estado, "ocultas": ["inventada"]}
    assert cliente.post(f"{BASE}/estados", json={"nombre": "x", "estado": malo}).status_code == 422
    fuera = {**estado, "valores_articulacion": {"j_piston": 5}}
    assert cliente.post(f"{BASE}/estados", json={"nombre": "x", "estado": fuera}).status_code == 422
    assert (
        cliente.post(
            f"{BASE}/estados", json={"nombre": "x", "estado": {**estado, "camara": [99, 0, 0]}}
        ).status_code
        == 422
    )


def test_eventos(cliente) -> None:  # type: ignore[no-untyped-def]
    assert cliente.post(f"{BASE}/eventos", json={"tipo": "seleccion", "pieza_id": "disco"}).status_code == 201
    assert cliente.post(f"{BASE}/eventos", json={"tipo": "seleccion", "pieza_id": "x"}).status_code == 422
    assert cliente.get(f"{BASE}/eventos").json()[0]["pieza_id"] == "disco"


@pytest.mark.parametrize(
    ("pregunta", "intencion"),
    [
        ("¿Qué función cumple esta pieza?", "funcion"),
        ("¿A qué conjunto pertenece?", "conjunto"),
        ("¿Cuáles son sus componentes relacionados?", "relacionadas"),
        ("¿Qué movimiento realiza?", "movimiento"),
        ("¿Qué documentación técnica está disponible?", "documentacion"),
        ("¿Qué piezas deben retirarse primero para desmontar el conjunto?", "retirar"),
        ("¿Cuál es el torque de apriete para reparar la pinza?", "seguridad"),
    ],
)
def test_preguntas_sobre_piezas(cliente, pregunta, intencion) -> None:  # type: ignore[no-untyped-def]
    r = cliente.post(f"{BASE}/preguntar", json={"pieza_id": "cuerpo_pinza", "pregunta": pregunta}).json()
    assert r["intencion"] == intencion
    if intencion == "seguridad":
        assert "No se generan procedimientos" in r["respuesta_modelo"] and r["documentado"] == []
    else:
        assert all(d["url"].startswith("https://") for d in r["documentado"])


def test_biblioteca_de_maquinas_usa_la_base(cliente) -> None:  # type: ignore[no-untyped-def]
    maquinas = cliente.get("/api/v1/maquinas").json()
    assert [m["id"] for m in maquinas] == ["freno", "prensa", "linea"]
    for m in maquinas:
        assert m["datos_empresa"] and all(d["url"].startswith("https://") for d in m["datos_empresa"])
    linea = cliente.get("/api/v1/maquinas/linea").json()
    capacidad = linea["parametros"][0]
    assert capacidad["valor"] == 24000 and capacidad["procedencia"] == "base_conocimiento"
    assert cliente.get("/api/v1/maquinas/otra").status_code == 404
