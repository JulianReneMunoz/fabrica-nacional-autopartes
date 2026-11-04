"""Las tres tareas del Módulo 1: Q&A, FAQ y Resumen."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from fabrica_autopartes.api.dependencias import obtener_servicio
from fabrica_autopartes.api.esquemas import SolicitudFAQ, SolicitudQA, SolicitudResumen
from fabrica_autopartes.domain.modelos import RespuestaQA, ResultadoFAQ, ResultadoResumen
from fabrica_autopartes.services.asistente import ServicioAsistente

router = APIRouter(prefix="/api/v1/tareas", tags=["Tareas LLM"])


@router.post("/qa", response_model=RespuestaQA, summary="Responder una pregunta con base en el contexto")
def qa(solicitud: SolicitudQA, servicio: ServicioAsistente = Depends(obtener_servicio)) -> RespuestaQA:
    return servicio.responder(
        solicitud.pregunta, canal="api", modo_contexto=solicitud.modo_contexto, **solicitud.como_kwargs()
    )


@router.post("/faq", response_model=ResultadoFAQ, summary="Generar preguntas frecuentes")
def faq(solicitud: SolicitudFAQ, servicio: ServicioAsistente = Depends(obtener_servicio)) -> ResultadoFAQ:
    return servicio.generar_faq(solicitud.n_preguntas, canal="api", **solicitud.como_kwargs())


@router.post("/resumen", response_model=ResultadoResumen, summary="Generar el resumen ejecutivo")
def resumen(
    solicitud: SolicitudResumen, servicio: ServicioAsistente = Depends(obtener_servicio)
) -> ResultadoResumen:
    return servicio.resumir(solicitud.enfoque, canal="api", **solicitud.como_kwargs())
