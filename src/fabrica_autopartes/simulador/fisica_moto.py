"""Cálculo simplificado de la motocicleta (física separada de la animación).

Relaciones (textos de dinámica vehicular y de máquinas alternativas):

* Diámetro de llanta ``ancho/perfil-rin``:  D = rin·25,4 + 2·ancho·perfil/100   (mm)
* Velocidad:        v [km/h] = rpm · 2π·R · 60 / (1000 · i_primaria · i_marcha · i_final)
* Cilindrada:       V = π/4 · D² · carrera
* Biela-manivela:   x(θ) = r·cos θ + √(L² − r²·sin² θ),  r = carrera/2   (θ = 0 en el PMS)
* Ciclo de 4 tiempos: 720° de cigüeñal (admisión, compresión, expansión, escape)
* Frenado:          se reutiliza ``fisica_freno.calcular`` por disco. Con CBS, la palanca trasera
  reparte la presión entre ambos discos con una proporción de supuesto didáctico.

Solo la lámina CB-160 (STD/DLX) aportada por el usuario respalda datos de la ficha; todo valor
necesario para la simulación que no está publicado se declara aquí como ``supuesto``
(«supuesto didáctico») y se muestra como tal en la interfaz. La geometría y la animación no
validan propiedades mecánicas.
"""

from __future__ import annotations

import math
import re
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from fabrica_autopartes.simulador.fisica_freno import EntradaFreno, ResultadoFreno, calcular

ID_MOTO = "moto_honda"
FASES_CICLO = ("admision", "compresion", "expansion", "escape")


class SupuestoDidactico(BaseModel):
    clave: str
    valor: float | list[float] | str
    unidad: str
    descripcion: str
    estado: Literal["supuesto"] = "supuesto"
    etiqueta: str = "supuesto didáctico"


def _s(clave: str, valor: float | list[float] | str, unidad: str, descripcion: str) -> SupuestoDidactico:
    return SupuestoDidactico(clave=clave, valor=valor, unidad=unidad, descripcion=descripcion)


SUPUESTOS_REFERENCIA: dict[str, SupuestoDidactico] = {
    s.clave: s
    for s in (
        _s(
            "cilindrada_nominal_cm3",
            150.0,
            "cm3",
            "Cilindrada de referencia tomada del nombre comercial; no consta en la lámina.",
        ),
        _s(
            "diametro_mm",
            57.0,
            "mm",
            "Diámetro del cilindro típico de la categoría (valor típico de la categoría).",
        ),
        _s("carrera_mm", 58.7, "mm", "Carrera típico de la categoría (valor típico de la categoría)."),
        _s(
            "longitud_biela_mm",
            105.0,
            "mm",
            "Distancia entre centros de la biela típico de la categoría (valor típico de la categoría).",
        ),
        _s(
            "medida_llanta_trasera",
            "130/70-17",
            "ancho/perfil-rin",
            "Medida de llanta trasera típica de la categoría.",
        ),
        _s("ralenti_rpm", 1400.0, "rpm", "Régimen de ralentí típico de la categoría."),
        _s(
            "corte_encendido_rpm",
            9500.0,
            "rpm",
            "Régimen de corte del limitador típico de la categoría (valor típico de la categoría).",
        ),
        _s("n_marchas", 5.0, "-", "Número de marchas típico de la categoría (valor típico de la categoría)."),
        _s(
            "relacion_primaria",
            3.35,
            "-",
            "Relación primaria típico de la categoría (valor típico de la categoría).",
        ),
        _s(
            "relaciones_marcha",
            [2.80, 1.90, 1.40, 1.10, 0.95],
            "-",
            "Relaciones de caja típico de la categoría (no publicadas).",
        ),
        _s(
            "relacion_final",
            3.0,
            "-",
            "Transmisión final típico de la categoría: corona 42 / piñón 14 (valor típico de la categoría).",
        ),
        _s(
            "presion_bar_por_newton",
            0.30,
            "bar/N",
            "Presión hidráulica por newton aplicado en la palanca (ejemplo).",
        ),
        _s(
            "reparto_cbs_delantero",
            0.40,
            "-",
            "Fracción de la presión que el CBS envía al disco delantero con la palanca trasera.",
        ),
        _s("coeficiente_friccion", 0.40, "-", "μ pastilla-disco típico de la categoría."),
        _s("adherencia_neumatico", 0.90, "-", "μ neumático-calzada típico de la categoría."),
        _s("diametro_piston_m", 0.030, "m", "Diámetro del pistón de pinza típico de la categoría."),
        _s("radio_efectivo_m", 0.10, "m", "Radio efectivo del disco típico de la categoría."),
        _s(
            "masa_por_rueda_kg",
            120.0,
            "kg",
            "Masa equivalente por rueda (moto y conductor) típico de la categoría.",
        ),
        _s("inercia_rueda_kg_m2", 0.9, "kg·m2", "Inercia de la rueda típico de la categoría."),
    )
}

