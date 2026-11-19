"""Base vectorial en Qdrant para IGNIS (R07): parte densa del híbrido, con filtros por payload.

- **Cliente:** ruta local (``QdrantClient(path=...)``, sin Docker), URL de un servidor (``FNA_QDRANT_URL``) o
  memoria, esta última solo si se pide explícitamente (pruebas). Sin ruta ni URL, ``crear_conexion`` falla
  con un mensaje claro.
- **Honestidad sobre HNSW:** el modo local de qdrant-client hace búsqueda exacta (fuerza bruta), ignora
  ``hnsw_config`` e informa ``indexed_vectors_count=0`` (``qdrant_client/local``, versión 1.20.0). Solo un
  servidor construye HNSW; ``info()`` informa ``hnsw`` únicamente si el servidor indexó vectores.
- **Payload:** ``fragmento_id``, ``documento_id``, ``seccion``, ``idioma``, ``origen``, ``url`` y
  ``titulo``. Los filtros funcionan en todos los modos; los índices keyword de los campos filtrables solo
  se crean en un servidor, porque el modo local no los usa. ``FiltroPayload.acepta`` aplica el mismo
  criterio a BM25, para que RRF fusione dos listas del mismo universo.

Los embeddings llegan como ``FuncionEmbeddings``: nomic en uso real y ``EmbeddingsDeterministas`` en el
CI. Este módulo no toca Chroma ni los recuperadores del M1.
"""

from __future__ import annotations

import json
import threading
import uuid
from dataclasses import dataclass
from pathlib import Path

import httpx
from pydantic import BaseModel, ValidationError
from qdrant_client import QdrantClient, models
from qdrant_client.http.exceptions import ApiException

from fabrica_autopartes.core.config import RAIZ_PROYECTO
from fabrica_autopartes.core.excepciones import ErrorConfiguracion, ErrorRecuperadorNoDisponible
from fabrica_autopartes.domain.modelos import (
    CAMPOS_PAYLOAD as CAMPOS_PAYLOAD,
)
from fabrica_autopartes.domain.modelos import (
    COLECCION_QDRANT as COLECCION_QDRANT,
)
from fabrica_autopartes.domain.modelos import (
    HNSW_EF_CONSTRUCT as HNSW_EF_CONSTRUCT,
)
from fabrica_autopartes.domain.modelos import (
    HNSW_M as HNSW_M,
)
from fabrica_autopartes.domain.modelos import (
    Fragmento,
)
from fabrica_autopartes.domain.modelos import (
    InfoVectorial as InfoVectorial,
)
from fabrica_autopartes.domain.modelos import (
    ModoQdrant as ModoQdrant,
)
from fabrica_autopartes.knowledge.embeddings import FuncionEmbeddings, texto_indexable
from fabrica_autopartes.knowledge.recuperacion import Recuperador, Resultado

# COLECCION_QDRANT, CAMPOS_PAYLOAD, HNSW_M, HNSW_EF_CONSTRUCT, ModoQdrant e InfoVectorial viven en
# domain/modelos.py y se reexportan aquí para no romper los imports existentes.
# Solo los usa un servidor: umbrales bajos (en KB) para que una colección pequeña (167 fragmentos, unos
# 0,5 MB) se indexe con HNSW y no se busque por barrido completo. El modo local los ignora.
UMBRAL_INDEXACION_KB = 1
UMBRAL_BUSQUEDA_EXACTA_KB = 1
MEMORIA = ":memory:"
# Resumen propio que escribe la indexación junto a la colección local: permite consultar el estado sin
# abrir un cliente (abrirlo bloquea la carpeta) ni crear la carpeta.
ARCHIVO_RESUMEN = "ignis_indice.json"
# Espacio de nombres fijo de los UUID5 de los puntos: el mismo fragmento recibe siempre el mismo id.
_ESPACIO_IDS = uuid.UUID("6f9f6c1e-5b55-4c39-9b8e-2a1f7c0e9d41")

