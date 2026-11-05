"""Generación procedural del GLB de la motocicleta: nodos, manifiesto y reproducibilidad."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import trimesh

from fabrica_autopartes.simulador.catalogo_moto_honda import construir_moto
from fabrica_autopartes.simulador.cinematica import ErrorEnsamblaje
from fabrica_autopartes.simulador.generacion import ENSAMBLAJES_GENERABLES, generar


@pytest.fixture(scope="module")
def generado(tmp_path_factory):  # type: ignore[no-untyped-def]
    destino = tmp_path_factory.mktemp("glb_moto")
    return destino, generar(destino, ensamblaje="moto_honda")


def test_glb_valido_con_un_nodo_por_pieza(generado) -> None:  # type: ignore[no-untyped-def]
    destino, manifiesto = generado
    escena = trimesh.load(destino / "moto_honda.glb")
    esperados = {p.id for p in construir_moto().piezas}
    assert set(escena.graph.nodes_geometry) >= esperados
    assert len(escena.geometry) == len(esperados) == len(manifiesto["piezas"])
    assert {p["nodo"] for p in manifiesto["piezas"]} == esperados


def test_manifiesto_completo_y_mallas_cerradas(generado) -> None:  # type: ignore[no-untyped-def]
    destino, manifiesto = generado
    en_disco = json.loads((destino / "moto_honda.manifiesto.json").read_text(encoding="utf-8"))
    assert en_disco == manifiesto
    assert manifiesto["ensamblaje"] == "moto_honda" and manifiesto["unidades"] == "m"
    assert all(p["cerrada"] and p["volumen_m3"] > 0 for p in manifiesto["piezas"])
    assert set(manifiesto["procedencia_parametros"].values()) == {"demostrativo"}
    assert "No es un diseño industrial" in manifiesto["advertencia"]


def test_generacion_reproducible(generado, tmp_path) -> None:  # type: ignore[no-untyped-def]
    _, primero = generado
    assert generar(tmp_path, ensamblaje="moto_honda")["sha256"] == primero["sha256"]


def test_ensamblaje_desconocido_y_registro(tmp_path) -> None:  # type: ignore[no-untyped-def]
    assert ENSAMBLAJES_GENERABLES == ("freno_disco", "moto_honda")
    with pytest.raises(ErrorEnsamblaje):
        generar(tmp_path, ensamblaje="otro")


def test_freno_sigue_generando_igual(tmp_path) -> None:  # type: ignore[no-untyped-def]
    ruta = Path(__file__).resolve().parents[2] / "web" / "public" / "modelos" / "freno_disco.manifiesto.json"
    publicado = json.loads(ruta.read_text(encoding="utf-8"))
    assert generar(tmp_path)["sha256"] == publicado["sha256"]


def test_presupuesto_de_rendimiento(generado) -> None:  # type: ignore[no-untyped-def]
    destino, manifiesto = generado
    assert (destino / "moto_honda.glb").stat().st_size < 3 * 1024 * 1024
    assert sum(p["caras"] for p in manifiesto["piezas"]) <= 150_000
    assert len(manifiesto["piezas"]) >= 70
