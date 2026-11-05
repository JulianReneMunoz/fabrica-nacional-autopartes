"""Servicio del simulador 3D: catálogo de ensamblajes, validación, estados, eventos y la
integración con el asistente (preguntas sobre piezas).

Regla de veracidad: cada respuesta separa
* **modelo**: características del modelo de demostración (geometría y valores demostrativos);
* **documentado**: fragmentos de la base de conocimiento obtenida por scraping, con su URL.
Nunca se generan procedimientos de reparación ni de seguridad crítica.
"""

from __future__ import annotations

import re
import unicodedata
from functools import lru_cache
from typing import Literal

from pydantic import BaseModel, Field

from fabrica_autopartes.core.excepciones import ErrorRecursoNoEncontrado
from fabrica_autopartes.knowledge.base import BaseConocimiento
from fabrica_autopartes.repositories.auditoria import RepositorioAuditoria
from fabrica_autopartes.simulador import cinematica as cin
from fabrica_autopartes.simulador.catalogo_freno import construir_freno
from fabrica_autopartes.simulador.catalogo_moto_honda import construir_moto
from fabrica_autopartes.simulador.modelos import Ensamblaje, Pieza, TipoArticulacion

Intencion = Literal[
    "funcion", "conjunto", "relacionadas", "movimiento", "retirar", "documentacion", "seguridad", "general"
]

MENSAJE_SEGURIDAD = (
    "No se generan procedimientos de reparación, montaje en vehículo ni instrucciones de seguridad "
    "a partir del modelo de demostración: requieren el manual técnico del fabricante y personal "
    "calificado. El simulador solo ilustra la relación entre piezas."
)

_PATRONES: list[tuple[Intencion, str]] = [
    (
        "seguridad",
        r"repar|reemplaz|cambiar|torque|apriete|purg|mantenimiento|instalar|procedimiento|"
        r"seguro|seguridad|especificaci[oó]n de taller",
    ),
    ("retirar", r"retir|desmont|quitar|primero|antes de"),
    ("movimiento", r"movimiento|mueve|gira|desliza|articulaci|recorrido|carrera"),
    ("relacionadas", r"relacionad|conect|componentes|vecin|contacto con"),
    ("conjunto", r"conjunto|pertenece|subconjunto|grupo"),
    ("documentacion", r"document|ficha|fanalca|fabric|cat[aá]logo|fuente|planta"),
    ("funcion", r"funci[oó]n|sirve|para qu[eé]|hace"),
]


