"""Salud, auditoría y operación del pipeline."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from fabrica_autopartes import __version__
from fabrica_autopartes.api.dependencias import exigir_admin, obtener_servicio
from fabrica_autopartes.api.esquemas import EjecucionDTO, InteraccionDTO, Pagina, SolicitudReconstruccion
from fabrica_autopartes.domain.modelos import EstadisticasBase
from fabrica_autopartes.services.asistente import ServicioAsistente

router = APIRouter(tags=["Operación"])


@router.get("/salud", summary="Verificación de disponibilidad")
def salud(servicio: ServicioAsistente = Depends(obtener_servicio)) -> dict:
    return {
        "estado": "ok",
        "version": __version__,
        "fragmentos": len(servicio.base.fragmentos),
        "proveedor_llm": servicio.config.proveedor_llm,
        "modelo_llm": servicio.config.modelo_llm,
    }


@router.get(
    "/api/v1/auditoria/interacciones",
    response_model=Pagina[InteraccionDTO],
    summary="Historial de interacciones",
)
def interacciones(
    pagina: int = Query(1, ge=1),
    tamano: int = Query(20, ge=1, le=100),
    tarea: str | None = Query(None, pattern="^(qa|faq|resumen)$"),
    servicio: ServicioAsistente = Depends(obtener_servicio),
) -> Pagina[InteraccionDTO]:
    filas, total = servicio.repo.listar_interacciones(pagina, tamano, tarea)
    return Pagina(
        elementos=[InteraccionDTO.model_validate(f) for f in filas], total=total, pagina=pagina, tamano=tamano
    )


@router.get(
    "/api/v1/pipeline/ejecuciones",
    response_model=list[EjecucionDTO],
    summary="Historial de ejecuciones del pipeline",
)
def ejecuciones(servicio: ServicioAsistente = Depends(obtener_servicio)) -> list[EjecucionDTO]:
    return [EjecucionDTO.model_validate(e) for e in servicio.repo.listar_ejecuciones()]


@router.post(
    "/api/v1/pipeline/reconstruir",
    response_model=EstadisticasBase,
    dependencies=[Depends(exigir_admin)],
    summary="Reconstruir Silver/Gold desde Bronze o semilla (requiere X-API-Key)",
)
def reconstruir(
    solicitud: SolicitudReconstruccion, servicio: ServicioAsistente = Depends(obtener_servicio)
) -> EstadisticasBase:
    return servicio.construir(solicitud.fuente).estadisticas
