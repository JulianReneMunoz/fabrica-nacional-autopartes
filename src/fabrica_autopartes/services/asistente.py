"""Fachada de aplicación: punto único usado por la API, Streamlit, la CLI y el servidor MCP.

Coordina base de conocimiento, cadenas LLM y auditoría, de modo que las reglas de negocio
no se dupliquen entre interfaces.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from functools import lru_cache
from typing import TYPE_CHECKING

from langchain_core.language_models.chat_models import BaseChatModel

from fabrica_autopartes.core.config import Configuracion, obtener_configuracion
from fabrica_autopartes.core.excepciones import ErrorProveedorLLM
from fabrica_autopartes.domain.modelos import (
    RespuestaAgente,
    RespuestaQA,
    RespuestaWeb,
    ResultadoFAQ,
    ResultadoResumen,
)
from fabrica_autopartes.knowledge.base import BaseConocimiento
from fabrica_autopartes.llm import cadenas
from fabrica_autopartes.llm.busqueda_web import BuscadorWeb
from fabrica_autopartes.llm.proveedores import traducir_error_anthropic

# Reexportada para las interfaces (Streamlit, API, CLI): estas solo importan de ``services``.
from fabrica_autopartes.llm.salvaguardas import es_rechazo as es_rechazo
from fabrica_autopartes.pipelines.bronze import AlmacenBronze
from fabrica_autopartes.pipelines.orquestador import ResultadoConstruccion, construir_base
from fabrica_autopartes.repositories.auditoria import RepositorioAuditoria
from fabrica_autopartes.scraping.rastreador import Rastreador, ResultadoRastreo
from fabrica_autopartes.services.busqueda_web import ServicioBusquedaWeb

if TYPE_CHECKING:  # importación perezosa en tiempo de ejecución: langchain.agents solo se carga si se usa
    from fabrica_autopartes.llm.proveedores import EstadoProveedor
    from fabrica_autopartes.services.agente import ServicioAgente

_ERRORES_CONEXION = {"ConnectError", "ConnectTimeout", "APIConnectionError", "APITimeoutError", "ReadTimeout"}


@contextmanager
def _proveedor_disponible(config: Configuracion) -> Iterator[None]:
    """Traduce fallos del proveedor LLM a un error 503 con un mensaje claro (nunca una traza).

    Primero los errores de estado de Anthropic (credenciales 401/403 o saldo; solicitud inválida 400;
    ADR-028) y después los de conexión (Ollama apagado, red caída).
    """
    try:
        yield
    except Exception as exc:
        traducido = traducir_error_anthropic(exc)
        if traducido is not None:
            raise traducido from exc
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
        buscador_web: BuscadorWeb | None = None,
        modelo_agente: BaseChatModel | None = None,
    ) -> None:
        self.config = config or obtener_configuracion()
        self.base = BaseConocimiento(
            self.config.dir_gold,
            self.config.dir_vectores,
            self.config.recuperador,
            self.config.embeddings_dispositivo,
        )
        self.repo = repositorio or RepositorioAuditoria(self.config.url_base_datos)
        self._modelo_inyectado = modelo_llm  # usado por pruebas
        self._modelo_agente = modelo_agente  # modelo simulado en pruebas (ADR-024)
        self._agente: ServicioAgente | None = None
        self._busqueda_web = ServicioBusquedaWeb(
            self.config.dir_datos / "revision" / "hallazgos_web.jsonl", buscador=buscador_web
        )

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

    def buscar_web(self, pregunta: str) -> RespuestaWeb:
        """Búsqueda web complementaria (ADR-019): solo a petición, tras el rechazo; fuera de la base."""
        return self._busqueda_web.buscar(pregunta)

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

    # ------------------------------------------------- agente con memoria
    @property
    def agente(self) -> ServicioAgente:
        """Agente con memoria en proceso (una instancia por servicio; ADR-024)."""
        if self._agente is None:
            from fabrica_autopartes.services.agente import ServicioAgente

            self._agente = ServicioAgente(self.config, self.base, self._modelo_agente)
        return self._agente

    def preguntar_agente(self, pregunta: str, thread_id: str, canal: str = "api") -> RespuestaAgente:
        r = self.agente.preguntar(pregunta, thread_id)
        self.repo.registrar_interaccion(
            tarea="agente",
            canal=canal,
            entrada=pregunta,
            salida=r.respuesta,
            proveedor=r.proveedor,
            modelo=r.modelo,
            version_prompt=r.version_prompt,
            modo_contexto="bloqueado" if r.bloqueada else "agente",
            fuentes=[f.fragmento_id for f in r.fuentes],
            fundamentada=r.fundamentada,
            latencia_ms=r.latencia_ms,
        )
        return r

    def verificar_agente(self, consultar: bool = True) -> EstadoProveedor:
        """Proveedor configurado para el agente y si responde (sin respaldo automático a otro proveedor)."""
        from fabrica_autopartes.llm.proveedores import verificar_proveedor_agente

        return verificar_proveedor_agente(self.config, consultar=consultar)

    # ------------------------------------------------------- base semántica
    def disponibilidad_semantica(self) -> tuple[bool, str]:
        """``(True, "")`` si el recuperador semántico puede usarse; si no, ``(False, motivo)`` (sin red)."""
        return self.base.disponibilidad_semantica()

    def indexar_vectores(self, descargar: bool = False) -> dict[str, object]:
        """Reconstruye ``data/vectores/`` (Chroma) con los fragmentos Gold y nomic (ADR-023).

        Con ``descargar=False`` no accede a la red: el modelo debe estar en la caché de Hugging Face.
        """
        from fabrica_autopartes.knowledge.semantica import EmbeddingsNomic, IndiceChroma

        self.base.exigir_contenido()
        fragmentos = self.base.fragmentos
        funcion = EmbeddingsNomic(self.config.embeddings_dispositivo, solo_local=not descargar)
        indice = IndiceChroma(self.config.dir_vectores, funcion, fragmentos)
        total = indice.indexar(fragmentos)
        self.base.usar_recuperador_semantico(indice)
        return {"fragmentos": total, "directorio": str(self.config.dir_vectores), **funcion.descripcion()}

    def evaluar_recuperacion(
        self, dispositivos: list[str], repeticiones: int = 3, calentamiento: int = 1
    ) -> list[str]:
        """Experimento de prefijos y comparación BM25 frente a semántico; guarda resultados en evaluacion/."""
        import tempfile
        from pathlib import Path

        from fabrica_autopartes.knowledge.embeddings import FuncionEmbeddings, dispositivos_disponibles
        from fabrica_autopartes.knowledge.semantica import EmbeddingsNomic, IndiceChroma, info_entorno
        from fabrica_autopartes.services import evaluacion_recuperacion as er
        from fabrica_autopartes.services.evaluacion import cargar_preguntas

        self.base.exigir_contenido()
        fragmentos = self.base.fragmentos
        dispositivos = dispositivos_disponibles(dispositivos)
        # Chroma mantiene abierto su SQLite en Windows: la carpeta temporal se borra sin exigirlo.
        with tempfile.TemporaryDirectory(prefix="fna-vectores-", ignore_cleanup_errors=True) as tmp:
            mediciones = iter(range(1, 10_000))

            def crear_indice(funcion: FuncionEmbeddings, principal: bool) -> IndiceChroma:
                # El índice principal es data/vectores; los de medición de tiempos van a la carpeta temporal.
                if principal:
                    return IndiceChroma(self.config.dir_vectores, funcion, fragmentos)
                directorio = Path(tmp) / f"medicion_{next(mediciones)}"
                return IndiceChroma(directorio, funcion, fragmentos)

            prefijos, recuperadores = er.evaluar_base_semantica(
                fragmentos,
                cargar_preguntas("v1"),  # fijo en v1: mediciones de E-05 y E-06 reproducibles
                self.base.indice,
                lambda d: EmbeddingsNomic(d),
                crear_indice,
                self.config.embeddings_dispositivo,
                dispositivos,
                repeticiones,
                calentamiento,
            )
        dispositivo = prefijos["entorno"]["dispositivo"]
        prefijos["entorno"] |= info_entorno(dispositivo)
        recuperadores["entorno"] |= info_entorno(dispositivo)
        for disp, t in recuperadores["tiempos_indexacion"].items():
            t |= info_entorno(disp)
        self.base.recargar()
        return [
            str(er.guardar_resultado("prefijos_c6", prefijos, er.markdown_prefijos(prefijos))),
            str(
                er.guardar_resultado("recuperadores", recuperadores, er.markdown_recuperadores(recuperadores))
            ),
        ]

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