def _sin_tildes(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", texto.lower()) if unicodedata.category(c) != "Mn")


def clasificar(pregunta: str) -> Intencion:
    t = _sin_tildes(pregunta)
    for intencion, patron in _PATRONES:
        if re.search(_sin_tildes(patron), t):
            return intencion
    return "general"


class FuenteDocumentada(BaseModel):
    fragmento_id: str
    url: str
    texto: str
    origen: str


class RespuestaPieza(BaseModel):
    pieza_id: str
    pregunta: str
    intencion: Intencion
    respuesta_modelo: str = Field(description="Características del modelo de demostración")
    documentado: list[FuenteDocumentada] = Field(default_factory=list)
    advertencia: str


@lru_cache(maxsize=1)
def catalogo() -> dict[str, Ensamblaje]:
    return {"freno_disco": construir_freno(), "moto_honda": construir_moto()}


def obtener_ensamblaje(ens_id: str) -> Ensamblaje:
    try:
        return catalogo()[ens_id]
    except KeyError as exc:
        raise ErrorRecursoNoEncontrado(f"No existe el ensamblaje '{ens_id}'") from exc


def obtener_pieza(ens: Ensamblaje, pieza_id: str) -> Pieza:
    try:
        return ens.pieza(pieza_id)
    except KeyError as exc:
        raise ErrorRecursoNoEncontrado(f"No existe la pieza '{pieza_id}' en '{ens.id}'") from exc


def _describir_movimiento(ens: Ensamblaje, pieza_id: str) -> str:
    partes = []
    for a in ens.articulaciones:
        if a.hijo != pieza_id:
            continue
        if a.tipo == TipoArticulacion.FIJA:
            partes.append(
                f"está fija ({a.nombre}); no tiene movimiento propio respecto a "
                f"{'la mangueta' if a.padre is None else ens.pieza(a.padre).nombre}"
            )
        elif a.tipo == TipoArticulacion.COMPUESTA:
            maestra = ens.articulacion(a.maestra or "")
            partes.append(
                f"se mueve arrastrada por «{maestra.nombre}» con relación {a.relacion} "
                f"(articulación compuesta, eje {a.eje})"
            )
        else:
            limites = (
                "sin límite (giro continuo)"
                if a.continua or a.limites is None
                else f"entre {a.limites.minimo} y {a.limites.maximo} {a.unidad}"
            )
            partes.append(
                f"articulación {a.tipo} «{a.nombre}» sobre el eje {a.eje}, {limites}; "
                f"valores {a.procedencia}s"
            )
    return "; ".join(partes) if partes else "sin articulaciones definidas"


def responder_pieza(
    ens: Ensamblaje, pieza_id: str, pregunta: str, base: BaseConocimiento | None
) -> RespuestaPieza:
    pieza = obtener_pieza(ens, pieza_id)
    intencion = clasificar(pregunta)
    sub = next(s for s in ens.subconjuntos if s.id == pieza.subconjunto)
    if intencion == "seguridad":
        texto = MENSAJE_SEGURIDAD
    elif intencion == "funcion":
        texto = f"{pieza.nombre}: {pieza.funcion} {pieza.descripcion}"
    elif intencion == "conjunto":
        texto = (
            f"{pieza.nombre} pertenece al subconjunto «{sub.nombre}» ({sub.descripcion}) "
            f"del ensamblaje «{ens.nombre}»."
        )
    elif intencion == "relacionadas":
        nombres = [ens.pieza(r).nombre for r in pieza.relacionadas]
        texto = f"{pieza.nombre} se relaciona con: {', '.join(nombres) or 'ninguna pieza'}."
    elif intencion == "movimiento":
        texto = f"{pieza.nombre} {_describir_movimiento(ens, pieza_id)}."
    elif intencion == "retirar":
        previas = [ens.pieza(r).nombre for r in cin.que_retirar_primero(ens, pieza_id)]
        texto = (
            f"En el modelo, antes de retirar {pieza.nombre} se retiran, en orden: {', '.join(previas)}."
            if previas
            else f"En el modelo, {pieza.nombre} puede retirarse sin desmontar otras piezas."
        )
    else:
        texto = (
            f"{pieza.nombre} ({pieza.tipo}, subconjunto «{sub.nombre}»). Función: {pieza.funcion} "
            f"Material {pieza.material or 'no definido'}. Movimiento: {_describir_movimiento(ens, pieza_id)}."
        )
    documentado: list[FuenteDocumentada] = []
    if base is not None and base.fragmentos and intencion != "seguridad":
        consulta = f"{pieza.nombre} {pieza.tipo} autopartes partes metálicas chasis {pregunta}"
        for r in base.buscar(consulta, k=2):
            documentado.append(
                FuenteDocumentada(
                    fragmento_id=r.fragmento.id,
                    url=r.fragmento.url,
                    texto=r.fragmento.texto[:400],
                    origen=r.fragmento.origen,
                )
            )
    advertencia = (
        f"{ens.advertencia} Referencia de la pieza: {pieza.referencia_documental}. "
        "La sección 'documentado' proviene de la base de conocimiento (sitios oficiales) y puede no "
        "referirse a esta pieza en particular."
    )
    return RespuestaPieza(
        pieza_id=pieza_id,
        pregunta=pregunta,
        intencion=intencion,
        respuesta_modelo=texto,
        documentado=documentado,
        advertencia=advertencia,
    )


class ServicioSimulador:
    def __init__(self, base: BaseConocimiento, repo: RepositorioAuditoria) -> None:
        self.base = base
        self.repo = repo

    def preguntar(self, ens_id: str, pieza_id: str, pregunta: str) -> RespuestaPieza:
        ens = obtener_ensamblaje(ens_id)
        r = responder_pieza(ens, pieza_id, pregunta, self.base)
        self.repo.registrar_evento(
            ens_id, "pregunta", pieza_id, {"pregunta": pregunta, "intencion": r.intencion}
        )
        return r