# Errores de un servidor caído o que no responde (API REST de qdrant-client sobre httpx).
ERRORES_CONEXION: tuple[type[Exception], ...] = (ApiException, httpx.HTTPError)


@dataclass(frozen=True)
class ConexionQdrant:
    cliente: QdrantClient
    modo: ModoQdrant
    destino: str


def ruta_visible(ruta: Path | str | None) -> str:
    """Ruta para mostrar en motivos y en la API sin exponer rutas absolutas del disco: relativa al proyecto
    («data/qdrant») si está dentro de él; si no, solo su último tramo («…/qdrant»)."""
    if ruta is None:
        return ""
    if str(ruta) == MEMORIA:
        return MEMORIA
    carpeta = Path(ruta)
    try:
        return carpeta.resolve().relative_to(RAIZ_PROYECTO.resolve()).as_posix()
    except ValueError:
        return f"…/{carpeta.name}"


def crear_conexion(ruta: Path | str | None = None, url: str | None = None) -> ConexionQdrant:
    """Cliente de Qdrant. La URL de un servidor gana sobre la ruta; ``ruta=":memory:"`` abre una base en
    memoria (solo para pruebas). Sin ruta ni URL lanza ``ErrorConfiguracion``: nunca se abre memoria por
    omisión."""
    if url:
        if not url.startswith(("http://", "https://")):
            # Sin repetir la URL recibida: podría llevar usuario y clave.
            raise ErrorConfiguracion("FNA_QDRANT_URL debe empezar por http:// o https://")
        return ConexionQdrant(QdrantClient(url=url), "servidor", url)
    if ruta is None or str(ruta).strip() == "":
        raise ErrorConfiguracion(
            "Qdrant sin destino: indicar la carpeta local (dir_qdrant), FNA_QDRANT_URL o ':memory:' "
            "en pruebas"
        )
    if str(ruta) == MEMORIA:
        return ConexionQdrant(QdrantClient(location=MEMORIA), "memoria", MEMORIA)
    carpeta = Path(ruta)
    carpeta.mkdir(parents=True, exist_ok=True)
    return ConexionQdrant(QdrantClient(path=str(carpeta)), "local", str(carpeta))


_CONEXIONES: dict[str, ConexionQdrant] = {}
_LOCK_CONEXIONES = threading.Lock()


def conexion_compartida(ruta: Path | str | None = None, url: str | None = None) -> ConexionQdrant:
    """Un solo cliente por destino y por proceso, protegido con un lock: el modo local bloquea su carpeta y
    un segundo cliente fallaría. Si otro proceso ya tiene la carpeta, lanza ``ErrorRecuperadorNoDisponible``
    con un mensaje claro (nunca toca el otro proceso)."""
    if url:
        clave = url
    elif ruta is not None and str(ruta).strip() not in ("", MEMORIA):
        clave = str(Path(ruta).resolve())
    else:
        clave = str(ruta)
    with _LOCK_CONEXIONES:
        if clave in _CONEXIONES:
            return _CONEXIONES[clave]
        try:
            conexion = crear_conexion(ruta, url)
        except RuntimeError as exc:  # portalocker: «Storage folder … is already accessed by another instance»
            raise ErrorRecuperadorNoDisponible(
                f"la carpeta {ruta_visible(ruta)} está en uso por otro proceso: el Qdrant local admite un "
                "solo proceso "
                "(usar FNA_QDRANT_URL para compartirlo)"
            ) from exc
        _CONEXIONES[clave] = conexion
        return conexion


def conexion_abierta(ruta: Path | str | None = None, url: str | None = None) -> ConexionQdrant | None:
    """Conexión compartida ya abierta en este proceso para ese destino, sin abrir ninguna nueva."""
    if url:
        clave = url
    elif ruta is not None and str(ruta).strip() not in ("", MEMORIA):
        clave = str(Path(ruta).resolve())
    else:
        clave = str(ruta)
    with _LOCK_CONEXIONES:
        return _CONEXIONES.get(clave)


