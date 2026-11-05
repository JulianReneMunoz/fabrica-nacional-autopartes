"""Dinámica de la motocicleta: la velocidad es una variable de estado continua (nunca salta)."""

from __future__ import annotations

import itertools
import json
import math
from pathlib import Path

import pytest
from pydantic import ValidationError

from fabrica_autopartes.simulador import fisica_moto as fm

S = fm.SUPUESTOS_REFERENCIA
DT = 0.05
PRIM = float(S["relacion_primaria"].valor)  # type: ignore[arg-type]
FINAL = float(S["relacion_final"].valor)  # type: ignore[arg-type]
MARCHAS: list[float] = list(S["relaciones_marcha"].valor)  # type: ignore[arg-type]
RALENTI = float(S["ralenti_rpm"].valor)  # type: ignore[arg-type]
CORTE = float(S["corte_encendido_rpm"].valor)  # type: ignore[arg-type]
K_MAX = float(S["aceleracion_max_m_s2"].valor)  # type: ignore[arg-type]
ADH = float(S["adherencia_neumatico"].valor)  # type: ignore[arg-type]
R = fm.radio_llanta_m(str(S["medida_llanta_trasera"].valor))
REFERENCIA = Path(__file__).resolve().parents[2] / "web" / "src" / "__tests__" / "referencia_moto.json"


def correr(
    est: fm.EstadoMoto, mando: fm.MandoMoto, segundos: float, medida: str | None = None
) -> list[fm.EstadoMoto]:
    pasos = []
    for _ in range(round(segundos / DT)):
        est = fm.paso_moto(est, mando, DT, medida)
        pasos.append(est)
    return pasos


def cota_a(v_ms: float) -> float:
    """Cota de |a| por paso: acelerador a fondo, o freno limitado por la adherencia, más resistencias."""
    return (
        max(K_MAX, 9.80665 * ADH)
        + float(S["rozamiento_m_s2"].valor)
        + float(S["arrastre_aero_1_m"].valor) * v_ms**2
    )  # type: ignore[arg-type]


def test_arranque_desde_cero_con_marcha_engranada_y_relacion_de_la_leccion() -> None:
    est = fm.EstadoMoto(v_ms=0.0, rpm_motor=RALENTI)
    mando = fm.MandoMoto(marcha=1, acelerador=1.0)
    pasos = correr(est, mando, 1.0)
    assert pasos[0].modo == "patinaje" and pasos[0].v_ms > 0  # patinaje de embrague rotulado
    pasos += correr(pasos[-1], mando, 3.0)
    normal = [p for p in pasos if p.modo == "normal"]
    assert normal, "la moto debe salir del patinaje y seguir la relación de la lección"
    for p in normal:
        esperado = p.v_ms / R * PRIM * MARCHAS[0] * FINAL * 60 / (2 * math.pi)
        assert p.rpm_motor == pytest.approx(esperado, rel=1e-9)


def test_cambio_de_marcha_no_salta_la_velocidad_pero_si_las_rpm() -> None:
    est = correr(fm.EstadoMoto(rpm_motor=RALENTI), fm.MandoMoto(marcha=1, acelerador=1.0), 3.0)[-1]
    v0, rpm0 = est.v_ms, est.rpm_motor
    for g in (3, 2, 4):
        nuevo = fm.paso_moto(est, fm.MandoMoto(marcha=g, acelerador=1.0), 0.0)
        assert nuevo.v_ms == est.v_ms  # Δv = 0 exacto en el instante del cambio
        esperado = nuevo.v_ms / R * PRIM * MARCHAS[g - 1] * FINAL * 60 / (2 * math.pi)
        assert nuevo.rpm_motor == pytest.approx(esperado, rel=1e-9)
        assert nuevo.rpm_motor != pytest.approx(rpm0, rel=1e-3)
    assert est.v_ms == v0


