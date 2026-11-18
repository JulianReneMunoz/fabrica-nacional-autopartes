"""Fachada de aplicación: punto único usado por la API, Streamlit, la CLI y el servidor MCP.

Coordina base de conocimiento, cadenas LLM y auditoría, de modo que las reglas de negocio
no se dupliquen entre interfaces.
"""

from __future__ import annotations

import threading
from collections.abc import Iterator
from contextlib import contextmanager
from functools import lru_cache
from typing import TYPE_CHECKING, Any

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
from fabrica_autopartes.repositories.auditoria import RepositorioAuditoria, RepositorioMemoriaIgnis
from fabrica_autopartes.repositories.memoria_agente import cerrar_store, crear_store
from fabrica_autopartes.repositories.sesiones import Hilo, RepositorioSesiones
from fabrica_autopartes.scraping.rastreador import Rastreador, ResultadoRastreo
from fabrica_autopartes.services.agente_ignis_m2 import AgenteIgnisM2
from fabrica_autopartes.services.busqueda_web import ServicioBusquedaWeb
from fabrica_autopartes.services.sesiones import ServicioSesiones

# Reexportado para la API: las interfaces solo importan de ``services.asistente``.
from fabrica_autopartes.services.sesiones import SesionUsuario as SesionUsuario
from fabrica_autopartes.services.sesiones import sesiones_configuradas as sesiones_configuradas
from fabrica_autopartes.services.voz import ServicioVoz

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
        self._ignis: AgenteIgnisM2 | None = None
        self._memoria_ignis: RepositorioMemoriaIgnis | None = None
        self._sesiones: ServicioSesiones | None = None
        self._voz: ServicioVoz | None = None
        self._lock_ignis = threading.Lock()
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

    def precargar_recuperador_agente(self, en_segundo_plano: bool = True) -> threading.Thread | None:
        """Carga el semántico al arrancar la API o Streamlit si el agente lo usa (ADR-031).

        Con ``FNA_AGENTE_RECUPERADOR=bm25`` no hace nada. En segundo plano no bloquea el arranque; si el
        semántico no está disponible, se registra un aviso y la herramienta vuelve a bm25. La carga ocurre
        una sola vez por proceso porque la base guarda el recuperador cargado.
        """
        if self.config.agente_recuperador == "bm25":
            return None
        if not en_segundo_plano:
            self.base.precargar_semantico()
            return None
        hilo = threading.Thread(target=self.base.precargar_semantico, name="precarga-semantico", daemon=True)
        hilo.start()
        return hilo

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

    # ------------------------------------------------------------ agente IGNIS
    def _memoria(self) -> RepositorioMemoriaIgnis:
        """Historial por hilo de IGNIS, compartido por el agente y las sesiones (se crea en el primer uso)."""
        if self._memoria_ignis is None:
            with self._lock_ignis:
                if self._memoria_ignis is None:
                    self._memoria_ignis = RepositorioMemoriaIgnis(
                        self.config.dir_datos / "ignis_memoria_m2.sqlite"
                    )
        return self._memoria_ignis

    def responder_ignis(self, mensaje: str, thread_id: str, user_id: str) -> dict[str, Any]:
        """Turno del agente IGNIS (Módulo 2) para el usuario seudónimo de la sesión (ADR-033).

        Comprueba que el hilo sea del usuario (o nuevo y sin historial), ejecuta el turno y actualiza el
        título, los turnos y la última ruta del hilo. El agente se construye en el primer uso, nunca al
        importar.
        """
        self.sesiones.reclamar_hilo(thread_id, user_id)
        if self._ignis is None:
            memoria = self._memoria()
            with self._lock_ignis:
                if self._ignis is None:
                    # Store persistente de largo plazo (ADR-033): sobrevive al reinicio del backend.
                    self._ignis = AgenteIgnisM2(self.base, memoria, crear_store(self.config.ruta_store))
        resultado = self._ignis.ejecutar_turno(mensaje, thread_id, user_id)
        self.sesiones.registrar_turno(thread_id, user_id, mensaje, str(resultado.get("ruta_router", "")))
        return resultado

    # ------------------------------------------------------------ sesiones (ADR-033)
    @property
    def sesiones(self) -> ServicioSesiones:
        """Sesiones por usuario seudónimo. Sin ``IGNIS_SECRETO_SESION`` sus operaciones lanzan 503."""
        if self._sesiones is None:
            memoria = self._memoria()
            with self._lock_ignis:
                if self._sesiones is None:
                    self._sesiones = ServicioSesiones(
                        self.config, RepositorioSesiones(self.config.ruta_sesiones), memoria
                    )
        return self._sesiones

    def crear_sesion(self, alias: str) -> tuple[SesionUsuario, str]:
        """Valida el alias y devuelve la sesión y el token cifrado de la cookie (el alias no se guarda)."""
        return self.sesiones.crear_sesion(alias)

    def sesion_activa(self, token: str | None) -> tuple[SesionUsuario, str]:
        """Sesión de la cookie y token renovado (8 h deslizantes); ``ErrorSinSesion`` si no es válida."""
        return self.sesiones.sesion_activa(token)

    def reclamar_hilo(self, thread_id: str, user_id: str) -> None:
        self.sesiones.reclamar_hilo(thread_id, user_id)

    def hilos(self, user_id: str) -> list[Hilo]:
        return self.sesiones.hilos(user_id)

    def nuevo_hilo(self, user_id: str) -> str:
        return self.sesiones.nuevo_hilo(user_id)

    def mensajes_hilo(self, thread_id: str, user_id: str) -> list[dict[str, Any]]:
        return self.sesiones.mensajes(thread_id, user_id)

    # ------------------------------------------------------------ voz (Piper)
    @property
    def voz(self) -> ServicioVoz:
        """Voz de IGNIS; el modelo se carga en la primera síntesis, nunca al importar."""
        if self._voz is None:
            with self._lock_ignis:
                if self._voz is None:
                    self._voz = ServicioVoz(self.config)
        return self._voz

    def sintetizar_voz(self, texto: str) -> bytes:
        """WAV de Piper para ``texto``; ``ErrorVozNoDisponible`` (503) si falta el modelo."""
        return self.voz.sintetizar(texto)

    def cerrar(self) -> None:
        """Cierra las conexiones de memoria persistente (checkpointer del agente y Store de IGNIS)."""
        if self._agente is not None:
            self._agente.cerrar()
        if self._ignis is not None and self._ignis.store is not None:
            cerrar_store(self._ignis.store)

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
