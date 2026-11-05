"""Biblioteca de máquinas interactivas (método Anatomy) alimentada por la base de conocimiento.

Cada máquina responde UNA pregunta con una relación medible. Los textos "datos de la empresa"
se extraen de la base Gold (scraping de los sitios oficiales) con su URL; los parámetros que
mueven la máquina se toman de la base cuando existe el dato (p. ej. capacidad anual de
chasises) y, si no, se marcan como demostrativos.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from pydantic import BaseModel, Field

from fabrica_autopartes.knowledge.base import BaseConocimiento
from fabrica_autopartes.knowledge.recuperacion import tokenizar


class DatoEmpresa(BaseModel):
    texto: str
    url: str
    fragmento_id: str
    origen: str


class Parametro(BaseModel):
    nombre: str
    valor: float
    unidad: str
    procedencia: str  # "base_conocimiento" | "demostrativo"
    fuente: str | None = None


class Maquina(BaseModel):
    id: str
    pregunta: str
    una_linea: str
    relacion: str
    ruta: str
    idea_principal: str
    datos_empresa: list[DatoEmpresa] = Field(default_factory=list)
    parametros: list[Parametro] = Field(default_factory=list)


@dataclass(frozen=True)
class _Definicion:
    id: str
    pregunta: str
    una_linea: str
    relacion: str
    idea_principal: str
    consultas: tuple[str, ...]


DEFINICIONES = (
    _Definicion(
        id="freno",
        pregunta="¿Cómo convierte un freno de disco la presión hidráulica en fuerza de frenado?",
        una_linea="Despiece 3D de una pinza flotante: presión → fuerza → par.",
        relacion="T = 2 · μ · p · A · r",
        idea_principal="La presión empuja un solo pistón; la pinza flotante reacciona y aprieta el disco por "
        "ambas caras, así el par crece con la presión, el área del pistón, μ y el radio.",
        consultas=(
            "partes metálicas automóviles vehículos comerciales chasis",
            "clientes ensambladoras automóviles camiones",
        ),
    ),
    _Definicion(
        id="prensa",
        pregunta="¿Cómo convierte una prensa una lámina de acero en un panel estampado?",
        una_linea="Prensa excéntrica: biela-manivela, tonelaje de corte y límite de la máquina.",
        relacion="F = L · t · τ",
        idea_principal="La fuerza para cortar crece con el perímetro, el espesor y la resistencia del acero; "
        "si supera la capacidad de la prensa, el ciclo no puede completarse.",
        consultas=(
            "paneles estampados",
            "planta Yumbo toneladas partes metálicas",
            "panel interior estampado",
        ),
    ),
    _Definicion(
        id="linea",
        pregunta="¿Cada cuánto debe salir un chasis de la línea de ensamble?",
        una_linea="Línea de soldadura de chasises: tiempo takt y estaciones necesarias.",
        relacion="takt = tiempo disponible / demanda",
        idea_principal="La demanda fija el ritmo: si una estación tarda más que el takt, la cola crece "
        "y la línea no alcanza la capacidad anual.",
        consultas=("Bogotá chasises al año soldadura remachado", "Medellín ensambles al año chasises"),
    ),
    _Definicion(
        id="moto_honda",
        pregunta="¿Cómo convierte una motocicleta Honda el giro del motor en velocidad de la rueda, "
        "y la palanca en fuerza de frenado?",
        una_linea="Motocicleta (referencia genérica) con fichas Honda",
        relacion="v = rpm · 2π · R · 60 / (1000 · i_prim · i_marcha · i_final)",
        idea_principal="La velocidad es el giro del motor dividido por las relaciones de transmisión y "
        "multiplicado por la circunferencia de la llanta; el freno invierte el camino y convierte la fuerza "
        "de la mano en torque sobre la rueda.",
        consultas=(
            "motocicletas Honda ensamble Acopi Yumbo",
            "negocio motocicletas Honda Fanalca",
        ),
    ),
)

_CHASISES = re.compile(r"(\d{1,3}(?:[.\s]\d{3})+|\d+)\s+chasis(?:es)?\s+al\s+año", re.I)


def _mejor_oracion(texto: str, consulta: str) -> str:
    terminos = set(tokenizar(consulta))
    oraciones = [o.strip(" -#") for o in re.split(r"(?<=[.!?])\s+|\n+", texto) if len(o.split()) >= 5]
    if not oraciones:
        return texto[:240]
    return max(oraciones, key=lambda o: len(terminos & set(tokenizar(o))))


def _capacidad_chasises(base: BaseConocimiento) -> Parametro:
    for f in base.fragmentos:
        m = _CHASISES.search(f.texto)
        if m:
            valor = float(re.sub(r"[.\s]", "", m.group(1)))
            return Parametro(
                nombre="capacidad_anual",
                valor=valor,
                unidad="chasises/año",
                procedencia="base_conocimiento",
                fuente=f.url,
            )
    return Parametro(nombre="capacidad_anual", valor=20000, unidad="chasises/año", procedencia="demostrativo")


def construir_biblioteca(base: BaseConocimiento) -> list[Maquina]:
    maquinas = []
    for d in DEFINICIONES:
        datos: list[DatoEmpresa] = []
        vistos: set[str] = set()
        for consulta in d.consultas:
            for r in base.buscar(consulta, k=1):
                if r.fragmento.id in vistos:
                    continue
                vistos.add(r.fragmento.id)
                datos.append(
                    DatoEmpresa(
                        texto=_mejor_oracion(r.fragmento.texto, consulta),
                        url=r.fragmento.url,
                        fragmento_id=r.fragmento.id,
                        origen=r.fragmento.origen,
                    )
                )
        parametros: list[Parametro] = []
        if d.id == "linea":
            parametros.append(_capacidad_chasises(base))
        maquinas.append(
            Maquina(
                id=d.id,
                pregunta=d.pregunta,
                una_linea=d.una_linea,
                relacion=d.relacion,
                ruta=f"#/maquina/{d.id}",
                idea_principal=d.idea_principal,
                datos_empresa=datos,
                parametros=parametros,
            )
        )
    return maquinas