def test_neutro_decae_sin_detenerse_en_seco_y_las_rpm_son_libres() -> None:
    est = fm.EstadoMoto(v_ms=15.0, rpm_motor=3000.0)
    pasos = correr(est, fm.MandoMoto(marcha=0, acelerador=0.0), 3.0)
    vs = [15.0] + [p.v_ms for p in pasos]
    assert all(b < a for a, b in itertools.pairwise(vs))  # decrece estrictamente
    assert vs[-1] > 10.0  # sin detenerse en seco (rozamiento supuesto: ~0,5 m/s² + arrastre)
    assert all(abs(b - a) <= cota_a(a) * DT for a, b in itertools.pairwise(vs))
    assert pasos[-1].rpm_motor == pytest.approx(RALENTI, abs=5)  # rpm libres: siguen al acelerador
    acelerado = correr(pasos[-1], fm.MandoMoto(marcha=0, acelerador=0.5), 3.0)[-1]
    assert acelerado.rpm_motor > 5000 and acelerado.modo == "neutro"


def test_frenado_monotono_hasta_detenerse_sin_velocidad_negativa() -> None:
    est = fm.EstadoMoto(v_ms=15.0, rpm_motor=RALENTI)
    mando = fm.MandoMoto(marcha=2, palanca="trasera", fuerza_palanca_n=180, cbs=True, freno=True)
    pasos = correr(est, mando, 10.0)
    vs = [15.0] + [p.v_ms for p in pasos]
    assert all(b <= a for a, b in itertools.pairwise(vs)) and min(vs) == 0.0 and vs[-1] == 0.0
    assert all(v >= 0 for v in vs)
    assert all(p.modo == "embrague" for p in pasos)
    assert all(abs(b - a) <= cota_a(a) * DT for a, b in itertools.pairwise(vs))
    assert pasos[0].t_freno_s == pytest.approx(DT)


def test_bloqueo_manda_la_adherencia() -> None:
    est = fm.EstadoMoto(v_ms=15.0, rpm_motor=RALENTI)
    fuerte = fm.MandoMoto(marcha=3, palanca="delantera", fuerza_palanca_n=600, freno=True)
    p = fm.paso_moto(est, fuerte, 1.0)
    lim = 9.80665 * ADH
    # deceleración media de ambos discos: solo el delantero frena (cae a g·μ) → a_veh = g·μ/2 + resistencias
    assert (15.0 - p.v_ms) == pytest.approx(lim / 2 + fm._resistencia(15.0), abs=1e-3)
    calc = fm.calcular_moto_desde_estado(est, fuerte)
    assert calc.rueda_delantera_bloqueada is True


def test_soltar_el_freno_continua_desde_la_velocidad_actual_y_se_puede_acelerar() -> None:
    est = fm.EstadoMoto(v_ms=15.0, rpm_motor=RALENTI)
    frenando = fm.MandoMoto(marcha=1, palanca="trasera", fuerza_palanca_n=180, cbs=True, freno=True)
    parada = correr(est, frenando, 10.0)[-1]
    assert parada.v_ms == 0.0
    suelto = fm.paso_moto(parada, fm.MandoMoto(marcha=1, acelerador=0.0), DT)
    assert suelto.v_ms == 0.0  # no recupera la velocidad anterior
    de_nuevo = correr(parada, fm.MandoMoto(marcha=1, acelerador=1.0), 3.0)
    assert de_nuevo[0].v_ms <= cota_a(0.0) * DT and de_nuevo[-1].v_ms > 3.0
    # soltar a mitad del frenado: continúa desde la v actual, sin saltos
    media = correr(est, frenando, 1.0)[-1]
    sigue = fm.paso_moto(media, fm.MandoMoto(marcha=1, acelerador=0.0), 0.0)
    assert sigue.v_ms == media.v_ms


