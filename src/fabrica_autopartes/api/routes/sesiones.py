"""Sesiones por usuario seudónimo (ADR-033): entrar con alias, sesión actual, hilos del usuario y cerrar
sesión.

La cookie ``ignis_sesion`` va cifrada con Fernet (httpOnly, SameSite=Lax, Path=/, Secure según
``FNA_COOKIE_SEGURA``) y se renueva en cada petición autenticada (8 h deslizantes). El alias nunca se
registra en el log: los errores son genéricos. La cookie no se puede revocar desde el servidor: cerrar sesión
la borra del navegador, pero una copia robada vale hasta su vencimiento.
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Path, Request, Response, status
from pydantic import BaseModel, Field

from fabrica_autopartes.api.dependencias import obtener_servicio
from fabrica_autopartes.core.config import Configuracion
from fabrica_autopartes.services.asistente import ServicioAsistente, SesionUsuario

NOMBRE_COOKIE = "ignis_sesion"
PATRON_THREAD_ID = r"^[A-Za-z0-9_\-]{1,64}$"

router = APIRouter(prefix="/api/v1/sesiones", tags=["Sesiones (ADR-033)"])


# ------------------------------------------------------------------ cookie
def poner_cookie(respuesta: Response, token: str, config: Configuracion) -> None:
    respuesta.set_cookie(
        NOMBRE_COOKIE,
        token,
        max_age=config.minutos_sesion * 60,
        path="/",
        httponly=True,
        samesite="lax",
        secure=config.cookie_segura,
    )


def borrar_cookie(respuesta: Response, config: Configuracion) -> None:
    respuesta.delete_cookie(
        NOMBRE_COOKIE, path="/", httponly=True, samesite="lax", secure=config.cookie_segura
    )


def sesion_requerida(
    request: Request,
    respuesta: Response,
    servicio: Annotated[ServicioAsistente, Depends(obtener_servicio)],
) -> SesionUsuario:
    """Sesión de la cookie (401 si falta o no es válida; 503 sin ``IGNIS_SECRETO_SESION``).

    Renueva la cookie en la respuesta. Los endpoints que devuelven su propia ``Response`` (el stream SSE)
    leen el token renovado de ``request.state.token_sesion`` y lo ponen ellos mismos.
    """
    sesion, token = servicio.sesion_activa(request.cookies.get(NOMBRE_COOKIE))
    poner_cookie(respuesta, token, servicio.config)
    request.state.token_sesion = token
    return sesion


# ------------------------------------------------------------------ esquemas
class EntradaSesion(BaseModel):
    alias: str = Field(..., min_length=1, max_length=64, description="Alias inventado, sin datos personales")


class DatosSesion(BaseModel):
    alias: str
    user_id_corto: str = Field(description="Primeros 8 caracteres del user_id seudónimo")


class HiloDTO(BaseModel):
    thread_id: str
    titulo: str
    turnos: int
    ultima_ruta: str
    creado: str
    actualizado: str


class NuevoHiloDTO(BaseModel):
    thread_id: str


class MensajeDTO(BaseModel):
    rol: str
    contenido: str
    ruta: str | None = None
    citas: list[dict[str, Any]] = Field(default_factory=list)


def _datos(sesion: SesionUsuario) -> DatosSesion:
    return DatosSesion(alias=sesion.alias, user_id_corto=sesion.user_id_corto)


# ------------------------------------------------------------------ endpoints
@router.post(
    "", response_model=DatosSesion, status_code=status.HTTP_201_CREATED, summary="Entrar con un alias"
)
def entrar(
    entrada: EntradaSesion,
    respuesta: Response,
    servicio: Annotated[ServicioAsistente, Depends(obtener_servicio)],
) -> DatosSesion:
    sesion, token = servicio.crear_sesion(entrada.alias)
    poner_cookie(respuesta, token, servicio.config)
    return _datos(sesion)


@router.get("/yo", response_model=DatosSesion, summary="Sesión actual")
def yo(sesion: Annotated[SesionUsuario, Depends(sesion_requerida)]) -> DatosSesion:
    return _datos(sesion)


@router.get("/yo/hilos", response_model=list[HiloDTO], summary="Hilos del usuario")
def hilos(
    sesion: Annotated[SesionUsuario, Depends(sesion_requerida)],
    servicio: Annotated[ServicioAsistente, Depends(obtener_servicio)],
) -> list[HiloDTO]:
    return [HiloDTO(**asdict(h)) for h in servicio.hilos(sesion.user_id)]


@router.post(
    "/yo/hilos",
    response_model=NuevoHiloDTO,
    status_code=status.HTTP_201_CREATED,
    summary="Crear un hilo nuevo",
)
def crear_hilo(
    sesion: Annotated[SesionUsuario, Depends(sesion_requerida)],
    servicio: Annotated[ServicioAsistente, Depends(obtener_servicio)],
) -> NuevoHiloDTO:
    return NuevoHiloDTO(thread_id=servicio.nuevo_hilo(sesion.user_id))


@router.get("/yo/hilos/{thread_id}/mensajes", response_model=list[MensajeDTO], summary="Historial de un hilo")
def mensajes(
    thread_id: Annotated[str, Path(pattern=PATRON_THREAD_ID)],
    sesion: Annotated[SesionUsuario, Depends(sesion_requerida)],
    servicio: Annotated[ServicioAsistente, Depends(obtener_servicio)],
) -> list[MensajeDTO]:
    return [
        MensajeDTO(
            rol=m["role"],
            contenido=m["content"],
            ruta=m["metadatos"].get("ruta"),
            citas=list(m["metadatos"].get("citas") or []),
        )
        for m in servicio.mensajes_hilo(thread_id, sesion.user_id)
    ]


@router.post("/cerrar", status_code=status.HTTP_204_NO_CONTENT, summary="Cerrar sesión")
def cerrar(servicio: Annotated[ServicioAsistente, Depends(obtener_servicio)]) -> Response:
    """Borra la cookie del navegador. No revoca copias de la cookie: vencen solas a las 8 h (ADR-033)."""
    respuesta = Response(status_code=status.HTTP_204_NO_CONTENT)
    borrar_cookie(respuesta, servicio.config)
    return respuesta
