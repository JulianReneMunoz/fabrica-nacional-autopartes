"""Herramienta ``consultar_datos_estructurados_fanalca`` (R06): ``@tool`` de LangChain con esquema Pydantic.
Devuelve los datos exactos de los archivos, sin calcular; su contenido es JSON para el modelo y su artefacto,
el resultado Pydantic que usa el agente."""

from __future__ import annotations

import json
from typing import Any

import pytest
import yaml
from langchain_core.messages import ToolMessage
from langchain_core.tools import BaseTool
from pydantic import ValidationError

from fabrica_autopartes.core.config import RAIZ_PROYECTO
from fabrica_autopartes.services.agente_ignis_m2 import (
    ConsultaDatosFanalcaInput,
    ResultadoEstructuradoFanalca,
    consultar_datos_estructurados_fanalca,
)
from fabrica_autopartes.services.ficha_fanalca import ARCHIVO_FICHA, cargar_ficha

HERRAMIENTA = consultar_datos_estructurados_fanalca
TIPOS = ["ficha_moto", "estadisticas_corpus", "unidades_negocio", "ficha_empresa"]


def _llamar(tipo: str) -> ToolMessage:
    """Llamada de herramienta, como la haría un agente."""
    mensaje = HERRAMIENTA.invoke(
        {
            "type": "tool_call",
            "id": f"prueba-{tipo}",
            "name": HERRAMIENTA.name,
            "args": {"tipo_consulta": tipo},
        }
    )
    assert isinstance(mensaje, ToolMessage)
    return mensaje


def _leer(ruta_relativa: str) -> dict[str, Any]:
    ruta = RAIZ_PROYECTO / ruta_relativa
    texto = ruta.read_text(encoding="utf-8")
    datos: dict[str, Any] = yaml.safe_load(texto) if ruta.suffix == ".yaml" else json.loads(texto)
    return datos


def test_es_un_tool_de_langchain_con_el_esquema_pydantic() -> None:
    assert isinstance(HERRAMIENTA, BaseTool)
    assert HERRAMIENTA.name == "consultar_datos_estructurados_fanalca"
    assert HERRAMIENTA.args_schema is ConsultaDatosFanalcaInput
    assert HERRAMIENTA.response_format == "content_and_artifact"
    assert "sin calcular" in HERRAMIENTA.description


def test_el_esquema_para_el_modelo_enumera_los_cuatro_tipos() -> None:
    propiedades = HERRAMIENTA.tool_call_schema.model_json_schema()["properties"]
    assert propiedades["tipo_consulta"]["enum"] == TIPOS
    assert propiedades["filtro"]["default"] == "cb160f"


@pytest.mark.parametrize(
    ("tipo", "archivo"),
    [
        ("ficha_moto", "data/catalogo/motos_honda.yaml"),
        ("estadisticas_corpus", "data/gold/estadisticas.json"),
        ("unidades_negocio", "data/gold/metricas_etapas.json"),
    ],
)
def test_devuelve_los_datos_exactos_del_archivo(tipo: str, archivo: str) -> None:
    resultado = _llamar(tipo).artifact
    assert isinstance(resultado, ResultadoEstructuradoFanalca)
    assert resultado.fuente_archivo == archivo
    assert resultado.datos_exactos == _leer(archivo)
    assert resultado.verificado is True


def test_la_ficha_empresa_es_la_ficha_corporativa_validada() -> None:
    resultado = _llamar("ficha_empresa").artifact
    assert isinstance(resultado, ResultadoEstructuradoFanalca)
    assert resultado.fuente_archivo == ARCHIVO_FICHA
    assert resultado.datos_exactos == cargar_ficha().model_dump()


@pytest.mark.parametrize("tipo", TIPOS)
def test_el_contenido_es_el_json_del_artefacto(tipo: str) -> None:
    mensaje = _llamar(tipo)
    assert isinstance(mensaje.content, str)
    assert json.loads(mensaje.content) == mensaje.artifact.model_dump(mode="json")


def test_un_tipo_de_consulta_desconocido_se_rechaza() -> None:
    with pytest.raises(ValidationError):
        HERRAMIENTA.invoke({"tipo_consulta": "precios"})
