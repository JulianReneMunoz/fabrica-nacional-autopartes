"""Base vectorial en Qdrant (R07) sin modelo ni red: ``QdrantClient(":memory:")`` (o una carpeta temporal) con
``EmbeddingsDeterministas``. Cubre la conexión, la colección, los filtros por payload, la información honesta
sobre HNSW y el híbrido RRF con BM25 filtrado por el mismo criterio."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest

from fabrica_autopartes.core.excepciones import ErrorConfiguracion, ErrorRecuperadorNoDisponible
from fabrica_autopartes.domain.modelos import Fragmento
from fabrica_autopartes.knowledge.embeddings import EmbeddingsDeterministas
from fabrica_autopartes.knowledge.recuperacion import IndiceBM25, RecuperadorHibrido
from fabrica_autopartes.knowledge.vectorial_qdrant import (
    CAMPOS_PAYLOAD,
    HNSW_EF_CONSTRUCT,
    HNSW_M,
    MEMORIA,
    FiltroPayload,
    IndiceQdrant,
    RecuperadorFiltrado,
    cerrar_conexiones,
    crear_conexion,
)


def _frag(
    i: str, texto: str, documento: str, seccion: str = "empresa", idioma: str = "es", origen: str = "scraping"
) -> Fragmento:
    return Fragmento(
        id=i,
        documento_id=documento,
        url=f"https://ejemplo-fna.test/{documento}",
        titulo=f"Documento {documento}",
        seccion=seccion,
        idioma=idioma,
        texto=texto,
        tokens_aprox=len(texto.split()),
        orden=0,
        origen=origen,
    )


FRAGMENTOS = [
    _frag("sede#000", "La sede principal de la empresa está en Yumbo, Valle del Cauca.", "sede"),
    _frag(
        "plantas#000", "Las plantas de autopartes producen frenos y suspensiones.", "plantas", "autopartes"
    ),
    _frag(
        "frenos#000", "Los frenos de disco se fabrican en la planta de autopartes.", "frenos", "autopartes"
    ),
    _frag(
        "sostenibilidad#000", "El informe de sostenibilidad mide agua y energía.", "informe", "sostenibilidad"
    ),
    _frag("english#000", "The main plant makes brakes and suspension parts.", "english", "autopartes", "en"),
    _frag(
        "prueba#000",
        "Documento de prueba con frenos y garantías ficticias.",
        "prueba",
        "demo",
        "es",
        "demostrativo",
    ),
]


@pytest.fixture(autouse=True)
def _cerrar_conexiones_compartidas() -> Iterator[None]:
    """«:memory:» comparte la misma clave en ``conexion_compartida``: sin cerrar, el estado pasaría de una
    prueba a otra."""
    yield
    cerrar_conexiones()


@pytest.fixture
def indice() -> Iterator[IndiceQdrant]:
    qdrant = IndiceQdrant(crear_conexion(MEMORIA), EmbeddingsDeterministas(), FRAGMENTOS)
    qdrant.indexar(FRAGMENTOS)
    yield qdrant
    qdrant.cerrar()


def _ids(resultados: list) -> list[str]:  # type: ignore[type-arg]
    return [r.fragmento.id for r in resultados]


# ------------------------------------------------------------------ conexión
@pytest.mark.parametrize("ruta", [None, "", "   "])
def test_sin_ruta_ni_url_falla_con_un_mensaje_claro(ruta: str | None) -> None:
    with pytest.raises(ErrorConfiguracion, match="Qdrant sin destino"):
        crear_conexion(ruta)


def test_la_url_debe_ser_http_o_https() -> None:
    with pytest.raises(ErrorConfiguracion, match="FNA_QDRANT_URL"):
        crear_conexion(url="ftp://qdrant.local:6333")


def test_memoria_solo_si_se_pide() -> None:
    conexion = crear_conexion(MEMORIA)
    try:
        assert conexion.modo == "memoria" and conexion.destino == MEMORIA
    finally:
        conexion.cliente.close()


def test_carpeta_local_persiste_y_libera_el_bloqueo(tmp_path: Path) -> None:
    carpeta = tmp_path / "qdrant"
    primero = IndiceQdrant(crear_conexion(carpeta), EmbeddingsDeterministas(), FRAGMENTOS)
    assert primero.conexion.modo == "local" and carpeta.is_dir()
    assert primero.indexar(FRAGMENTOS) == len(FRAGMENTOS)
    primero.cerrar()  # sin cerrar, otro cliente no podría abrir la carpeta (un solo proceso por carpeta)
    segundo = IndiceQdrant(crear_conexion(carpeta), EmbeddingsDeterministas(), FRAGMENTOS)
    try:
        assert segundo.info().puntos == len(FRAGMENTOS)
        assert _ids(segundo.buscar("frenos de disco", 1)) == ["frenos#000"]
    finally:
        segundo.cerrar()


# ------------------------------------------------------------------ colección y búsqueda
def test_indexar_crea_la_coleccion_con_un_punto_por_fragmento(indice: IndiceQdrant) -> None:
    info = indice.info()
    assert info.disponible and info.puntos == len(FRAGMENTOS)
    assert info.dimension == 256 and info.distancia == "Cosine"
    assert info.modelo == "deterministas-hash" and info.revision == "sha256"
    assert info.campos_payload == list(CAMPOS_PAYLOAD)


def test_reindexar_reemplaza_la_coleccion(indice: IndiceQdrant) -> None:
    assert indice.indexar(FRAGMENTOS[:2]) == 2
    assert indice.info().puntos == 2


def test_buscar_es_determinista_y_trae_lo_relevante(indice: IndiceQdrant) -> None:
    primero = indice.buscar("¿Dónde está la sede principal en Yumbo?", 3)
    assert _ids(primero)[0] == "sede#000"
    assert _ids(indice.buscar("¿Dónde está la sede principal en Yumbo?", 3)) == _ids(primero)
    assert all(0.0 <= r.puntaje <= 1.0 for r in primero)


def test_buscar_omite_puntos_de_fragmentos_desconocidos(indice: IndiceQdrant) -> None:
    parcial = IndiceQdrant(indice.conexion, indice.funcion, FRAGMENTOS[:1])
    assert _ids(parcial.buscar("frenos sede plantas", 6)) == ["sede#000"]


def test_consulta_vacia_o_k_cero_no_busca(indice: IndiceQdrant) -> None:
    assert indice.buscar("   ", 5) == [] and indice.buscar("frenos", 0) == []


def test_sin_coleccion_buscar_avisa_y_info_explica_el_motivo() -> None:
    vacio = IndiceQdrant(crear_conexion(MEMORIA), EmbeddingsDeterministas(), FRAGMENTOS)
    try:
        with pytest.raises(ErrorRecuperadorNoDisponible, match="no existe la colección"):
            vacio.buscar("frenos", 3)
        info = vacio.info()
        assert not info.disponible and "fabrica indexar-qdrant" in info.motivo
    finally:
        vacio.cerrar()


# ------------------------------------------------------------------ honestidad sobre HNSW
@pytest.mark.parametrize("modo", ["memoria", "local"])
def test_el_modo_local_informa_busqueda_exacta(tmp_path: Path, modo: str) -> None:
    destino = MEMORIA if modo == "memoria" else tmp_path / "qdrant"
    qdrant = IndiceQdrant(crear_conexion(destino), EmbeddingsDeterministas(), FRAGMENTOS)
    try:
        qdrant.indexar(FRAGMENTOS)
        info = qdrant.info()
        assert info.modo == modo
        assert info.tipo_busqueda == "exacta" and info.vectores_indexados == 0
        assert "búsqueda exacta" in info.explicacion and "no construye HNSW" in info.explicacion
        assert "sin índices" in info.explicacion  # los filtros recorren los puntos en modo local
        assert (info.hnsw_m, info.hnsw_ef_construct) == (HNSW_M, HNSW_EF_CONSTRUCT)  # declarados
        assert info.umbral_busqueda_exacta_kb is None  # el modo local no lo usa
    finally:
        qdrant.cerrar()


# ------------------------------------------------------------------ filtros por payload
@pytest.mark.parametrize(
    ("filtro", "esperados"),
    [
        (FiltroPayload(seccion="autopartes"), {"plantas#000", "frenos#000", "english#000"}),
        (FiltroPayload(documento_id="frenos"), {"frenos#000"}),
        (FiltroPayload(idioma="en"), {"english#000"}),
        (FiltroPayload(origen="demostrativo"), {"prueba#000"}),
        (FiltroPayload(seccion="autopartes", idioma="es"), {"plantas#000", "frenos#000"}),
        (
            FiltroPayload(excluir_documentos=("prueba", "english")),
            {"sede#000", "plantas#000", "frenos#000", "sostenibilidad#000"},
        ),
    ],
)
def test_filtros_por_payload(indice: IndiceQdrant, filtro: FiltroPayload, esperados: set[str]) -> None:
    filtrado = indice.con_filtro(filtro)
    assert set(_ids(filtrado.buscar("frenos plantas sede informe documento", 10))) == esperados
    # El mismo criterio sobre los fragmentos (lo que usa BM25) da el mismo universo.
    assert {f.id for f in FRAGMENTOS if filtro.acepta(f)} == esperados


def test_filtro_vacio_no_restringe(indice: IndiceQdrant) -> None:
    assert FiltroPayload().a_qdrant() is None and FiltroPayload().vacio()
    assert len(indice.buscar("frenos plantas sede informe documento", 10)) == len(FRAGMENTOS)


def test_con_filtro_comparte_el_cliente(indice: IndiceQdrant) -> None:
    filtrado = indice.con_filtro(FiltroPayload(idioma="en"))
    assert filtrado.cliente is indice.cliente and filtrado.coleccion == indice.coleccion
    assert indice.filtro.vacio()  # el original no cambia


# ------------------------------------------------------------------ BM25 filtrado e híbrido RRF
def test_bm25_filtrado_aplica_el_mismo_criterio() -> None:
    filtro = FiltroPayload(seccion="autopartes", excluir_documentos=("english",))
    resultados = RecuperadorFiltrado(IndiceBM25(FRAGMENTOS), filtro).buscar("frenos plantas autopartes", 5)
    assert resultados and all(filtro.acepta(r.fragmento) for r in resultados)
    assert "english#000" not in _ids(resultados)


def test_bm25_sin_filtro_es_igual_a_bm25() -> None:
    bm25 = IndiceBM25(FRAGMENTOS)
    assert _ids(RecuperadorFiltrado(bm25, FiltroPayload()).buscar("frenos", 3)) == _ids(
        bm25.buscar("frenos", 3)
    )
    assert RecuperadorFiltrado(bm25, FiltroPayload(idioma="es")).buscar("frenos", 0) == []


def test_hibrido_rrf_con_qdrant_es_determinista_y_respeta_el_filtro(indice: IndiceQdrant) -> None:
    filtro = FiltroPayload(excluir_documentos=("prueba",))
    hibrido = RecuperadorHibrido(
        RecuperadorFiltrado(IndiceBM25(FRAGMENTOS), filtro), indice.con_filtro(filtro)
    )
    primero = hibrido.buscar("frenos de disco en la planta de autopartes", 3)
    assert _ids(primero)[0] == "frenos#000"
    assert "prueba#000" not in _ids(primero)
    assert _ids(hibrido.buscar("frenos de disco en la planta de autopartes", 3)) == _ids(primero)
