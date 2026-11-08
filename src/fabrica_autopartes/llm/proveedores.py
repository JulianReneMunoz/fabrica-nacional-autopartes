"""Fábrica de modelos de chat (LangChain) según el proveedor configurado.

Proveedores por defecto:

* Q&A, FAQ y resumen (``crear_modelo``): el de ``FNA_PROVEEDOR_LLM``.
* Agente con memoria (``crear_modelo_agente``): ``anthropic`` con Claude Haiku 5.5
  (``claude-haiku-5-5``, ADR-026); ``ollama`` es opcional. Sin respaldo automático entre proveedores.

Proveedores soportados:

* ``ollama``: modelos abiertos locales (p. ej. ``llama3.2:3b``, ``qwen3:8b``), opcional: sin costo por
  token y sin que los datos salgan del equipo; no viene instalado.
* ``openai``: API privada (requiere ``FNA_OPENAI_API_KEY`` con facturación activa).
* ``anthropic``: API de Anthropic con ``FNA_ANTHROPIC_API_KEY`` (nunca ``ANTHROPIC_API_KEY``) de la
  Claude Console. Créditos de API: Claude Pro no los incluye; los planes Max y Ultra incluyen créditos
  mensuales al vincular una organización de la Console (``docs/arquitectura/modelos.md``).
* ``claude_code``: Claude mediante la CLI de Claude Code (``claude -p``) con la sesión de la
  suscripción, sin clave de API; para desarrollo y evaluación local (ver ``llm/claude_code.py``).
  No se usa en el agente.
* ``extractivo``: línea base determinista sin LLM, para pruebas y CI.
"""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse

import requests
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
            # langchain-anthropic es dependencia principal: si falta, el entorno no coincide con uv.lock.
            raise ErrorProveedorLLM(
                "No se pudo importar langchain-anthropic (dependencia del proyecto): el entorno no está "
                "sincronizado con uv.lock. Ejecutar 'make instalar-semantica-gpu' o 'uv sync --locked'."
            ) from exc
        # Diccionario de argumentos: los alias de Pydantic (model, max_tokens) no son visibles para mypy.
        argumentos: dict = {
            "model": modelo,
            "api_key": config.anthropic_api_key,
            "temperature": config.temperatura,
            "max_tokens": 1024,
        }
        return ChatAnthropic(**argumentos)

    raise ErrorProveedorLLM(f"Proveedor no soportado: {proveedor}")


# --------------------------------------------------------------------- agente (ADR-024)
HOSTS_LOCALES = frozenset({"localhost", "127.0.0.1", "::1"})
INSTRUCCION_OLLAMA = (
    "Instalar Ollama (https://ollama.com/download), ejecutar 'ollama pull {modelo}' y dejar el servicio "
    "activo ('ollama serve'); o elegir FNA_PROVEEDOR_AGENTE=anthropic."
)
INSTRUCCION_ANTHROPIC = (
    "Los planes Max y Ultra incluyen créditos mensuales de API: vincular una organización de la Claude "
    "Console en claude.ai > Settings > Billing > API credits, crear allí una clave y guardarla en .env como "
    "FNA_ANTHROPIC_API_KEY (nunca ANTHROPIC_API_KEY, para no afectar a Claude Code); comprobar con "
    "'make verificar-agente' (pasos en CONTRIBUTING.md)."
)


@dataclass(frozen=True)
class EstadoProveedor:
    """Resultado de verificar el proveedor del agente (no contiene la clave)."""

    proveedor: str
    modelo: str
    disponible: bool
    mensaje: str


def _validar_url_ollama(url: str) -> str:
    """El agente solo habla con un Ollama local: evita enviar el corpus a un servidor remoto."""
    partes = urlparse(url)
    if partes.scheme not in ("http", "https") or (partes.hostname or "") not in HOSTS_LOCALES:
        raise ErrorProveedorLLM(
            f"OLLAMA_BASE_URL debe apuntar a un host local (localhost, 127.0.0.1 o ::1); se recibió '{url}'."
        )
    return url.rstrip("/")


