"""Pruebas del servidor MCP: llamadas directas y sesión real por stdio (JSON-RPC)."""

from __future__ import annotations

import json
import os
import sys

import pytest
from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

from fabrica_autopartes.mcp_server import server


@pytest.fixture
def servidor(config_con_base, monkeypatch):  # type: ignore[no-untyped-def]
    monkeypatch.setattr(server, "_base", None)
    monkeypatch.setattr(server, "obtener_configuracion", lambda: config_con_base)
    return server.mcp


def _json(resultado) -> object:  # type: ignore[no-untyped-def]
    return json.loads(resultado.content[0].text)


async def test_herramientas_registradas_y_solo_lectura(servidor) -> None:  # type: ignore[no-untyped-def]
    herramientas = {t.name: t for t in await servidor.list_tools()}
    assert set(herramientas) == {
        "buscar_fragmentos",
        "obtener_fragmento",
        "estadisticas_base",
        "validar_corpus",
        "responder_pregunta",
        "consultar_pieza",
    }
    assert all(t.annotations and t.annotations.read_only_hint for t in herramientas.values())


async def test_buscar_y_obtener(servidor) -> None:  # type: ignore[no-untyped-def]
    r = await servidor.call_tool("buscar_fragmentos", {"consulta": "Fundación Fanalca", "k": 50})
    datos = r.structured_content["result"] if r.structured_content else _json(r)
    assert 1 <= len(datos) <= server.MAX_RESULTADOS
    assert datos[0]["seccion"] == "sostenibilidad"
    frag = await servidor.call_tool("obtener_fragmento", {"fragmento_id": datos[0]["id"]})
    assert "Fundación" in (frag.structured_content or _json(frag))["texto"]  # type: ignore[index]


async def test_validar_y_estadisticas(servidor) -> None:  # type: ignore[no-untyped-def]
    v = await servidor.call_tool("validar_corpus", {})
    assert (v.structured_content or _json(v))["aprobado"] is True  # type: ignore[index]


async def test_responder_deshabilitado_por_defecto(servidor) -> None:  # type: ignore[no-untyped-def]
    r = await servidor.call_tool("responder_pregunta", {"pregunta": "¿Dónde queda la sede?"})
    assert "deshabilitada" in json.dumps(r.structured_content or _json(r), ensure_ascii=False)


async def test_recursos_y_prompt(servidor) -> None:  # type: ignore[no-untyped-def]
    uris = {str(r.uri) for r in await servidor.list_resources()}
    assert {"fna://base/consolidada", "fna://base/fuentes"} <= uris
    prompts = {p.name for p in await servidor.list_prompts()}
    assert "plantilla_qa" in prompts


async def test_sesion_stdio_real() -> None:
    """Arranca el servidor como subproceso y dialoga por JSON-RPC sobre stdio."""
    parametros = StdioServerParameters(
        command=sys.executable,
        args=["-m", "fabrica_autopartes.mcp_server.server"],
        env={**os.environ},
    )
    async with stdio_client(parametros) as (lectura, escritura), ClientSession(lectura, escritura) as sesion:
        await sesion.initialize()
        nombres = {t.name for t in (await sesion.list_tools()).tools}
        assert "buscar_fragmentos" in nombres
        r = await sesion.call_tool("estadisticas_base", {})
        assert not r.is_error


async def test_consultar_pieza_separa_modelo_y_documentado(servidor) -> None:  # type: ignore[no-untyped-def]
    r = await servidor.call_tool(
        "consultar_pieza", {"pieza_id": "piston", "pregunta": "¿Qué función cumple?"}
    )
    datos = r.structured_content or _json(r)
    assert datos["intencion"] == "funcion" and "F = p·A" in datos["respuesta_modelo"]  # type: ignore[index]
    assert "demostración" in datos["advertencia"]  # type: ignore[index]


async def test_consultar_pieza_de_la_moto_con_ensamblaje_id(servidor) -> None:  # type: ignore[no-untyped-def]
    r = await servidor.call_tool(
        "consultar_pieza",
        {"pieza_id": "ciguenal", "pregunta": "¿Qué función cumple?", "ensamblaje_id": "moto_honda"},
    )
    datos = r.structured_content or _json(r)
    assert datos["pieza_id"] == "ciguenal" and "cigüeñal" in datos["respuesta_modelo"].lower()  # type: ignore[index]
    assert "No es un diseño industrial" in datos["advertencia"]  # type: ignore[index]
