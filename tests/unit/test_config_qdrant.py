"""Configuración de la base vectorial de IGNIS en Qdrant (R07): recuperador opcional, URL del servidor y
carpeta local. Sin leer .env (``_env_file=None``); las variables se fijan con ``monkeypatch``."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from fabrica_autopartes.core.config import Configuracion

VARIABLES = ("FNA_IGNIS_RECUPERADOR", "FNA_QDRANT_URL", "FNA_RECUPERADOR", "FNA_AGENTE_RECUPERADOR")


@pytest.fixture(autouse=True)
def _sin_variables(monkeypatch: pytest.MonkeyPatch) -> None:
    for nombre in VARIABLES:
        monkeypatch.delenv(nombre, raising=False)


def _config(**valores: object) -> Configuracion:
    return Configuracion(_env_file=None, **valores)  # type: ignore[call-arg]


def test_por_defecto_ignis_usa_bm25_sin_servidor_qdrant() -> None:
    config = _config()
    assert config.ignis_recuperador == "bm25"
    assert config.qdrant_url is None


def test_los_valores_por_defecto_del_m1_no_cambian() -> None:
    config = _config()
    assert config.recuperador == "bm25"
    assert config.agente_recuperador == "hibrido"


def test_dir_qdrant_esta_bajo_dir_datos_y_fuera_del_gold(tmp_path: Path) -> None:
    config = _config(dir_datos=tmp_path / "data")
    assert config.dir_qdrant == tmp_path / "data" / "qdrant"
    assert config.dir_gold not in config.dir_qdrant.parents and config.dir_qdrant != config.dir_gold


def test_las_variables_de_entorno_se_leen(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FNA_IGNIS_RECUPERADOR", "hibrido_qdrant")
    monkeypatch.setenv("FNA_QDRANT_URL", "  http://127.0.0.1:6333  ")
    config = _config()
    assert config.ignis_recuperador == "hibrido_qdrant"
    assert config.qdrant_url == "http://127.0.0.1:6333"


@pytest.mark.parametrize("valor", ["", "   "])
def test_url_vacia_equivale_a_sin_servidor(monkeypatch: pytest.MonkeyPatch, valor: str) -> None:
    monkeypatch.setenv("FNA_QDRANT_URL", valor)
    assert _config().qdrant_url is None


@pytest.mark.parametrize("url", ["ftp://qdrant.local:6333", "qdrant.local:6333", "file:///tmp/qdrant"])
def test_url_que_no_es_http_se_rechaza(url: str) -> None:
    with pytest.raises(ValidationError, match="FNA_QDRANT_URL"):
        _config(qdrant_url=url)


def test_recuperador_de_ignis_desconocido_se_rechaza(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FNA_IGNIS_RECUPERADOR", "semantico")
    with pytest.raises(ValidationError):
        _config()
