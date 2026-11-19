"""Servicio y CLI de la base Qdrant de IGNIS (R07): ``indexar_qdrant``, ``fabrica indexar-qdrant`` e
``info_vectorial``. Configuración temporal de conftest (``dir_datos`` en ``tmp_path``), nomic sustituido por
``EmbeddingsDeterministas`` y sin red. Consultar el estado nunca crea ni bloquea la carpeta local."""

from __future__ import annotations

import json
import shutil
import subprocess
from collections.abc import Iterator
from typing import Any

import pytest

from fabrica_autopartes import cli
from fabrica_autopartes.core.config import RAIZ_PROYECTO, Configuracion
from fabrica_autopartes.core.excepciones import ErrorRecuperadorNoDisponible
from fabrica_autopartes.knowledge import semantica, vectorial_qdrant
from fabrica_autopartes.knowledge.embeddings import EmbeddingsDeterministas
from fabrica_autopartes.knowledge.vectorial_qdrant import (
    ARCHIVO_RESUMEN,
    cerrar_conexiones,
    conexion_abierta,
    crear_conexion,
)
from fabrica_autopartes.llm.extractivo import ModeloExtractivo
from fabrica_autopartes.repositories.auditoria import RepositorioAuditoria
from fabrica_autopartes.services import asistente
from fabrica_autopartes.services.asistente import ServicioAsistente


@pytest.fixture(autouse=True)
def _cerrar_conexiones_compartidas() -> Iterator[None]:
    yield
    cerrar_conexiones()


@pytest.fixture
def pedidos_modelo(monkeypatch: pytest.MonkeyPatch) -> list[bool]:
    """Sustituye nomic por embeddings deterministas y registra ``solo_local`` de cada carga del modelo."""
    pedidos: list[bool] = []

    def nomic_falso(
        _dispositivo: str = "auto", solo_local: bool = True, **_k: Any
    ) -> EmbeddingsDeterministas:
        pedidos.append(solo_local)
        return EmbeddingsDeterministas()

    monkeypatch.setattr(semantica, "extra_instalado", lambda: True)
    monkeypatch.setattr(semantica, "modelo_en_cache", lambda: True)
    monkeypatch.setattr(semantica, "EmbeddingsNomic", nomic_falso)
    return pedidos


def _servicio(config: Configuracion) -> ServicioAsistente:
    return ServicioAsistente(
        config, RepositorioAuditoria(config.url_base_datos), modelo_llm=ModeloExtractivo()
    )


def test_indexar_crea_la_coleccion_sin_red(
    config_con_base: Configuracion, pedidos_modelo: list[bool]
) -> None:
    servicio = _servicio(config_con_base)
    resumen = servicio.indexar_qdrant()
    fragmentos = servicio.base.fragmentos
    assert resumen["puntos"] == len(fragmentos) > 0
    assert resumen["modo"] == "local" and resumen["tipo_busqueda"] == "exacta"
    assert resumen["destino"] == str(config_con_base.dir_qdrant)
    assert pedidos_modelo == [True]  # solo la caché: sin --descargar no hay red
    assert config_con_base.dir_qdrant.is_dir() and (config_con_base.dir_qdrant / ARCHIVO_RESUMEN).is_file()
    # Ni el resumen devuelto ni el archivo de resumen llevan textos de fragmentos.
    textos = json.dumps(resumen, ensure_ascii=False) + (
        config_con_base.dir_qdrant / ARCHIVO_RESUMEN
    ).read_text(encoding="utf-8")
    assert not any(f.texto[:40] in textos for f in fragmentos)


def test_descargar_permite_la_red_solo_si_se_pide(
    config_con_base: Configuracion, pedidos_modelo: list[bool]
) -> None:
    _servicio(config_con_base).indexar_qdrant(descargar=True)
    assert pedidos_modelo == [False]


def test_consultar_sin_indice_no_crea_la_carpeta(config_con_base: Configuracion) -> None:
    servicio = _servicio(config_con_base)
    info = servicio.info_vectorial()
    assert not info.disponible and "indexar-qdrant" in info.motivo
    assert info.recuperador_ignis == "bm25"
    assert servicio.base.disponibilidad_qdrant()[0] is False
    assert not config_con_base.dir_qdrant.exists()


def test_info_antes_y_despues_de_indexar(config_con_base: Configuracion, pedidos_modelo: list[bool]) -> None:
    servicio = _servicio(config_con_base)
    assert not servicio.info_vectorial().disponible
    servicio.indexar_qdrant()
    info = servicio.info_vectorial()
    assert info.disponible and info.puntos == len(servicio.base.fragmentos)
    assert info.modo == "local" and info.tipo_busqueda == "exacta" and info.recuperador_ignis == "bm25"


