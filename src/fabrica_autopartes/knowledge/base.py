"""Acceso de solo lectura a la base de conocimiento Gold y armado del contexto."""

from __future__ import annotations

import json
import logging
import threading
from dataclasses import dataclass
from pathlib import Path

from fabrica_autopartes.core.excepciones import (
    ErrorBaseConocimientoVacia,
    ErrorConfiguracion,
    ErrorRecuperadorNoDisponible,
    ErrorRecursoNoEncontrado,
)
from fabrica_autopartes.domain.modelos import EstadisticasBase, Fragmento
from fabrica_autopartes.knowledge.recuperacion import IndiceBM25, Recuperador, RecuperadorHibrido, Resultado
from fabrica_autopartes.pipelines.texto import tokens_aprox

_log = logging.getLogger(__name__)


@dataclass
class ContextoArmado:
    texto: str
    fragmentos: list[Fragmento]
    modo: str
    tokens_aprox: int


def formatear_fragmento(f: Fragmento) -> str:
    return f'<fragmento id="{f.id}" seccion="{f.seccion}" fuente="{f.url}">\n{f.texto}\n</fragmento>'


class BaseConocimiento:
    def __init__(
        self,
        dir_gold: Path,
        dir_vectores: Path | None = None,
        recuperador: str = "bm25",
        dispositivo_embeddings: str = "auto",
    ) -> None:
        self.dir_gold = dir_gold
        self.dir_vectores = dir_vectores or dir_gold.parent / "vectores"
        self.recuperador_por_defecto = recuperador
        self.dispositivo_embeddings = dispositivo_embeddings
        self._fragmentos: list[Fragmento] | None = None
        self._indice: IndiceBM25 | None = None
        self._semantico: Recuperador | None = None
        self._lock_semantico = threading.Lock()
        self._motivo_sin_semantico: str | None = None  # motivo de la última vuelta a bm25 (ADR-031)

    # ------------------------------------------------------------ carga
    @property
    def fragmentos(self) -> list[Fragmento]:
        if self._fragmentos is None:
            ruta = self.dir_gold / "fragmentos.jsonl"
            if not ruta.exists():
                self._fragmentos = []
            else:
                self._fragmentos = [
                    Fragmento.model_validate_json(linea)
                    for linea in ruta.read_text(encoding="utf-8").splitlines()
                    if linea.strip()
                ]
        return self._fragmentos

    @property
    def indice(self) -> IndiceBM25:
        if self._indice is None:
            self._indice = IndiceBM25(self.fragmentos)
        return self._indice

    def recuperador(self, nombre: str | None = None) -> Recuperador:
        """Recuperador ``bm25`` (por defecto), ``semantico`` (Chroma + nomic, ADR-023) o ``hibrido`` (RRF,
        ADR-031). Los dos últimos lanzan ``ErrorRecuperadorNoDisponible`` si el semántico no está listo."""
        nombre = nombre or self.recuperador_por_defecto
        if nombre == "bm25":
            return self.indice
        if nombre == "hibrido":
            return RecuperadorHibrido(self.indice, self._cargar_semantico())
        if nombre != "semantico":
            raise ErrorConfiguracion(f"Recuperador desconocido: '{nombre}' (bm25, semantico o hibrido)")
        return self._cargar_semantico()

    def _cargar_semantico(self) -> Recuperador:
        """Carga el modelo y el índice una sola vez por instancia (unos 20 s); el lock evita cargas dobles
        cuando la precarga en segundo plano y una consulta llegan a la vez."""
        with self._lock_semantico:
            if self._semantico is None:
                from fabrica_autopartes.knowledge import semantica

                disponible, motivo = semantica.disponibilidad(self.dir_vectores)
                if not disponible:
                    raise ErrorRecuperadorNoDisponible(motivo)
                self._semantico = semantica.IndiceChroma(
                    self.dir_vectores, semantica.EmbeddingsNomic(self.dispositivo_embeddings), self.fragmentos
                )
            return self._semantico

    def buscar_con_respaldo(self, consulta: str, k: int, recuperador: str) -> tuple[list[Resultado], str]:
        """Busca con ``recuperador`` y, si el semántico no está disponible, vuelve a ``bm25`` (ADR-031).

        Devuelve los resultados y el recuperador realmente usado. La vuelta se registra con un aviso la
        primera vez y el motivo se recuerda, para no volver a comprobar la disponibilidad en cada consulta.
        """
        if recuperador != "bm25" and self._motivo_sin_semantico is None:
            try:
                return self.recuperador(recuperador).buscar(consulta, k), recuperador
            except ErrorRecuperadorNoDisponible as exc:
                self._motivo_sin_semantico = exc.motivo
                _log.warning(
                    "Recuperador '%s' no disponible (%s): se usa bm25 (ADR-031).", recuperador, exc.motivo
                )
        return self.indice.buscar(consulta, k), "bm25"

    def precargar_semantico(self) -> tuple[bool, str]:
        """Carga el semántico por adelantado (arranque de la API o de Streamlit). Nunca lanza: devuelve
        ``(True, "")`` o ``(False, motivo)``, y en ese caso las búsquedas vuelven a bm25."""
        try:
            self._cargar_semantico()
        except ErrorRecuperadorNoDisponible as exc:
            self._motivo_sin_semantico = exc.motivo
            _log.warning("Precarga del recuperador semántico omitida (%s): se usará bm25.", exc.motivo)
            return False, exc.motivo
        except Exception as exc:  # el arranque no debe caer por un fallo del modelo o de Chroma
            self._motivo_sin_semantico = f"error al cargar el modelo: {type(exc).__name__}"
            _log.warning("Precarga del recuperador semántico fallida: %s", exc)
            return False, self._motivo_sin_semantico
        return True, ""

    def disponibilidad_semantica(self) -> tuple[bool, str]:
        """Disponibilidad del recuperador semántico sin cargar el modelo (para la API y la interfaz)."""
        if self._semantico is not None:
            return True, ""
        from fabrica_autopartes.knowledge import semantica

        return semantica.disponibilidad(self.dir_vectores)

    def usar_recuperador_semantico(self, recuperador: Recuperador) -> None:
        """Inyecta un recuperador semántico (pruebas o índice ya construido)."""
        self._semantico = recuperador
        self._motivo_sin_semantico = None

    def recargar(self) -> None:
        self._fragmentos = None
        self._indice = None
        self._semantico = None
        self._motivo_sin_semantico = None

    def exigir_contenido(self) -> None:
        if not self.fragmentos:
            raise ErrorBaseConocimientoVacia(
                "La base de conocimiento está vacía. Ejecutar 'uv run fabrica build'."
            )

    # --------------------------------------------------------- consultas
    def estadisticas(self) -> EstadisticasBase:
        ruta = self.dir_gold / "estadisticas.json"
        if ruta.exists():
            return EstadisticasBase.model_validate(json.loads(ruta.read_text(encoding="utf-8")))
        return EstadisticasBase(
            documentos=0, fragmentos=0, tokens_aprox=0, secciones={}, origenes={}, urls=[]
        )

    def obtener(self, fragmento_id: str) -> Fragmento:
        for f in self.fragmentos:
            if f.id == fragmento_id:
                return f
        raise ErrorRecursoNoEncontrado(f"No existe el fragmento '{fragmento_id}'")

    def buscar(self, consulta: str, k: int = 5, recuperador: str | None = None) -> list[Resultado]:
        return self.recuperador(recuperador).buscar(consulta, k)

    def filtrar(self, seccion: str | None = None, texto: str | None = None) -> list[Fragmento]:
        resultado = self.fragmentos
        if seccion:
            resultado = [f for f in resultado if f.seccion.startswith(seccion)]
        if texto:
            bajo = texto.lower()
            resultado = [f for f in resultado if bajo in f.texto.lower() or bajo in f.titulo.lower()]
        return resultado

    def texto_consolidado(self) -> str:
        ruta = self.dir_gold / "base_conocimiento.txt"
        return ruta.read_text(encoding="utf-8") if ruta.exists() else ""

    # ----------------------------------------------------- contexto LLM
    def armar_contexto(
        self,
        consulta: str | None,
        modo: str = "auto",
        presupuesto_tokens: int = 9000,
        k: int = 8,
        recuperador: str | None = None,
    ) -> ContextoArmado:
        """Devuelve el contexto delimitado por etiquetas XML.

        - ``completo``: toda la base (exigencia literal del Módulo 1).
        - ``seleccion``: los ``k`` fragmentos más pertinentes según el recuperador (BM25 por defecto).
        - ``auto``: completo si cabe en el presupuesto; si no, selección.
        """
        self.exigir_contenido()
        total = sum(f.tokens_aprox for f in self.fragmentos)
        if modo == "auto":
            modo = "completo" if total <= presupuesto_tokens or not consulta else "seleccion"
        if modo == "completo":
            elegidos = list(self.fragmentos)
            if total > presupuesto_tokens:
                # Se recorta por orden para no exceder la ventana del modelo.
                acumulado, elegidos = 0, []
                for f in self.fragmentos:
                    if acumulado + f.tokens_aprox > presupuesto_tokens:
                        break
                    elegidos.append(f)
                    acumulado += f.tokens_aprox
        else:
            elegidos = [r.fragmento for r in self.buscar(consulta or "", k, recuperador)]
        texto = "\n\n".join(formatear_fragmento(f) for f in elegidos)
        return ContextoArmado(texto=texto, fragmentos=elegidos, modo=modo, tokens_aprox=tokens_aprox(texto))