MEDIDA_TRASERA_CB160F = "140/70-17"  # publicado en la lámina CB-160 (STD/DLX); solo con «Ver con ficha de…»
_PATRON_MEDIDA = re.compile(r"^(\d{2,3})/(\d{2})-(\d{2})$")


def _v(clave: str) -> float:
    valor = SUPUESTOS_REFERENCIA[clave].valor
    assert isinstance(valor, float)
    return valor


def parsear_medida_llanta(medida: str) -> tuple[int, int, int]:
    """Devuelve (ancho mm, perfil %, rin pulgadas) de una medida ``ancho/perfil-rin``."""
    m = _PATRON_MEDIDA.match(medida.strip())
    if m is None:
        raise ValueError(f"Medida de llanta inválida: '{medida}' (formato ancho/perfil-rin)")
    return int(m.group(1)), int(m.group(2)), int(m.group(3))


def diametro_llanta_mm(medida: str) -> float:
    ancho, perfil, rin = parsear_medida_llanta(medida)
    return rin * 25.4 + 2 * ancho * perfil / 100


def radio_llanta_m(medida: str) -> float:
    return diametro_llanta_mm(medida) / 2000


def relacion_total(primaria: float, marcha: float, final: float) -> float:
    return primaria * marcha * final


def velocidad_kmh(rpm: float, radio_m: float, primaria: float, marcha: float, final: float) -> float:
    return rpm * 2 * math.pi * radio_m * 60 / (1000 * relacion_total(primaria, marcha, final))


def cilindrada_cm3(diametro_mm: float, carrera_mm: float) -> float:
    return math.pi / 4 * diametro_mm**2 * carrera_mm / 1000


def posicion_piston_m(theta_rad: float, carrera_m: float, biela_m: float) -> float:
    """Distancia eje del cigüeñal–bulón del pistón; máxima (PMS) en θ = 0, mínima (PMI) en θ = π."""
    r = carrera_m / 2
    return r * math.cos(theta_rad) + math.sqrt(biela_m**2 - (r * math.sin(theta_rad)) ** 2)


