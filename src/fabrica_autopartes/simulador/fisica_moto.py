"""Cálculo simplificado de la motocicleta (física separada de la animación).

Relaciones (textos de dinámica vehicular y de máquinas alternativas):

* Diámetro de llanta ``ancho/perfil-rin``:  D = rin·25,4 + 2·ancho·perfil/100   (mm)
* Velocidad:        v [km/h] = rpm · 2π·R · 60 / (1000 · i_primaria · i_marcha · i_final)
* Cilindrada:       V = π/4 · D² · carrera
* Biela-manivela:   x(θ) = r·cos θ + √(L² − r²·sin² θ),  r = carrera/2   (θ = 0 en el PMS)
* Dinámica (``paso_moto``): la velocidad es una variable de estado continua. Con marcha engranada las rpm
  se derivan de ella (rpm = v·i_total·60/(2π·R)); el acelerador da una aceleración a = k·acelerador (limitada
  por el corte), el freno una deceleración tomada de ``fisica_freno.calcular`` y en neutro la velocidad decae
  por rozamiento. Todos los parámetros de la dinámica son «supuesto didáctico».
* Ángulo de biela:  φ(θ) = asin(r·sin θ / L)   (inclinación de la biela respecto al eje del cilindro)
* Cadena:           v_cadena = ω_piñón·r_piñón = ω_corona·r_corona,  ω_piñón = ω_motor / (i_primaria·i_marcha)
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

from pydantic import BaseModel, ConfigDict, Field, model_validator

from fabrica_autopartes.simulador.fisica_freno import EntradaFreno, ResultadoFreno, calcular

ID_MOTO = "moto_honda"
EstadoMotor = Literal["normal", "limitador", "ahogado", "neutro", "patinaje", "embrague"]
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
            "Cilindrada nominal de referencia, típica de la categoría; no tomada de un nombre comercial.",
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
        _s(
            "medida_llanta_delantera",
            "90/80-17",
            "ancho/perfil-rin",
            "Medida de llanta delantera típica de la categoría (la lámina no la publica).",
        ),
        _s(
            "aceleracion_max_m_s2",
            3.0,
            "m/s2",
            "Aceleración con el acelerador a fondo: a = k·acelerador (dinámica simplificada).",
        ),
        _s(
            "rozamiento_m_s2",
            0.5,
            "m/s2",
            "Deceleración constante por rodadura (neutro y marcha sin acelerar).",
        ),
        _s("arrastre_aero_1_m", 0.0023, "1/m", "Coeficiente del arrastre aerodinámico: a = c·v²."),
        _s(
            "tau_rpm_libre_s",
            0.25,
            "s",
            "Constante de tiempo con que las rpm libres (neutro) siguen al acelerador.",
        ),
        _s(
            "rpm_tope_libre",
            11000.0,
            "rpm",
            "rpm que pediría el acelerador a fondo en neutro (sin limitador).",
        ),
        _s(
            "banda_limitador_rpm",
            100.0,
            "rpm",
            "Banda bajo el corte donde la aceleración se anula progresivamente (limitador suave).",
        ),
        _s(
            "acelerador_minimo_sin_ahogo",
            0.2,
            "-",
            "Acelerador mínimo (0-1) para que el embrague patine sin ahogar en marchas altas.",
        ),
        _s(
            "marcha_minima_ahogo",
            3.0,
            "-",
            "Desde esta marcha, rpm derivadas bajo el ralentí y poco acelerador ahogan el motor; en las "
            "marchas bajas el embrague patina (arranque).",
        ),
    )
}

MEDIDA_DELANTERA_DEMO = str(SUPUESTOS_REFERENCIA["medida_llanta_delantera"].valor)
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


def angulo_biela_rad(theta_rad: float, carrera_m: float, biela_m: float) -> float:
    """Inclinación φ de la biela respecto al eje del cilindro: φ = asin(r·sin θ / L), r = carrera/2."""
    r = carrera_m / 2
    return math.asin(r * math.sin(theta_rad) / biela_m)


# Radios de paso del piñón y la corona (m) del modelo 3D; su cociente es la relación final (42/14 = 3).
RADIO_PINON_M = 0.03
RADIO_CORONA_M = 0.09


def velocidad_angular_rad_s(rpm: float) -> float:
    return rpm * 2 * math.pi / 60


def velocidad_angular_pinon_rad_s(rpm: float, primaria: float, marcha: float) -> float:
    """ω del piñón de salida: el giro del motor dividido por la relación primaria y la de marcha."""
    return velocidad_angular_rad_s(rpm) / (primaria * marcha)


def velocidad_angular_corona_rad_s(rpm: float, primaria: float, marcha: float, final: float) -> float:
    """ω de la corona (igual a la de la rueda trasera): ω del piñón dividida por la relación final."""
    return velocidad_angular_pinon_rad_s(rpm, primaria, marcha) / final


def velocidad_cadena_m_s(
    rpm: float, primaria: float, marcha: float, radio_pinon_m: float = RADIO_PINON_M
) -> float:
    """Velocidad lineal de la cadena en el piñón: v = ω_piñón · r_piñón."""
    return velocidad_angular_pinon_rad_s(rpm, primaria, marcha) * radio_pinon_m


def velocidad_cadena_desde_corona_m_s(
    rpm: float,
    primaria: float,
    marcha: float,
    final: float,
    radio_corona_m: float = RADIO_CORONA_M,
) -> float:
    """Misma velocidad calculada desde la corona (ω_corona · r_corona); coincide con la del piñón."""
    return velocidad_angular_corona_rad_s(rpm, primaria, marcha, final) * radio_corona_m


def fase_ciclo(theta_720_grados: float) -> str:
    return FASES_CICLO[int((theta_720_grados % 720) // 180)]


class EntradaMoto(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False, extra="forbid")

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
    estado_motor: EstadoMotor
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


def repartir_presion(e: EntradaMoto | MandoMoto, presion_total_bar: float) -> tuple[float, float]:
    """Presión (delantera, trasera) según palanca y CBS. La suma se conserva con CBS."""
    if e.palanca == "delantera":
        return presion_total_bar, 0.0
    if e.cbs:
        f = _v("reparto_cbs_delantero")
        return presion_total_bar * f, presion_total_bar * (1 - f)
    return 0.0, presion_total_bar


def _frenos(
    e: EntradaMoto | MandoMoto, v_kmh: float, radio_tras_m: float
) -> tuple[ResultadoFreno | None, ResultadoFreno | None]:
    """Resultados de los discos (delantero, trasero); cada uno con el radio de su propia llanta."""
    radio_del = radio_llanta_m(MEDIDA_DELANTERA_DEMO)
    p_del, p_tras = repartir_presion(e, e.fuerza_palanca_n * _v("presion_bar_por_newton"))
    f_del = _freno(p_del, v_kmh, radio_del) if p_del > 0 else None
    f_tras = _freno(p_tras, v_kmh, radio_tras_m) if p_tras > 0 else None
    return f_del, f_tras


def _medida_trasera(medida_llanta: str | None) -> str:
    return (
        str(SUPUESTOS_REFERENCIA["medida_llanta_trasera"].valor) if medida_llanta is None else medida_llanta
    )


def _componer(
    e: EntradaMoto | MandoMoto,
    medida: str,
    rpm: float,
    estado: EstadoMotor,
    v_kmh: float,
    ratio: float | None,
    v_frenado: float,
) -> ResultadoMoto:
    radio = radio_llanta_m(medida)
    f_del, f_tras = _frenos(e, v_frenado, radio)
    total = sum(f.fuerza_piston_n for f in (f_del, f_tras) if f is not None)
    nominal = _v("cilindrada_nominal_cm3")
    calculada = cilindrada_cm3(_v("diametro_mm"), _v("carrera_mm"))
    return ResultadoMoto(
        radio_llanta_m=round(radio, 5),
        medida_llanta=medida,
        relacion_total=None if ratio is None else round(ratio, 4),
        rpm_efectivas=round(rpm, 3),
        estado_motor=estado,
        velocidad_kmh=round(v_kmh, 3),
        angulo_fase="n/a",
        cilindrada_calculada_cm3=round(calculada, 3),
        cilindrada_referencia_cm3=nominal,
        diferencia_cilindrada_pct=round((calculada - nominal) / nominal * 100, 3),
        freno_delantero=f_del,
        freno_trasero=f_tras,
        fuerza_pistones_total_n=round(total, 3),
        # Sin movimiento no hay bloqueo que informar.
        rueda_delantera_bloqueada=bool(f_del and f_del.rueda_bloqueada and v_frenado > 0),
        rueda_trasera_bloqueada=bool(f_tras and f_tras.rueda_bloqueada and v_frenado > 0),
        supuestos=sorted(SUPUESTOS_REFERENCIA),
    )


def _relacion_marcha(marcha: int) -> float:
    marchas = SUPUESTOS_REFERENCIA["relaciones_marcha"].valor
    assert isinstance(marchas, list)
    return float(marchas[marcha - 1])


def calcular_moto(e: EntradaMoto, medida_llanta: str | None = None) -> ResultadoMoto:
    """Instantánea «de lección»: velocidad desde rpm y marcha (v = rpm·2πR / i_total) con marcha engranada."""
    medida = _medida_trasera(medida_llanta)
    radio = radio_llanta_m(medida)
    ralenti, corte = _v("ralenti_rpm"), _v("corte_encendido_rpm")
    rpm = e.rpm
    estado: EstadoMotor = "normal"
    if rpm > corte:
        rpm, estado = corte, "limitador"
    if e.marcha >= 1 and e.rpm < ralenti:
        estado = "ahogado" if e.marcha >= _v("marcha_minima_ahogo") else "patinaje"
    ratio: float | None = None
    v = 0.0
    if e.marcha == 0:
        estado = "limitador" if estado == "limitador" else "neutro"
    elif estado != "ahogado":
        g = _relacion_marcha(e.marcha)
        ratio = relacion_total(_v("relacion_primaria"), g, _v("relacion_final"))
        v = velocidad_kmh(rpm, radio, _v("relacion_primaria"), g, _v("relacion_final"))
    v_frenado = e.velocidad_inicial_kmh if e.velocidad_inicial_kmh is not None else v
    return _componer(e, medida, rpm, estado, v, ratio, v_frenado)


# ---------------------------------------------------------------------------------------------
# Dinámica: la velocidad es una variable de estado continua (nunca se recalcula de golpe)
# ---------------------------------------------------------------------------------------------


class MandoMoto(BaseModel):
    """Mandos del conductor en un instante (el backend los valida; NaN/Infinity se rechazan)."""

    model_config = ConfigDict(allow_inf_nan=False, extra="forbid")

    version: Literal["STD", "DLX"] = "DLX"
    acelerador: float = Field(0.0, ge=0.0, le=1.0)
    marcha: int = Field(0, ge=0, le=6, description="0 = neutro")
    palanca: Literal["delantera", "trasera"] = "delantera"
    fuerza_palanca_n: float = Field(0.0, ge=0.0, le=600.0)
    cbs: bool = False
    freno: bool = False

    @model_validator(mode="after")
    def _coherente(self) -> MandoMoto:
        if self.cbs and self.version == "STD":
            raise ValueError("La versión STD no tiene CBS según la lámina; use la versión DLX")
        if self.marcha > int(_v("n_marchas")):
            raise ValueError(f"La marcha {self.marcha} no existe (máximo {int(_v('n_marchas'))})")
        return self


class EstadoMoto(BaseModel):
    v_ms: float = Field(0.0, ge=0.0)
    rpm_motor: float = Field(1400.0, ge=0.0)
    modo: EstadoMotor = "neutro"
    t_freno_s: float = Field(0.0, ge=0.0)
    a_ms2: float = 0.0


def rpm_derivadas(v_ms: float, radio_m: float, primaria: float, marcha: float, final: float) -> float:
    """rpm del motor con marcha engranada: rpm = v / R · i_total · 60 / 2π."""
    return v_ms / radio_m * relacion_total(primaria, marcha, final) * 60 / (2 * math.pi)


def velocidad_ms_en_corte(radio_m: float, primaria: float, marcha: float, final: float) -> float:
    return _v("corte_encendido_rpm") * 2 * math.pi / 60 * radio_m / relacion_total(primaria, marcha, final)


def _resistencia(v_ms: float) -> float:
    return _v("rozamiento_m_s2") + _v("arrastre_aero_1_m") * v_ms * v_ms if v_ms > 0 else 0.0


def paso_moto(est: EstadoMoto, mando: MandoMoto, dt: float, medida_llanta: str | None = None) -> EstadoMoto:
    """Avanza ``dt`` segundos. Función pura: la misma lógica vive en ``web/src/modelos/moto.ts``."""
    if not math.isfinite(dt) or dt < 0:
        raise ValueError("dt debe ser finito y no negativo")
    medida = _medida_trasera(medida_llanta)
    radio = radio_llanta_m(medida)
    ralenti, corte = _v("ralenti_rpm"), _v("corte_encendido_rpm")
    prim, final = _v("relacion_primaria"), _v("relacion_final")
    banda = _v("banda_limitador_rpm")
    tau = _v("tau_rpm_libre_s")
    v = max(est.v_ms, 0.0)
    resist = _resistencia(v)
    frenando = mando.freno and mando.fuerza_palanca_n > 0
    k = _v("aceleracion_max_m_s2") * mando.acelerador
    g = _relacion_marcha(mando.marcha) if mando.marcha >= 1 else None
    ahogo = False
    if frenando:
        f_del, f_tras = _frenos(mando, v * 3.6, radio)
        a_fr = (
            (f_del.deceleracion_m_s2 if f_del else 0.0) + (f_tras.deceleracion_m_s2 if f_tras else 0.0)
        ) / 2
        a = -(a_fr + resist)
    elif g is None:
        a = -resist
    else:
        rpm_der = rpm_derivadas(v, radio, prim, g, final)
        ahogo = (
            rpm_der < ralenti
            and mando.marcha >= _v("marcha_minima_ahogo")
            and mando.acelerador < _v("acelerador_minimo_sin_ahogo")
        )
        # Limitador suave: la aceleración se anula al acercarse al corte.
        a_motor = 0.0 if ahogo else k * min(max((corte - rpm_der) / banda, 0.0), 1.0)
        a = a_motor - resist
    v_nueva = v + a * dt
    if v_nueva < 0.0 or (v == 0.0 and a < 0.0):
        v_nueva = 0.0
    if g is not None and not frenando and not ahogo:
        v_nueva = min(v_nueva, velocidad_ms_en_corte(radio, prim, g, final))
    rpm: float
    modo: EstadoMotor
    if frenando:
        modo = "embrague"  # el embrague se acciona al frenar: el motor queda libre
        rpm = est.rpm_motor + (ralenti - est.rpm_motor) * (1 - math.exp(-dt / tau))
    elif g is None:
        objetivo = ralenti + mando.acelerador * (_v("rpm_tope_libre") - ralenti)
        rpm = est.rpm_motor + (objetivo - est.rpm_motor) * (1 - math.exp(-dt / tau))
        modo = "neutro"
        if rpm >= corte - banda and objetivo >= corte - banda:
            rpm, modo = min(rpm, corte), "limitador"
    elif ahogo:
        rpm, modo = 0.0, "ahogado"
    else:
        rpm_nueva = rpm_derivadas(v_nueva, radio, prim, g, final)
        if rpm_nueva >= corte - banda:
            rpm, modo = min(rpm_nueva, corte), "limitador"
        elif rpm_nueva < ralenti:
            rpm, modo = ralenti, "patinaje"  # embrague patinando: la relación de la lección no rige
        else:
            rpm, modo = rpm_nueva, "normal"
    return EstadoMoto(
        v_ms=v_nueva,
        rpm_motor=rpm,
        modo=modo,
        t_freno_s=est.t_freno_s + dt if frenando else 0.0,
        a_ms2=(v_nueva - v) / dt if dt > 0 else 0.0,
    )


def calcular_moto_desde_estado(
    est: EstadoMoto, mando: MandoMoto, medida_llanta: str | None = None
) -> ResultadoMoto:
    """Instantánea derivada del estado dinámico (velocidad y rpm provienen del estado, no de la fórmula)."""
    medida = _medida_trasera(medida_llanta)
    ratio = (
        relacion_total(_v("relacion_primaria"), _relacion_marcha(mando.marcha), _v("relacion_final"))
        if mando.marcha >= 1
        else None
    )
    return _componer(mando, medida, est.rpm_motor, est.modo, est.v_ms * 3.6, ratio, est.v_ms * 3.6)
