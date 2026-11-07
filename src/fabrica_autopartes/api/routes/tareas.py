"""Las tres tareas del Módulo 1: Q&A, FAQ y Resumen."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from fabrica_autopartes.api.dependencias import obtener_servicio
from fabrica_autopartes.api.esquemas import SolicitudFAQ, SolicitudQA, SolicitudQAWeb, SolicitudResumen
from fabrica_autopartes.domain.modelos import RespuestaQA, RespuestaWeb, ResultadoFAQ, ResultadoResumen
from fabrica_autopartes.services.asistente import ServicioAsistente

router = APIRouter(prefix="/api/v1/tareas", tags=["Tareas LLM"])


@router.post(
    "/qa",
    response_model=RespuestaQA,
    summary="Responder una pregunta con base en el contexto",
    responses={
        422: {"description": "Solicitud inválida (por ejemplo, un recuperador distinto de bm25 o semantico)"},
        503: {"description": "Recuperador semántico no disponible: falta el extra, el modelo o el índice"},
    },
)
def qa(solicitud: SolicitudQA, servicio: ServicioAsistente = Depends(obtener_servicio)) -> RespuestaQA:
    return servicio.responder(
        solicitud.pregunta,
        canal="api",
        modo_contexto=solicitud.modo_contexto,
        recuperador=solicitud.recuperador,
        **solicitud.como_kwargs(),
    )


@router.post(
    "/qa-web",
    response_model=RespuestaWeb,
    summary="Búsqueda web complementaria con Claude (solo a petición, tras la frase de rechazo)",
    responses={
        422: {"description": "Pregunta inválida o bloqueada"},
        429: {"description": "Límite de búsquedas"},
    },
)
def qa_web(
    solicitud: SolicitudQAWeb, servicio: ServicioAsistente = Depends(obtener_servicio)
) -> RespuestaWeb:
    """Respuesta complementaria desde la web: no proviene de la base verificada ni entra en ella."""
    return servicio.buscar_web(solicitud.pregunta)


@router.post("/faq", response_model=ResultadoFAQ, summary="Generar preguntas frecuentes")
def faq(solicitud: SolicitudFAQ, servicio: ServicioAsistente = Depends(obtener_servicio)) -> ResultadoFAQ:
    return servicio.generar_faq(solicitud.n_preguntas, canal="api", **solicitud.como_kwargs())


@router.post("/resumen", response_model=ResultadoResumen, summary="Generar el resumen ejecutivo")
def resumen(
    solicitud: SolicitudResumen, servicio: ServicioAsistente = Depends(obtener_servicio)
) -> ResultadoResumen:
    return servicio.resumir(solicitud.enfoque, canal="api", **solicitud.como_kwargs())
