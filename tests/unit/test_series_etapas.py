"""Series de la pestaña «Proceso de datos»: mismos cálculos que las PNG de ``pipelines.graficas``."""

from __future__ import annotations

import json

from fabrica_autopartes.core.config import RAIZ_PROYECTO
from fabrica_autopartes.pipelines.graficas import ETAPAS, series_etapas


def test_series_con_las_metricas_reales() -> None:
    m = json.loads((RAIZ_PROYECTO / "data" / "gold" / "metricas_etapas.json").read_text(encoding="utf-8"))
    s = series_etapas(m)
    assert set(s) == {clave for clave, _ in ETAPAS}
    paginas = [p for p in m["paginas"] if not p.get("descartada")]
    reduccion = {f["etiqueta"]: f["valor"] for f in s["03_reduccion"]["filas"]}
    assert reduccion["Texto extraído"] == sum(p["caracteres_extraidos"] for p in paginas) / 1024
    assert reduccion["Fragmentos (Gold)"] == m["gold"]["caracteres"] / 1024
    rastreo = {f["etiqueta"]: f for f in s["01_rastreo"]["filas"]}
    assert rastreo["Errores HTTP / red"]["incidencia"] is (m["bronze"]["rastreo"]["errores"] > 0)
    assert rastreo["Omitidas por robots.txt"]["incidencia"] is (m["bronze"]["rastreo"]["omitidas_robots"] > 0)
    assert not rastreo["URL visitadas"]["incidencia"]  # solo las incidencias van en naranja
    assert s["02_bronze_paginas"]["total"] == sum(1 for p in m["paginas"] if p.get("bytes_html"))
    assert len(s["06_tokens_fragmento"]["tokens"]) == m["gold"]["fragmentos"]


def test_sin_rastreo_ni_bronze_la_etapa_se_omite() -> None:
    m = json.loads((RAIZ_PROYECTO / "data" / "gold" / "metricas_etapas.json").read_text(encoding="utf-8"))
    m["bronze"] = None
    for p in m["paginas"]:
        p["bytes_html"] = 0
    s = series_etapas(m)
    assert "01_rastreo" not in s and "02_bronze_paginas" not in s
    assert s["03_reduccion"]["filas"][0]["etiqueta"] == "Texto extraído"