def modelo_del_agente(config: Configuracion) -> str:
    return config.modelo_ollama if config.proveedor_agente == "ollama" else config.modelo_anthropic


def verificar_proveedor_agente(config: Configuracion, consultar: bool = False) -> EstadoProveedor:
    """Comprueba la configuración del proveedor del agente; con ``consultar=True`` contacta el servicio.

    No hay respaldo automático: si el proveedor configurado no está disponible, se informa con la instrucción.
    """
    proveedor, modelo = config.proveedor_agente, modelo_del_agente(config)
    try:
        if proveedor == "ollama":
            url = _validar_url_ollama(config.ollama_url)
            if consultar:
                try:
                    r = requests.get(f"{url}/api/tags", timeout=2)
                    r.raise_for_status()
                except requests.RequestException as exc:
                    raise ErrorProveedorLLM(
                        f"Ollama no responde en {url}. " + INSTRUCCION_OLLAMA.format(modelo=modelo)
                    ) from exc
                nombres = {m.get("name", "") for m in r.json().get("models", [])}
                if modelo not in nombres and f"{modelo}:latest" not in nombres:
                    raise ErrorProveedorLLM(
                        f"Ollama responde, pero el modelo '{modelo}' no está descargado: "
                        f"ejecutar 'ollama pull {modelo}'."
                    )
            return EstadoProveedor(proveedor, modelo, True, f"Ollama en {url} con el modelo {modelo}")
        if config.anthropic_api_key is None or not config.anthropic_api_key.get_secret_value().strip():
            raise ErrorProveedorLLM("Falta FNA_ANTHROPIC_API_KEY. " + INSTRUCCION_ANTHROPIC)
        if consultar:
            import anthropic

            cliente = anthropic.Anthropic(api_key=config.anthropic_api_key.get_secret_value(), timeout=10)
            try:
                cliente.models.retrieve(modelo)  # no consume tokens
            except anthropic.APIError as exc:
                raise ErrorProveedorLLM(
                    f"La API de Anthropic rechazó la consulta del modelo '{modelo}': {exc}"
                ) from exc
        return EstadoProveedor(proveedor, modelo, True, f"Anthropic con el modelo {modelo}")
    except ErrorProveedorLLM as exc:
        return EstadoProveedor(proveedor, modelo, False, str(exc))


def crear_modelo_agente(config: Configuracion) -> BaseChatModel:
    """Modelo de chat del agente (temperatura 0, salida acotada).

    Lanza ``ErrorProveedorLLM`` (503) si falta la configuración; la disponibilidad se comprueba al
    invocar o con ``verificar_proveedor_agente(consultar=True)``.
    """
    estado = verificar_proveedor_agente(config)
    if not estado.disponible:
        raise ErrorProveedorLLM(estado.mensaje)
    if config.proveedor_agente == "ollama":
        from langchain_ollama import ChatOllama

        return ChatOllama(
            model=config.modelo_ollama,
            base_url=_validar_url_ollama(config.ollama_url),
            temperature=0,
            num_predict=config.agente_max_tokens,
            reasoning=config.ollama_razonamiento,
            client_kwargs={"timeout": config.agente_timeout_s},
        )
    # Comprobación explícita (no un assert, que desaparece con python -O): sin clave no se construye el
    # modelo, aunque verificar_proveedor_agente se haya omitido o sustituido.
    if config.anthropic_api_key is None or not config.anthropic_api_key.get_secret_value().strip():
        raise ErrorProveedorLLM("Falta FNA_ANTHROPIC_API_KEY. " + INSTRUCCION_ANTHROPIC)
    from langchain_anthropic import ChatAnthropic

    argumentos: dict = {
        "model": config.modelo_anthropic,
        "api_key": config.anthropic_api_key,  # explícita: nunca se toma ANTHROPIC_API_KEY del entorno
        "temperature": 0,
        "max_tokens": config.agente_max_tokens,
        "default_request_timeout": config.agente_timeout_s,
        "max_retries": 1,
    }
    return ChatAnthropic(**argumentos)
