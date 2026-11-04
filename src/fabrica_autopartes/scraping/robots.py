"""Cumplimiento de robots.txt (RFC 9309) y del alcance de dominios permitidos.

Regla del curso: lo que está en ``Disallow`` no se toca. Si robots.txt no puede
descargarse por un error de servidor (5xx), se asume prohibición total por prudencia;
si responde 404, se asume permiso (comportamiento estándar del protocolo).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

from fabrica_autopartes.core.registro import obtener_registro

log = obtener_registro(__name__)


def dominio_de(url: str) -> str:
    host = urlparse(url).hostname or ""
    return host.removeprefix("www.")


def esta_en_dominios(url: str, dominios: list[str]) -> bool:
    host = dominio_de(url)
    return any(host == d or host.endswith("." + d) for d in dominios)


@dataclass
class PoliticaRobots:
    """Analizador de robots.txt con caché por host."""

    agente_usuario: str
    _cache: dict[str, RobotFileParser] = field(default_factory=dict)
    _demoras: dict[str, float | None] = field(default_factory=dict)

    def cargar_desde_texto(self, base: str, contenido: str) -> None:
        parser = RobotFileParser()
        parser.parse(contenido.splitlines())
        host = urlparse(base).netloc
        self._cache[host] = parser
        self._demoras[host] = self._extraer_demora(parser)

    def cargar(self, base: str, obtener_texto: Callable[[str], tuple[int, str]]) -> None:
        """Descarga robots.txt usando la función ``obtener_texto(url) -> (estado, texto)``."""
        url_robots = urljoin(base, "/robots.txt")
        host = urlparse(base).netloc
        try:
            estado, texto = obtener_texto(url_robots)
        except Exception as exc:  # red caída: por prudencia, no rastrear
            log.warning("No fue posible leer %s (%s). Se bloquea el host.", url_robots, exc)
            self.cargar_desde_texto(base, "User-agent: *\nDisallow: /")
            return
        if estado >= 500:
            self.cargar_desde_texto(base, "User-agent: *\nDisallow: /")
        elif estado >= 400:
            self.cargar_desde_texto(base, "")
        else:
            self.cargar_desde_texto(base, texto)
        log.info("robots.txt de %s cargado (HTTP %s)", host, estado)

    def permitido(self, url: str) -> bool:
        host = urlparse(url).netloc
        parser = self._cache.get(host)
        if parser is None:
            return False  # sin robots cargado no se rastrea
        return parser.can_fetch(self.agente_usuario, url)

    def demora_rastreo(self, url: str) -> float | None:
        return self._demoras.get(urlparse(url).netloc)

    def sitemaps(self, url: str) -> list[str]:
        parser = self._cache.get(urlparse(url).netloc)
        if parser is None:
            return []
        return list(parser.site_maps() or [])

    def _extraer_demora(self, parser: RobotFileParser) -> float | None:
        demora = parser.crawl_delay(self.agente_usuario)
        return float(demora) if demora is not None else None
