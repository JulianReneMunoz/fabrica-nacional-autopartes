"""Fixtures compartidas: configuración aislada en un directorio temporal, base Gold
construida desde la semilla del repositorio y servicio con el modelo extractivo."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from fabrica_autopartes.core.config import RAIZ_PROYECTO, Configuracion
from fabrica_autopartes.llm.extractivo import ModeloExtractivo
from fabrica_autopartes.pipelines.orquestador import construir_base
from fabrica_autopartes.repositories.auditoria import RepositorioAuditoria
from fabrica_autopartes.services.asistente import ServicioAsistente

DIR_FIXTURES = Path(__file__).parent / "fixtures"
DOMINIO_PRUEBA = "https://ejemplo-fna.test"


@pytest.fixture
def config(tmp_path: Path) -> Configuracion:
    datos = tmp_path / "data"
    shutil.copytree(RAIZ_PROYECTO / "data" / "seed", datos / "seed")
    return Configuracion(
        _env_file=None,  # type: ignore[call-arg]
        dir_datos=datos,
        url_base_datos=f"sqlite:///{(tmp_path / 'prueba.db').as_posix()}",
        proveedor_llm="extractivo",
        pausa_entre_peticiones_s=0.0,
        reintentos=0,
        dominios_permitidos=["ejemplo-fna.test"],
        urls_semilla=[f"{DOMINIO_PRUEBA}/"],
        api_clave_admin="clave-de-prueba",
    )


@pytest.fixture
def config_con_base(config: Configuracion) -> Configuracion:
    construir_base(config, "semilla")
    return config


@pytest.fixture
def servicio(config_con_base: Configuracion) -> ServicioAsistente:
    return ServicioAsistente(
        config_con_base,
        RepositorioAuditoria(config_con_base.url_base_datos),
        modelo_llm=ModeloExtractivo(),
    )
