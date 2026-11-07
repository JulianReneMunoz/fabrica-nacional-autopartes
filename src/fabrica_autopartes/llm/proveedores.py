"""Fábrica de modelos de chat (LangChain) según el proveedor configurado.

Proveedores soportados:

* ``ollama``: modelos abiertos locales (p. ej. ``llama3.2:3b``, ``mistral``). Opción por
  defecto del proyecto: sin costo por token y los datos no salen del equipo.
* ``openai``: API privada (requiere ``FNA_OPENAI_API_KEY`` con facturación activa).
* ``anthropic``: API de Anthropic (requiere ``FNA_ANTHROPIC_API_KEY`` de la Consola;
  una suscripción Claude Pro/Max **no** incluye créditos de API).
* ``claude_code``: Claude mediante la CLI de Claude Code (``claude -p``) con la sesión de la
  suscripción, sin clave de API; para desarrollo y evaluación local (ver ``llm/claude_code.py``).
* ``extractivo``: línea base determinista sin LLM, para pruebas y CI.
"""

from __future__ import annotations

from langchain_core.language_models.chat_models import BaseChatModel

from fabrica_autopartes.core.config import Configuracion
from fabrica_autopartes.core.excepciones import ErrorProveedorLLM
from fabrica_autopartes.llm.extractivo import ModeloExtractivo


def _modelo_sin_temperatura(modelo: str) -> bool:
    """Algunos modelos de razonamiento solo aceptan la temperatura por defecto."""
    return modelo.startswith(("gpt-5", "o1", "o3", "o4"))


def aplica_temperatura(proveedor: str, modelo: str) -> bool:
    """Indica si ``config.temperatura`` llega realmente al modelo.

    ``claude_code`` usa la CLI ``claude -p``, sin opción de temperatura, y ``extractivo`` no es un LLM;
    algunos modelos de razonamiento de OpenAI solo aceptan la temperatura por defecto.
    """
    if proveedor in ("ollama", "anthropic"):
        return True
    if proveedor == "openai":
        return not _modelo_sin_temperatura(modelo)
    return False


def crear_modelo(
    config: Configuracion,
    proveedor: str | None = None,
    modelo: str | None = None,
    salida_json: bool = False,
) -> BaseChatModel:
    proveedor = proveedor or config.proveedor_llm
    modelo = modelo or config.modelo_llm

    if proveedor == "extractivo":
        return ModeloExtractivo()

    if proveedor == "ollama":
        from langchain_ollama import ChatOllama

        return ChatOllama(
            model=modelo,
            base_url=config.ollama_url,
            temperature=config.temperatura,
            num_ctx=config.ollama_num_ctx,
            format="json" if salida_json else None,
        )

    if proveedor == "openai":
        if config.openai_api_key is None:
            raise ErrorProveedorLLM("Falta FNA_OPENAI_API_KEY en el entorno o en .env")
        from langchain_openai import ChatOpenAI

        kwargs: dict = {"model": modelo, "api_key": config.openai_api_key}
        if not _modelo_sin_temperatura(modelo):
            kwargs["temperature"] = config.temperatura
        if salida_json:
            kwargs["model_kwargs"] = {"response_format": {"type": "json_object"}}
        return ChatOpenAI(**kwargs)

    if proveedor == "claude_code":
        from fabrica_autopartes.llm.claude_code import ChatClaudeCode, modelo_claude_code

        return ChatClaudeCode(modelo=modelo_claude_code(modelo))

    if proveedor == "anthropic":
        if config.anthropic_api_key is None:
            raise ErrorProveedorLLM("Falta FNA_ANTHROPIC_API_KEY en el entorno o en .env")
        try:
            from langchain_anthropic import ChatAnthropic
        except ImportError as exc:
            raise ErrorProveedorLLM("Instalar el extra: uv sync --extra anthropic") from exc
        # Diccionario de argumentos: los alias de Pydantic (model, max_tokens) no son visibles para mypy.
        argumentos: dict = {
            "model": modelo,
            "api_key": config.anthropic_api_key,
            "temperature": config.temperatura,
            "max_tokens": 1024,
        }
        return ChatAnthropic(**argumentos)

    raise ErrorProveedorLLM(f"Proveedor no soportado: {proveedor}")
