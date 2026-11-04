"""Cliente HTTP responsable: User-Agent identificable, timeout, reintentos con
*backoff* exponencial y control de frecuencia por host."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from urllib.parse import urlparse

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from fabrica_autopartes.core.registro import obtener_registro

log = obtener_registro(__name__)


@dataclass
class RespuestaHTTP:
    url: str
    url_final: str
    estado: int
    tipo_contenido: str
    contenido: bytes

    @property
    def texto(self) -> str:
        return self.contenido.decode("utf-8", errors="replace")


@dataclass
class ClienteHTTP:
    agente_usuario: str
    tiempo_espera_s: float = 20.0
    pausa_s: float = 2.0
    reintentos: int = 3
    _ultima_peticion: dict[str, float] = field(default_factory=dict)
    _sesion: requests.Session | None = None

    @property
    def sesion(self) -> requests.Session:
        if self._sesion is None:
            sesion = requests.Session()
            reintento = Retry(
                total=self.reintentos,
                backoff_factor=1.0,  # 1 s, 2 s, 4 s ...
                status_forcelist=(429, 500, 502, 503, 504),
                allowed_methods=("GET", "HEAD"),
                respect_retry_after_header=True,
            )
            adaptador = HTTPAdapter(max_retries=reintento)
            sesion.mount("https://", adaptador)
            sesion.mount("http://", adaptador)
            sesion.headers.update(
                {
                    "User-Agent": self.agente_usuario,
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.5",
                    "Accept-Language": "es-CO,es;q=0.9,en;q=0.6",
                }
            )
            self._sesion = sesion
        return self._sesion

    def _respetar_frecuencia(self, url: str, demora_extra: float | None = None) -> None:
        host = urlparse(url).netloc
        espera = max(self.pausa_s, demora_extra or 0.0)
        anterior = self._ultima_peticion.get(host)
        if anterior is not None:
            transcurrido = time.monotonic() - anterior
            if transcurrido < espera:
                time.sleep(espera - transcurrido)
        self._ultima_peticion[host] = time.monotonic()

    def obtener(self, url: str, demora_extra: float | None = None) -> RespuestaHTTP:
        self._respetar_frecuencia(url, demora_extra)
        log.debug("GET %s", url)
        r = self.sesion.get(url, timeout=self.tiempo_espera_s, allow_redirects=True)
        return RespuestaHTTP(
            url=url,
            url_final=r.url,
            estado=r.status_code,
            tipo_contenido=r.headers.get("Content-Type", ""),
            contenido=r.content,
        )

    def obtener_texto(self, url: str) -> tuple[int, str]:
        r = self.obtener(url)
        return r.estado, r.texto
