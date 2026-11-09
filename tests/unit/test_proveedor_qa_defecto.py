"""Proveedor del Q&A por defecto (ADR-027): extractivo, sin red, sin instalación y sin costo."""

from __future__ import annotations

import pytest

from fabrica_autopartes.core.config import Configuracion
from fabrica_autopartes.llm.extractivo import ModeloExtractivo
from fabrica_autopartes.llm.proveedores import crear_modelo
from fabrica_autopartes.repositories.auditoria import RepositorioAuditoria
from fabrica_autopartes.services.asistente import ServicioAsistente


def test_valor_por_defecto_es_extractivo(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("FNA_PROVEEDOR_LLM", raising=False)
    config = Configuracion(_env_file=None)  # type: ignore[call-arg]
    assert config.proveedor_llm == "extractivo"
    assert isinstance(crear_modelo(config), ModeloExtractivo)


def test_fna_proveedor_llm_sobrescribe_el_valor_por_defecto(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FNA_PROVEEDOR_LLM", "claude_code")
    assert Configuracion(_env_file=None).proveedor_llm == "claude_code"  # type: ignore[call-arg]


def test_qa_con_el_valor_por_defecto_responde_sin_red(
    config_con_base: Configuracion, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Clon nuevo sin .env: el Q&A responde con el proveedor por defecto, sin modelo inyectado ni red."""
    monkeypatch.delenv("FNA_PROVEEDOR_LLM", raising=False)
    config = Configuracion(
        _env_file=None,  # type: ignore[call-arg]
        dir_datos=config_con_base.dir_datos,
        url_base_datos=config_con_base.url_base_datos,
    )
    assert config.proveedor_llm == "extractivo"
    servicio = ServicioAsistente(
        config, RepositorioAuditoria(config.url_base_datos)
    )  # sin modelo_llm inyectado
    r = servicio.responder("¿Cuál es el teléfono de contacto?", canal="prueba")
    assert r.proveedor == "extractivo" and r.modelo == "lexico-bm25"
    assert r.respuesta and r.fuentes
