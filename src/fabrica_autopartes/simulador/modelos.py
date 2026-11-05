"""Modelo de componentes mecánicos, articulaciones y ensamblajes (versión 2.0).

Unidades: metros, grados para rotaciones de articulaciones y radianes solo en cálculos
internos. Eje del sistema de referencia: Y hacia arriba (convención glTF); el eje de la
rueda del caso de demostración es Z.

Toda magnitud lleva su procedencia: ``especificacion`` (dato verificable con fuente) o
``demostrativo`` (valor elegido para el modelo didáctico). El modelo NO es un diseño
industrial certificado.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

Vector3 = tuple[float, float, float]
Procedencia = Literal["especificacion", "demostrativo"]


class TipoArticulacion(StrEnum):
    FIJA = "fija"
    ROTACIONAL = "rotacional"
    PRISMATICA = "prismatica"
    ESFERICA = "esferica"
    COMPUESTA = "compuesta"


class Transformacion(BaseModel):
    """Posición (m) y rotación de Euler XYZ (grados) respecto al sistema del ensamblaje."""

    posicion: Vector3 = (0.0, 0.0, 0.0)
    rotacion_grados: Vector3 = (0.0, 0.0, 0.0)


class Geometria(BaseModel):
    primitiva: Literal[
        "cilindro",
        "anillo",
        "caja",
        "pinza",
        "tornillo",
        "disco_ventilado",
        "cubo",
        "toro",
        "elipsoide",
        "manivela",
        "cadena",
        "cilindro_corte",
        "revolucion",
        "tubo",
        "extrusion",
        "engranaje",
        "rin_rayos",
    ]
    parametros: dict[str, float]
    nodo_glb: str

    @field_validator("parametros")
    @classmethod
    def _positivos(cls, v: dict[str, float]) -> dict[str, float]:
        for k, valor in v.items():
            if k.startswith(("n_", "lados", "c_")):  # contadores y coordenadas con signo
                continue
            if valor <= 0:
                raise ValueError(f"El parámetro geométrico '{k}' debe ser positivo (valor={valor})")
        return v


class Pieza(BaseModel):
    id: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    nombre: str
    tipo: str
    descripcion: str
    funcion: str
    material: str | None = None
    dimensiones_m: dict[str, float]
    geometria: Geometria
    transformacion: Transformacion
    ancla: Vector3
    subconjunto: str
    relacionadas: list[str] = Field(default_factory=list)
    articulaciones: list[str] = Field(default_factory=list)
    direccion_despiece: Vector3
    distancia_despiece_m: float = Field(gt=0, le=1.0)
    retirar_antes: list[str] = Field(
        default_factory=list, description="Piezas que deben retirarse antes que esta"
    )
    visible: bool = True
    metadatos: dict[str, str] = Field(default_factory=dict)
    referencia_documental: str


class LimitesMovimiento(BaseModel):
    minimo: float
    maximo: float

    @model_validator(mode="after")
    def _orden(self) -> LimitesMovimiento:
        if self.minimo > self.maximo:
            raise ValueError("El límite mínimo no puede superar al máximo")
        return self


class Articulacion(BaseModel):
    id: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    nombre: str
    tipo: TipoArticulacion
    padre: str | None  # None = referencia fija del vehículo (mangueta)
    hijo: str
    eje: Vector3 = (0.0, 0.0, 1.0)
    origen: Vector3 = (0.0, 0.0, 0.0)
    limites: LimitesMovimiento | None = None
    unidad: Literal["grados", "m", "-"] = "-"
    valor_inicial: float = 0.0
    continua: bool = False
    procedencia: Procedencia = "demostrativo"
    descripcion: str = ""
    # Articulaciones compuestas: relación de transmisión simplificada hijo = k·valor_maestra
    maestra: str | None = None
    relacion: float | None = None

    @model_validator(mode="after")
    def _coherencia(self) -> Articulacion:
        if self.tipo in (TipoArticulacion.ROTACIONAL, TipoArticulacion.PRISMATICA):
            norma = sum(c * c for c in self.eje) ** 0.5
            if abs(norma - 1.0) > 1e-6:
                raise ValueError(f"El eje de '{self.id}' debe ser unitario (norma={norma:.4f})")
            if not self.continua and self.limites is None:
                raise ValueError(f"La articulación '{self.id}' requiere límites o continua=True")
        if self.tipo == TipoArticulacion.COMPUESTA and (self.maestra is None or self.relacion is None):
            raise ValueError("Una articulación compuesta requiere 'maestra' y 'relacion'")
        return self


class Subconjunto(BaseModel):
    id: str
    nombre: str
    padre: str | None
    descripcion: str


class Ensamblaje(BaseModel):
    id: str
    nombre: str
    descripcion: str
    version: str
    advertencia: str
    subconjuntos: list[Subconjunto]
    piezas: list[Pieza]
    articulaciones: list[Articulacion]
    archivo_glb: str
    parametros: dict[str, float]
    procedencia_parametros: dict[str, Procedencia]

    def pieza(self, pieza_id: str) -> Pieza:
        for p in self.piezas:
            if p.id == pieza_id:
                return p
        raise KeyError(pieza_id)

    def articulacion(self, art_id: str) -> Articulacion:
        for a in self.articulaciones:
            if a.id == art_id:
                return a
        raise KeyError(art_id)


class NodoJerarquia(BaseModel):
    id: str
    nombre: str
    tipo: Literal["ensamblaje", "subconjunto", "pieza"]
    hijos: list[NodoJerarquia] = Field(default_factory=list)
