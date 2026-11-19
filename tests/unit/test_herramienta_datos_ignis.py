"""Herramienta ``consultar_datos_estructurados_fanalca`` (R06): ``@tool`` de LangChain con esquema Pydantic.
Devuelve los datos exactos de los archivos, sin calcular; su contenido es JSON para el modelo y su artefacto,
el resultado Pydantic que usa el agente."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
import yaml
from langchain_core.messages import ToolMessage
from langchain_core.tools import BaseTool
from pydantic import ValidationError

from fabrica_autopartes.core.config import RAIZ_PROYECTO
from fabrica_autopartes.services import agente_ignis_m2
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


@pytest.fixture
def raiz_vacia(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Repositorio temporal sin los archivos de datos (observación 3 del hook del PR anterior)."""
    monkeypatch.setattr(agente_ignis_m2, "RAIZ_REPO", tmp_path)
    return tmp_path


@pytest.mark.parametrize("tipo", ["ficha_moto", "estadisticas_corpus", "unidades_negocio"])
def test_sin_el_archivo_no_se_marca_verificado(raiz_vacia: Path, tipo: str) -> None:
    resultado = _llamar(tipo).artifact
    assert resultado.datos_exactos == {}
    assert resultado.verificado is False


@pytest.mark.parametrize(
    ("ruta", "contenido", "tipo"),
    [
        ("data/catalogo/motos_honda.yaml", "", "ficha_moto"),
        ("data/catalogo/motos_honda.yaml", "# solo un comentario\n", "ficha_moto"),
        ("data/gold/estadisticas.json", "null", "estadisticas_corpus"),
    ],
)
def test_archivo_vacio_devuelve_datos_vacios_sin_verificar(
    raiz_vacia: Path, ruta: str, contenido: str, tipo: str
) -> None:
    archivo = raiz_vacia / ruta
    archivo.parent.mkdir(parents=True)
    archivo.write_text(contenido, encoding="utf-8")
    resultado = _llamar(tipo).artifact
    assert resultado.datos_exactos == {}
    assert resultado.verificado is False


def test_resumen_acotado_no_trae_valores() -> None:
    resultado = _llamar("ficha_moto").artifact
    resumen = agente_ignis_m2.resumir_salida(resultado)
    assert resumen["claves"] == list(resultado.datos_exactos)[: agente_ignis_m2.MAX_CLAVES_RESUMEN]
    assert resumen["total_claves"] == len(resultado.datos_exactos)
    assert len(json.dumps(resumen, ensure_ascii=False).encode("utf-8")) <= agente_ignis_m2.MAX_BYTES_RESUMEN


def test_resumen_de_datos_grandes_no_pasa_de_1_kb() -> None:
    datos = {f"clave_{'x' * 200}_{i}": list(range(i)) for i in range(50)}
    resumen = agente_ignis_m2.resumir_salida(
        ResultadoEstructuradoFanalca(fuente_archivo="data/x.json", datos_exactos=datos)
    )
    assert resumen["total_claves"] == 50
    assert len(resumen["claves"]) <= agente_ignis_m2.MAX_CLAVES_RESUMEN
    assert all(len(c) <= agente_ignis_m2.MAX_TEXTO_RESUMEN for c in resumen["claves"])
    assert len(json.dumps(resumen, ensure_ascii=False).encode("utf-8")) <= agente_ignis_m2.MAX_BYTES_RESUMEN
