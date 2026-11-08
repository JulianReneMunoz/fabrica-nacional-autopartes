"""Proveedor claude_code: invoca 'claude -p' con aislamiento (ADR-025); se prueba sin ejecutar la CLI real."""

from __future__ import annotations

import json
import subprocess

import pytest
from langchain_core.messages import HumanMessage, SystemMessage

from fabrica_autopartes.core.excepciones import ErrorProveedorLLM
from fabrica_autopartes.llm import claude_code
from fabrica_autopartes.llm.claude_code import ChatClaudeCode, modelo_claude_code
from tests.simulados import AYUDA_CLAUDE, es_ayuda, respuesta_ayuda

AISLAMIENTO = (
    "--tools",
    "",
    "--strict-mcp-config",
    "--safe-mode",
    "--restricted",
    "--permission-prompts",
    "none",
    "--no-session-persistence",
)


def test_modelo_por_alias_o_identificador() -> None:
    assert modelo_claude_code("haiku") == "haiku"
    assert modelo_claude_code("claude-sonnet-5-5") == "claude-sonnet-5-5"
    assert modelo_claude_code("llama3.2:3b") == "sonnet"
    assert modelo_claude_code(None) == "sonnet"


def _contiene_en_orden(comando: list[str], secuencia: tuple[str, ...]) -> bool:
    n = len(secuencia)
    return any(tuple(comando[i : i + n]) == secuencia for i in range(len(comando) - n + 1))


def test_invoca_cli_aislada_y_devuelve_resultado(monkeypatch, tmp_path) -> None:  # type: ignore[no-untyped-def]
    llamadas: list[dict] = []

    def falso_run(comando, **kwargs):  # type: ignore[no-untyped-def]
        if es_ayuda(comando):
            return respuesta_ayuda(comando)
        llamadas.append({"comando": comando, **kwargs})
        salida = json.dumps({"type": "result", "is_error": False, "result": '{"respuesta": "Yumbo"}'})
        return subprocess.CompletedProcess(comando, 0, stdout=salida, stderr="")

    monkeypatch.setattr(claude_code.shutil, "which", lambda _: "/usr/bin/claude")
    monkeypatch.setattr(claude_code.subprocess, "run", falso_run)
    r = ChatClaudeCode(modelo="haiku").invoke(
        [SystemMessage("TAREA: QA <contexto>x</contexto>"), HumanMessage("¿Sede?")]
    )
    assert r.content == '{"respuesta": "Yumbo"}'
    llamada = llamadas[0]
    comando = llamada["comando"]
    assert comando[:2] == ["/usr/bin/claude", "-p"]
    assert comando[comando.index("--model") : comando.index("--model") + 2] == ["--model", "haiku"]
    assert "--max-turns" in comando
    assert "TAREA: QA" in llamada["input"] and "¿Sede?" in llamada["input"]
    assert "TAREA: QA" not in " ".join(comando)  # el contenido viaja por la entrada estándar
    assert llamada["cwd"] != str(tmp_path)  # carpeta temporal propia, fuera del repositorio
    assert llamada["timeout"] == 300.0  # se conserva el límite de tiempo


def test_comando_incluye_todos_los_flags_de_aislamiento() -> None:
    comando = claude_code.comando_claude("claude", "sonnet")
    assert _contiene_en_orden(comando, ("--tools", ""))  # ninguna herramienta propia
    assert _contiene_en_orden(comando, ("--permission-prompts", "none"))
    for flag in ("--strict-mcp-config", "--safe-mode", "--restricted", "--no-session-persistence"):
        assert flag in comando
    assert "--mcp-config" not in comando  # MCP estricto y vacío
    assert "--bare" not in comando  # obligaría a usar ANTHROPIC_API_KEY en lugar de la suscripción
    assert "--dangerously-skip-permissions" not in comando and "--allowedTools" not in comando
    assert tuple(comando[-len(AISLAMIENTO) :]) == AISLAMIENTO


def test_si_la_cli_no_admite_un_flag_no_se_ejecuta(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    ejecutadas: list[list[str]] = []
    ayuda_vieja = AYUDA_CLAUDE.replace("--safe-mode", "--otro-flag")

    def falso_run(comando, **kwargs):  # type: ignore[no-untyped-def]
        if es_ayuda(comando):
            return respuesta_ayuda(comando, ayuda_vieja)
        ejecutadas.append(comando)
        raise AssertionError("no debe ejecutarse 'claude -p' sin aislamiento")

    monkeypatch.setattr(claude_code.shutil, "which", lambda _: "claude")
    monkeypatch.setattr(claude_code.subprocess, "run", falso_run)
    with pytest.raises(ErrorProveedorLLM, match=r"no admite: --safe-mode.*sin aislamiento"):
        ChatClaudeCode().invoke([HumanMessage("hola")])
    assert ejecutadas == []


def test_si_no_se_puede_leer_la_ayuda_no_se_ejecuta(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    def falso_run(comando, **kwargs):  # type: ignore[no-untyped-def]
        if es_ayuda(comando):
            raise subprocess.TimeoutExpired(comando, 30)
        raise AssertionError("no debe ejecutarse 'claude -p' sin aislamiento")

    monkeypatch.setattr(claude_code.shutil, "which", lambda _: "claude")
    monkeypatch.setattr(claude_code.subprocess, "run", falso_run)
    with pytest.raises(ErrorProveedorLLM, match="comprobar el aislamiento"):
        ChatClaudeCode().invoke([HumanMessage("hola")])


def test_la_ayuda_se_consulta_una_sola_vez_por_ejecutable(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    ayudas: list[list[str]] = []

    def falso_run(comando, **kwargs):  # type: ignore[no-untyped-def]
        if es_ayuda(comando):
            ayudas.append(comando)
            return respuesta_ayuda(comando)
        return subprocess.CompletedProcess(comando, 0, stdout=json.dumps({"result": "ok"}), stderr="")

    monkeypatch.setattr(claude_code.shutil, "which", lambda _: "claude")
    monkeypatch.setattr(claude_code.subprocess, "run", falso_run)
    for _ in range(3):
        ChatClaudeCode().invoke([HumanMessage("hola")])
    assert len(ayudas) == 1


def test_errores_claros(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(claude_code.shutil, "which", lambda _: None)
    with pytest.raises(ErrorProveedorLLM, match="No se encontró la CLI"):
        ChatClaudeCode().invoke([HumanMessage("hola")])
    monkeypatch.setattr(claude_code.shutil, "which", lambda _: "claude")

    def falso_run(comando, **kwargs):  # type: ignore[no-untyped-def]
        if es_ayuda(comando):
            return respuesta_ayuda(comando)
        return subprocess.CompletedProcess(
            comando, 1, stdout="", stderr="Invalid API key · Please run /login"
        )

    monkeypatch.setattr(claude_code.subprocess, "run", falso_run)
    with pytest.raises(ErrorProveedorLLM, match="Verificar la sesión"):
        ChatClaudeCode().invoke([HumanMessage("hola")])
