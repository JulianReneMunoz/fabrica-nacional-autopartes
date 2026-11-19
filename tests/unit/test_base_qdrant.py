"""``BaseConocimiento`` con ``hibrido_qdrant`` (R07): RRF de BM25 y Qdrant con filtros, respaldo a bm25 con
motivo registrado y conexión única por destino. Sin modelo ni red: ``:memory:`` o ``tmp_path`` con
``EmbeddingsDeterministas``; el servidor caído se simula con un cliente falso. No escribe en ``data/``."""

from __future__ import annotations

import logging
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import httpx
import pytest

from fabrica_autopartes.core.excepciones import ErrorConfiguracion, ErrorRecuperadorNoDisponible
from fabrica_autopartes.domain.modelos import Fragmento
from fabrica_autopartes.knowledge import semantica, vectorial_qdrant
from fabrica_autopartes.knowledge.base import RECUPERADOR_QDRANT, BaseConocimiento
from fabrica_autopartes.knowledge.embeddings import EmbeddingsDeterministas
from fabrica_autopartes.knowledge.recuperacion import IndiceBM25
from fabrica_autopartes.knowledge.vectorial_qdrant import (
    MEMORIA,
    ConexionQdrant,
    FiltroPayload,
    IndiceQdrant,
    cerrar_conexiones,
    conexion_compartida,
    info_coleccion,
)

CONSULTA_PRIVADA = "consulta-privada-del-cliente frenos"


def _frag(i: str, texto: str, documento: str) -> Fragmento:
    return Fragmento(
        id=i,
        documento_id=documento,
        url=f"https://ejemplo-fna.test/{documento}",
        titulo=f"Documento {documento}",
        seccion="autopartes",
        texto=texto,
        tokens_aprox=len(texto.split()),
        orden=0,
    )


FRAGMENTOS = [
    _frag("frenos#000", "Los frenos de disco se fabrican en la planta de autopartes.", "frenos"),
    _frag("plantas#000", "Las plantas de autopartes producen frenos y suspensiones.", "plantas"),
    _frag("sede#000", "La sede principal está en Yumbo, Valle del Cauca.", "sede"),
    _frag("listado#000", "Listado del blog con frenos frenos frenos.", "listado"),
]


@pytest.fixture(autouse=True)
def _cerrar_conexiones_compartidas() -> Iterator[None]:
    """«:memory:» comparte la misma clave en ``conexion_compartida``: sin cerrar, el estado pasaría de una
    prueba a otra."""
    yield
    cerrar_conexiones()


@pytest.fixture
def dir_gold(tmp_path: Path) -> Path:
    gold = tmp_path / "gold"
    gold.mkdir()
    (gold / "fragmentos.jsonl").write_text(
        "".join(f.model_dump_json() + "\n" for f in FRAGMENTOS), encoding="utf-8"
    )
    return gold


def _base_con_indice(dir_gold: Path) -> BaseConocimiento:
    base = BaseConocimiento(dir_gold, dir_qdrant=None)
    indice = IndiceQdrant(conexion_compartida(MEMORIA), EmbeddingsDeterministas(), base.fragmentos)
    indice.indexar(base.fragmentos)
    base.usar_indice_qdrant(indice)
    return base


def _ids(resultados: list[Any]) -> list[str]:
    return [r.fragmento.id for r in resultados]


class _ClienteCaido:
    """Cliente falso de un servidor que no responde (sin abrir conexiones)."""

    def collection_exists(self, nombre: str) -> bool:
        raise httpx.ConnectError("conexión rechazada")

    def close(self) -> None:
        """Nada que cerrar."""


# ------------------------------------------------------------------ los recuperadores de hoy no cambian
def test_bm25_sigue_siendo_el_indice_bm25(dir_gold: Path) -> None:
    base = BaseConocimiento(dir_gold)
    assert isinstance(base.recuperador("bm25"), IndiceBM25)
    assert isinstance(base.recuperador(), IndiceBM25)


