"""Agente con memoria por conversación (ADR-024)."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from fabrica_autopartes.api.dependencias import obtener_servicio
from fabrica_autopartes.api.esquemas import SolicitudAgente
from fabrica_autopartes.domain.modelos import RespuestaAgente
from fabrica_autopartes.services.asistente import ServicioAsistente

router = APIRouter(prefix="/api/v1", tags=["Agente"])


@router.post(
    "/agente",
    response_model=RespuestaAgente,
    summary="Preguntar al agente con memoria (herramienta de búsqueda y citas)",
    responses={
        422: {"description": "Pregunta o thread_id inválidos"},
        503: {"description": "Proveedor del agente no disponible (Ollama sin responder o falta la clave)"},
    },
)
def preguntar_agente(
    solicitud: SolicitudAgente, servicio: ServicioAsistente = Depends(obtener_servicio)
) -> RespuestaAgente:
    """La memoria vive en el proceso: se pierde al reiniciar y no se comparte entre workers."""
    return servicio.preguntar_agente(solicitud.pregunta, solicitud.thread_id, canal="api")