def fase_ciclo(theta_720_grados: float) -> str:
    return FASES_CICLO[int((theta_720_grados % 720) // 180)]


class EntradaMoto(BaseModel):
    version: Literal["STD", "DLX"] = "DLX"
    rpm: float = Field(1400.0, ge=0.0, le=20000.0)
    marcha: int = Field(0, ge=0, le=6, description="0 = neutro")
    palanca: Literal["delantera", "trasera"] = "delantera"
    fuerza_palanca_n: float = Field(0.0, ge=0.0, le=600.0)
    cbs: bool = False
    velocidad_inicial_kmh: float | None = Field(None, ge=0.0, le=200.0)

    @model_validator(mode="after")
    def _coherente(self) -> EntradaMoto:
        if self.cbs and self.version == "STD":
            raise ValueError("La versión STD no tiene CBS según la lámina; use la versión DLX")
        if self.marcha > int(_v("n_marchas")):
            raise ValueError(f"La marcha {self.marcha} no existe (máximo {int(_v('n_marchas'))})")
        return self


class ResultadoMoto(BaseModel):
    radio_llanta_m: float
    medida_llanta: str
    relacion_total: float | None
    rpm_efectivas: float
    estado_motor: Literal["normal", "limitador", "ahogado", "neutro"]
    velocidad_kmh: float
    angulo_fase: str
    cilindrada_calculada_cm3: float
    cilindrada_referencia_cm3: float
    diferencia_cilindrada_pct: float
    freno_delantero: ResultadoFreno | None
    freno_trasero: ResultadoFreno | None
    fuerza_pistones_total_n: float
    rueda_delantera_bloqueada: bool
    rueda_trasera_bloqueada: bool
    supuestos: list[str]
    advertencia: str = (
        "Cálculo didáctico: los valores marcados como supuesto no provienen de la ficha oficial; "
        "no validan propiedades mecánicas."
    )


def _freno(presion_bar: float, velocidad_kmh_: float, radio_m: float) -> ResultadoFreno:
    return calcular(
        EntradaFreno(
            presion_bar=min(presion_bar, 200.0),
            diametro_piston_m=_v("diametro_piston_m"),
            coeficiente_friccion=_v("coeficiente_friccion"),
            adherencia_neumatico=_v("adherencia_neumatico"),
            radio_efectivo_m=_v("radio_efectivo_m"),
            velocidad_kmh=min(velocidad_kmh_, 200.0),
            radio_neumatico_m=radio_m,
            masa_cuarto_vehiculo_kg=_v("masa_por_rueda_kg"),
            inercia_rueda_kg_m2=_v("inercia_rueda_kg_m2"),
        )
    )


def repartir_presion(e: EntradaMoto, presion_total_bar: float) -> tuple[float, float]:
    """Presión (delantera, trasera) según palanca y CBS. La suma se conserva con CBS."""
    if e.palanca == "delantera":
        return presion_total_bar, 0.0
    if e.cbs:
        f = _v("reparto_cbs_delantero")
        return presion_total_bar * f, presion_total_bar * (1 - f)
    return 0.0, presion_total_bar


def calcular_moto(e: EntradaMoto, medida_llanta: str | None = None) -> ResultadoMoto:
    if medida_llanta is None:
        medida_llanta = str(SUPUESTOS_REFERENCIA["medida_llanta_trasera"].valor)
    radio = radio_llanta_m(medida_llanta)
    ralenti, corte = _v("ralenti_rpm"), _v("corte_encendido_rpm")
    rpm = e.rpm
    estado: Literal["normal", "limitador", "ahogado", "neutro"] = "normal"
    if rpm > corte:
        rpm, estado = corte, "limitador"
    if e.marcha >= 1 and e.rpm < ralenti:
        estado = "ahogado"
    ratio: float | None = None
    v = 0.0
    if e.marcha == 0:
        estado = "limitador" if estado == "limitador" else "neutro"
    elif estado != "ahogado":
        marchas = SUPUESTOS_REFERENCIA["relaciones_marcha"].valor
        assert isinstance(marchas, list)
        ratio = relacion_total(_v("relacion_primaria"), marchas[e.marcha - 1], _v("relacion_final"))
        v = velocidad_kmh(rpm, radio, _v("relacion_primaria"), marchas[e.marcha - 1], _v("relacion_final"))
    v_frenado = e.velocidad_inicial_kmh if e.velocidad_inicial_kmh is not None else v
    p_total = e.fuerza_palanca_n * _v("presion_bar_por_newton")
    p_del, p_tras = repartir_presion(e, p_total)
    f_del = _freno(p_del, v_frenado, radio) if p_del > 0 else None
    f_tras = _freno(p_tras, v_frenado, radio) if p_tras > 0 else None
    total = sum(f.fuerza_piston_n for f in (f_del, f_tras) if f is not None)
    nominal = _v("cilindrada_nominal_cm3")
    calculada = cilindrada_cm3(_v("diametro_mm"), _v("carrera_mm"))
    return ResultadoMoto(
        radio_llanta_m=round(radio, 5),
        medida_llanta=medida_llanta,
        relacion_total=None if ratio is None else round(ratio, 4),
        rpm_efectivas=round(rpm, 3),
        estado_motor=estado,
        velocidad_kmh=round(v, 3),
        angulo_fase="n/a",
        cilindrada_calculada_cm3=round(calculada, 3),
        cilindrada_referencia_cm3=nominal,
        diferencia_cilindrada_pct=round((calculada - nominal) / nominal * 100, 3),
        freno_delantero=f_del,
        freno_trasero=f_tras,
        fuerza_pistones_total_n=round(total, 3),
        rueda_delantera_bloqueada=bool(f_del and f_del.rueda_bloqueada),
        rueda_trasera_bloqueada=bool(f_tras and f_tras.rueda_bloqueada),
        supuestos=sorted(SUPUESTOS_REFERENCIA),
    )
