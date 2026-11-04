"""API del simulador 3D (v2.0) y de la biblioteca de máquinas.

El backend no confía en valores geométricos ni cinemáticos del cliente: los identificadores,
límites de articulación, factores de despiece y parámetros físicos se validan aquí.
"""

from __future__ import annotations

import math
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, field_validator

from fabrica_autopartes.api.dependencias import obtener_servicio
from fabrica_autopartes.core.excepciones import ErrorRecursoNoEncontrado
from fabrica_autopartes.services.asistente import ServicioAsistente
from fabrica_autopartes.services.maquinas import Maquina, construir_biblioteca
from fabrica_autopartes.services.simulador import (
    RespuestaPieza,
    ServicioSimulador,
    catalogo,
    obtener_ensamblaje,
    obtener_pieza,
)
from fabrica_autopartes.simulador import cinematica as cin
from fabrica_autopartes.simulador.fisica_freno import EntradaFreno, ResultadoFreno, calcular
from fabrica_autopartes.simulador.modelos import Articulacion, Ensamblaje, NodoJerarquia, Pieza

router = APIRouter(prefix="/api/v1", tags=["Simulador 3D (v2.0)"])


def _sim(servicio: ServicioAsistente) -> ServicioSimulador:
    return ServicioSimulador(servicio.base, servicio.repo)


class ResumenEnsamblaje(BaseModel):
    id: str
    nombre: str
    descripcion: str
    version: str
    piezas: int
    articulaciones: int
    archivo_glb: str
    advertencia: str


class SolicitudCinematica(BaseModel):
    valores: dict[str, float] = Field(default_factory=dict, examples=[{"j_rueda": 45.0, "j_piston": 0.001}])


class Lectura(BaseModel):
    posicion: list[float]
    rotacion_grados: list[float]


class EstadoVisual(BaseModel):
    modo: Literal["ensamblado", "despiece", "reensamblaje", "frenado"] = "ensamblado"
    factor_despiece: float = Field(0.0, ge=0.0, le=1.0)
    velocidad_animacion: float = Field(1.0, ge=0.1, le=4.0)
    ocultas: list[str] = Field(default_factory=list)
    transparencia: float = Field(0.0, ge=0.0, le=0.9)
    seleccionada: str | None = None
    valores_articulacion: dict[str, float] = Field(default_factory=dict)
    camara: list[float] | None = Field(None, min_length=3, max_length=3)

    @field_validator("camara")
    @classmethod
    def _camara_finita(cls, v: list[float] | None) -> list[float] | None:
        if v is not None and (not all(math.isfinite(c) for c in v) or max(abs(c) for c in v) > 10):
            raise ValueError("La cámara debe estar a menos de 10 m del origen")
        return v


class SolicitudEstado(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=120)
    estado: EstadoVisual


class EstadoGuardado(BaseModel):
    id: int
    nombre: str
    ensamblaje: str
    estado: EstadoVisual


class SolicitudEvento(BaseModel):
    tipo: Literal["seleccion", "despiece", "reensamblaje", "frenado", "visibilidad", "captura", "camara"]
    pieza_id: str | None = None
    detalle: dict = Field(default_factory=dict)


class SolicitudPregunta(BaseModel):
    pieza_id: str
    pregunta: str = Field(..., min_length=3, max_length=300)


def _validar_ids(ens: Ensamblaje, ids: list[str]) -> None:
    validos = {p.id for p in ens.piezas}
    invalidos = [i for i in ids if i not in validos]
    if invalidos:
        raise HTTPException(422, f"Piezas inexistentes: {invalidos}")


@router.get("/simulador/ensamblajes", response_model=list[ResumenEnsamblaje])
def listar_ensamblajes() -> list[ResumenEnsamblaje]:
    return [
        ResumenEnsamblaje(
            id=e.id,
            nombre=e.nombre,
            descripcion=e.descripcion,
            version=e.version,
            piezas=len(e.piezas),
            articulaciones=len(e.articulaciones),
            archivo_glb=e.archivo_glb,
            advertencia=e.advertencia,
        )
        for e in catalogo().values()
    ]