def test_consultar_con_indice_no_abre_ni_bloquea_la_carpeta(
    config_con_base: Configuracion, pedidos_modelo: list[bool], monkeypatch: pytest.MonkeyPatch
) -> None:
    servicio = _servicio(config_con_base)
    puntos = servicio.indexar_qdrant()["puntos"]
    servicio.cerrar()  # como otro proceso: sin cliente abierto
    assert conexion_abierta(config_con_base.dir_qdrant) is None

    def no_abrir(*_a: object, **_k: object) -> None:
        raise AssertionError("consultar el estado no debe abrir un cliente")

    monkeypatch.setattr(vectorial_qdrant, "crear_conexion", no_abrir)
    otro = _servicio(config_con_base)
    info = otro.info_vectorial()
    assert info.disponible and info.puntos == puntos and info.generado_en
    assert otro.base.disponibilidad_qdrant() == (True, "")
    assert conexion_abierta(config_con_base.dir_qdrant) is None


def test_cerrar_libera_la_carpeta(config_con_base: Configuracion, pedidos_modelo: list[bool]) -> None:
    servicio = _servicio(config_con_base)
    servicio.indexar_qdrant()
    servicio.cerrar()
    otro_cliente = crear_conexion(config_con_base.dir_qdrant)  # fallaría si la carpeta siguiera bloqueada
    otro_cliente.cliente.close()


def test_sin_extra_falla_con_un_motivo_claro(
    config_con_base: Configuracion, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(semantica, "extra_instalado", lambda: False)
    with pytest.raises(ErrorRecuperadorNoDisponible, match="falta el extra"):
        _servicio(config_con_base).indexar_qdrant()
    assert not config_con_base.dir_qdrant.exists()


def test_el_m1_no_cambia_con_la_configuracion_por_defecto(config_con_base: Configuracion) -> None:
    servicio = _servicio(config_con_base)
    assert servicio.base.recuperador_por_defecto == "bm25"
    assert config_con_base.ignis_recuperador == "bm25" and config_con_base.agente_recuperador == "hibrido"
    assert servicio.base.buscar("autopartes", 3)
    assert not config_con_base.dir_qdrant.exists()  # nada de Qdrant se abre ni se crea


# ------------------------------------------------------------------ CLI
@pytest.fixture
def cli_con_config(config_con_base: Configuracion, monkeypatch: pytest.MonkeyPatch) -> Configuracion:
    monkeypatch.setattr(asistente, "obtener_configuracion", lambda: config_con_base)
    return config_con_base


def test_cli_indexar_qdrant(
    cli_con_config: Configuracion, pedidos_modelo: list[bool], capsys: pytest.CaptureFixture[str]
) -> None:
    assert cli.main(["indexar-qdrant"]) == 0
    salida = json.loads(capsys.readouterr().out)
    assert salida["puntos"] > 0 and salida["modo"] == "local" and salida["tipo_busqueda"] == "exacta"
    assert pedidos_modelo == [True]


def test_cli_sin_modelo_en_cache_sale_con_1_sin_traza(
    cli_con_config: Configuracion, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def no_cargar(*_a: object, **_k: object) -> None:
        raise AssertionError("sin el modelo en caché no debe intentar cargarlo")

    monkeypatch.setattr(semantica, "extra_instalado", lambda: True)
    monkeypatch.setattr(semantica, "modelo_en_cache", lambda: False)
    monkeypatch.setattr(semantica, "EmbeddingsNomic", no_cargar)
    assert cli.main(["indexar-qdrant"]) == 1
    error = capsys.readouterr().err
    assert "no está en la caché" in error and "--descargar" in error
    assert "Traceback" not in error and "make indexar" not in error
    assert not cli_con_config.dir_qdrant.exists()


def test_cli_carpeta_en_uso_por_otro_proceso(
    cli_con_config: Configuracion,
    pedidos_modelo: list[bool],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def ocupada(*_a: object, **_k: object) -> None:
        raise RuntimeError("Storage folder is already accessed by another instance of Qdrant client.")

    monkeypatch.setattr(vectorial_qdrant, "crear_conexion", ocupada)
    assert cli.main(["indexar-qdrant"]) == 1
    error = capsys.readouterr().err
    assert "en uso por otro proceso" in error and "FNA_QDRANT_URL" in error and "Traceback" not in error


# ------------------------------------------------------------------ .gitignore
@pytest.mark.skipif(shutil.which("git") is None, reason="git no está instalado")
def test_data_qdrant_esta_ignorada_en_git() -> None:
    r = subprocess.run(
        ["git", "check-ignore", "-q", "data/qdrant/storage.sqlite"], cwd=RAIZ_PROYECTO, check=False
    )
    assert r.returncode == 0
