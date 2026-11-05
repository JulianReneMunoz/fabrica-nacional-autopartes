"""API de la motocicleta de referencia con fichas Honda (fichas curadas y cálculo didáctico).

El backend valida rpm, marcha, fuerza de palanca y versión (422 ante entradas inválidas). Las
respuestas de modelo son deterministas: salen de la ficha curada y citan campo y fuente.
"""

from __future__ import annotations

from fastapi import APIRouter, Query

from fabrica_autopartes.services import motos as srv
from fabrica_autopartes.simulador.fisica_moto import EntradaMoto

router = APIRouter(prefix="/api/v1", tags=["Motocicleta de referencia (v2.0)"])


@router.get("/motos", response_model=list[srv.ResumenMoto])
def listar() -> list[srv.ResumenMoto]:
    return srv.listar_motos()


@router.get("/motos/{moto_id}", response_model=srv.FichaMoto)
def ficha(moto_id: str) -> srv.FichaMoto:
    return srv.obtener_ficha(moto_id)


@router.get("/motos/{moto_id}/faq", response_model=list[srv.RespuestaModelo])
def faq(moto_id: str) -> list[srv.RespuestaModelo]:
    return srv.preguntas_modelo(moto_id)


@router.post("/motos/{moto_id}/calculo", response_model=srv.CalculoMoto)
def calculo(
    moto_id: str,
    entrada: EntradaMoto,
    con_ficha: bool = Query(True, description="Aplica los campos publicados de la ficha"),
) -> srv.CalculoMoto:
    srv.obtener_ficha(moto_id)  # 404 si la ficha no existe
    return srv.calcular(moto_id if con_ficha else None, entrada)
