"""Configuración central basada en variables de entorno (pydantic-settings).

Los valores se leen, en orden de prioridad, desde variables de entorno con prefijo
``FNA_`` y desde el archivo ``.env`` ubicado en la raíz del repositorio. Ningún secreto
se define en el código: las claves de API se declaran como ``SecretStr`` y solo se leen
del entorno.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import AliasChoices, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

RAIZ_PROYECTO = Path(__file__).resolve().parents[3]

Proveedor = Literal["ollama", "openai", "anthropic", "claude_code", "extractivo"]
ModoContexto = Literal["auto", "completo", "seleccion"]
Recuperador = Literal["bm25", "semantico"]
DispositivoEmbeddings = Literal["auto", "cpu", "cuda"]
ProveedorAgente = Literal["ollama", "anthropic"]


class Configuracion(BaseSettings):
    """Parámetros de ejecución del sistema."""

    model_config = SettingsConfigDict(
        env_prefix="FNA_",
        env_file=RAIZ_PROYECTO / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    # --- Empresa y fuentes -------------------------------------------------
    empresa_nombre: str = "Fábrica Nacional de Autopartes (Fanalca)"
    sitio_base: str = "https://autopartesfanalca.com.co/"
    dominios_permitidos: list[str] = Field(
        default_factory=lambda: ["autopartesfanalca.com.co", "fanalca.com"]
    )
    # Semillas verificadas el 2026-11-04: sitio de la unidad de autopartes (fuente principal)
    # y sitio corporativo del grupo (fuente complementaria).
    urls_semilla: list[str] = Field(
        default_factory=lambda: [
            "https://autopartesfanalca.com.co/",
            "https://autopartesfanalca.com.co/nosotros/",
            "https://autopartesfanalca.com.co/productos/",
            "https://autopartesfanalca.com.co/clientes/",
            "https://autopartesfanalca.com.co/contacto/",
            "https://fanalca.com/",
            "https://fanalca.com/negocios/honda-motocicletas/",
            "https://fanalca.com/en/who-we-are/",
            "https://fanalca.com/en/business/",
            "https://fanalca.com/en/sustainability/",
            "https://fanalca.com/en/contact/",
        ]
    )
    rutas_excluidas: list[str] = Field(
        default_factory=lambda: [
            "/wp-admin",
            "/wp-login",
            "/wp-json",
            "/feed",
            "/carrito",
            "?s=",
            "/vacantes",
            "/wp-content/uploads",
            # Plantillas y páginas sin contenido para el cliente (detectadas en el scraping real)
            "elementskit_template",
            "/firma",
            "/sitio-en-construccion",
            # Avisos legales extensos: diluyen la base de primer contacto (decisión documentada)
            "/aviso-de-privacidad",
            "/privacy-notice",
        ]
    )
    # Expresiones regulares sobre la ruta: paginación de listados (repiten resúmenes de noticias) y
    # filtros de vacantes por área o ciudad (equivalentes a /vacantes, ya excluida).
    patrones_excluidos: list[str] = Field(
        default_factory=lambda: [
            r"/(?:page|noticias|news)/\d+/?$",
            r"^/(?:en/)?(?:area|ciudad)/",
        ]
    )

    # --- Scraping responsable ---------------------------------------------
    agente_usuario: str = "FNA-KB/1.0 (+https://github.com/JulianReneMunoz/fabrica-nacional-autopartes)"
    tiempo_espera_s: float = 20.0
    pausa_entre_peticiones_s: float = 2.0
    reintentos: int = 3
    max_paginas: int = 80
    profundidad_maxima: int = 3

    # --- Rutas de datos (arquitectura Medallion) ---------------------------
    dir_datos: Path = RAIZ_PROYECTO / "data"

    # --- Fragmentación ----------------------------------------------------
    tamano_fragmento: int = 1200
    solapamiento_fragmento: int = 150

    # --- LLM ---------------------------------------------------------------
    # Q&A, FAQ y resumen (ADR-027): extractivo funciona en un clon nuevo sin instalar nada, sin red ni costo,
    # igual que en CI y Docker. claude_code, anthropic u ollama se eligen con FNA_PROVEEDOR_LLM en .env.
    proveedor_llm: Proveedor = "extractivo"
    modelo_llm: str = "llama3.2:3b"
    # 0: salida lo más determinista posible (C4); claude_code y extractivo no la usan (aplica_temperatura).
    temperatura: float = 0.0
    # Se lee de OLLAMA_BASE_URL (sin prefijo) o de FNA_OLLAMA_URL; el agente solo acepta un host local.
    ollama_url: str = Field(
        default="http://localhost:11434",
        validation_alias=AliasChoices("OLLAMA_BASE_URL", "FNA_OLLAMA_URL", "ollama_url"),
    )
    ollama_num_ctx: int = 16384
    openai_api_key: SecretStr | None = None
    anthropic_api_key: SecretStr | None = None
    version_prompt: str = "v3"
    modo_contexto: ModoContexto = "auto"
    presupuesto_tokens_contexto: int = 9000
    fragmentos_seleccion: int = 8

    # --- Base semántica (ADR-023; requiere el extra semantica-cpu o semantica-gpu) ---------
    recuperador: Recuperador = "bm25"
    # Se lee de EMBEDDINGS_DEVICE (sin prefijo) o de FNA_EMBEDDINGS_DEVICE.
    embeddings_dispositivo: DispositivoEmbeddings = Field(
        default="auto",
        validation_alias=AliasChoices("EMBEDDINGS_DEVICE", "FNA_EMBEDDINGS_DEVICE", "embeddings_dispositivo"),
    )

    # --- Agente con memoria (ADR-024) --------------------------------------
    # Por defecto Claude Haiku 5.5 vía API (créditos de API del plan Max; ADR-026). Ollama es opcional.
    proveedor_agente: ProveedorAgente = "anthropic"
    modelo_ollama: str = "qwen3:8b"
    # qwen3 y otros modelos «que razonan»: True activa el razonamiento en ChatOllama; nunca se muestra.
    ollama_razonamiento: bool = False
    modelo_anthropic: str = "claude-haiku-5-5"
    agente_max_tokens: int = Field(default=1024, ge=64, le=4096)
    agente_max_iteraciones: int = Field(default=6, ge=1, le=20)
    agente_limite_historial_tokens: int = Field(default=3000, ge=200, le=100_000)
    agente_timeout_s: float = Field(default=60.0, gt=0, le=600)
    # Tope de conversaciones en memoria (vive en el proceso): al superarlo se descarta la menos usada.
    agente_max_hilos: int = Field(default=500, ge=1, le=100_000)

    # --- Persistencia y API -----------------------------------------------
    url_base_datos: str = f"sqlite:///{(RAIZ_PROYECTO / 'data' / 'app.db').as_posix()}"
    api_clave_admin: SecretStr | None = None
    mcp_permitir_llm: bool = False

    @property
    def dir_bronze(self) -> Path:
        return self.dir_datos / "bronze"

    @property
    def dir_silver(self) -> Path:
        return self.dir_datos / "silver"

    @property
    def dir_gold(self) -> Path:
        return self.dir_datos / "gold"

    @property
    def dir_semilla(self) -> Path:
        return self.dir_datos / "seed"

    @property
    def archivo_consolidado(self) -> Path:
        return self.dir_gold / "base_conocimiento.txt"

    @property
    def archivo_fragmentos(self) -> Path:
        return self.dir_gold / "fragmentos.jsonl"

    @property
    def dir_vectores(self) -> Path:
        return self.dir_datos / "vectores"


@lru_cache(maxsize=1)
def obtener_configuracion() -> Configuracion:
    """Devuelve una instancia única de configuración (patrón *singleton* perezoso)."""
    return Configuracion()
