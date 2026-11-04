"""Pruebas unitarias de robots.txt, sitemaps, extracción y normalización de URLs."""

from __future__ import annotations

from fabrica_autopartes.scraping.extraccion import extraer_contenido, extraer_enlaces
from fabrica_autopartes.scraping.rastreador import normalizar_url
from fabrica_autopartes.scraping.robots import PoliticaRobots, esta_en_dominios
from fabrica_autopartes.scraping.sitemap import analizar_sitemap
from tests.conftest import DIR_FIXTURES

SITIO = DIR_FIXTURES / "sitio"
BASE = "https://ejemplo-fna.test/"


def _robots() -> PoliticaRobots:
    p = PoliticaRobots(agente_usuario="FNA-KnowledgeBot/0.1")
    p.cargar_desde_texto(BASE, (SITIO / "robots.txt").read_text())
    return p


def test_robots_respeta_disallow() -> None:
    p = _robots()
    assert p.permitido(BASE + "quienes-somos/")
    assert not p.permitido(BASE + "privado/intranet/")
    assert not p.permitido(BASE + "wp-admin/")


def test_robots_expone_sitemaps_y_demora() -> None:
    p = _robots()
    assert p.sitemaps(BASE) == ["https://ejemplo-fna.test/wp-sitemap.xml"]
    assert p.demora_rastreo(BASE) == 0.0


def test_robots_error_servidor_bloquea_todo() -> None:
    p = PoliticaRobots(agente_usuario="x")
    p.cargar(BASE, lambda url: (503, ""))
    assert not p.permitido(BASE + "cualquier/")


def test_robots_404_permite() -> None:
    p = PoliticaRobots(agente_usuario="x")
    p.cargar(BASE, lambda url: (404, ""))
    assert p.permitido(BASE + "cualquier/")


def test_host_sin_robots_no_se_rastrea() -> None:
    assert not PoliticaRobots(agente_usuario="x").permitido(BASE)


def test_dominios_permitidos() -> None:
    assert esta_en_dominios("https://www.fanalca.com/x", ["fanalca.com"])
    assert esta_en_dominios("https://sub.fanalca.com/x", ["fanalca.com"])
    assert not esta_en_dominios("https://fanalca.com.evil.test/", ["fanalca.com"])


def test_sitemap_indice_y_urls() -> None:
    hijos, urls = analizar_sitemap((SITIO / "wp-sitemap.xml").read_text())
    assert hijos == ["https://ejemplo-fna.test/wp-sitemap-posts-page-1.xml"] and urls == []
    hijos, urls = analizar_sitemap((SITIO / "wp-sitemap-posts-page-1.xml").read_text())
    assert hijos == [] and "https://ejemplo-fna.test/quienes-somos/" in urls


def test_sitemap_invalido_falla_seguro() -> None:
    assert analizar_sitemap("<no-es-xml") == ([], [])


def test_extraccion_elimina_ruido() -> None:
    html = (SITIO / "inicio.html").read_text()
    pagina = extraer_contenido(html, BASE, usar_trafilatura=False)
    assert pagina.titulo == "Empresa Ejemplo de Autopartes"
    assert "# Empresa Ejemplo de Autopartes" in pagina.texto
    assert "- Autopartes metálicas" in pagina.texto
    for ruido in ("cookies", "Copyright", "console.log", "Quiénes somos"):
        assert ruido not in pagina.texto
    assert pagina.idioma == "es"


def test_extraccion_con_trafilatura_conserva_contenido() -> None:
    html = (SITIO / "autopartes.html").read_text()
    pagina = extraer_contenido(html, BASE + "negocios/autopartes/")
    assert "travesaños" in pagina.texto
    assert "cookies" not in pagina.texto.lower()


def test_enlaces_absolutos_sin_mailto() -> None:
    enlaces = extraer_enlaces((SITIO / "inicio.html").read_text(), BASE)
    assert "https://ejemplo-fna.test/quienes-somos/" in enlaces
    assert not any(e.startswith("mailto:") for e in enlaces)


def test_normalizar_url_quita_rastreo_y_fragmento() -> None:
    assert (
        normalizar_url("HTTPS://Ejemplo-FNA.test/a/?utm_source=x&id=2#sec")
        == "https://ejemplo-fna.test/a/?id=2"
    )
    assert normalizar_url("https://ejemplo-fna.test") == "https://ejemplo-fna.test/"
