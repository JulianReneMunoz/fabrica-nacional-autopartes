"""Proveedor ``claude_code``: Claude a través de la CLI de Claude Code, con la sesión de la suscripción.

Permite ejecutar Resumen, FAQ, Q&A y la evaluación con Claude **sin clave de API**: cada llamada
invoca ``claude -p`` (modo no interactivo) con la cuenta con la que se inició sesión en Claude Code
(Pro/Max). Uso previsto: desarrollo y evaluación local por la persona titular de la cuenta. Para
un despliegue con usuarios finales se utiliza el proveedor ``anthropic`` con clave de API.

Aislamiento: el proceso se ejecuta en una carpeta temporal vacía (no lee el repositorio ni su
CLAUDE.md), con un único turno y sin herramientas aprobadas, de modo que solo responde con el
contexto que la cadena LangChain le entrega.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, SystemMessage
from langchain_core.outputs import ChatGeneration, ChatResult

from fabrica_autopartes.core.excepciones import ErrorProveedorLLM

ALIAS = ("sonnet", "opus", "haiku", "fable")
_INSTRUCCION = (
    "Responder únicamente siguiendo las INSTRUCCIONES DEL SISTEMA y el MENSAJE recibidos por la "
    "entrada estándar. No usar herramientas ni leer archivos."
)


def modelo_claude_code(modelo: str | None) -> str:
    """Acepta alias (sonnet, opus, haiku) o identificadores completos (claude-...); si no, usa sonnet."""
    if modelo and (modelo in ALIAS or modelo.startswith("claude-")):
        return modelo
    return "sonnet"


class ChatClaudeCode(BaseChatModel):
    modelo: str = "sonnet"
    tiempo_espera_s: float = 300.0
    ejecutable: str = "claude"

    @property
    def _llm_type(self) -> str:
        return "claude-code-cli"

    def _texto_entrada(self, messages: list[BaseMessage]) -> str:
        sistema = "\n\n".join(str(m.content) for m in messages if isinstance(m, SystemMessage))
        resto = "\n\n".join(str(m.content) for m in messages if not isinstance(m, SystemMessage))
        return f"### INSTRUCCIONES DEL SISTEMA\n{sistema}\n\n### MENSAJE\n{resto}\n"

    def _generate(
        self, messages: list[BaseMessage], stop: Any = None, run_manager: Any = None, **kwargs: Any
    ) -> ChatResult:
        ruta = shutil.which(self.ejecutable)
        if ruta is None:
            raise ErrorProveedorLLM(
                "No se encontró la CLI de Claude Code ('claude'). Instalarla e iniciar sesión con 'claude'."
            )
        comando = [
            ruta,
            "-p",
            _INSTRUCCION,
            "--output-format",
            "json",
            "--model",
            self.modelo,
            "--max-turns",
            "1",
        ]
        with tempfile.TemporaryDirectory(prefix="fna-claude-") as carpeta:
            try:
                proceso = subprocess.run(
                    comando,
                    input=self._texto_entrada(messages),
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    cwd=carpeta,
                    timeout=self.tiempo_espera_s,
                    check=False,
                )
            except subprocess.TimeoutExpired as exc:
                raise ErrorProveedorLLM(f"Claude Code no respondió en {self.tiempo_espera_s:.0f} s") from exc
        try:
            datos = json.loads(proceso.stdout)
        except json.JSONDecodeError as exc:
            detalle = (proceso.stderr or proceso.stdout).strip()[:300]
            raise ErrorProveedorLLM(
                f"Respuesta no válida de Claude Code (código {proceso.returncode}): {detalle}. "
                "Verificar la sesión con 'claude' (iniciar sesión con la cuenta de la suscripción)."
            ) from exc
        if datos.get("is_error") or proceso.returncode != 0:
            raise ErrorProveedorLLM(f"Claude Code devolvió un error: {str(datos.get('result', ''))[:300]}")
        texto = str(datos.get("result", ""))
        uso = datos.get("usage") or {}
        mensaje = AIMessage(
            content=texto,
            response_metadata={"modelo": self.modelo, "costo_usd": datos.get("total_cost_usd"), "uso": uso},
        )
        return ChatResult(generations=[ChatGeneration(message=mensaje)])
