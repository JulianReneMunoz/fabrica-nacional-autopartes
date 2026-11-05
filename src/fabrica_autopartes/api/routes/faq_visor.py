"""Respuestas precalculadas de las preguntas frecuentes de Fanalca para el visor."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from fabrica_autopartes.api.dependencias import obtener_servicio
from fabrica_autopartes.core.excepciones import ErrorRecursoNoEncontrado
from fabrica_autopartes.services.asistente import ServicioAsistente
from fabrica_autopartes.services.faq_visor import leer_faq_visor

router = APIRouter(prefix="/api/v1", tags=["FAQ del visor"])


@router.get("/faq-visor")
def faq_visor(servicio: ServicioAsistente = Depends(obtener_servicio)) -> dict[str, Any]:
    datos = leer_faq_visor(servicio.config.dir_gold)
    if datos is None:
        raise ErrorRecursoNoEncontrado("Aún no se generó faq_visor.json: ejecutar «fabrica faq-visor»")
    return datos
