"""Modelo de chat simulado para probar el agente sin red ni clave (ADR-024).

``GenericFakeChatModel`` no implementa ``bind_tools``, que ``create_agent`` exige. Este modelo sí: sigue
un guion de respuestas (mensajes o funciones que los construyen) y registra los mensajes que recibe en cada
llamada, para comprobar la memoria y el recorte del historial.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from pydantic import Field

Paso = AIMessage | Callable[[list[BaseMessage]], AIMessage] | BaseException


class ModeloSimulado(BaseChatModel):
    guion: list[Any] = Field(default_factory=list)
    recibidos: list[list[BaseMessage]] = Field(default_factory=list)
    repetir_ultimo: bool = False

    @property
    def _llm_type(self) -> str:
        return "simulado"

    def bind_tools(self, tools: Sequence[Any], **kwargs: Any) -> ModeloSimulado:  # type: ignore[override]
        return self

    def _generate(
        self, messages: list[BaseMessage], stop: Any = None, run_manager: Any = None, **kwargs: Any
    ) -> ChatResult:
        self.recibidos.append(list(messages))
        if not self.guion:
            raise AssertionError("El guion del modelo simulado se agotó")
        paso = self.guion[0] if (self.repetir_ultimo and len(self.guion) == 1) else self.guion.pop(0)
        if isinstance(paso, BaseException):
            raise paso
        mensaje = paso(list(messages)) if callable(paso) else paso
        return ChatResult(generations=[ChatGeneration(message=mensaje)])


def llamada(consulta: str, id_: str, k: int = 3, **extra: Any) -> AIMessage:
    """Mensaje del modelo que pide ``buscar_fragmentos``."""
    return AIMessage(
        "",
        tool_calls=[
            {"name": "buscar_fragmentos", "args": {"consulta": consulta, "k": k, **extra}, "id": id_}
        ],
    )


def responder_citando_primera_url(prefijo: str = "Respuesta") -> Callable[[list[BaseMessage]], AIMessage]:
    """Respuesta final que cita la URL del primer fragmento devuelto por la herramienta en el turno."""

    def paso(mensajes: list[BaseMessage]) -> AIMessage:
        from langchain_core.messages import ToolMessage

        ultimo = next(m for m in reversed(mensajes) if isinstance(m, ToolMessage))
        url = ultimo.content.split('url="', 1)[1].split('"', 1)[0] if 'url="' in str(ultimo.content) else ""
        return AIMessage(f"{prefijo} ({url}).")

    return paso


# ------------------------------------------------------------- CLI de Claude Code (ADR-025)
AYUDA_CLAUDE = """Usage: claude [options] [command] [prompt]

Options:
  --tools <tools...>                    Specify the list of available tools
  --allowedTools, --allowed-tools <tools...>
  --strict-mcp-config                   Only use MCP servers from --mcp-config
  --safe-mode                           Start with all customizations disabled
  --restricted                          Restricted mode
  --permission-prompts <target>         Who answers permission prompts
  --no-session-persistence              Disable session persistence
"""


def es_ayuda(comando: Sequence[str]) -> bool:
    """La llamada es ``claude --help`` (comprobación previa del aislamiento, sin consumir cupo)."""
    return list(comando[1:]) == ["--help"]


def respuesta_ayuda(comando: Sequence[str], texto: str = AYUDA_CLAUDE) -> Any:
    import subprocess

    return subprocess.CompletedProcess(list(comando), 0, stdout=texto, stderr="")