def cerrar_conexiones() -> None:
    """Cierra los clientes compartidos (al apagar la API y al terminar las pruebas)."""
    with _LOCK_CONEXIONES:
        for conexion in _CONEXIONES.values():
            conexion.cliente.close()
        _CONEXIONES.clear()


class FiltroPayload(BaseModel):
    """Filtro por payload: igualdad en cada campo indicado y exclusión de documentos."""

    seccion: str | None = None
    documento_id: str | None = None
    idioma: str | None = None
    origen: str | None = None
    excluir_documentos: tuple[str, ...] = ()

    def _igualdades(self) -> dict[str, str]:
        valores = {
            "seccion": self.seccion,
            "documento_id": self.documento_id,
            "idioma": self.idioma,
            "origen": self.origen,
        }
        return {campo: valor for campo, valor in valores.items() if valor is not None}

    def vacio(self) -> bool:
        return not self._igualdades() and not self.excluir_documentos

    def a_qdrant(self) -> models.Filter | None:
        if self.vacio():
            return None
        must: list[models.Condition] = [
            models.FieldCondition(key=campo, match=models.MatchValue(value=valor))
            for campo, valor in self._igualdades().items()
        ]
        must_not: list[models.Condition] = []
        if self.excluir_documentos:
            must_not.append(
                models.FieldCondition(
                    key="documento_id", match=models.MatchAny(any=list(self.excluir_documentos))
                )
            )
        return models.Filter(must=must or None, must_not=must_not or None)

    def acepta(self, f: Fragmento) -> bool:
        """Mismo criterio que ``a_qdrant``, sobre un fragmento (para filtrar BM25)."""
        if f.documento_id in self.excluir_documentos:
            return False
        return all(getattr(f, campo) == valor for campo, valor in self._igualdades().items())


def _id_punto(fragmento_id: str) -> str:
    return str(uuid.uuid5(_ESPACIO_IDS, fragmento_id))


def _payload(f: Fragmento) -> dict[str, str]:
    return {
        "fragmento_id": f.id,
        "documento_id": f.documento_id,
        "seccion": f.seccion,
        "idioma": f.idioma,
        "origen": f.origen,
        "url": f.url,
        "titulo": f.titulo,
    }


