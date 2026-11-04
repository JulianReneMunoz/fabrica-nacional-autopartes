"""Rastreador (crawler) en anchura con límites estrictos y trazabilidad de procedencia.

Flujo: robots.txt → sitemaps → URLs semilla → enlaces internos (BFS hasta
``profundidad_maxima``) → captura en Bronze. Se respetan ``Disallow``, ``Crawl-delay``,
dominios permitidos, rutas excluidas y un máximo de páginas.
"""

from __future__ import annotations

import hashlib
import time
from collections import deque
from dataclasses import dataclass, field
from urllib.parse import urljoin, urlparse, urlunparse

from fabrica_autopartes.core.config import Configuracion
from fabrica_autopartes.core.registro import obtener_registro
from fabrica_autopartes.domain.puertos import AlmacenCapturas
from fabrica_autopartes.scraping.cliente_http import ClienteHTTP
from fabrica_autopartes.scraping.extraccion import extraer_enlaces
from fabrica_autopartes.scraping.robots import PoliticaRobots, esta_en_dominios
from fabrica_autopartes.scraping.sitemap import analizar_sitemap

log = obtener_registro(__name__)

_EXTENSIONES_NO_HTML = (
    ".pdf",
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".webp",
    ".svg",
    ".zip",
    ".mp4",
    ".mp3",
    ".doc",
    ".docx",
    ".xls",
    ".xlsx",
    ".ppt",
    ".pptx",
    ".css",
    ".js",
    ".ico",
    ".xml",
)


def normalizar_url(url: str) -> str:
    """Normaliza esquema/host en minúsculas, quita fragmentos y parámetros de rastreo."""
    p = urlparse(url)
    consulta = "&".join(
        par for par in p.query.split("&") if par and not par.lower().startswith(("utm_", "fbclid"))
    )
    ruta = p.path or "/"
    return urlunparse((p.scheme.lower(), p.netloc.lower(), ruta, "", consulta, ""))


@dataclass
class ResultadoRastreo:
    capturadas: list[str] = field(default_factory=list)
    omitidas_robots: list[str] = field(default_factory=list)
    errores: list[str] = field(default_factory=list)
    duplicadas: int = 0
    descubiertas_sitemap: int = 0
    visitadas: int = 0
    duracion_s: float = 0.0

    def a_dict(self) -> dict:
        return {
            "capturadas": len(self.capturadas),
            "omitidas_robots": len(self.omitidas_robots),
            "errores": len(self.errores),
            "duplicadas": self.duplicadas,
            "descubiertas_sitemap": self.descubiertas_sitemap,
            "visitadas": self.visitadas,
            "duracion_s": round(self.duracion_s, 2),
            "urls_capturadas": self.capturadas,
            "urls_omitidas_robots": self.omitidas_robots,
            "urls_error": self.errores,
        }


