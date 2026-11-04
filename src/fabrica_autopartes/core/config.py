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

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

RAIZ_PROYECTO = Path(__file__).resolve().parents[3]

Proveedor = Literal["ollama", "openai", "anthropic", "extractivo"]
ModoContexto = Literal["auto", "completo", "seleccion"]


class Configuracion(BaseSettings):
    """Parámetros de ejecución del sistema."""

    model_config = SettingsConfigDict(
        env_prefix="FNA_",
        env_file=RAIZ_PROYECTO / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
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
        ]
    )

    # --- Scraping responsable ---------------------------------------------
    agente_usuario: str = (
        "FNA-KnowledgeBot/0.1 (proyecto academico UAO; contacto: ver README del repositorio)"
    )
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
    proveedor_llm: Proveedor = "ollama"
    modelo_llm: str = "llama3.2:3b"
    temperatura: float = 0.1
    ollama_url: str = "http://localhost:11434"
    ollama_num_ctx: int = 16384
    openai_api_key: SecretStr | None = None
    anthropic_api_key: SecretStr | None = None
    version_prompt: str = "v3"
    modo_contexto: ModoContexto = "auto"
    presupuesto_tokens_contexto: int = 9000
    fragmentos_seleccion: int = 8

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


@lru_cache(maxsize=1)
def obtener_configuracion() -> Configuracion:
    """Devuelve una instancia única de configuración (patrón *singleton* perezoso)."""
    return Configuracion()
