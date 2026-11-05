"""Proveedor claude_code: invoca 'claude -p' con aislamiento; se prueba sin ejecutar la CLI real."""

from __future__ import annotations

import json
import subprocess

import pytest
from langchain_core.messages import HumanMessage, SystemMessage

from fabrica_autopartes.core.excepciones import ErrorProveedorLLM
from fabrica_autopartes.llm import claude_code
from fabrica_autopartes.llm.claude_code import ChatClaudeCode, modelo_claude_code


def test_modelo_por_alias_o_identificador() -> None:
    assert modelo_claude_code("haiku") == "haiku"
    assert modelo_claude_code("claude-sonnet-5-5") == "claude-sonnet-5-5"
    assert modelo_claude_code("llama3.2:3b") == "sonnet"
    assert modelo_claude_code(None) == "sonnet"


def test_invoca_cli_aislada_y_devuelve_resultado(monkeypatch, tmp_path) -> None:  # type: ignore[no-untyped-def]
    llamadas: list[dict] = []

    def falso_run(comando, **kwargs):  # type: ignore[no-untyped-def]
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
    assert llamada["comando"][:2] == ["/usr/bin/claude", "-p"]
    assert llamada["comando"][
        llamada["comando"].index("--model") : llamada["comando"].index("--model") + 2
    ] == ["--model", "haiku"]
    assert "--max-turns" in llamada["comando"]
    assert "TAREA: QA" in llamada["input"] and "¿Sede?" in llamada["input"]
    assert llamada["cwd"] != str(tmp_path)  # carpeta temporal propia, fuera del repositorio


def test_errores_claros(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(claude_code.shutil, "which", lambda _: None)
    with pytest.raises(ErrorProveedorLLM, match="No se encontró la CLI"):
        ChatClaudeCode().invoke([HumanMessage("hola")])
    monkeypatch.setattr(claude_code.shutil, "which", lambda _: "claude")
    monkeypatch.setattr(
        claude_code.subprocess,
        "run",
        lambda c, **k: subprocess.CompletedProcess(
            c, 1, stdout="", stderr="Invalid API key · Please run /login"
        ),
    )
    with pytest.raises(ErrorProveedorLLM, match="Verificar la sesión"):
        ChatClaudeCode().invoke([HumanMessage("hola")])
