"""DTO de entrada y salida de la API (contratos validados con Pydantic)."""

from __future__ import annotations

from datetime import datetime
from typing import Generic, Literal, TypeVar

from pydantic import BaseModel, Field

from fabrica_autopartes.domain.modelos import Fragmento
from fabrica_autopartes.services.motos import (  # noqa: F401  (contratos de /api/v1/motos)
    CalculoMoto,
    CampoFicha,
    FichaAplicada,
    FichaMoto,
    RespuestaModelo,
    ResumenMoto,
)
from fabrica_autopartes.simulador.fisica_moto import EntradaMoto, ResultadoMoto  # noqa: F401

T = TypeVar("T")

ProveedorAPI = Literal["ollama", "openai", "anthropic", "claude_code", "extractivo"]
VersionAPI = Literal["v1", "v2", "v3"]
ModoAPI = Literal["auto", "completo", "seleccion"]
RecuperadorAPI = Literal["bm25", "semantico"]


class OpcionesLLM(BaseModel):
    proveedor: ProveedorAPI | None = Field(None, description="Sobrescribe FNA_PROVEEDOR_LLM")
    modelo: str | None = Field(None, examples=["llama3.2:3b"])
    version_prompt: VersionAPI | None = None

    def como_kwargs(self) -> dict[str, str | None]:
        return {"proveedor": self.proveedor, "modelo": self.modelo, "version_prompt": self.version_prompt}


class SolicitudQA(OpcionesLLM):
    pregunta: str = Field(
        ..., min_length=3, max_length=500, examples=["¿Dónde queda la sede principal de Fanalca?"]
    )
    modo_contexto: ModoAPI | None = None
    recuperador: RecuperadorAPI = Field(
        "bm25",
        description="Recuperador del modo seleccion: bm25 (por defecto) o semantico (nomic + Chroma)",
    )


class SolicitudAgente(BaseModel):
    pregunta: str = Field(
        ..., min_length=3, max_length=500, examples=["¿Dónde queda la sede principal de Fanalca?"]
    )
    thread_id: str = Field(
        ...,
        min_length=1,
        max_length=64,
        pattern=r"^[A-Za-z0-9_-]+$",
        description="Identificador de la conversación: la memoria del agente se guarda por thread_id",
        examples=["demo-1"],
    )


class SolicitudQAWeb(BaseModel):
    pregunta: str = Field(
        ...,
        min_length=3,
        max_length=500,
        examples=["¿Cuántos empleados tiene Fanalca en la planta de Yumbo?"],
    )


class SolicitudFAQ(OpcionesLLM):
    n_preguntas: int = Field(8, ge=3, le=20)


class SolicitudResumen(OpcionesLLM):
    enfoque: str | None = Field(None, max_length=200, examples=["negocios y productos"])


class Pagina(BaseModel, Generic[T]):
    elementos: list[T]
    total: int
    pagina: int
    tamano: int


class FragmentoBuscado(BaseModel):
    fragmento: Fragmento
    puntaje: float | None = None


class InteraccionDTO(BaseModel):
    id: int
    fecha: datetime | None
    tarea: str
    canal: str
    entrada: str
    salida: str
    proveedor: str
    modelo: str
    version_prompt: str
    modo_contexto: str
    fuentes: list
    fundamentada: bool | None
    latencia_ms: int

    model_config = {"from_attributes": True}


class EjecucionDTO(BaseModel):
    id: int
    inicio: datetime | None
    fin: datetime | None
    etapa: str
    estado: str
    detalle: dict

    model_config = {"from_attributes": True}


class SolicitudReconstruccion(BaseModel):
    fuente: Literal["auto", "scraping", "semilla", "ambas"] = "auto"


class ErrorDTO(BaseModel):
    codigo: str
    mensaje: str
