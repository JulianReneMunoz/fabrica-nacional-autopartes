"""Embeddings para la base semántica (ADR-023): prefijos de nomic, normalización L2 y dispositivo.

Este módulo solo depende de numpy y se prueba en CI. El modelo real (``nomic-embed-text-v1.5`` con
sentence-transformers) y el índice Chroma viven en ``knowledge/semantica.py``, que requiere el extra
``semantica-cpu`` o ``semantica-gpu``.

Los modelos nomic se entrenaron con prefijos de tarea: ``search_document: `` para lo que se indexa y
``search_query: `` para la consulta. Sin ellos, la similitud entre consulta y documento se degrada.
"""

from __future__ import annotations

import hashlib
import logging
from abc import ABC, abstractmethod
from collections.abc import Sequence

import numpy as np
import numpy.typing as npt

from fabrica_autopartes.core.excepciones import ErrorConfiguracion
from fabrica_autopartes.domain.modelos import Fragmento
from fabrica_autopartes.knowledge.recuperacion import Resultado, tokenizar

PREFIJO_DOCUMENTO = "search_document: "
PREFIJO_CONSULTA = "search_query: "

Matriz = npt.NDArray[np.float32]

_log = logging.getLogger(__name__)


def normalizar_l2(vectores: npt.ArrayLike) -> Matriz:
    """Divide cada fila por su norma L2 (las filas nulas quedan en cero)."""
    m = np.atleast_2d(np.asarray(vectores, dtype=np.float32))
    normas = np.linalg.norm(m, axis=1, keepdims=True)
    return np.divide(m, normas, out=np.zeros_like(m), where=normas > 0)


def texto_indexable(f: Fragmento) -> str:
    """Texto que se convierte en vector: título, encabezado y cuerpo del fragmento."""
    return "\n".join(p for p in (f.titulo, f.encabezado, f.texto) if p)


class FuncionEmbeddings(ABC):
    """Interfaz común: aplica el prefijo de tarea y devuelve vectores normalizados (L2)."""

    nombre: str = "abstracta"
    revision: str = ""
    dispositivo: str = "cpu"

    @abstractmethod
    def _codificar(self, textos: list[str]) -> Matriz:
        """Codifica textos ya preparados (con o sin prefijo)."""

    def documentos(self, textos: Sequence[str], con_prefijo: bool = True) -> Matriz:
        prefijo = PREFIJO_DOCUMENTO if con_prefijo else ""
        return normalizar_l2(self._codificar([prefijo + t for t in textos]))

    def consultas(self, textos: Sequence[str], con_prefijo: bool = True) -> Matriz:
        prefijo = PREFIJO_CONSULTA if con_prefijo else ""
        return normalizar_l2(self._codificar([prefijo + t for t in textos]))

    def descripcion(self) -> dict[str, str]:
        return {"modelo": self.nombre, "revision": self.revision, "dispositivo": self.dispositivo}


class EmbeddingsDeterministas(FuncionEmbeddings):
    """Embeddings simulados para pruebas: bolsa de palabras con *hashing* (sin red ni modelos).

    Textos que comparten palabras quedan cerca. El prefijo agrega dos tokens propios
    (``search_document`` o ``search_query``), de modo que el efecto del prefijo es observable.
    """

    nombre = "deterministas-hash"
    revision = "sha256"

    def __init__(self, dimension: int = 256) -> None:
        self.dimension = dimension

    def _indice(self, token: str) -> int:
        return int.from_bytes(hashlib.sha256(token.encode("utf-8")).digest()[:4], "big") % self.dimension

    def _codificar(self, textos: list[str]) -> Matriz:
        m = np.zeros((len(textos), self.dimension), dtype=np.float32)
        for fila, texto in enumerate(textos):
            for token in tokenizar(texto.replace("_", " ")):
                m[fila, self._indice(token)] += 1.0
        return m


class IndiceVectorialMemoria:
    """Índice semántico en memoria (numpy), con la misma interfaz que ``IndiceBM25``.

    Sirve para pruebas y experimentos sin Chroma; el índice persistente es ``IndiceChroma``.
    """

    def __init__(self, fragmentos: list[Fragmento], funcion: FuncionEmbeddings) -> None:
        self.funcion = funcion
        self.fragmentos: list[Fragmento] = []
        self._matriz: Matriz = np.zeros((0, 1), dtype=np.float32)
        self.indexar(fragmentos)

    def indexar(self, fragmentos: list[Fragmento]) -> int:
        self.fragmentos = list(fragmentos)
        if self.fragmentos:
            self._matriz = self.funcion.documentos([texto_indexable(f) for f in self.fragmentos])
        return len(self.fragmentos)

    def buscar(self, consulta: str, k: int = 5) -> list[Resultado]:
        if not self.fragmentos or not consulta.strip():
            return []
        similitudes = self._matriz @ self.funcion.consultas([consulta])[0]
        orden = np.argsort(-similitudes, kind="stable")[:k]
        return [Resultado(self.fragmentos[i], round(float(similitudes[i]), 4)) for i in orden]


def resolver_dispositivo(preferencia: str, cuda_disponible: bool | None = None) -> str:
    """Traduce ``auto|cpu|cuda`` al dispositivo real; ``cuda`` sin GPU es un error explícito."""
    if preferencia not in {"auto", "cpu", "cuda"}:
        raise ErrorConfiguracion(f"EMBEDDINGS_DEVICE inválido: '{preferencia}' (auto, cpu o cuda)")
    if preferencia == "cpu":
        return "cpu"
    if cuda_disponible is None:
        import torch  # extra semantica-cpu o semantica-gpu

        cuda_disponible = bool(torch.cuda.is_available())
    if preferencia == "cuda" and not cuda_disponible:
        raise ErrorConfiguracion(
            "EMBEDDINGS_DEVICE=cuda, pero PyTorch no detecta una GPU CUDA "
            "(instalar el extra semantica-gpu o usar EMBEDDINGS_DEVICE=cpu)"
        )
    dispositivo = "cuda" if cuda_disponible else "cpu"
    _log.info("Embeddings: EMBEDDINGS_DEVICE=%s → dispositivo %s", preferencia, dispositivo)
    return dispositivo


def dispositivos_disponibles(solicitados: Sequence[str], cuda_disponible: bool | None = None) -> list[str]:
    """Filtra los dispositivos pedidos para medir tiempos; omite ``cuda`` (con aviso) si no hay GPU."""
    disponibles: list[str] = []
    for d in solicitados:
        try:
            if resolver_dispositivo(d, cuda_disponible) == d or d == "auto":
                disponibles.append(d)
        except ErrorConfiguracion:
            _log.warning("Dispositivo %s omitido: PyTorch no detecta una GPU CUDA", d)
    return disponibles
