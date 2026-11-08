"""Proveedor ``claude_code``: Claude a través de la CLI de Claude Code, con la sesión de la suscripción.

Permite ejecutar Resumen, FAQ, Q&A y la evaluación con Claude **sin clave de API**: cada llamada
invoca ``claude -p`` (modo no interactivo) con la cuenta con la que se inició sesión en Claude Code
(Pro/Max). Uso previsto: desarrollo y evaluación local por la persona titular de la cuenta. Para
un despliegue con usuarios finales se utiliza el proveedor ``anthropic`` con clave de API.

Aislamiento (ADR-025): el proceso se ejecuta en una carpeta temporal vacía, con un único turno y con
``FLAGS_AISLAMIENTO``: ninguna herramienta propia de Claude Code, ningún servidor MCP, sin CLAUDE.md,
skills, plugins, hooks ni archivos de configuración del usuario, sin solicitudes de permiso y sin guardar la
sesión. Así, un contenido descargado (fragmentos del corpus) que pida leer archivos locales o ejecutar
órdenes no tiene con qué hacerlo. Antes de la primera llamada se comprueba con ``claude --help`` (sin
consumir cupo) que la CLI admite todos esos flags; si falta alguno, no se ejecuta sin protección.
"""

from __future__ import annotations

import json
import re
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


# Flags verificados en la ayuda de Claude Code 2.1.319 (ADR-025). No se usa --bare: obliga a autenticarse
# con ANTHROPIC_API_KEY y dejaría de usar la sesión de la suscripción.
FLAGS_AISLAMIENTO: tuple[str, ...] = (
    "--tools",
    "",  # "" desactiva todas las herramientas integradas (Bash, Read, Write, Edit, WebFetch, WebSearch…)
    "--strict-mcp-config",  # sin --mcp-config: ningún servidor MCP
    "--safe-mode",  # sin CLAUDE.md, skills, plugins, hooks, MCP ni comandos o agentes propios
    "--restricted",  # ignora los archivos de configuración del usuario, del proyecto y locales
    "--permission-prompts",
    "none",  # lo que pediría permiso se deniega automáticamente
    "--no-session-persistence",  # la sesión no se guarda en disco
)
# Búsqueda web (ADR-019): conserva WebSearch y WebFetch, así que no lleva --tools "" ni --restricted
# (la ayuda indica que --restricted quita WebFetch salvo que --tools lo nombre; se omite por prudencia).
FLAGS_AISLAMIENTO_WEB: tuple[str, ...] = (
    "--strict-mcp-config",
    "--safe-mode",
    "--permission-prompts",
    "none",
    "--no-session-persistence",
)


def flags_requeridos(flags: tuple[str, ...]) -> tuple[str, ...]:
    """Nombres de flag (``--x``) de una lista de argumentos, sin sus valores."""
    return tuple(f for f in flags if f.startswith("--"))


FLAGS_REQUERIDOS: tuple[str, ...] = flags_requeridos(FLAGS_AISLAMIENTO)
_CLI_VERIFICADAS: set[tuple[str, tuple[str, ...]]] = set()


def verificar_flags_aislamiento(
    ruta: str, requeridos: tuple[str, ...] = FLAGS_REQUERIDOS, tiempo_espera_s: float = 30.0
) -> None:
    """Comprueba con ``claude --help`` (no consume cupo) que la CLI admite los flags ``requeridos``.

    El resultado se guarda por ejecutable y conjunto de flags. Si falta alguno o la ayuda no puede leerse,
    lanza ``ErrorProveedorLLM`` y la llamada no se ejecuta sin protección.
    """
    if (ruta, requeridos) in _CLI_VERIFICADAS:
        return
    try:
        ayuda = subprocess.run(
            [ruta, "--help"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=tiempo_espera_s,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ErrorProveedorLLM(
            f"No fue posible leer 'claude --help' para comprobar el aislamiento: {exc}. No se ejecuta."
        ) from exc
    texto = f"{ayuda.stdout}\n{ayuda.stderr}"
    faltan = [f for f in requeridos if not re.search(rf"(?<![\w-]){re.escape(f)}(?![\w-])", texto)]
    if faltan:
        raise ErrorProveedorLLM(
            f"La CLI de Claude Code no admite: {', '.join(faltan)}. Actualizar Claude Code "
            "('claude update'); no se ejecuta 'claude -p' sin aislamiento."
        )
    _CLI_VERIFICADAS.add((ruta, requeridos))


def leer_salida_json(proceso: subprocess.CompletedProcess[str]) -> dict[str, Any]:
    """Objeto JSON de ``--output-format json``.

    Cualquier otra salida es ``ErrorProveedorLLM`` (nunca ``AttributeError``): texto que no es JSON, o JSON
    válido que no es un objeto (lista, número, cadena o null).
    """
    detalle = (proceso.stderr or proceso.stdout or "").strip()[:300]
    try:
        datos = json.loads(proceso.stdout)
    except json.JSONDecodeError as exc:
        raise ErrorProveedorLLM(
            f"Respuesta no válida de Claude Code (código {proceso.returncode}): {detalle}. "
            "Verificar la sesión con 'claude' (iniciar sesión con la cuenta de la suscripción)."
        ) from exc
    if not isinstance(datos, dict):
        raise ErrorProveedorLLM(
            f"Respuesta inesperada de Claude Code (código {proceso.returncode}): se esperaba un objeto "
            f"JSON y se recibió {type(datos).__name__}: {detalle}. Verificar la versión de la CLI "
            "('claude --version')."
        )
    return datos


def comando_claude(ruta: str, modelo: str) -> list[str]:
    """Comando de ``claude -p`` con aislamiento; el contenido viaja por la entrada estándar."""
    return [
        ruta,
        "-p",
        _INSTRUCCION,
        "--output-format",
        "json",
        "--model",
        modelo,
        "--max-turns",
        "1",
        *FLAGS_AISLAMIENTO,
    ]


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
        verificar_flags_aislamiento(ruta)
        comando = comando_claude(ruta, self.modelo)
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
        datos = leer_salida_json(proceso)
        if datos.get("is_error") or proceso.returncode != 0:
            raise ErrorProveedorLLM(f"Claude Code devolvió un error: {str(datos.get('result', ''))[:300]}")
        texto = str(datos.get("result", ""))
        uso = datos.get("usage") or {}
        mensaje = AIMessage(
            content=texto,
            response_metadata={"modelo": self.modelo, "costo_usd": datos.get("total_cost_usd"), "uso": uso},
        )
        return ChatResult(generations=[ChatGeneration(message=mensaje)])
