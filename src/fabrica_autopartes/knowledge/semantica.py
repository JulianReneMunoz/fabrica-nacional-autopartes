"""Modelo nomic y índice Chroma local (ADR-023). Requiere el extra ``semantica-cpu`` o ``semantica-gpu``.

Riesgo documentado (bitácora S-09): ``nomic-embed-text-v1.5`` usa ``trust_remote_code=True``, es decir,
ejecuta código Python de Hugging Face. Se acota fijando la revisión del modelo y la del código remoto
(``nomic-ai/nomic-bert-2048``), revisado a mano; sin revisión fijada no se carga. Por omisión no se accede
a la red (``solo_local=True``): la descarga es un paso explícito (``fabrica indexar-vectores --descargar``).

Las importaciones de ``torch``, ``sentence_transformers`` y ``chromadb`` son perezosas para que la
instalación base (y CI) funcione sin el extra.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import numpy as np

from fabrica_autopartes.core.excepciones import ErrorConfiguracion, ErrorRecuperadorNoDisponible
from fabrica_autopartes.domain.modelos import Fragmento
from fabrica_autopartes.knowledge.embeddings import (
    FuncionEmbeddings,
    Matriz,
    resolver_dispositivo,
    texto_indexable,
)
from fabrica_autopartes.knowledge.recuperacion import Resultado

MODELO_NOMIC = "nomic-ai/nomic-embed-text-v1.5"
REVISION_MODELO = "e9b6763023c676ca8431644204f50c2b100d9aab"
CODIGO_REMOTO = "nomic-ai/nomic-bert-2048"
REVISION_CODIGO = "7710840340a098cfb869c4f65e87cf2b1b70caca"
COLECCION = "fragmentos_nomic_v15"

_log = logging.getLogger(__name__)


def extra_instalado() -> bool:
    """Indica si están instalados los paquetes del extra semántico."""
    from importlib.util import find_spec

    return all(find_spec(m) is not None for m in ("torch", "sentence_transformers", "chromadb"))


def modelo_en_cache() -> bool:
    """Indica si la revisión fijada del modelo ya está en la caché de Hugging Face (sin red)."""
    if not extra_instalado():
        return False
    from huggingface_hub import try_to_load_from_cache

    ruta = try_to_load_from_cache(MODELO_NOMIC, "config.json", revision=REVISION_MODELO)
    return isinstance(ruta, str)


def indice_construido(directorio: Path) -> bool:
    """Indica si ``directorio`` contiene la colección de Chroma (sin cargar el modelo)."""
    if not (directorio / "chroma.sqlite3").exists():
        return False
    import chromadb
    from chromadb.config import Settings

    cliente = chromadb.PersistentClient(path=str(directorio), settings=Settings(anonymized_telemetry=False))
    return any(c.name == COLECCION for c in cliente.list_collections())


def disponibilidad(directorio: Path) -> tuple[bool, str]:
    """``(True, "")`` si el recuperador semántico puede usarse; si no, ``(False, motivo)``. Sin red."""
    if not extra_instalado():
        return False, "falta el extra semantica-cpu o semantica-gpu (torch, sentence-transformers, chromadb)"
    if not modelo_en_cache():
        return False, f"el modelo {MODELO_NOMIC} no está en la caché de Hugging Face"
    if not indice_construido(directorio):
        return False, f"no existe el índice vectorial en {directorio.name}/"
    return True, ""


def info_entorno(dispositivo: str) -> dict[str, Any]:
    """Versión de PyTorch y GPU usadas, para registrar en los resultados."""
    import torch

    info: dict[str, Any] = {
        "torch": torch.__version__,
        "cuda_disponible": bool(torch.cuda.is_available()),
        "dispositivo": dispositivo,
    }
    if dispositivo == "cuda":
        info["gpu"] = torch.cuda.get_device_name(0)
        info["cuda"] = torch.version.cuda
    return info


class EmbeddingsNomic(FuncionEmbeddings):
    """``nomic-embed-text-v1.5`` (768 dimensiones) mediante sentence-transformers."""

    nombre = MODELO_NOMIC
    revision = REVISION_MODELO

    def __init__(self, preferencia: str = "auto", solo_local: bool = True, lote: int = 32) -> None:
        if "PENDIENTE" in (REVISION_MODELO, REVISION_CODIGO):
            raise ErrorConfiguracion("Revisión del modelo nomic sin fijar: no se carga código remoto")
        from sentence_transformers import SentenceTransformer

        self.dispositivo = resolver_dispositivo(preferencia)
        self.lote = lote
        kwargs_codigo = {"code_revision": REVISION_CODIGO}
        self._modelo = SentenceTransformer(
            MODELO_NOMIC,
            revision=REVISION_MODELO,
            trust_remote_code=True,
            device=self.dispositivo,
            local_files_only=solo_local,
            model_kwargs=kwargs_codigo,
            config_kwargs=kwargs_codigo,
        )
        _log.info("Modelo %s@%s cargado en %s", MODELO_NOMIC, REVISION_MODELO[:10], self.dispositivo)

    def _codificar(self, textos: list[str]) -> Matriz:
        vectores = self._modelo.encode(
            textos,
            batch_size=self.lote,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return np.asarray(vectores, dtype=np.float32)


class IndiceChroma:
    """Índice vectorial persistente (``chromadb.PersistentClient``) con la interfaz de ``IndiceBM25``.

    Chroma nunca calcula embeddings por su cuenta (``embedding_function=None``): así no descarga su modelo
    ONNX por defecto. La telemetría anónima queda desactivada.
    """

    def __init__(self, directorio: Path, funcion: FuncionEmbeddings, fragmentos: list[Fragmento]) -> None:
        import chromadb
        from chromadb.config import Settings

        self.directorio = directorio
        self.funcion = funcion
        self._por_id = {f.id: f for f in fragmentos}
        directorio.mkdir(parents=True, exist_ok=True)
        self._cliente = chromadb.PersistentClient(
            path=str(directorio), settings=Settings(anonymized_telemetry=False)
        )

    def indexar(self, fragmentos: list[Fragmento]) -> int:
        """Reconstruye la colección completa a partir de los fragmentos Gold."""
        if any(c.name == COLECCION for c in self._cliente.list_collections()):
            self._cliente.delete_collection(COLECCION)
        coleccion = self._cliente.create_collection(
            COLECCION,
            embedding_function=None,
            metadata={
                "hnsw:space": "cosine",
                "modelo": self.funcion.nombre,
                "revision": self.funcion.revision,
            },
        )
        if not fragmentos:
            return 0
        vectores = self.funcion.documentos([texto_indexable(f) for f in fragmentos])
        coleccion.add(
            ids=[f.id for f in fragmentos],
            embeddings=vectores.tolist(),
            documents=[f.texto for f in fragmentos],
            metadatas=[
                {"fragmento_id": f.id, "url": f.url, "titulo": f.titulo, "seccion": f.seccion}
                for f in fragmentos
            ],
        )
        self._por_id = {f.id: f for f in fragmentos}
        return coleccion.count()

    def buscar(self, consulta: str, k: int = 5) -> list[Resultado]:
        if not consulta.strip():
            return []
        from chromadb.errors import NotFoundError

        try:
            coleccion = self._cliente.get_collection(COLECCION)
        except NotFoundError as exc:
            raise ErrorRecuperadorNoDisponible("no existe el índice vectorial") from exc
        total = coleccion.count()
        if total == 0 or k <= 0:
            return []
        respuesta = coleccion.query(
            query_embeddings=self.funcion.consultas([consulta]).tolist(),
            n_results=min(k, total),
            include=["distances"],
        )
        ids, distancias = respuesta["ids"][0], (respuesta["distances"] or [[]])[0]
        return [
            Resultado(self._por_id[i], round(1.0 - float(d), 4))
            for i, d in zip(ids, distancias, strict=True)
            if i in self._por_id
        ]