def test_hibrido_sin_chroma_falla_igual_que_hoy(dir_gold: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(semantica, "disponibilidad", lambda _d: (False, "falta el extra"))
    base = BaseConocimiento(dir_gold)
    with pytest.raises(ErrorRecuperadorNoDisponible, match="falta el extra"):
        base.recuperador("hibrido")
    resultados, usado = base.buscar_con_respaldo("frenos", 2, "hibrido")
    assert usado == "bm25" and _ids(resultados) == _ids(base.indice.buscar("frenos", 2))
    assert base._motivo_sin_qdrant is None  # el respaldo de Chroma (M1) no toca el de Qdrant


def test_recuperador_desconocido_mantiene_el_mensaje(dir_gold: Path) -> None:
    with pytest.raises(ErrorConfiguracion, match="bm25, semantico o hibrido"):
        BaseConocimiento(dir_gold).recuperador("otro")


# ------------------------------------------------------------------ hibrido_qdrant
def test_hibrido_qdrant_fusiona_y_respeta_el_filtro(dir_gold: Path) -> None:
    base = _base_con_indice(dir_gold)
    filtro = FiltroPayload(excluir_documentos=("listado",))
    primero, usado = base.buscar_con_respaldo("frenos de disco en la planta", 3, RECUPERADOR_QDRANT, filtro)
    assert usado == RECUPERADOR_QDRANT
    assert _ids(primero)[0] == "frenos#000" and "listado#000" not in _ids(primero)
    segundo, _ = base.buscar_con_respaldo("frenos de disco en la planta", 3, RECUPERADOR_QDRANT, filtro)
    assert _ids(segundo) == _ids(primero)


def test_sin_destino_vuelve_a_bm25_y_recuerda_el_motivo(
    dir_gold: Path, caplog: pytest.LogCaptureFixture
) -> None:
    base = BaseConocimiento(dir_gold)
    filtro = FiltroPayload(excluir_documentos=("listado",))
    with caplog.at_level(logging.WARNING):
        resultados, usado = base.buscar_con_respaldo(CONSULTA_PRIVADA, 3, RECUPERADOR_QDRANT, filtro)
    assert usado == "bm25" and resultados
    assert "listado#000" not in _ids(resultados)  # el respaldo conserva el filtro
    assert base._motivo_sin_qdrant is not None and "sin destino" in base._motivo_sin_qdrant
    # El registro nombra el recuperador y el motivo, nunca la consulta ni el contenido de los fragmentos.
    assert "hibrido_qdrant" in caplog.text
    assert "consulta-privada" not in caplog.text and "Valle del Cauca" not in caplog.text
    # Ya no reintenta: el motivo queda recordado.
    caplog.clear()
    with caplog.at_level(logging.WARNING):
        _, usado = base.buscar_con_respaldo(CONSULTA_PRIVADA, 3, RECUPERADOR_QDRANT)
    assert usado == "bm25" and caplog.text == ""


def test_sin_coleccion_vuelve_a_bm25_sin_cargar_el_modelo(
    dir_gold: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def no_cargar(*_a: object, **_k: object) -> None:
        raise AssertionError("no debe cargar el modelo si no hay colección")

    monkeypatch.setattr(semantica, "EmbeddingsNomic", no_cargar)
    base = BaseConocimiento(dir_gold, dir_qdrant=tmp_path / "qdrant")
    _, usado = base.buscar_con_respaldo("frenos", 2, RECUPERADOR_QDRANT)
    assert usado == "bm25"
    assert base._motivo_sin_qdrant is not None and "indexar-qdrant" in base._motivo_sin_qdrant
    assert base.disponibilidad_qdrant() == (False, base.info_vectorial().motivo)


@pytest.mark.parametrize(
    ("extra", "modelo", "motivo"),
    [(False, False, "falta el extra"), (True, False, "no está en la caché")],
)
def test_sin_extra_o_sin_modelo_da_el_motivo(
    dir_gold: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    extra: bool,
    modelo: bool,
    motivo: str,
) -> None:
    carpeta = tmp_path / "qdrant"
    indice = IndiceQdrant(conexion_compartida(carpeta), EmbeddingsDeterministas(), FRAGMENTOS)
    indice.indexar(FRAGMENTOS)
    monkeypatch.setattr(semantica, "extra_instalado", lambda: extra)
    monkeypatch.setattr(semantica, "modelo_en_cache", lambda: modelo)
    base = BaseConocimiento(dir_gold, dir_qdrant=carpeta)
    disponible, texto = base.disponibilidad_qdrant()
    assert not disponible and motivo in texto
    _, usado = base.buscar_con_respaldo("frenos", 2, RECUPERADOR_QDRANT)
    assert usado == "bm25" and motivo in (base._motivo_sin_qdrant or "")


def test_un_fallo_al_cargar_el_modelo_vuelve_a_bm25(
    dir_gold: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    carpeta = tmp_path / "qdrant"
    IndiceQdrant(conexion_compartida(carpeta), EmbeddingsDeterministas(), FRAGMENTOS).indexar(FRAGMENTOS)

    def falla(*_a: object, **_k: object) -> None:
        raise OSError("modelo dañado")

    monkeypatch.setattr(semantica, "extra_instalado", lambda: True)
    monkeypatch.setattr(semantica, "modelo_en_cache", lambda: True)
    monkeypatch.setattr(semantica, "EmbeddingsNomic", falla)
    base = BaseConocimiento(dir_gold, dir_qdrant=carpeta)
    _, usado = base.buscar_con_respaldo("frenos", 2, RECUPERADOR_QDRANT)
    assert usado == "bm25" and "error al cargar el modelo: OSError" in (base._motivo_sin_qdrant or "")


def test_servidor_caido_vuelve_a_bm25_e_info_no_falla(
    dir_gold: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    caido = ConexionQdrant(_ClienteCaido(), "servidor", "http://qdrant.test:6333")  # type: ignore[arg-type]
    monkeypatch.setattr(vectorial_qdrant, "conexion_compartida", lambda *_a, **_k: caido)
    base = BaseConocimiento(dir_gold, qdrant_url="http://qdrant.test:6333")
    _, usado = base.buscar_con_respaldo("frenos", 2, RECUPERADOR_QDRANT)
    assert usado == "bm25" and "no responde (ConnectError)" in (base._motivo_sin_qdrant or "")
    info = base.info_vectorial()
    assert not info.disponible and info.modo == "servidor" and "no responde" in info.motivo
    assert not info_coleccion(caido).disponible


def test_buscar_con_el_servidor_caido_se_informa_como_no_disponible() -> None:
    indice = IndiceQdrant(
        ConexionQdrant(_ClienteCaido(), "servidor", "http://qdrant.test:6333"),  # type: ignore[arg-type]
        EmbeddingsDeterministas(),
        FRAGMENTOS,
    )
    with pytest.raises(ErrorRecuperadorNoDisponible, match="no responde"):
        indice.buscar("frenos", 2)


# ------------------------------------------------------------------ conexión compartida
def test_un_cliente_por_destino(tmp_path: Path) -> None:
    carpeta = tmp_path / "qdrant"
    primera = conexion_compartida(carpeta)
    assert conexion_compartida(carpeta) is primera
    assert conexion_compartida(str(carpeta)) is primera  # la misma carpeta, aunque llegue como texto
    assert conexion_compartida(MEMORIA) is not primera


def test_carpeta_en_uso_por_otro_proceso(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def ocupada(*_a: object, **_k: object) -> None:
        raise RuntimeError("Storage folder is already accessed by another instance of Qdrant client.")

    monkeypatch.setattr(vectorial_qdrant, "crear_conexion", ocupada)
    with pytest.raises(ErrorRecuperadorNoDisponible, match="en uso por otro proceso"):
        conexion_compartida(tmp_path / "qdrant")


def test_cerrar_conexiones_permite_reabrir_la_carpeta(tmp_path: Path) -> None:
    carpeta = tmp_path / "qdrant"
    primera = conexion_compartida(carpeta)
    cerrar_conexiones()
    assert conexion_compartida(carpeta) is not primera


# ------------------------------------------------------------------ información y recarga
def test_info_vectorial_sin_y_con_coleccion(dir_gold: Path, tmp_path: Path) -> None:
    sin_destino = BaseConocimiento(dir_gold).info_vectorial()
    assert not sin_destino.disponible and "sin destino" in sin_destino.motivo
    carpeta = tmp_path / "qdrant"
    base = BaseConocimiento(dir_gold, dir_qdrant=carpeta)
    assert not base.info_vectorial().disponible
    IndiceQdrant(conexion_compartida(carpeta), EmbeddingsDeterministas(), FRAGMENTOS).indexar(FRAGMENTOS)
    info = base.info_vectorial()
    assert info.disponible and info.puntos == len(FRAGMENTOS) and info.tipo_busqueda == "exacta"


def test_recargar_olvida_el_indice_y_el_motivo(dir_gold: Path) -> None:
    base = _base_con_indice(dir_gold)
    assert base.disponibilidad_qdrant() == (True, "")
    base._motivo_sin_qdrant = "motivo anterior"
    base.recargar()
    assert base._qdrant is None and base._motivo_sin_qdrant is None


def test_sin_destino_no_abre_ninguna_carpeta(dir_gold: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Por omisión (como hoy en el M1 y en IGNIS con bm25) no se crea ningún cliente de Qdrant."""

    def no_abrir(*_a: object, **_k: object) -> None:
        raise AssertionError("no debe abrir Qdrant sin destino")

    monkeypatch.setattr(vectorial_qdrant, "crear_conexion", no_abrir)
    base = BaseConocimiento(dir_gold)
    assert base.dir_qdrant is None and base.qdrant_url is None
    assert base.buscar("frenos", 2) and not base.info_vectorial().disponible