class IndiceQdrant:
    """Índice vectorial en Qdrant con la interfaz de ``Recuperador`` (``buscar(consulta, k)``)."""

    def __init__(
        self,
        conexion: ConexionQdrant,
        funcion: FuncionEmbeddings,
        fragmentos: list[Fragmento],
        filtro: FiltroPayload | None = None,
        coleccion: str = COLECCION_QDRANT,
    ) -> None:
        self.conexion = conexion
        self.funcion = funcion
        self.filtro = filtro or FiltroPayload()
        self.coleccion = coleccion
        self._por_id = {f.id: f for f in fragmentos}

    @property
    def cliente(self) -> QdrantClient:
        return self.conexion.cliente

    def indexar(self, fragmentos: list[Fragmento]) -> int:
        """Reconstruye la colección completa: vectores coseno, índices de payload y un punto por fragmento."""
        if self.cliente.collection_exists(self.coleccion):
            self.cliente.delete_collection(self.coleccion)
        self._por_id = {f.id: f for f in fragmentos}
        if not fragmentos:
            return 0
        vectores = self.funcion.documentos([texto_indexable(f) for f in fragmentos])
        self.cliente.create_collection(
            self.coleccion,
            vectors_config=models.VectorParams(size=int(vectores.shape[1]), distance=models.Distance.COSINE),
            hnsw_config=models.HnswConfigDiff(
                m=HNSW_M, ef_construct=HNSW_EF_CONSTRUCT, full_scan_threshold=UMBRAL_BUSQUEDA_EXACTA_KB
            ),
            optimizers_config=models.OptimizersConfigDiff(indexing_threshold=UMBRAL_INDEXACION_KB),
            metadata={"modelo": self.funcion.nombre, "revision": self.funcion.revision},
        )
        if self.conexion.modo == "servidor":  # el modo local no usa índices de payload (filtra recorriendo)
            for campo in CAMPOS_PAYLOAD:
                self.cliente.create_payload_index(self.coleccion, campo, models.PayloadSchemaType.KEYWORD)
        self.cliente.upsert(
            self.coleccion,
            points=[
                models.PointStruct(id=_id_punto(f.id), vector=v.tolist(), payload=_payload(f))
                for f, v in zip(fragmentos, vectores, strict=True)
            ],
        )
        total = self.cliente.count(self.coleccion, exact=True).count
        if self.conexion.modo == "local":
            escribir_resumen(Path(self.conexion.destino), self.info())
        return total

    def con_filtro(self, filtro: FiltroPayload) -> IndiceQdrant:
        """Mismo cliente y mismos fragmentos, con otro filtro de payload."""
        otro = IndiceQdrant(self.conexion, self.funcion, [], filtro, self.coleccion)
        otro._por_id = self._por_id
        return otro

    def buscar(self, consulta: str, k: int = 5) -> list[Resultado]:
        if not consulta.strip() or k <= 0:
            return []
        try:
            if not self.cliente.collection_exists(self.coleccion):
                raise ErrorRecuperadorNoDisponible(f"no existe la colección Qdrant {self.coleccion}")
            respuesta = self.cliente.query_points(
                self.coleccion,
                query=self.funcion.consultas([consulta])[0].tolist(),
                limit=k,
                query_filter=self.filtro.a_qdrant(),
                with_payload=["fragmento_id"],
            )
        except ERRORES_CONEXION as exc:
            raise ErrorRecuperadorNoDisponible(
                f"el servidor Qdrant no responde ({type(exc).__name__})"
            ) from exc
        resultados = []
        for punto in respuesta.points:
            fragmento_id = str((punto.payload or {}).get("fragmento_id", ""))
            if fragmento_id in self._por_id:
                resultados.append(Resultado(self._por_id[fragmento_id], round(float(punto.score), 4)))
        return resultados

    def info(self) -> InfoVectorial:
        """Estado de la colección (ver ``info_coleccion``)."""
        return info_coleccion(self.conexion, self.coleccion)

    def cerrar(self) -> None:
        """Libera el cliente (en modo local, el bloqueo de la carpeta)."""
        self.cliente.close()


class RecuperadorFiltrado:
    """Aplica ``FiltroPayload.acepta`` a otro recuperador (BM25), pidiendo más candidatos para completar
    ``k``."""

    def __init__(self, base: Recuperador, filtro: FiltroPayload, profundidad: int = 200) -> None:
        self.base, self.filtro, self.profundidad = base, filtro, profundidad

    def buscar(self, consulta: str, k: int = 5) -> list[Resultado]:
        if k <= 0:
            return []
        if self.filtro.vacio():
            return self.base.buscar(consulta, k)
        candidatos = self.base.buscar(consulta, max(k, self.profundidad))
        return [r for r in candidatos if self.filtro.acepta(r.fragmento)][:k]


