"""Fachada de aplicación: punto único usado por la API, Streamlit, la CLI y el servidor MCP.

Coordina base de conocimiento, cadenas LLM y auditoría, de modo que las reglas de negocio
no se dupliquen entre interfaces.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from functools import lru_cache

from langchain_core.language_models.chat_models import BaseChatModel

from fabrica_autopartes.core.config import Configuracion, obtener_configuracion
from fabrica_autopartes.core.excepciones import ErrorProveedorLLM
from fabrica_autopartes.domain.modelos import RespuestaQA, ResultadoFAQ, ResultadoResumen
from fabrica_autopartes.knowledge.base import BaseConocimiento
from fabrica_autopartes.llm import cadenas

# Reexportada para las interfaces (Streamlit, API, CLI): estas solo importan de ``services``.
from fabrica_autopartes.llm.salvaguardas import es_rechazo as es_rechazo
from fabrica_autopartes.pipelines.bronze import AlmacenBronze
from fabrica_autopartes.pipelines.orquestador import ResultadoConstruccion, construir_base
from fabrica_autopartes.repositories.auditoria import RepositorioAuditoria
from fabrica_autopartes.scraping.rastreador import Rastreador, ResultadoRastreo

_ERRORES_CONEXION = {"ConnectError", "ConnectTimeout", "APIConnectionError", "APITimeoutError", "ReadTimeout"}


@contextmanager
def _proveedor_disponible(config: Configuracion) -> Iterator[None]:
    """Traduce fallos de conexión del proveedor LLM (Ollama apagado, red caída) a un error 503."""
    try:
        yield
    except Exception as exc:
        if isinstance(exc, ConnectionError) or type(exc).__name__ in _ERRORES_CONEXION:
            raise ErrorProveedorLLM(
                f"No fue posible conectar con el proveedor '{config.proveedor_llm}'. "
                "Con Ollama: ejecutar 'ollama serve' y 'ollama pull llama3.2:3b'."
            ) from exc
        raise


class ServicioAsistente:
    def __init__(
        self,
        config: Configuracion | None = None,
        repositorio: RepositorioAuditoria | None = None,
        modelo_llm: BaseChatModel | None = None,
    ) -> None:
        self.config = config or obtener_configuracion()
        self.base = BaseConocimiento(self.config.dir_gold)
        self.repo = repositorio or RepositorioAuditoria(self.config.url_base_datos)
        self._modelo_inyectado = modelo_llm  # usado por pruebas

    # ------------------------------------------------------------ tareas LLM
    def responder(self, pregunta: str, canal: str = "api", **op: str | None) -> RespuestaQA:
        with _proveedor_disponible(self.config):
            r = cadenas.ejecutar_qa(pregunta, self.base, self.config, self._modelo_inyectado, **op)
        self.repo.registrar_interaccion(
            tarea="qa",
            canal=canal,
            entrada=pregunta,
            salida=r.respuesta,
            proveedor=r.proveedor,
            modelo=r.modelo,
            version_prompt=r.version_prompt,
            modo_contexto=r.modo_contexto,
            fuentes=[f.fragmento_id for f in r.fuentes],
            fundamentada=r.fundamentada,
            latencia_ms=r.latencia_ms,
        )
        return r

    def generar_faq(self, n_preguntas: int = 8, canal: str = "api", **op: str | None) -> ResultadoFAQ:
        with _proveedor_disponible(self.config):
            r = cadenas.ejecutar_faq(self.base, self.config, n_preguntas, self._modelo_inyectado, **op)
        self.repo.registrar_interaccion(
            tarea="faq",
            canal=canal,
            entrada=f"n={n_preguntas}",
            salida="\n".join(f"P: {i.pregunta}\nR: {i.respuesta}" for i in r.items),
            proveedor=r.proveedor,
            modelo=r.modelo,
            version_prompt=r.version_prompt,
            modo_contexto="completo",
            fuentes=sorted({f for i in r.items for f in i.fuentes}),
            latencia_ms=r.latencia_ms,
        )
        return r

    def resumir(self, enfoque: str | None = None, canal: str = "api", **op: str | None) -> ResultadoResumen:
        with _proveedor_disponible(self.config):
            r = cadenas.ejecutar_resumen(
                self.base,
                self.config,
                enfoque or cadenas.ENFOQUE_GENERAL,
                self._modelo_inyectado,
                **op,
            )
        self.repo.registrar_interaccion(
            tarea="resumen",
            canal=canal,
            entrada=r.enfoque,
            salida=r.resumen,
            proveedor=r.proveedor,
            modelo=r.modelo,
            version_prompt=r.version_prompt,
            modo_contexto="completo",
            fuentes=[],
            latencia_ms=r.latencia_ms,
        )
        return r

    # -------------------------------------------------------------- pipeline
    def construir(self, fuente: str = "auto") -> ResultadoConstruccion:
        id_ = self.repo.iniciar_ejecucion("construccion")
        try:
            resultado = construir_base(self.config, fuente)  # type: ignore[arg-type]
        except Exception as exc:
            self.repo.finalizar_ejecucion(id_, "error", {"error": repr(exc)})
            raise
        self.base.recargar()
        self.repo.finalizar_ejecucion(
            id_,
            "ok",
            {
                "fuente": resultado.fuente_usada,
                "documentos": resultado.documentos_silver,
                "duplicados": resultado.duplicados_descartados,
                "fragmentos": resultado.estadisticas.fragmentos,
                "tokens_aprox": resultado.estadisticas.tokens_aprox,
                "advertencias": resultado.advertencias,
            },
        )
        return resultado

    def rastrear(self, semillas: list[str] | None = None, usar_sitemap: bool = True) -> ResultadoRastreo:
        id_ = self.repo.iniciar_ejecucion("scraping")
        rastreador = Rastreador(self.config, AlmacenBronze(self.config.dir_bronze))
        try:
            resultado = rastreador.rastrear(semillas, usar_sitemap=usar_sitemap)
        except Exception as exc:
            self.repo.finalizar_ejecucion(id_, "error", {"error": repr(exc)})
            raise
        self.repo.finalizar_ejecucion(
            id_,
            "ok" if resultado.capturadas else "sin_capturas",
            {
                "capturadas": len(resultado.capturadas),
                "omitidas_robots": resultado.omitidas_robots,
                "errores": resultado.errores,
                "duplicadas": resultado.duplicadas,
            },
        )
        return resultado


@lru_cache(maxsize=1)
def servicio_por_defecto() -> ServicioAsistente:
    return ServicioAsistente()
