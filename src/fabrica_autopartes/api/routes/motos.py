"""API de la motocicleta de referencia con fichas Honda (fichas curadas y cálculo didáctico).

El backend valida rpm, marcha, fuerza de palanca y versión (422 ante entradas inválidas). Las
respuestas de modelo son deterministas: salen de la ficha curada y citan campo y fuente.
"""

from __future__ import annotations

from fastapi import APIRouter, Query

from fabrica_autopartes.api.esquemas import (
    CalculoMoto,
    EntradaMoto,
    FichaMoto,
    RespuestaModelo,
    ResumenMoto,
)
from fabrica_autopartes.services import motos as srv

router = APIRouter(prefix="/api/v1", tags=["Motocicleta de referencia (v2.0)"])


@router.get("/motos", response_model=list[ResumenMoto])
def listar() -> list[ResumenMoto]:
    return srv.listar_motos()


@router.get("/motos/{moto_id}", response_model=FichaMoto)
def ficha(moto_id: str) -> FichaMoto:
    return srv.obtener_ficha(moto_id)


@router.get("/motos/{moto_id}/faq", response_model=list[RespuestaModelo])
def faq(moto_id: str) -> list[RespuestaModelo]:
    return srv.preguntas_modelo(moto_id)


@router.post("/motos/{moto_id}/calculo", response_model=CalculoMoto)
def calculo(
    moto_id: str,
    entrada: EntradaMoto,
    con_ficha: bool = Query(True, description="Aplica los campos publicados de la ficha"),
) -> CalculoMoto:
    srv.obtener_ficha(moto_id)  # 404 si la ficha no existe
    return srv.calcular(moto_id if con_ficha else None, entrada)