def info_coleccion(conexion: ConexionQdrant, coleccion: str = COLECCION_QDRANT) -> InfoVectorial:
    """Estado de la colección sin cargar el modelo de embeddings. Informa ``hnsw`` solo si un servidor indexó
    vectores; en cualquier otro caso, ``exacta`` con su explicación. Un servidor caído se informa como no
    disponible."""
    modo, cliente = conexion.modo, conexion.cliente
    try:
        if not cliente.collection_exists(coleccion):
            return InfoVectorial(
                disponible=False,
                modo=modo,
                coleccion=coleccion,
                motivo=f"no existe la colección {coleccion}: ejecutar «fabrica indexar-qdrant»",
            )
        datos = cliente.get_collection(coleccion)
    except ERRORES_CONEXION as exc:
        return InfoVectorial(
            disponible=False,
            modo=modo,
            coleccion=coleccion,
            motivo=f"el servidor Qdrant no responde ({type(exc).__name__})",
        )
    vectores = datos.config.params.vectors
    params = vectores if isinstance(vectores, models.VectorParams) else None
    metadatos = datos.config.metadata or {}
    info = InfoVectorial(
        disponible=True,
        modo=modo,
        coleccion=coleccion,
        puntos=datos.points_count or 0,
        dimension=params.size if params else None,
        distancia=params.distance.value if params else None,
        modelo=str(metadatos.get("modelo", "")),
        revision=str(metadatos.get("revision", "")),
    )
    if modo != "servidor":
        info.explicacion = (
            "El modo local de qdrant-client hace búsqueda exacta (fuerza bruta): no construye HNSW. "
            f"Los parámetros HNSW (m={HNSW_M}, ef_construct={HNSW_EF_CONSTRUCT}) se declaran al crear la "
            "colección, pero solo los usa un servidor. Los filtros por payload funcionan recorriendo los "
            "puntos, sin índices."
        )
        return info
    hnsw = datos.config.hnsw_config
    info.hnsw_m, info.hnsw_ef_construct = hnsw.m, hnsw.ef_construct
    info.umbral_busqueda_exacta_kb = hnsw.full_scan_threshold
    info.vectores_indexados = datos.indexed_vectors_count or 0
    if info.vectores_indexados > 0:
        info.tipo_busqueda = "hnsw"
        info.explicacion = (
            f"El servidor construyó HNSW para {info.vectores_indexados} de {info.puntos} vectores "
            f"(m={hnsw.m}, ef_construct={hnsw.ef_construct})."
        )
    else:
        info.explicacion = (
            "El servidor todavía no indexó los vectores (por debajo del umbral de indexación o con la "
            "optimización pendiente): la búsqueda es exacta."
        )
    return info


def escribir_resumen(carpeta: Path, info: InfoVectorial) -> None:
    """Guarda el resumen de la colección local (escritura atómica). Solo datos de la colección: nunca
    textos de fragmentos ni consultas."""
    from datetime import UTC, datetime

    datos = info.model_copy(update={"generado_en": datetime.now(UTC).isoformat(timespec="seconds")})
    campos = {"coleccion", "puntos", "dimension", "distancia", "modelo", "revision", "generado_en"}
    temporal = carpeta / f"{ARCHIVO_RESUMEN}.tmp"
    temporal.write_text(
        json.dumps(datos.model_dump(include=campos), ensure_ascii=False, indent=2), encoding="utf-8"
    )
    temporal.replace(carpeta / ARCHIVO_RESUMEN)


def info_local_sin_bloqueo(carpeta: Path) -> InfoVectorial:
    """Estado de la colección local leyendo solo el resumen de la indexación: no abre un cliente, así que no
    bloquea la carpeta, y no la crea si no existe."""
    explicacion_local = (
        "El modo local de qdrant-client hace búsqueda exacta (fuerza bruta): no construye HNSW. "
        f"Los parámetros HNSW (m={HNSW_M}, ef_construct={HNSW_EF_CONSTRUCT}) se declaran al crear la "
        "colección, pero solo los usa un servidor. Los filtros por payload funcionan recorriendo los "
        "puntos, sin índices."
    )
    if not carpeta.is_dir():
        return InfoVectorial(
            disponible=False,
            modo="local",
            motivo=f"no existe la carpeta {ruta_visible(carpeta)}: ejecutar «fabrica indexar-qdrant»",
        )
    resumen = carpeta / ARCHIVO_RESUMEN
    if not resumen.is_file():
        return InfoVectorial(
            disponible=False,
            modo="local",
            motivo=(
                f"no hay un índice construido en {ruta_visible(carpeta)}: ejecutar «fabrica indexar-qdrant»"
            ),
        )
    try:
        datos = json.loads(resumen.read_text(encoding="utf-8"))
        return InfoVectorial(disponible=True, modo="local", explicacion=explicacion_local, **datos)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, TypeError, ValidationError):
        # Resumen ilegible, que no es JSON o con campos inesperados: sin excepción ni 500 en la API.
        return InfoVectorial(
            disponible=False, modo="local", motivo="resumen dañado: ejecutar «fabrica indexar-qdrant»"
        )
