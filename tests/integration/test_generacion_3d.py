"""Generación procedural del GLB: carga, nodos, mallas cerradas y reproducibilidad."""

from __future__ import annotations

import json

import pytest
import trimesh

from fabrica_autopartes.simulador.catalogo_freno import ParametrosFreno
from fabrica_autopartes.simulador.generacion import generar


@pytest.fixture(scope="module")
def generado(tmp_path_factory):  # type: ignore[no-untyped-def]
    destino = tmp_path_factory.mktemp("glb")
    return destino, generar(destino)


def test_glb_carga_con_nodos_por_pieza(generado) -> None:  # type: ignore[no-untyped-def]
    destino, manifiesto = generado
    escena = trimesh.load(destino / "freno_disco.glb")
    nodos = set(escena.graph.nodes_geometry)
    assert {p["nodo"] for p in manifiesto["piezas"]} <= nodos
    assert len(escena.geometry) == 15


def test_manifiesto_completo_y_mallas_cerradas(generado) -> None:  # type: ignore[no-untyped-def]
    destino, manifiesto = generado
    en_disco = json.loads((destino / "freno_disco.manifiesto.json").read_text(encoding="utf-8"))
    assert en_disco == manifiesto
    assert all(p["cerrada"] and p["volumen_m3"] > 0 for p in manifiesto["piezas"])
    assert set(manifiesto["procedencia_parametros"].values()) == {"demostrativo"}


def test_generacion_reproducible(generado, tmp_path) -> None:  # type: ignore[no-untyped-def]
    _, primero = generado
    assert generar(tmp_path)["sha256"] == primero["sha256"]


def test_parametros_alteran_la_geometria(tmp_path) -> None:  # type: ignore[no-untyped-def]
    otro = generar(tmp_path, ParametrosFreno(diametro_disco=0.32, radio_efectivo=0.13))
    disco = next(p for p in otro["piezas"] if p["id"] == "disco")
    assert disco["limites_locales_m"][1][0] == pytest.approx(0.16, abs=1e-3)