def test_limitador_impide_acelerar_mas_alla_del_corte_y_en_neutro_acota_las_rpm() -> None:
    est = fm.EstadoMoto(v_ms=20.0, rpm_motor=8000)
    pasos = correr(est, fm.MandoMoto(marcha=3, acelerador=1.0), 12.0)
    v_corte = fm.velocidad_ms_en_corte(R, PRIM, MARCHAS[2], FINAL)
    assert max(p.v_ms for p in pasos) <= v_corte + 1e-12
    assert pasos[-1].modo == "limitador" and pasos[-1].rpm_motor <= CORTE
    libre = correr(fm.EstadoMoto(rpm_motor=RALENTI), fm.MandoMoto(marcha=0, acelerador=1.0), 3.0)[-1]
    assert libre.modo == "limitador" and libre.rpm_motor == CORTE


def test_ahogo_en_marcha_alta_con_poco_acelerador_y_no_en_marchas_bajas() -> None:
    lenta = fm.EstadoMoto(v_ms=3.0, rpm_motor=RALENTI)
    assert fm.paso_moto(lenta, fm.MandoMoto(marcha=5, acelerador=0.0), DT).modo == "ahogado"
    assert fm.paso_moto(lenta, fm.MandoMoto(marcha=5, acelerador=0.0), DT).rpm_motor == 0.0
    assert fm.paso_moto(lenta, fm.MandoMoto(marcha=1, acelerador=0.0), DT).modo != "ahogado"
    # con acelerador suficiente el embrague patina en vez de ahogar
    assert fm.paso_moto(lenta, fm.MandoMoto(marcha=5, acelerador=0.6), DT).modo == "patinaje"


def test_mando_invalido() -> None:
    for malo in ({"acelerador": 1.5}, {"marcha": 9}, {"version": "STD", "cbs": True}, {"extra": 1}):
        with pytest.raises(ValidationError):
            fm.MandoMoto(**malo)  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        fm.paso_moto(fm.EstadoMoto(), fm.MandoMoto(), -1.0)
    with pytest.raises(ValueError):
        fm.paso_moto(fm.EstadoMoto(), fm.MandoMoto(), math.nan)


@pytest.mark.parametrize("indice", [0, 1])
def test_escenario_exportado_es_continuo_y_cumple_la_leccion(indice: int) -> None:
    din = json.loads(REFERENCIA.read_text(encoding="utf-8"))["dinamica"][indice]
    medida = din["medida"]
    radio = fm.radio_llanta_m(medida or str(S["medida_llanta_trasera"].valor))
    est = fm.EstadoMoto.model_validate(din["estado_inicial"])
    previo = est
    for paso in din["pasos"]:
        est = fm.paso_moto(est, fm.MandoMoto.model_validate(paso["mando"]), paso["dt"], medida)
        esperado = paso["estado"]
        assert est.v_ms == pytest.approx(esperado["v_ms"], abs=1e-9)
        assert est.rpm_motor == pytest.approx(esperado["rpm_motor"], abs=1e-6)
        assert est.modo == esperado["modo"]
        assert est.v_ms >= 0 and not math.isnan(est.rpm_motor)
        if paso["dt"] == 0.0:
            assert est.v_ms == previo.v_ms  # Δv = 0 exacto en el instante del cambio
        else:
            assert abs(est.v_ms - previo.v_ms) <= cota_a(previo.v_ms) * paso["dt"] + 1e-12
        if (
            paso["mando"]["marcha"] >= 1
            and est.modo in ("normal", "limitador")
            and not paso["mando"]["freno"]
        ):
            g = MARCHAS[paso["mando"]["marcha"] - 1]
            deriv = est.v_ms / radio * PRIM * g * FINAL * 60 / (2 * math.pi)
            assert est.rpm_motor == pytest.approx(min(deriv, CORTE), rel=1e-9)
        previo = est
    modos = {p["estado"]["modo"] for p in din["pasos"]}
    assert {"neutro", "normal", "patinaje", "limitador", "embrague", "ahogado"} <= modos
