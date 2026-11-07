"""Embeddings de la base semántica sin modelos ni red (ADR-023): prefijos, L2, dispositivo e índice."""

from __future__ import annotations

import numpy as np
import pytest

from fabrica_autopartes.core.config import Configuracion
from fabrica_autopartes.core.excepciones import ErrorConfiguracion, ErrorRecuperadorNoDisponible
from fabrica_autopartes.domain.modelos import Fragmento
from fabrica_autopartes.knowledge.base import BaseConocimiento
from fabrica_autopartes.knowledge.embeddings import (
    PREFIJO_CONSULTA,
    PREFIJO_DOCUMENTO,
    EmbeddingsDeterministas,
    FuncionEmbeddings,
    IndiceVectorialMemoria,
    Matriz,
    dispositivos_disponibles,
    normalizar_l2,
    resolver_dispositivo,
)


def _fragmento(id_: str, texto: str) -> Fragmento:
    return Fragmento(
        id=id_,
        documento_id=id_.split("#")[0],
        url=f"https://fanalca.com/{id_}",
        titulo="",
        seccion="general",
        texto=texto,
        tokens_aprox=len(texto.split()),
        orden=0,
    )


FRAGMENTOS = [
    _fragmento("sede#000", "La sede principal queda en la Calle 13 de Acopi, Yumbo"),
    _fragmento("historia#000", "Fanalca se constituyó el 31 de mayo de 1958"),
    _fragmento("contacto#000", "Teléfono de contacto 651 5343"),
]


class _Espia(FuncionEmbeddings):
    """Registra los textos recibidos para comprobar los prefijos."""

    def __init__(self) -> None:
        self.recibidos: list[str] = []

    def _codificar(self, textos: list[str]) -> Matriz:
        self.recibidos.extend(textos)
        return np.ones((len(textos), 4), dtype=np.float32) * 3


def test_prefijos_de_documento_y_consulta() -> None:
    espia = _Espia()
    espia.documentos(["doc"])
    espia.consultas(["pregunta"])
    espia.consultas(["sin"], con_prefijo=False)
    assert espia.recibidos == [f"{PREFIJO_DOCUMENTO}doc", f"{PREFIJO_CONSULTA}pregunta", "sin"]
    assert PREFIJO_DOCUMENTO == "search_document: " and PREFIJO_CONSULTA == "search_query: "


def test_salida_normalizada_l2() -> None:
    vectores = _Espia().documentos(["a", "b"])
    np.testing.assert_allclose(np.linalg.norm(vectores, axis=1), 1.0, rtol=1e-6)


def test_normalizar_l2_conserva_filas_nulas() -> None:
    m = normalizar_l2([[3.0, 4.0], [0.0, 0.0]])
    np.testing.assert_allclose(m, [[0.6, 0.8], [0.0, 0.0]])


def test_embeddings_deterministas_son_reproducibles() -> None:
    a = EmbeddingsDeterministas().documentos(["Calle 13 Yumbo"])
    b = EmbeddingsDeterministas().documentos(["Calle 13 Yumbo"])
    np.testing.assert_array_equal(a, b)


def test_indice_memoria_recupera_el_fragmento_pertinente() -> None:
    indice = IndiceVectorialMemoria(FRAGMENTOS, EmbeddingsDeterministas())
    resultados = indice.buscar("¿Cuál es el teléfono de contacto?", k=2)
    assert resultados[0].fragmento.id == "contacto#000"
    assert len(resultados) == 2
    assert indice.buscar("   ") == []
    assert IndiceVectorialMemoria([], EmbeddingsDeterministas()).buscar("sede") == []


@pytest.mark.parametrize(
    ("preferencia", "cuda", "esperado"),
    [("auto", True, "cuda"), ("auto", False, "cpu"), ("cpu", True, "cpu"), ("cuda", True, "cuda")],
)
def test_resolver_dispositivo(preferencia: str, cuda: bool, esperado: str) -> None:
    assert resolver_dispositivo(preferencia, cuda_disponible=cuda) == esperado


def test_cuda_sin_gpu_es_un_error_explicito() -> None:
    with pytest.raises(ErrorConfiguracion, match="EMBEDDINGS_DEVICE=cuda"):
        resolver_dispositivo("cuda", cuda_disponible=False)
    with pytest.raises(ErrorConfiguracion, match="inválido"):
        resolver_dispositivo("tpu", cuda_disponible=True)


def test_dispositivos_disponibles_omite_cuda_sin_gpu() -> None:
    assert dispositivos_disponibles(["cpu", "cuda"], cuda_disponible=False) == ["cpu"]
    assert dispositivos_disponibles(["cpu", "cuda"], cuda_disponible=True) == ["cpu", "cuda"]


def test_embeddings_device_se_lee_sin_prefijo(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EMBEDDINGS_DEVICE", "cpu")
    assert Configuracion(_env_file=None).embeddings_dispositivo == "cpu"  # type: ignore[call-arg]
    monkeypatch.delenv("EMBEDDINGS_DEVICE")
    assert Configuracion(_env_file=None).embeddings_dispositivo == "auto"  # type: ignore[call-arg]


def test_base_usa_bm25_por_defecto_y_el_semantico_inyectado(config_con_base: Configuracion) -> None:
    base = BaseConocimiento(config_con_base.dir_gold)
    assert base.recuperador() is base.indice
    semantico = IndiceVectorialMemoria(base.fragmentos, EmbeddingsDeterministas())
    base.usar_recuperador_semantico(semantico)
    assert base.recuperador("semantico") is semantico
    ctx = base.armar_contexto("sede principal", "seleccion", k=3, recuperador="semantico")
    assert [f.id for f in ctx.fragmentos] == [r.fragmento.id for r in semantico.buscar("sede principal", 3)]
    with pytest.raises(ErrorConfiguracion, match="desconocido"):
        base.recuperador("vectorial")


def test_semantico_sin_extra_da_un_error_claro(
    config_con_base: Configuracion, monkeypatch: pytest.MonkeyPatch
) -> None:
    from fabrica_autopartes.knowledge import semantica

    monkeypatch.setattr(semantica, "extra_instalado", lambda: False)
    with pytest.raises(ErrorRecuperadorNoDisponible, match="semantica-cpu") as error:
        BaseConocimiento(config_con_base.dir_gold).recuperador("semantico")
    assert error.value.estado_http == 503 and "make indexar" in str(error.value)
    disponible, motivo = BaseConocimiento(config_con_base.dir_gold).disponibilidad_semantica()
    assert not disponible and "semantica-cpu" in motivo


def test_disponibilidad_sin_indice(config_con_base: Configuracion, monkeypatch: pytest.MonkeyPatch) -> None:
    from fabrica_autopartes.knowledge import semantica

    monkeypatch.setattr(semantica, "extra_instalado", lambda: True)
    monkeypatch.setattr(semantica, "modelo_en_cache", lambda: True)
    disponible, motivo = semantica.disponibilidad(config_con_base.dir_datos / "vectores")
    assert not disponible and "índice vectorial" in motivo
    monkeypatch.setattr(semantica, "modelo_en_cache", lambda: False)
    assert "caché" in semantica.disponibilidad(config_con_base.dir_datos / "vectores")[1]