@router.get("/simulador/ensamblajes/{ens_id}", response_model=Ensamblaje)
def ensamblaje(ens_id: str) -> Ensamblaje:
    return obtener_ensamblaje(ens_id)


@router.get("/simulador/ensamblajes/{ens_id}/jerarquia", response_model=NodoJerarquia)
def jerarquia(ens_id: str) -> NodoJerarquia:
    return cin.jerarquia(obtener_ensamblaje(ens_id))


@router.get("/simulador/ensamblajes/{ens_id}/piezas", response_model=list[Pieza])
def piezas(ens_id: str) -> list[Pieza]:
    return obtener_ensamblaje(ens_id).piezas


@router.get("/simulador/ensamblajes/{ens_id}/piezas/{pieza_id}", response_model=Pieza)
def pieza(ens_id: str, pieza_id: str) -> Pieza:
    return obtener_pieza(obtener_ensamblaje(ens_id), pieza_id)


@router.get("/simulador/ensamblajes/{ens_id}/articulaciones", response_model=list[Articulacion])
def articulaciones(ens_id: str) -> list[Articulacion]:
    return obtener_ensamblaje(ens_id).articulaciones


@router.get("/simulador/ensamblajes/{ens_id}/despiece", response_model=dict[str, list[float]])
def despiece(ens_id: str, factor: float = Query(1.0, ge=0.0, le=1.0)) -> dict[str, list[float]]:
    return {k: list(v) for k, v in cin.posiciones_despiece(obtener_ensamblaje(ens_id), factor).items()}


@router.get("/simulador/ensamblajes/{ens_id}/secuencia", response_model=list[str])
def secuencia(ens_id: str, modo: Literal["desmontaje", "reensamblaje"] = "desmontaje") -> list[str]:
    ens = obtener_ensamblaje(ens_id)
    return cin.secuencia_desmontaje(ens) if modo == "desmontaje" else cin.secuencia_reensamblaje(ens)


@router.get("/simulador/ensamblajes/{ens_id}/animacion")
def parametros_animacion(ens_id: str) -> dict:
    """Parámetros de animación: duración por pieza y orden (la animación es visual, no física)."""
    ens = obtener_ensamblaje(ens_id)
    orden = cin.secuencia_desmontaje(ens)
    return {
        "duracion_por_pieza_s": 0.35,
        "solape": 0.5,
        "orden_desmontaje": orden,
        "orden_reensamblaje": list(reversed(orden)),
        "frenado": {
            "holgura_m": ens.parametros["holgura_pastilla"],
            "articulaciones": {
                "j_piston": 2 * ens.parametros["holgura_pastilla"],
                "j_pinza_flotante": ens.parametros["holgura_pastilla"],
            },
        },
    }


@router.post("/simulador/ensamblajes/{ens_id}/cinematica", response_model=dict[str, Lectura])
def cinematica(ens_id: str, solicitud: SolicitudCinematica) -> dict[str, Lectura]:
    ens = obtener_ensamblaje(ens_id)
    try:
        datos = cin.lecturas(ens, solicitud.valores)
    except cin.ErrorEnsamblaje as exc:
        raise HTTPException(422, str(exc)) from exc
    return {k: Lectura(**v) for k, v in datos.items()}


@router.post("/simulador/ensamblajes/{ens_id}/calculo-freno", response_model=ResultadoFreno)
def calculo_freno(ens_id: str, entrada: EntradaFreno) -> ResultadoFreno:
    obtener_ensamblaje(ens_id)
    return calcular(entrada)


