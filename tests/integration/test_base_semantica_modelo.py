"""Pruebas con el modelo nomic real y Chroma; se omiten si el extra o el modelo no están (CI)."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from fabrica_autopartes.domain.modelos import Fragmento
from fabrica_autopartes.knowledge import semantica

pytestmark = pytest.mark.skipif(
    not semantica.modelo_en_cache(),
    reason="Requiere el extra semantica-cpu/gpu y el modelo nomic en la caché de Hugging Face",
)


def _fragmento(id_: str, texto: str) -> Fragmento:
    return Fragmento(
        id=id_,
        documento_id=id_,
        url=f"https://fanalca.com/{id_}",
        titulo="",
        seccion="general",
        texto=texto,
        tokens_aprox=len(texto.split()),
        orden=0,
    )


@pytest.fixture(scope="module")
def nomic() -> semantica.EmbeddingsNomic:
    return semantica.EmbeddingsNomic("auto")


def test_nomic_768_dimensiones_normalizado(nomic: semantica.EmbeddingsNomic) -> None:
    v = nomic.documentos(["La sede principal queda en Yumbo"])
    assert v.shape == (1, 768)
    np.testing.assert_allclose(np.linalg.norm(v, axis=1), 1.0, rtol=1e-5)


def test_chroma_persistente_ida_y_vuelta(nomic: semantica.EmbeddingsNomic, tmp_path: Path) -> None:
    fragmentos = [
        _fragmento("sede", "La sede principal queda en la Calle 13, Acopi, Yumbo"),
        _fragmento("moto", "Motocicletas Honda ensambladas en Colombia"),
    ]
    indice = semantica.IndiceChroma(tmp_path / "vectores", nomic, fragmentos)
    assert indice.indexar(fragmentos) == 2
    reabierto = semantica.IndiceChroma(tmp_path / "vectores", nomic, fragmentos)
    resultados = reabierto.buscar("¿Dónde está la sede?", k=2)
    assert resultados[0].fragmento.id == "sede"
    assert 0.0 < resultados[0].puntaje <= 1.0


def test_chroma_vacio_y_sin_coleccion(nomic: semantica.EmbeddingsNomic, tmp_path: Path) -> None:
    from fabrica_autopartes.core.excepciones import ErrorBaseConocimientoVacia

    indice = semantica.IndiceChroma(tmp_path / "vectores", nomic, [])
    with pytest.raises(ErrorBaseConocimientoVacia, match="indexar-vectores"):
        indice.buscar("sede")
    assert indice.indexar([]) == 0
    assert indice.buscar("sede") == []
