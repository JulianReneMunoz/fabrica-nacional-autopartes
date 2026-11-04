"""Integración del rastreador con un sitio simulado (sin acceso a Internet).

``responses`` intercepta las peticiones de ``requests``: así las pruebas no dependen
del sitio de producción ni alteran su tráfico.
"""

from __future__ import annotations

import re

import responses

from fabrica_autopartes.pipelines.bronze import AlmacenBronze
from fabrica_autopartes.pipelines.orquestador import construir_base
from fabrica_autopartes.scraping.rastreador import Rastreador
from tests.conftest import DIR_FIXTURES, DOMINIO_PRUEBA

SITIO = DIR_FIXTURES / "sitio"
HTML = "text/html; charset=utf-8"


def _registrar_sitio() -> None:
    responses.add(responses.GET, f"{DOMINIO_PRUEBA}/robots.txt", body=(SITIO / "robots.txt").read_text())
    for nombre in ("wp-sitemap.xml", "wp-sitemap-posts-page-1.xml"):
        responses.add(
            responses.GET,
            f"{DOMINIO_PRUEBA}/{nombre}",
            body=(SITIO / nombre).read_text(),
            content_type="application/xml",
        )
    paginas = {
        "/": "inicio.html",
        "/quienes-somos/": "quienes-somos.html",
        "/negocios/autopartes/": "autopartes.html",
        "/contacto/": "contacto.html",
    }
    for ruta, archivo in paginas.items():
        responses.add(
            responses.GET, f"{DOMINIO_PRUEBA}{ruta}", body=(SITIO / archivo).read_bytes(), content_type=HTML
        )
    responses.add(
        responses.GET, re.compile(rf"{re.escape(DOMINIO_PRUEBA)}/privado/.*"), status=200, body="NO"
    )


@responses.activate
def test_rastreo_completo_respeta_robots_y_limites(config) -> None:  # type: ignore[no-untyped-def]
    _registrar_sitio()
    almacen = AlmacenBronze(config.dir_bronze)
    res = Rastreador(config, almacen).rastrear()
    capturadas = set(res.capturadas)
    assert {
        f"{DOMINIO_PRUEBA}/",
        f"{DOMINIO_PRUEBA}/quienes-somos/",
        f"{DOMINIO_PRUEBA}/negocios/autopartes/",
        f"{DOMINIO_PRUEBA}/contacto/",
    } == capturadas
    # robots.txt: /privado/ nunca se solicita
    assert not any("/privado/" in c.request.url for c in responses.calls)
    assert any("/privado/" in u for u in res.omitidas_robots)
    # el PDF y el dominio externo se filtran antes de solicitarse
    assert not any(c.request.url.endswith(".pdf") or "externo.test" in c.request.url for c in responses.calls)
    # User-Agent identificable
    assert all(c.request.headers["User-Agent"].startswith("FNA-KnowledgeBot") for c in responses.calls)
    # manifiesto Bronze con hash y HTML guardado
    registros = list(almacen.registros())
    assert len(registros) == 4 and all(len(r.sha256) == 64 for r in registros)
    assert all((config.dir_bronze / r.archivo_html).exists() for r in registros)


@responses.activate
def test_reanudacion_no_repite_capturas(config) -> None:  # type: ignore[no-untyped-def]
    _registrar_sitio()
    almacen = AlmacenBronze(config.dir_bronze)
    Rastreador(config, almacen).rastrear()
    llamadas_paginas = sum(1 for c in responses.calls if c.request.url.endswith("/"))
    Rastreador(config, almacen).rastrear()
    segunda = sum(1 for c in responses.calls if c.request.url.endswith("/")) - llamadas_paginas
    assert segunda == 0
    assert len(list(almacen.registros())) == 4


@responses.activate
def test_errores_http_se_registran(config) -> None:  # type: ignore[no-untyped-def]
    responses.add(responses.GET, f"{DOMINIO_PRUEBA}/robots.txt", body="User-agent: *\nAllow: /")
    responses.add(responses.GET, f"{DOMINIO_PRUEBA}/", status=404)
    almacen = AlmacenBronze(config.dir_bronze)
    res = Rastreador(config, almacen).rastrear(usar_sitemap=False)
    assert res.errores == [f"{DOMINIO_PRUEBA}/"] and almacen.errores.exists()


@responses.activate
def test_pipeline_bronze_silver_gold_desde_rastreo(config) -> None:  # type: ignore[no-untyped-def]
    _registrar_sitio()
    Rastreador(config, AlmacenBronze(config.dir_bronze)).rastrear()
    res = construir_base(config, "scraping")
    assert res.fuente_usada == "scraping" and res.documentos_silver == 4
    texto = (config.dir_gold / "base_conocimiento.txt").read_text()
    assert "travesaños" in texto
    assert "cookies" not in texto.lower() and "Copyright" not in texto
    assert "persona.privada@gmail.com" not in texto and "prensa@fanalca.com" in texto
    assert res.estadisticas.origenes == {"scraping": res.estadisticas.fragmentos}


def test_construccion_auto_usa_semilla_si_bronze_vacio(config) -> None:  # type: ignore[no-untyped-def]
    res = construir_base(config, "auto")
    assert res.fuente_usada == "semilla" and res.advertencias