@router.post("/simulador/ensamblajes/{ens_id}/preguntar", response_model=RespuestaPieza)
def preguntar(
    ens_id: str, solicitud: SolicitudPregunta, servicio: ServicioAsistente = Depends(obtener_servicio)
) -> RespuestaPieza:
    return _sim(servicio).preguntar(ens_id, solicitud.pieza_id, solicitud.pregunta)


@router.post("/simulador/ensamblajes/{ens_id}/estados", response_model=EstadoGuardado, status_code=201)
def guardar_estado(
    ens_id: str, solicitud: SolicitudEstado, servicio: ServicioAsistente = Depends(obtener_servicio)
) -> EstadoGuardado:
    ens = obtener_ensamblaje(ens_id)
    e = solicitud.estado
    _validar_ids(ens, e.ocultas + ([e.seleccionada] if e.seleccionada else []))
    try:
        cin.resolver_valores(ens, e.valores_articulacion)
    except cin.ErrorEnsamblaje as exc:
        raise HTTPException(422, str(exc)) from exc
    id_ = servicio.repo.guardar_estado(ens_id, solicitud.nombre, e.model_dump())
    return EstadoGuardado(id=id_, nombre=solicitud.nombre, ensamblaje=ens_id, estado=e)


@router.get("/simulador/ensamblajes/{ens_id}/estados", response_model=list[EstadoGuardado])
def listar_estados(
    ens_id: str, servicio: ServicioAsistente = Depends(obtener_servicio)
) -> list[EstadoGuardado]:
    obtener_ensamblaje(ens_id)
    return [
        EstadoGuardado(
            id=f.id, nombre=f.nombre, ensamblaje=f.ensamblaje, estado=EstadoVisual.model_validate(f.estado)
        )
        for f in servicio.repo.listar_estados(ens_id)
    ]


@router.get("/simulador/estados/{estado_id}", response_model=EstadoGuardado)
def obtener_estado(estado_id: int, servicio: ServicioAsistente = Depends(obtener_servicio)) -> EstadoGuardado:
    f = servicio.repo.obtener_estado(estado_id)
    if f is None:
        raise ErrorRecursoNoEncontrado(f"No existe el estado {estado_id}")
    return EstadoGuardado(
        id=f.id, nombre=f.nombre, ensamblaje=f.ensamblaje, estado=EstadoVisual.model_validate(f.estado)
    )


@router.post("/simulador/ensamblajes/{ens_id}/eventos", status_code=201)
def registrar_evento(
    ens_id: str, solicitud: SolicitudEvento, servicio: ServicioAsistente = Depends(obtener_servicio)
) -> dict:
    ens = obtener_ensamblaje(ens_id)
    if solicitud.pieza_id:
        _validar_ids(ens, [solicitud.pieza_id])
    id_ = servicio.repo.registrar_evento(ens_id, solicitud.tipo, solicitud.pieza_id, solicitud.detalle)
    return {"id": id_}


@router.get("/simulador/ensamblajes/{ens_id}/eventos")
def listar_eventos(ens_id: str, servicio: ServicioAsistente = Depends(obtener_servicio)) -> list[dict]:
    obtener_ensamblaje(ens_id)
    return [
        {"id": f.id, "fecha": f.fecha, "tipo": f.tipo, "pieza_id": f.pieza_id, "detalle": f.detalle}
        for f in servicio.repo.listar_eventos(ens_id)
    ]


@router.get("/maquinas", response_model=list[Maquina], tags=["Biblioteca de máquinas"])
def maquinas(servicio: ServicioAsistente = Depends(obtener_servicio)) -> list[Maquina]:
    return construir_biblioteca(servicio.base)


@router.get("/maquinas/{maquina_id}", response_model=Maquina, tags=["Biblioteca de máquinas"])
def maquina(maquina_id: str, servicio: ServicioAsistente = Depends(obtener_servicio)) -> Maquina:
    for m in construir_biblioteca(servicio.base):
        if m.id == maquina_id:
            return m
    raise ErrorRecursoNoEncontrado(f"No existe la máquina '{maquina_id}'")
