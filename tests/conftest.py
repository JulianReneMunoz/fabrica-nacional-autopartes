"""Fixtures compartidas: configuración aislada en un directorio temporal, base Gold
construida desde la semilla del repositorio y servicio con el modelo extractivo."""

from __future__ import annotations

import functools
import json
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
SECRETO_SESION_PRUEBA = "secreto-de-prueba-de-sesiones-ignis-0123456789"
RAZON_GOLD_VERSIONADO = "Requiere el corpus Gold versionado; el CI usa la base de demostración"
# Identificadores que solo existen en el Gold versionado, no en la base de demostración que el CI construye
# con «fabrica build --fuente semilla» antes de pytest. Son fijos a propósito: no se leen de
# config/ignis_exclusiones.yaml, para que una exclusión inexistente haga fallar la prueba en vez de omitirla.
_FRAGMENTO_GOLD_VERSIONADO = "nosotros#002"
_DOCUMENTO_GOLD_VERSIONADO = "negocio-honda-motos"


@functools.cache
def gold_versionado_completo() -> bool:
    """True si data/gold es el corpus versionado completo y no la base de demostración (semilla)."""
    ruta = RAIZ_PROYECTO / "data" / "gold" / "fragmentos.jsonl"
    if not ruta.exists():
        return False
    ids, documentos = set(), set()
    for linea in ruta.read_text(encoding="utf-8").splitlines():
        if linea.strip():
            fragmento = json.loads(linea)
            ids.add(fragmento["id"])
            documentos.add(fragmento["documento_id"])
    return _FRAGMENTO_GOLD_VERSIONADO in ids and _DOCUMENTO_GOLD_VERSIONADO in documentos


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers", "gold_versionado: se omite si data/gold es la base de demostración (CI)"
    )


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    if gold_versionado_completo():
        return
    omitir = pytest.mark.skip(reason=RAZON_GOLD_VERSIONADO)
    for item in items:
        if "gold_versionado" in item.keywords:
            item.add_marker(omitir)


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
        # Secreto de sesiones SOLO para pruebas (ADR-033): nunca va en .env.example ni como valor por defecto.
        secreto_sesion=SECRETO_SESION_PRUEBA,
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


@pytest.fixture(autouse=True)
def _sin_cache_de_flags_claude() -> None:
    """Cada prueba vuelve a comprobar los flags de aislamiento de ``claude`` (ADR-025)."""
    from fabrica_autopartes.llm import claude_code

    claude_code._CLI_VERIFICADAS.clear()
