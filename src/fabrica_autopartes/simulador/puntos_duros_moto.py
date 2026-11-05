"""Puntos duros de la motocicleta de referencia genérica (fuente única de coordenadas).

Todas las piezas de ``catalogo_moto_honda`` se posicionan a partir de estos puntos. Las
proporciones son las de una naked de ~150 cc elegidas como supuesto didáctico (procedencia
``demostrativo``): distancia entre ejes de 1,30 m y altura de sillín de 0,79 m. No corresponden a
un modelo comercial.

Sistema de referencia: X hacia delante, Y hacia arriba (suelo en Y = 0), Z hacia el lado derecho
del conductor. Los puntos 2D se dan como (x, y) en el plano medio (z = 0).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from fabrica_autopartes.simulador.fisica_moto import (
    RADIO_CORONA_M,
    RADIO_PINON_M,
    SUPUESTOS_REFERENCIA,
    radio_llanta_m,
)

Punto2 = tuple[float, float]

MEDIDA_DELANTERA_DEMO = "90/80-17"
ENTRE_EJES_M = 1.30
ALTURA_SILLIN_M = 0.79
LANZAMIENTO_GRADOS = 26.0
INCLINACION_CILINDRO_GRADOS = 15.0
Z_HORQUILLA_M = 0.09
Z_BRAZOS_M = 0.10
Z_CADENA_M = 0.075
RADIO_PASO_PINON_M = RADIO_PINON_M  # los de fisica_moto: 0,03 / 0,09 m (relación 3,0)
RADIO_PASO_CORONA_M = RADIO_CORONA_M
DIENTES_PINON = 14
DIENTES_CORONA = 42


def _radio_trasero_generico() -> float:
    return radio_llanta_m(str(SUPUESTOS_REFERENCIA["medida_llanta_trasera"].valor))


@dataclass(frozen=True)
class PuntosDuros:
    """Coordenadas (m) que definen la geometría base de la motocicleta."""

    radio_trasero: float
    radio_delantero: float
    eje_trasero: Punto2
    eje_delantero: Punto2
    pipa: Punto2  # centro de la pipa de dirección (sobre el eje de la horquilla)
    eje_horquilla: Punto2  # vector unitario hacia abajo (hacia el eje delantero)
    ciguenal: Punto2
    eje_cilindro: Punto2  # vector unitario del cilindro (hacia arriba y adelante)
    normal_cilindro: Punto2  # perpendicular, hacia delante
    pivote_basculante: Punto2
    amortiguador_superior: Punto2
    amortiguador_inferior: Punto2
    soporte_motor_delantero: Punto2
    soporte_motor_inferior: Punto2
    soporte_motor_trasero: Punto2

    def sobre_horquilla(self, s: float) -> Punto2:
        """Punto del eje de la horquilla a ``s`` m de la pipa (positivo hacia la rueda)."""
        return (self.pipa[0] + self.eje_horquilla[0] * s, self.pipa[1] + self.eje_horquilla[1] * s)

    def en_motor(self, t: float, lateral: float = 0.0) -> Punto2:
        """Punto a ``t`` m del cigüeñal sobre el eje del cilindro y ``lateral`` m hacia delante."""
        return (
            self.ciguenal[0] + self.eje_cilindro[0] * t + self.normal_cilindro[0] * lateral,
            self.ciguenal[1] + self.eje_cilindro[1] * t + self.normal_cilindro[1] * lateral,
        )


def calcular_puntos_duros() -> PuntosDuros:
    r_t = _radio_trasero_generico()
    r_d = radio_llanta_m(MEDIDA_DELANTERA_DEMO)
    eje_t = (-0.64, r_t)
    eje_d = (eje_t[0] + ENTRE_EJES_M, r_d)
    lanz = math.radians(LANZAMIENTO_GRADOS)
    u = (math.sin(lanz), -math.cos(lanz))
    pipa_y = 0.74
    pipa = (eje_d[0] - math.tan(lanz) * (pipa_y - r_d), pipa_y)
    inc = math.radians(INCLINACION_CILINDRO_GRADOS)
    ciguenal = (0.10, 0.33)
    return PuntosDuros(
        radio_trasero=r_t,
        radio_delantero=r_d,
        eje_trasero=eje_t,
        eje_delantero=eje_d,
        pipa=pipa,
        eje_horquilla=u,
        ciguenal=ciguenal,
        eje_cilindro=(math.sin(inc), math.cos(inc)),
        normal_cilindro=(math.cos(inc), -math.sin(inc)),
        pivote_basculante=(-0.26, 0.345),
        amortiguador_superior=(-0.19, 0.685),
        amortiguador_inferior=(-0.45, 0.33),
        soporte_motor_delantero=(0.22, 0.30),
        soporte_motor_inferior=(0.15, 0.205),
        soporte_motor_trasero=(-0.20, 0.275),
    )


PUNTOS = calcular_puntos_duros()


def tabla_puntos_duros() -> list[tuple[str, float, float]]:
    """Filas (nombre, x, y) de los puntos duros, en metros, para informes y manifiesto."""
    p = PUNTOS
    return [
        ("eje_trasero", *p.eje_trasero),
        ("eje_delantero", *p.eje_delantero),
        ("pipa_direccion", *p.pipa),
        ("pivote_basculante", *p.pivote_basculante),
        ("ciguenal", *p.ciguenal),
        ("amortiguador_superior", *p.amortiguador_superior),
        ("amortiguador_inferior", *p.amortiguador_inferior),
        ("soporte_motor_delantero", *p.soporte_motor_delantero),
        ("soporte_motor_inferior", *p.soporte_motor_inferior),
        ("soporte_motor_trasero", *p.soporte_motor_trasero),
    ]
