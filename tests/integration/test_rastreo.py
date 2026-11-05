"""Integración del rastreador con un sitio simulado (sin acceso a Internet).

``responses`` intercepta las peticiones de ``requests``: así las pruebas no dependen
del sitio de producción ni alteran su tráfico.
"""

from __future__ import annotations

import re

import responses

from fabrica_autopartes.knowledge.base import BaseConocimiento
from fabrica_autopartes.pipelines.bronze import AlmacenBronze
from fabrica_autopartes.pipelines.orquestador import construir_base
from fabrica_autopartes.scraping.rastreador import Rastreador
from tests.conftest import DIR_FIXTURES, DOMINIO_PRUEBA

SITIO = DIR_FIXTURES / "sitio"
HTML = "text/html; charset=utf-8"


def _registrar_sitio() -> None:
    responses.add(
        responses.GET, f"{DOMINIO_PRUEBA}/robots.txt", body=(SITIO / "robots.txt").read_text(encoding="utf-8")
    )
    for nombre in ("wp-sitemap.xml", "wp-sitemap-posts-page-1.xml"):
        responses.add(
            responses.GET,
            f"{DOMINIO_PRUEBA}/{nombre}",
            body=(SITIO / nombre).read_text(encoding="utf-8"),
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
    assert all(c.request.headers["User-Agent"].startswith("FNA-KB") for c in responses.calls)
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
    texto = (config.dir_gold / "base_conocimiento.txt").read_text(encoding="utf-8")
    assert "travesaños" in texto
    assert "cookies" not in texto.lower() and "Copyright" not in texto
    assert "persona.privada@gmail.com" not in texto and "prensa@fanalca.com" in texto
    assert res.estadisticas.origenes == {"scraping": res.estadisticas.fragmentos}


def test_construccion_auto_usa_semilla_si_bronze_vacio(config) -> None:  # type: ignore[no-untyped-def]
    res = construir_base(config, "auto")
    assert res.fuente_usada == "semilla" and res.advertencias


PROTEGIDO = "https://protegido-fna.test"


@responses.activate
def test_host_con_proteccion_antibots_se_omite_sin_eludirla(config) -> None:  # type: ignore[no-untyped-def]
    """Un desafío SG-Captcha (HTTP 202) marca el host como protegido: no se insiste ni se elude."""
    _registrar_sitio()
    desafio = {"SG-Captcha": "challenge"}
    responses.add(responses.GET, f"{PROTEGIDO}/robots.txt", status=202, body="<html></html>", headers=desafio)
    for ruta in ("/", "/productos/", "/contacto/"):
        responses.add(responses.GET, f"{PROTEGIDO}{ruta}", status=202, body="<html></html>", headers=desafio)
    config.dominios_permitidos = ["ejemplo-fna.test", "protegido-fna.test"]
    config.urls_semilla = [
        f"{PROTEGIDO}/",
        f"{PROTEGIDO}/productos/",
        f"{PROTEGIDO}/contacto/",
        f"{DOMINIO_PRUEBA}/",
    ]
    almacen = AlmacenBronze(config.dir_bronze)
    res = Rastreador(config, almacen).rastrear()
    assert "protegido-fna.test" in res.hosts_protegidos
    assert "SiteGround" in res.hosts_protegidos["protegido-fna.test"]
    # solo se solicitó robots.txt del host protegido; las páginas no se piden
    pedidas = [c.request.url for c in responses.calls if c.request.url.startswith(PROTEGIDO)]
    assert pedidas == [f"{PROTEGIDO}/robots.txt"]
    assert len(res.omitidas_proteccion) == 3
    assert "Protección antibots" in almacen.errores.read_text(encoding="utf-8")
    # el otro dominio se rastrea normalmente
    assert f"{DOMINIO_PRUEBA}/contacto/" in res.capturadas
    assert almacen.leer_resumen()["hosts_protegidos"]["protegido-fna.test"].startswith("SiteGround")


@responses.activate
def test_exclusiones_nuevas_se_aplican_a_bronze_existente(config) -> None:  # type: ignore[no-untyped-def]
    """Ajustar ``rutas_excluidas`` limpia Silver sin borrar Bronze ni volver a rastrear."""
    _registrar_sitio()
    Rastreador(config, AlmacenBronze(config.dir_bronze)).rastrear()
    assert construir_base(config, "scraping").documentos_silver == 4
    config.rutas_excluidas = [*config.rutas_excluidas, "/contacto"]
    res = construir_base(config, "scraping")
    assert res.documentos_silver == 3
    assert "/contacto/" not in (config.dir_gold / "base_conocimiento.txt").read_text(encoding="utf-8")


@responses.activate
def test_fuente_mixta_complementa_solo_dominios_sin_capturas(config) -> None:  # type: ignore[no-untyped-def]
    """La lectura web de autopartesfanalca.com.co complementa el scraping si ese dominio no se capturó."""
    _registrar_sitio()
    Rastreador(config, AlmacenBronze(config.dir_bronze)).rastrear()
    res = construir_base(config, "mixta")
    origenes = res.metricas["gold"]["origenes"]
    assert origenes.get("scraping", 0) > 0 and origenes.get("lectura_web", 0) > 0
    assert "semilla" not in origenes  # la semilla genérica nunca se mezcla
    assert any("autopartesfanalca.com.co" in a for a in res.advertencias)
    urls = {f.url for f in BaseConocimiento(config.dir_gold).fragmentos}
    assert any(u.startswith("https://autopartesfanalca.com.co") for u in urls)


SEDE = "https://sede-fna.test"


@responses.activate
def test_direccion_del_pie_llega_a_la_base_una_sola_vez(config) -> None:  # type: ignore[no-untyped-def]
    """El pie con la dirección se repite en todas las páginas: se guarda una sola copia en Gold."""
    pie = (
        '<footer class="site-footer"><p>Sede principal: Calle 13 # 31A - 80, Acopi, Yumbo</p>'
        "<p>PBX (602) 555 0000</p><p>Todos los derechos reservados</p></footer>"
    )
    cuerpo = "<p>" + " ".join(["Contenido institucional de prueba sobre la empresa"] * 6) + "</p>"
    responses.add(responses.GET, f"{SEDE}/robots.txt", body="User-agent: *\nAllow: /")
    for ruta, titulo in (("/", "Inicio"), ("/nosotros/", "Nosotros"), ("/negocios/", "Negocios")):
        cabecera = f"<html><head><title>{titulo}</title></head>"
        html = f"{cabecera}<body><main><h1>{titulo}</h1>{cuerpo}</main>{pie}</body></html>"
        responses.add(responses.GET, f"{SEDE}{ruta}", body=html, content_type=HTML)
    config.dominios_permitidos = ["sede-fna.test"]
    config.urls_semilla = [f"{SEDE}/", f"{SEDE}/nosotros/", f"{SEDE}/negocios/"]
    Rastreador(config, AlmacenBronze(config.dir_bronze)).rastrear(usar_sitemap=False)
    construir_base(config, "scraping")
    base = (config.dir_gold / "base_conocimiento.txt").read_text(encoding="utf-8")
    assert base.count("Calle 13 # 31A - 80") == 1
    assert "contacto-sitio" in base
    assert "derechos reservados" not in base
