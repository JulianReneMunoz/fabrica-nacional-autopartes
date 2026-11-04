"""Consulta de la base de conocimiento (solo lectura)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from fabrica_autopartes.api.dependencias import obtener_servicio
from fabrica_autopartes.api.esquemas import FragmentoBuscado, Pagina
from fabrica_autopartes.domain.modelos import EstadisticasBase, Fragmento
from fabrica_autopartes.services.asistente import ServicioAsistente

router = APIRouter(prefix="/api/v1/base", tags=["Base de conocimiento"])


@router.get("/estadisticas", response_model=EstadisticasBase, summary="Estadísticas del corpus Gold")
def estadisticas(servicio: ServicioAsistente = Depends(obtener_servicio)) -> EstadisticasBase:
    return servicio.base.estadisticas()


@router.get("/fragmentos", response_model=Pagina[FragmentoBuscado], summary="Listar o buscar fragmentos")
def listar(
    q: str | None = Query(None, description="Consulta BM25; si se omite se lista en orden"),
    seccion: str | None = Query(None, examples=["negocios"]),
    pagina: int = Query(1, ge=1),
    tamano: int = Query(10, ge=1, le=100),
    servicio: ServicioAsistente = Depends(obtener_servicio),
) -> Pagina[FragmentoBuscado]:
    if q:
        resultados = servicio.base.buscar(q, k=200)
        elementos = [
            FragmentoBuscado(fragmento=r.fragmento, puntaje=r.puntaje)
            for r in resultados
            if not seccion or r.fragmento.seccion.startswith(seccion)
        ]
    else:
        elementos = [FragmentoBuscado(fragmento=f) for f in servicio.base.filtrar(seccion=seccion)]
    inicio = (pagina - 1) * tamano
    return Pagina(
        elementos=elementos[inicio : inicio + tamano], total=len(elementos), pagina=pagina, tamano=tamano
    )


@router.get("/fragmentos/{fragmento_id:path}", response_model=Fragmento, summary="Obtener un fragmento")
def obtener(fragmento_id: str, servicio: ServicioAsistente = Depends(obtener_servicio)) -> Fragmento:
    return servicio.base.obtener(fragmento_id)
