"""Modelos de dominio (Pydantic) compartidos por pipelines, servicios, API y MCP."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl


def ahora_utc() -> datetime:
    return datetime.now(UTC)


class RegistroCaptura(BaseModel):
    """Metadatos de una captura en la capa Bronze (una línea del manifiesto JSONL)."""

    url: str
    url_final: str
    fecha_captura: datetime = Field(default_factory=ahora_utc)
    estado_http: int
    tipo_contenido: str = ""
    sha256: str
    archivo_html: str
    bytes: int
    agente_usuario: str
    permitido_robots: bool = True


class DocumentoLimpio(BaseModel):
    """Documento de la capa Silver: texto útil sin menús, scripts ni pies de página."""

    id: str
    url: str
    titulo: str
    seccion: str
    idioma: str = "es"
    texto: str
    sha256_texto: str
    fecha_captura: datetime
    origen: Literal["scraping", "semilla", "lectura_web"] = "scraping"


class Fragmento(BaseModel):
    """Fragmento (*chunk*) semánticamente coherente de la capa Gold."""

    id: str
    documento_id: str
    url: str
    titulo: str
    seccion: str
    encabezado: str = ""
    idioma: str = "es"
    texto: str
    tokens_aprox: int
    orden: int
    origen: Literal["scraping", "semilla", "lectura_web"] = "scraping"


class Fuente(BaseModel):
    fragmento_id: str
    titulo: str
    url: str


class RespuestaQA(BaseModel):
    pregunta: str
    respuesta: str
    fuentes: list[Fuente] = Field(default_factory=list)
    fundamentada: bool
    confianza: Literal["alta", "media", "baja", "ninguna"] = "media"
    version_prompt: str
    proveedor: str
    modelo: str
    modo_contexto: str
    # Recuperador usado en el modo «seleccion»; «no_aplica» con contexto completo o bloqueado.
    recuperador: Literal["bm25", "semantico", "no_aplica"] = "no_aplica"
    latencia_ms: int = 0


class RespuestaAgente(BaseModel):
    """Respuesta del agente con memoria (ADR-024)."""

    pregunta: str
    respuesta: str
    fuentes: list[Fuente] = Field(default_factory=list)
    thread_id: str
    proveedor: str
    modelo: str
    version_prompt: str = "v1"
    llamadas_herramienta: int = 0
    # Comparación de la respuesta con el texto de los fragmentos citados (mismo criterio que el Q&A).
    fundamentada: bool = False
    bloqueada: bool = False
    limite_alcanzado: bool = False
    latencia_ms: int = 0


ETIQUETA_RESPUESTA_WEB = "Respuesta complementaria desde la web — no proviene de la base verificada"


class HallazgoWeb(BaseModel):
    """Un dato encontrado en la web con su URL y la fecha de consulta (pendiente de revisión humana)."""

    dato: str
    url: str
    fecha_consulta: str


class RespuestaWeb(BaseModel):
    """Búsqueda web complementaria (fase 9): nunca entra a la base verificada ni a la evaluación v1–v3."""

    pregunta: str
    respuesta: str
    hallazgos: list[HallazgoWeb] = Field(default_factory=list)
    encontrado: bool
    etiqueta: str = ETIQUETA_RESPUESTA_WEB
    fecha_consulta: str
    proveedor: str
    modelo: str
    version_prompt: str
    latencia_ms: int = 0


class ItemFAQ(BaseModel):
    pregunta: str
    respuesta: str
    fuentes: list[str] = Field(default_factory=list)


class ResultadoFAQ(BaseModel):
    items: list[ItemFAQ]
    version_prompt: str
    proveedor: str
    modelo: str
    latencia_ms: int = 0
    advertencias: list[str] = Field(default_factory=list)


class ResultadoResumen(BaseModel):
    resumen: str
    enfoque: str
    version_prompt: str
    proveedor: str
    modelo: str
    latencia_ms: int = 0


class EstadisticasBase(BaseModel):
    documentos: int
    fragmentos: int
    tokens_aprox: int
    secciones: dict[str, int]
    origenes: dict[str, int]
    urls: list[str]
    generado_en: datetime | None = None


class SolicitudScraping(BaseModel):
    urls: list[HttpUrl]
    max_paginas: int = 50
