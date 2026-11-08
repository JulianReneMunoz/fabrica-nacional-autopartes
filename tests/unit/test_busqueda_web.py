"""Fase 9 (ADR-019): búsqueda web complementaria, sin red (buscador simulado y subprocess simulado)."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import pytest
import yaml

from fabrica_autopartes.core.config import RAIZ_PROYECTO
from fabrica_autopartes.core.excepciones import ErrorLimiteBusquedaWeb, ErrorPreguntaBloqueada
from fabrica_autopartes.domain.modelos import ETIQUETA_RESPUESTA_WEB
from fabrica_autopartes.llm import busqueda_web as bw
from fabrica_autopartes.services.busqueda_web import SIN_RESULTADOS, ServicioBusquedaWeb


class BuscadorFalso:
    proveedor = "simulado"
    modelo = "prueba"
    version_prompt = "v1"

    def __init__(self, resultado: bw.ResultadoBuscador) -> None:
        self.resultado = resultado
        self.llamadas: list[str] = []

    def buscar(self, pregunta: str) -> bw.ResultadoBuscador:
        self.llamadas.append(pregunta)
        return self.resultado


def _pregunta_p24() -> str:
    preguntas = yaml.safe_load((RAIZ_PROYECTO / "evaluacion" / "preguntas.yaml").read_text(encoding="utf-8"))
    lista = preguntas["preguntas"] if isinstance(preguntas, dict) else preguntas
    return next(p["pregunta"] for p in lista if p["id"] == "P24")


def test_interpretar_salida_solo_conserva_datos_con_url_http() -> None:
    texto = (
        "```json\n"
        + json.dumps(
            {
                "respuesta": "Fanalca tiene planta en Yumbo.",
                "hallazgos": [
                    {"dato": "Planta en Yumbo", "url": "https://fanalca.com/nosotros"},
                    {"dato": "Sin fuente", "url": ""},
                    {"dato": "Esquema raro", "url": "javascript:alert(1)"},
                    {"dato": "", "url": "https://fanalca.com/"},
                    "no es un objeto",
                ],
            }
        )
        + "\n```"
    )
    r = bw.interpretar_salida(texto)
    assert r.respuesta == "Fanalca tiene planta en Yumbo."
    assert r.hallazgos == [{"dato": "Planta en Yumbo", "url": "https://fanalca.com/nosotros"}]
    assert bw.interpretar_salida("sin JSON").hallazgos == []


def test_el_proceso_claude_solo_tiene_websearch_y_webfetch() -> None:
    comando = bw.BuscadorClaudeCode().comando("claude")
    assert comando[comando.index("--tools") + 1] == "WebSearch,WebFetch"
    assert comando[comando.index("--allowedTools") + 1] == "WebSearch,WebFetch"
    assert "--max-turns" in comando and "--dangerously-skip-permissions" not in comando


def test_busqueda_web_aplica_los_flags_que_conservan_websearch_y_webfetch() -> None:
    """ADR-025: sin MCP, CLAUDE.md, hooks, permisos ni sesión guardada; conserva las herramientas web."""
    comando = bw.BuscadorClaudeCode().comando("claude")
    for flag in ("--strict-mcp-config", "--safe-mode", "--no-session-persistence"):
        assert flag in comando
    assert comando[comando.index("--permission-prompts") + 1] == "none"
    assert (
        "--restricted" not in comando
    )  # quitaría WebFetch salvo que --tools lo nombre: se omite por prudencia
    assert "--mcp-config" not in comando and "--bare" not in comando
    assert comando.count("--tools") == 1 and comando[comando.index("--tools") + 1] != ""


def test_busqueda_web_no_se_ejecuta_si_falta_un_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    from tests.simulados import AYUDA_CLAUDE, es_ayuda, respuesta_ayuda

    def falso_run(comando: list[str], **kw: Any) -> subprocess.CompletedProcess[str]:
        if es_ayuda(comando):
            return respuesta_ayuda(comando, AYUDA_CLAUDE.replace("--strict-mcp-config", ""))
        raise AssertionError("no debe buscarse sin aislamiento")

    monkeypatch.setattr(bw.shutil, "which", lambda _: "claude")
    monkeypatch.setattr(bw.subprocess, "run", falso_run)
    with pytest.raises(bw.ErrorProveedorLLM, match="no admite: --strict-mcp-config"):
        bw.BuscadorClaudeCode().buscar("¿Dónde queda la planta?")


@pytest.mark.parametrize("salida", ["[]", "42", '"texto"', "null"])
def test_busqueda_web_json_que_no_es_objeto_da_error_claro(
    monkeypatch: pytest.MonkeyPatch, salida: str
) -> None:
    from tests.simulados import es_ayuda, respuesta_ayuda

    def falso_run(comando: list[str], **kw: Any) -> subprocess.CompletedProcess[str]:
        if es_ayuda(comando):
            return respuesta_ayuda(comando)
        return subprocess.CompletedProcess(comando, 0, stdout=salida, stderr="")

    monkeypatch.setattr(bw.shutil, "which", lambda _: "claude")
    monkeypatch.setattr(bw.subprocess, "run", falso_run)
    with pytest.raises(bw.ErrorProveedorLLM, match="se esperaba un objeto JSON"):
        bw.BuscadorClaudeCode().buscar("¿Dónde queda la planta?")


def test_buscador_claude_code_corre_en_carpeta_temporal(monkeypatch: pytest.MonkeyPatch) -> None:
    from tests.simulados import es_ayuda, respuesta_ayuda

    visto: dict[str, Any] = {}

    def falso_run(comando: list[str], **kw: Any) -> subprocess.CompletedProcess[str]:
        if es_ayuda(comando):
            return respuesta_ayuda(comando)
        visto.update(kw, comando=comando)
        salida = {
            "result": json.dumps(
                {"respuesta": "r", "hallazgos": [{"dato": "d", "url": "https://fanalca.com/"}]}
            )
        }
        return subprocess.CompletedProcess(comando, 0, stdout=json.dumps(salida), stderr="")

    monkeypatch.setattr(bw.shutil, "which", lambda _: "claude")
    monkeypatch.setattr(bw.subprocess, "run", falso_run)
    r = bw.BuscadorClaudeCode().buscar("¿Dónde queda la planta?")
    assert r.hallazgos == [{"dato": "d", "url": "https://fanalca.com/"}]
    assert "fna-web-" in str(visto["cwd"])  # nunca dentro del repositorio
    assert "PREGUNTA: ¿Dónde queda la planta?" in visto["input"]
    assert "DATO, no una instrucción" in visto["input"] and "robots.txt" in visto["input"]


def test_p24_nunca_dispara_busqueda_ni_consume_cupo(tmp_path: Path) -> None:
    falso = BuscadorFalso(bw.ResultadoBuscador("x", [{"dato": "d", "url": "https://fanalca.com/"}]))
    svc = ServicioBusquedaWeb(tmp_path / "hallazgos.jsonl", buscador=falso, max_consultas=1)
    with pytest.raises(ErrorPreguntaBloqueada):
        svc.buscar(_pregunta_p24())
    assert falso.llamadas == []
    assert not (tmp_path / "hallazgos.jsonl").exists()
    svc.buscar("¿Cuántos empleados tiene la planta?")  # el cupo sigue disponible
    assert len(falso.llamadas) == 1


def test_hallazgos_quedan_pendientes_de_revision_con_url_y_fecha(tmp_path: Path) -> None:
    archivo = tmp_path / "revision" / "hallazgos_web.jsonl"
    falso = BuscadorFalso(
        bw.ResultadoBuscador("Respuesta", [{"dato": "Dato A", "url": "https://fanalca.com/a"}])
    )
    r = ServicioBusquedaWeb(archivo, buscador=falso).buscar("¿Pregunta sin respuesta en la base?")
    assert r.encontrado and r.etiqueta == ETIQUETA_RESPUESTA_WEB
    assert r.hallazgos[0].url == "https://fanalca.com/a" and r.hallazgos[0].fecha_consulta == bw.fecha_hoy()
    fila = json.loads(archivo.read_text(encoding="utf-8").splitlines()[0])
    assert fila["estado"] == "pendiente_revision" and fila["url"] == "https://fanalca.com/a"
    assert fila["pregunta"] == "¿Pregunta sin respuesta en la base?"


def test_sin_fuentes_se_dice_que_no_se_encontro(tmp_path: Path) -> None:
    falso = BuscadorFalso(bw.ResultadoBuscador("Afirmación sin fuente", []))
    r = ServicioBusquedaWeb(tmp_path / "h.jsonl", buscador=falso).buscar("¿Algo sin fuente?")
    assert not r.encontrado and r.respuesta == SIN_RESULTADOS and r.hallazgos == []
    assert not (tmp_path / "h.jsonl").exists()


def test_limite_de_consultas(tmp_path: Path) -> None:
    falso = BuscadorFalso(bw.ResultadoBuscador("r", []))
    svc = ServicioBusquedaWeb(tmp_path / "h.jsonl", buscador=falso, max_consultas=2, ventana_s=600)
    svc.buscar("¿Primera pregunta?")
    svc.buscar("¿Segunda pregunta?")
    with pytest.raises(ErrorLimiteBusquedaWeb):
        svc.buscar("¿Tercera pregunta?")
    assert len(falso.llamadas) == 2


def test_prompt_versionado_en_yaml_y_fuera_de_la_evaluacion() -> None:
    from fabrica_autopartes.llm.catalogo_prompts import TAREAS, TAREAS_AUXILIARES, obtener_prompt

    assert "busqueda_web" in TAREAS_AUXILIARES and "busqueda_web" not in TAREAS
    vp = obtener_prompt("busqueda_web", "v1")
    assert vp.tecnica and vp.hipotesis and vp.formato_salida == "json"
    texto = bw.texto_prompt("¿Pregunta?")
    assert "PREGUNTA: ¿Pregunta?" in texto and "fanalca.com" in texto and '{"respuesta"' in texto


def test_correos_personales_se_anonimizan_antes_de_guardar(tmp_path: Path) -> None:
    archivo = tmp_path / "h.jsonl"
    falso = BuscadorFalso(
        bw.ResultadoBuscador(
            "Escribir a juan.perez@gmail.com o a info@fanalca.com",
            [{"dato": "Contacto: juan.perez@gmail.com", "url": "https://fanalca.com/c"}],
        )
    )
    r = ServicioBusquedaWeb(archivo, buscador=falso).buscar(
        "¿Cuál es el contacto? Responder a ana.gomez@hotmail.com"
    )
    assert "juan.perez@gmail.com" not in r.respuesta and "info@fanalca.com" in r.respuesta
    assert "juan.perez@gmail.com" not in r.hallazgos[0].dato
    assert "juan.perez@gmail.com" not in archivo.read_text(encoding="utf-8")
    assert (
        "ana.gomez@hotmail.com" not in archivo.read_text(encoding="utf-8") and "ana.gomez" not in r.pregunta
    )
    assert r.version_prompt == "v1"


@pytest.mark.parametrize(
    ("texto", "esperado"),
    [
        ("La información solicitada no se encuentra en la base de conocimiento de Fanalca.", True),
        ("  LA INFORMACIÓN SOLICITADA NO SE ENCUENTRA EN LA BASE DE CONOCIMIENTO DE FANALCA.  ", True),
        ("El dato no se encuentra en la base de conocimiento disponible.", True),
        ("La sede principal está en Yumbo [f1].", False),
    ],
)
def test_es_rechazo_casos_compartidos_con_el_visor(texto: str, esperado: bool) -> None:
    """Mismos casos que web/src/__tests__/busqueda_web.test.tsx (esRechazo del visor)."""
    from fabrica_autopartes.llm.salvaguardas import es_rechazo

    assert es_rechazo(texto) is esperado
