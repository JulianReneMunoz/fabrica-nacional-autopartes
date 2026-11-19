"""GET /api/v1/base/vectorial (R07): estado de la base vectorial Qdrant de IGNIS. Configuración temporal de
conftest, nomic sustituido por ``EmbeddingsDeterministas`` y sin red. La consulta no crea ni bloquea la
carpeta local, un servidor caído responde 200 con el motivo y nunca se exponen rutas absolutas ni textos."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient

from fabrica_autopartes.api.dependencias import obtener_servicio
from fabrica_autopartes.api.main import crear_app
from fabrica_autopartes.core.config import Configuracion
from fabrica_autopartes.knowledge import semantica, vectorial_qdrant
from fabrica_autopartes.knowledge.embeddings import EmbeddingsDeterministas
from fabrica_autopartes.knowledge.vectorial_qdrant import ConexionQdrant, cerrar_conexiones, ruta_visible
from fabrica_autopartes.llm.extractivo import ModeloExtractivo
from fabrica_autopartes.repositories.auditoria import RepositorioAuditoria
from fabrica_autopartes.services.asistente import ServicioAsistente

RUTA = "/api/v1/base/vectorial"


@pytest.fixture(autouse=True)
def _cerrar_conexiones_compartidas() -> Iterator[None]:
    yield
    cerrar_conexiones()


@pytest.fixture
def nomic_falso(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(semantica, "extra_instalado", lambda: True)
    monkeypatch.setattr(semantica, "modelo_en_cache", lambda: True)
    monkeypatch.setattr(semantica, "EmbeddingsNomic", lambda *_a, **_k: EmbeddingsDeterministas())


def _servicio(config: Configuracion) -> ServicioAsistente:
    return ServicioAsistente(
        config, RepositorioAuditoria(config.url_base_datos), modelo_llm=ModeloExtractivo()
    )


def _consultar(servicio: ServicioAsistente) -> tuple[dict[str, Any], str]:
    app = crear_app()
    app.dependency_overrides[obtener_servicio] = lambda: servicio
    r = TestClient(app).get(RUTA)
    assert r.status_code == 200
    return r.json(), r.text


def _sin_rutas_absolutas(texto: str, *rutas: Path) -> None:
    for ruta in rutas:
        assert str(ruta) not in texto and ruta.as_posix() not in texto
        assert str(ruta).replace("\\", "\\\\") not in texto  # también escapada dentro del JSON


def test_sin_indice_responde_no_disponible_sin_crear_la_carpeta(config_con_base: Configuracion) -> None:
    datos, texto = _consultar(_servicio(config_con_base))
    assert datos["disponible"] is False and "indexar-qdrant" in datos["motivo"]
    assert datos["recuperador_ignis"] == "bm25" and datos["modo"] == "local"
    assert not config_con_base.dir_qdrant.exists()
    _sin_rutas_absolutas(texto, config_con_base.dir_qdrant, config_con_base.dir_datos)
    assert ruta_visible(config_con_base.dir_qdrant) in datos["motivo"]  # «…/qdrant» fuera del proyecto


def test_con_indice_informa_la_coleccion_y_la_busqueda_exacta(
    config_con_base: Configuracion, nomic_falso: None
) -> None:
    servicio = _servicio(config_con_base)
    puntos = servicio.indexar_qdrant()["puntos"]
    servicio.cerrar()  # como el backend recién arrancado: sin cliente abierto
    datos, texto = _consultar(_servicio(config_con_base))
    assert datos["disponible"] is True and datos["puntos"] == puntos > 0
    assert (
        datos["modo"] == "local" and datos["tipo_busqueda"] == "exacta" and datos["vectores_indexados"] == 0
    )
    assert "no construye HNSW" in datos["explicacion"]
    assert datos["dimension"] == 256 and datos["distancia"] == "Cosine"
    assert datos["campos_payload"] == ["seccion", "documento_id", "idioma", "origen"]
    _sin_rutas_absolutas(texto, config_con_base.dir_qdrant, config_con_base.dir_datos)
    fragmentos = servicio.base.fragmentos
    assert not any(f.texto[:40] in texto for f in fragmentos)  # sin textos de fragmentos


class _ClienteCaido:
    def collection_exists(self, nombre: str) -> bool:
        raise httpx.ConnectError("conexión rechazada")

    def close(self) -> None:
        """Nada que cerrar."""


def test_servidor_caido_responde_200_con_el_motivo(
    config_con_base: Configuracion, monkeypatch: pytest.MonkeyPatch
) -> None:
    caido = ConexionQdrant(_ClienteCaido(), "servidor", "http://qdrant.test:6333")  # type: ignore[arg-type]
    monkeypatch.setattr(vectorial_qdrant, "conexion_compartida", lambda *_a, **_k: caido)
    config = config_con_base.model_copy(update={"qdrant_url": "http://qdrant.test:6333"})
    datos, _ = _consultar(_servicio(config))
    assert datos["disponible"] is False and datos["modo"] == "servidor"
    assert "no responde" in datos["motivo"]


def test_ruta_visible_no_expone_rutas_absolutas(tmp_path: Path) -> None:
    from fabrica_autopartes.core.config import RAIZ_PROYECTO

    assert ruta_visible(RAIZ_PROYECTO / "data" / "qdrant") == "data/qdrant"
    assert ruta_visible(tmp_path / "qdrant") == "…/qdrant"
    assert ruta_visible(":memory:") == ":memory:" and ruta_visible(None) == ""


def test_la_ruta_esta_documentada_en_openapi(config_con_base: Configuracion) -> None:
    app = crear_app()
    app.dependency_overrides[obtener_servicio] = lambda: _servicio(config_con_base)
    esquema = TestClient(app).get("/openapi.json").json()
    assert RUTA in esquema["paths"] and "get" in esquema["paths"][RUTA]


@pytest.mark.parametrize(
    "contenido",
    [b"{no es json", b"[1, 2, 3]", b'{"puntos": "muchos"}', b"\xff\xfe\x00no utf-8"],
    ids=["json_invalido", "no_es_objeto", "tipo_incorrecto", "no_utf8"],
)
def test_resumen_danado_responde_no_disponible_sin_500(
    config_con_base: Configuracion, contenido: bytes
) -> None:
    from fabrica_autopartes.knowledge.vectorial_qdrant import ARCHIVO_RESUMEN

    config_con_base.dir_qdrant.mkdir(parents=True)
    (config_con_base.dir_qdrant / ARCHIVO_RESUMEN).write_bytes(contenido)
    datos, _ = _consultar(_servicio(config_con_base))
    assert datos["disponible"] is False
    assert datos["motivo"] == "resumen dañado: ejecutar «fabrica indexar-qdrant»"