class Rastreador:
    def __init__(
        self,
        config: Configuracion,
        almacen: AlmacenCapturas,
        cliente: ClienteHTTP | None = None,
    ) -> None:
        self.config = config
        self.almacen = almacen
        self.cliente = cliente or ClienteHTTP(
            agente_usuario=config.agente_usuario,
            tiempo_espera_s=config.tiempo_espera_s,
            pausa_s=config.pausa_entre_peticiones_s,
            reintentos=config.reintentos,
        )
        self.robots = PoliticaRobots(agente_usuario=config.agente_usuario)
        self._hosts_cargados: set[str] = set()

    # ------------------------------------------------------------------ filtros
    def _url_valida(self, url: str) -> bool:
        p = urlparse(url)
        if p.scheme not in ("http", "https"):
            return False
        if not esta_en_dominios(url, self.config.dominios_permitidos):
            return False
        if p.path.lower().endswith(_EXTENSIONES_NO_HTML):
            return False
        completa = p.path + ("?" + p.query if p.query else "")
        return not any(excl in completa for excl in self.config.rutas_excluidas)

    def _asegurar_robots(self, url: str) -> None:
        host = urlparse(url).netloc
        if host in self._hosts_cargados:
            return
        base = f"{urlparse(url).scheme}://{host}/"
        self.robots.cargar(base, self.cliente.obtener_texto)
        self._hosts_cargados.add(host)

    # ----------------------------------------------------------------- sitemaps
    def descubrir_sitemaps(self, base: str) -> list[str]:
        self._asegurar_robots(base)
        candidatos = self.robots.sitemaps(base) or [
            urljoin(base, "/wp-sitemap.xml"),
            urljoin(base, "/sitemap_index.xml"),
            urljoin(base, "/sitemap.xml"),
        ]
        urls: list[str] = []
        pendientes = deque(candidatos)
        vistos: set[str] = set()
        while pendientes and len(vistos) < 25:
            sm = pendientes.popleft()
            if sm in vistos or not self.robots.permitido(sm):
                continue
            vistos.add(sm)
            try:
                estado, xml = self.cliente.obtener_texto(sm)
            except Exception as exc:
                log.info("Sitemap no disponible %s (%s)", sm, exc)
                continue
            if estado != 200:
                continue
            hijos, encontradas = analizar_sitemap(xml)
            pendientes.extend(h for h in hijos if h not in vistos)
            urls.extend(u for u in encontradas if self._url_valida(u))
        log.info("Sitemaps: %d URLs válidas descubiertas", len(urls))
        return urls

    # ------------------------------------------------------------------ rastreo
    def rastrear(
        self,
        semillas: list[str] | None = None,
        usar_sitemap: bool = True,
        reanudar: bool = True,
    ) -> ResultadoRastreo:
        semillas = semillas or self.config.urls_semilla
        resultado = ResultadoRastreo()
        inicio = time.monotonic()
        ya_capturadas = self.almacen.urls_capturadas() if reanudar else set()
        hashes_vistos: set[str] = {r.sha256 for r in self.almacen.registros()} if reanudar else set()

        cola: deque[tuple[str, int]] = deque((normalizar_url(u), 0) for u in semillas)
        if usar_sitemap and semillas:
            hosts_vistos: set[str] = set()
            for semilla in semillas:
                host = urlparse(semilla).netloc
                if host in hosts_vistos:
                    continue
                hosts_vistos.add(host)
                descubiertas = self.descubrir_sitemaps(semilla)
                resultado.descubiertas_sitemap += len(descubiertas)
                for u in descubiertas:
                    cola.append((normalizar_url(u), 1))
        visitadas: set[str] = set()

        while cola and len(resultado.capturadas) < self.config.max_paginas:
            url, profundidad = cola.popleft()
            if url in visitadas or not self._url_valida(url):
                continue
            visitadas.add(url)
            self._asegurar_robots(url)
            if not self.robots.permitido(url):
                resultado.omitidas_robots.append(url)
                log.info("Omitida por robots.txt: %s", url)
                continue
            if url in ya_capturadas:
                continue
            try:
                r = self.cliente.obtener(url, demora_extra=self.robots.demora_rastreo(url))
            except Exception as exc:
                resultado.errores.append(url)
                self.almacen.registrar_error(url, repr(exc))
                log.warning("Error al capturar %s: %s", url, exc)
                continue
            if r.estado != 200 or "html" not in r.tipo_contenido.lower():
                self.almacen.registrar_error(url, f"HTTP {r.estado} {r.tipo_contenido}")
                resultado.errores.append(url)
                continue
            sha = hashlib.sha256(r.contenido).hexdigest()
            if sha in hashes_vistos:
                resultado.duplicadas += 1
                continue
            hashes_vistos.add(sha)
            self.almacen.guardar(
                url=url,
                url_final=normalizar_url(r.url_final),
                estado=r.estado,
                tipo_contenido=r.tipo_contenido,
                contenido=r.contenido,
                agente_usuario=self.config.agente_usuario,
            )
            resultado.capturadas.append(url)
            log.info("[%d] Capturada %s", len(resultado.capturadas), url)
            if profundidad < self.config.profundidad_maxima:
                for enlace in extraer_enlaces(r.texto, r.url_final):
                    n = normalizar_url(enlace)
                    if n not in visitadas and self._url_valida(n):
                        cola.append((n, profundidad + 1))
        resultado.visitadas = len(visitadas)
        resultado.duracion_s = time.monotonic() - inicio
        guardar = getattr(self.almacen, "guardar_resumen", None)
        if callable(guardar):
            guardar(resultado.a_dict())
        return resultado
