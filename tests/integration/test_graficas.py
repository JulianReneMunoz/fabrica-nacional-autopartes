"""Pipeline completo sobre el sitio simulado y gráficas por etapa."""

from __future__ import annotations

import json

import responses

from fabrica_autopartes.pipelines.bronze import AlmacenBronze
from fabrica_autopartes.pipelines.graficas import generar_graficas
from fabrica_autopartes.pipelines.orquestador import construir_base
from fabrica_autopartes.scraping.rastreador import Rastreador
from tests.integration.test_rastreo import _registrar_sitio


@responses.activate
def test_metricas_y_graficas_desde_scraping(config, tmp_path) -> None:  # type: ignore[no-untyped-def]
    _registrar_sitio()
    Rastreador(config, AlmacenBronze(config.dir_bronze)).rastrear()
    construir_base(config, "scraping")
    metricas = json.loads((config.dir_gold / "metricas_etapas.json").read_text(encoding="utf-8"))
    assert metricas["fuente"] == "scraping"
    assert metricas["bronze"]["rastreo"]["capturadas"] == 4
    assert metricas["bronze"]["rastreo"]["omitidas_robots"] >= 1
    for p in metricas["paginas"]:
        assert p["bytes_html"] > p["caracteres_limpios"] > 0
    rutas = generar_graficas(config.dir_gold / "metricas_etapas.json", tmp_path)
    assert [r.name for r in rutas] == [
        "01_rastreo.png",
        "02_bronze_paginas.png",
        "03_reduccion.png",
        "04_limpieza_paginas.png",
        "05_fragmentos_seccion.png",
        "06_tokens_fragmento.png",
    ]
    assert all(r.stat().st_size > 10_000 for r in rutas)


def test_graficas_desde_semilla_declaran_ausencia_de_bronze(config, tmp_path) -> None:  # type: ignore[no-untyped-def]
    construir_base(config, "semilla")
    rutas = generar_graficas(config.dir_gold / "metricas_etapas.json", tmp_path)
    assert len(rutas) == 6
