"""Series de la pestaña «Proceso de datos»: mismos cálculos que las PNG de ``pipelines.graficas``.

Las pruebas no dependen del estado de ``data/gold``: CI reconstruye la base con ``fabrica build`` antes de
pytest y esa construcción no incluye el rastreo ni Bronze, así que las métricas se completan aquí.
"""

from __future__ import annotations

import copy
import json
from typing import Any

from fabrica_autopartes.core.config import RAIZ_PROYECTO
from fabrica_autopartes.pipelines.graficas import ETAPAS, series_etapas

RASTREO = {
    "fecha": "2026-11-04T23:50:26+00:00",
    "capturadas": 75,
    "omitidas_robots": 0,
    "errores": 17,
    "duplicadas": 9,
    "descubiertas_sitemap": 71,
    "visitadas": 107,
    "duracion_s": 316.12,
    "omitidas_proteccion": 6,
}


def _metricas(con_rastreo: bool) -> dict[str, Any]:
    m = json.loads((RAIZ_PROYECTO / "data" / "gold" / "metricas_etapas.json").read_text(encoding="utf-8"))
    m = copy.deepcopy(m)
    if con_rastreo:
        m["bronze"] = {"capturas": 75, "rastreo": dict(RASTREO)}
        for i, p in enumerate(m["paginas"]):
            p["bytes_html"] = 1000 * (i + 1)
    else:
        m["bronze"] = None
        for p in m["paginas"]:
            p["bytes_html"] = 0
    return m


def test_series_con_rastreo_y_bronze() -> None:
    m = _metricas(con_rastreo=True)
    s = series_etapas(m)
    assert set(s) == {clave for clave, _ in ETAPAS}
    paginas = [p for p in m["paginas"] if not p.get("descartada")]
    reduccion = {f["etiqueta"]: f["valor"] for f in s["03_reduccion"]["filas"]}
    assert reduccion["HTML capturado (Bronze)"] == sum(p["bytes_html"] for p in m["paginas"]) / 1024
    assert reduccion["Texto extraído"] == sum(p["caracteres_extraidos"] for p in paginas) / 1024
    assert reduccion["Fragmentos (Gold)"] == m["gold"]["caracteres"] / 1024
    rastreo = {f["etiqueta"]: f for f in s["01_rastreo"]["filas"]}
    assert rastreo["Errores HTTP / red"]["incidencia"] is True
    assert (
        rastreo["Omitidas por robots.txt"]["incidencia"] is False
    )  # incidencia solo con valor distinto de cero
    assert not rastreo["URL visitadas"]["incidencia"]  # solo las incidencias van en naranja
    assert s["02_bronze_paginas"]["total"] == len(m["paginas"])
    assert len(s["06_tokens_fragmento"]["tokens"]) == m["gold"]["fragmentos"]


def test_sin_rastreo_ni_bronze_la_etapa_se_omite() -> None:
    s = series_etapas(_metricas(con_rastreo=False))
    assert "01_rastreo" not in s and "02_bronze_paginas" not in s
    assert s["03_reduccion"]["filas"][0]["etiqueta"] == "Texto extraído"
