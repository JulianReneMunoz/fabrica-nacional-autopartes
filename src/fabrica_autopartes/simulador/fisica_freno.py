"""Cálculo simplificado del freno de disco (simulación física, separada de la animación).

Fórmulas estándar de un freno de disco con pinza flotante y dinámica de un cuarto de vehículo
(textos de diseño de elementos de máquinas y de dinámica vehicular):

* Área del pistón:            A = π·d² / 4
* Fuerza del pistón:          F = p · A                         (p en Pa)
* Sujeción por pastilla:      F (pinza flotante: acción en el pistón, reacción en los dedos)
* Fricción total en el disco: F_f = 2 · μ · F                    (dos caras)
* Par de frenado:             T = F_f · r_e
* Inercia equivalente:        I_eq = I_rueda + m_¼ · R²          (cuarto de vehículo, sin deslizamiento)
* Deceleración angular:       α = T / I_eq ;  lineal a = α · R
* Bloqueo de rueda:           a > g · μ_neumático  →  la rueda deslizaría (modelo sin ABS)
* Detención:                  t = v / a ;  d = v² / (2·a)

Los parámetros por defecto (μ, masas, inercias, adherencia) son DEMOSTRATIVOS. La animación
del visualizador reproduce estos números, pero no valida propiedades mecánicas reales.
"""

from __future__ import annotations

import math

from pydantic import BaseModel, Field

BAR_A_PA = 1e5
G = 9.80665


class EntradaFreno(BaseModel):
    presion_bar: float = Field(25.0, ge=0.0, le=200.0, description="Presión hidráulica en la pinza")
    diametro_piston_m: float = Field(0.054, ge=0.03, le=0.075)
    coeficiente_friccion: float = Field(0.40, ge=0.10, le=0.70, description="μ pastilla-disco")
    radio_efectivo_m: float = Field(0.115, ge=0.07, le=0.20)
    velocidad_kmh: float = Field(60.0, ge=0.0, le=200.0)
    radio_neumatico_m: float = Field(0.30, ge=0.20, le=0.50)
    masa_cuarto_vehiculo_kg: float = Field(300.0, ge=50.0, le=2000.0)
    inercia_rueda_kg_m2: float = Field(1.2, gt=0.05, le=10.0)
    adherencia_neumatico: float = Field(0.9, ge=0.1, le=1.2, description="μ neumático-calzada")


class ResultadoFreno(BaseModel):
    area_piston_m2: float
    fuerza_piston_n: float
    fuerza_sujecion_por_pastilla_n: float
    fuerza_friccion_total_n: float
    par_frenado_nm: float
    inercia_equivalente_kg_m2: float
    deceleracion_rad_s2: float
    deceleracion_m_s2: float
    deceleracion_g: float
    rueda_bloqueada: bool
    tiempo_detencion_s: float | None
    distancia_detencion_m: float | None
    rpm_inicial: float
    procedencia: str = "Fórmulas estándar; parámetros demostrativos"


def calcular(e: EntradaFreno) -> ResultadoFreno:
    area = math.pi * e.diametro_piston_m**2 / 4
    fuerza = e.presion_bar * BAR_A_PA * area
    friccion = 2 * e.coeficiente_friccion * fuerza
    par = friccion * e.radio_efectivo_m
    inercia = e.inercia_rueda_kg_m2 + e.masa_cuarto_vehiculo_kg * e.radio_neumatico_m**2
    alfa = par / inercia
    a_freno = alfa * e.radio_neumatico_m
    limite = G * e.adherencia_neumatico
    bloqueada = a_freno > limite
    a = min(a_freno, limite)  # con la rueda bloqueada manda la adherencia del neumático
    v = e.velocidad_kmh / 3.6
    return ResultadoFreno(
        area_piston_m2=round(area, 8),
        fuerza_piston_n=round(fuerza, 3),
        fuerza_sujecion_por_pastilla_n=round(fuerza, 3),
        fuerza_friccion_total_n=round(friccion, 3),
        par_frenado_nm=round(par, 3),
        inercia_equivalente_kg_m2=round(inercia, 4),
        deceleracion_rad_s2=round(alfa, 4),
        deceleracion_m_s2=round(a, 4),
        deceleracion_g=round(a / G, 4),
        rueda_bloqueada=bloqueada,
        tiempo_detencion_s=round(v / a, 4) if a > 0 else None,
        distancia_detencion_m=round(v**2 / (2 * a), 4) if a > 0 else None,
        rpm_inicial=round(v / e.radio_neumatico_m * 60 / (2 * math.pi), 3),
    )
