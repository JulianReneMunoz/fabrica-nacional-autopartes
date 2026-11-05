"""Pruebas de la física didáctica de la motocicleta y del catálogo de fichas."""

from __future__ import annotations

import math

import pytest
import yaml
from pydantic import ValidationError

from fabrica_autopartes.services import motos as srv
from fabrica_autopartes.simulador import fisica_moto as fm

A_ESPERADA = 0.3139


def _carrera_m() -> float:
    return float(fm.SUPUESTOS_REFERENCIA["carrera_mm"].valor) / 1000  # type: ignore[arg-type]


def _biela_m() -> float:
    return float(fm.SUPUESTOS_REFERENCIA["longitud_biela_mm"].valor) / 1000  # type: ignore[arg-type]


def test_radio_140_70_17() -> None:
    assert fm.diametro_llanta_mm("140/70-17") == pytest.approx(627.8, abs=0.01)
    assert fm.radio_llanta_m("140/70-17") == pytest.approx(A_ESPERADA, abs=0.001)


def test_medida_invalida() -> None:
    with pytest.raises(ValueError):
        fm.radio_llanta_m("140-70/17")


def test_velocidad_lineal_con_rpm_y_decrece_con_relacion() -> None:
    r = fm.radio_llanta_m("140/70-17")
    v1 = fm.velocidad_kmh(3000, r, 3.35, 1.4, 3.0)
    v2 = fm.velocidad_kmh(6000, r, 3.35, 1.4, 3.0)
    assert v2 == pytest.approx(2 * v1)
    assert fm.velocidad_kmh(6000, r, 3.35, 1.1, 3.0) > v2


def test_cilindrada_referencia_dentro_del_1_por_ciento() -> None:
    calculada = fm.cilindrada_cm3(
        fm.SUPUESTOS_REFERENCIA["diametro_mm"].valor,  # type: ignore[arg-type]
        fm.SUPUESTOS_REFERENCIA["carrera_mm"].valor,  # type: ignore[arg-type]
    )
    nominal = fm.SUPUESTOS_REFERENCIA["cilindrada_nominal_cm3"].valor
    assert abs(calculada - nominal) / nominal < 0.01  # type: ignore[operator]


def test_piston_entre_pmi_y_pms_y_carrera_es_2r() -> None:
    carrera, biela = _carrera_m(), _biela_m()
    xs = [fm.posicion_piston_m(math.radians(t), carrera, biela) for t in range(0, 721, 5)]
    assert max(xs) == pytest.approx(biela + carrera / 2)
    assert min(xs) == pytest.approx(biela - carrera / 2)
    assert max(xs) - min(xs) == pytest.approx(carrera)


def test_ciclo_dura_720_grados() -> None:
    assert [fm.fase_ciclo(t) for t in (0, 180, 360, 540)] == list(fm.FASES_CICLO)
    assert fm.fase_ciclo(720) == fm.fase_ciclo(0)


def test_cbs_reparte_40_60_y_conserva_la_suma_por_disco_a_igual_velocidad() -> None:
    f = float(fm.SUPUESTOS_REFERENCIA["reparto_cbs_delantero"].valor)  # type: ignore[arg-type]
    k = float(fm.SUPUESTOS_REFERENCIA["presion_bar_por_newton"].valor)  # type: ignore[arg-type]
    base = {"palanca": "trasera", "fuerza_palanca_n": 100, "velocidad_inicial_kmh": 60}
    sin_cbs = fm.calcular_moto(fm.EntradaMoto(cbs=False, **base))  # type: ignore[arg-type]
    con_cbs = fm.calcular_moto(fm.EntradaMoto(cbs=True, **base))  # type: ignore[arg-type]
    assert sin_cbs.freno_delantero is None and sin_cbs.freno_trasero is not None
    assert con_cbs.freno_delantero is not None and con_cbs.freno_trasero is not None
    p_del, p_tras = 100 * k * f, 100 * k * (1 - f)
    assert (p_del, p_tras) == pytest.approx((12.0, 18.0))  # 40/60 de 30 bar
    assert p_del + p_tras == pytest.approx(100 * k)
    # Mismo pistón: la fuerza de pistón de cada disco es proporcional a su presión.
    d = float(fm.SUPUESTOS_REFERENCIA["diametro_piston_m"].valor)  # type: ignore[arg-type]
    area = math.pi * d**2 / 4
    assert con_cbs.freno_delantero.fuerza_piston_n == pytest.approx(p_del * 1e5 * area, rel=1e-6)
    assert con_cbs.freno_trasero.fuerza_piston_n == pytest.approx(p_tras * 1e5 * area, rel=1e-6)
    assert con_cbs.fuerza_pistones_total_n == pytest.approx(sin_cbs.fuerza_pistones_total_n, rel=1e-6)


def _decel(p_bar: float, radio: float) -> float:
    return fm.calcular(
        fm.EntradaFreno(
            presion_bar=p_bar,
            diametro_piston_m=0.03,
            coeficiente_friccion=0.4,
            radio_efectivo_m=0.1,
            velocidad_kmh=60,
            radio_neumatico_m=radio,
            masa_cuarto_vehiculo_kg=120,
            inercia_rueda_kg_m2=0.9,
            adherencia_neumatico=0.9,
        )
    ).deceleracion_m_s2


def test_freno_delantero_usa_el_radio_de_la_llanta_delantera() -> None:
    delantera = fm.radio_llanta_m(fm.MEDIDA_DELANTERA_DEMO)
    trasera = fm.radio_llanta_m(str(fm.SUPUESTOS_REFERENCIA["medida_llanta_trasera"].valor))
    assert delantera != pytest.approx(trasera)
    r = fm.calcular_moto(
        fm.EntradaMoto(palanca="trasera", cbs=True, fuerza_palanca_n=100, velocidad_inicial_kmh=60)
    )
    assert r.freno_delantero is not None and r.freno_trasero is not None
    assert r.freno_delantero.deceleracion_m_s2 == pytest.approx(_decel(12.0, delantera), abs=1e-3)
    assert r.freno_trasero.deceleracion_m_s2 == pytest.approx(_decel(18.0, trasera), abs=1e-3)
    assert r.freno_delantero.deceleracion_m_s2 != pytest.approx(_decel(12.0, trasera), abs=1e-3)


def test_sin_movimiento_no_se_informa_bloqueo() -> None:
    parado = fm.calcular_moto(fm.EntradaMoto(rpm=1400, marcha=0, palanca="delantera", fuerza_palanca_n=600))
    assert parado.velocidad_kmh == 0 and parado.freno_delantero is not None
    assert parado.rueda_delantera_bloqueada is False
    en_marcha = fm.calcular_moto(
        fm.EntradaMoto(rpm=5000, marcha=3, palanca="delantera", fuerza_palanca_n=600)
    )
    assert en_marcha.rueda_delantera_bloqueada is True


def test_cadena_radios_coherentes_con_la_relacion_final() -> None:
    final = float(fm.SUPUESTOS_REFERENCIA["relacion_final"].valor)  # type: ignore[arg-type]
    assert pytest.approx(final) == fm.RADIO_CORONA_M / fm.RADIO_PINON_M
    from fabrica_autopartes.simulador.catalogo_moto_honda import construir_moto

    ens = construir_moto()
    assert ens.pieza("pinon").dimensiones_m["radio"] == pytest.approx(fm.RADIO_PINON_M)
    assert ens.pieza("corona").dimensiones_m["radio"] == pytest.approx(fm.RADIO_CORONA_M)


def _sin_nan(obj: object) -> None:
    if isinstance(obj, float):
        assert math.isfinite(obj)
    elif isinstance(obj, dict):
        for v in obj.values():
            _sin_nan(v)
    elif isinstance(obj, list):
        for v in obj:
            _sin_nan(v)


def test_sin_nan_ni_infinitos_incluidos_los_frenos() -> None:
    for rpm in (0, 900, 1400, 8000, 12000):
        for marcha in range(0, 6):
            for palanca in ("delantera", "trasera"):
                for cbs in (False, True):
                    e = fm.EntradaMoto(rpm=rpm, marcha=marcha, palanca=palanca, fuerza_palanca_n=150, cbs=cbs)
                    r = fm.calcular_moto(e)
                    _sin_nan(r.model_dump())
                    assert r.freno_delantero is not None or r.freno_trasero is not None


def test_limitador_y_ahogo_segun_la_marcha() -> None:
    corte = fm.SUPUESTOS_REFERENCIA["corte_encendido_rpm"].valor
    alto = fm.calcular_moto(fm.EntradaMoto(rpm=15000, marcha=2))
    assert alto.estado_motor == "limitador" and alto.rpm_efectivas == corte
    # Marcha alta con rpm bajas: se ahoga. En marchas bajas el embrague patina (arranque), no ahoga.
    ahogado = fm.calcular_moto(fm.EntradaMoto(rpm=600, marcha=5))
    assert ahogado.estado_motor == "ahogado" and ahogado.velocidad_kmh == 0
    assert fm.calcular_moto(fm.EntradaMoto(rpm=600, marcha=1)).estado_motor == "patinaje"


def test_entrada_rechaza_nan_infinito_y_campos_extra() -> None:
    for malo in ({"rpm": math.nan}, {"rpm": math.inf}, {"fuerza_palanca_n": -math.inf}, {"otro": 1}):
        with pytest.raises(ValidationError):
            fm.EntradaMoto(**malo)  # type: ignore[arg-type]


def test_entrada_invalida() -> None:
    with pytest.raises(ValidationError):
        fm.EntradaMoto(rpm=-1)
    with pytest.raises(ValidationError):
        fm.EntradaMoto(marcha=6)  # la referencia tiene 5 marchas
    with pytest.raises(ValidationError):
        fm.EntradaMoto(version="STD", cbs=True)


def test_catalogo_yaml_cumple_el_esquema() -> None:
    datos = yaml.safe_load(srv.RUTA_CATALOGO.read_text(encoding="utf-8"))
    assert srv.validar_catalogo(datos) == []


def test_validador_detecta_valor_sin_fuente() -> None:
    datos = {"modelos": [{"id": "x", "motor": {"tipo": {"valor": "4T", "estado": "publicado"}}}]}
    assert any("sin fuente" in e for e in srv.validar_catalogo(datos))


def test_ver_con_ficha_aplica_solo_publicados() -> None:
    ap = srv.aplicar_ficha("cb160f", "DLX")
    assert ap.aplicados["llantas.trasera"] == "140/70-17"
    assert "motor.cilindrada (cilindrada_nominal_cm3)" in ap.conservados_genericos
    calculo = srv.calcular("cb160f", fm.EntradaMoto(rpm=8000, marcha=5))
    assert calculo.resultado.medida_llanta == "140/70-17"
    generico = srv.calcular(None, fm.EntradaMoto(rpm=8000, marcha=5))
    assert generico.resultado.medida_llanta == "130/70-17"


def test_faq_marca_no_publicado() -> None:
    faq = {r.id: r for r in srv.preguntas_modelo("cb160f")}
    assert faq["cilindrada"].respuesta == "Cilindrada: No publicado."
    assert faq["potencia"].estado == "no_publicado"
    assert faq["llanta_trasera"].fuentes == ["lamina-cb160-std-dlx (aportada por el usuario)"]


def test_angulo_de_biela_es_cero_en_los_puntos_muertos_y_acotado() -> None:
    carrera, biela = _carrera_m(), _biela_m()
    assert fm.angulo_biela_rad(0.0, carrera, biela) == pytest.approx(0.0)
    assert fm.angulo_biela_rad(math.pi, carrera, biela) == pytest.approx(0.0, abs=1e-12)
    limite = math.asin(carrera / 2 / biela)
    angulos = [fm.angulo_biela_rad(math.radians(t), carrera, biela) for t in range(0, 361, 5)]
    assert max(angulos) == pytest.approx(limite, rel=1e-3)
    assert min(angulos) == pytest.approx(-limite, rel=1e-3)
    # φ cumple r·sin θ = L·sin φ (la biela cierra el triángulo con la manivela).
    t = math.radians(70)
    assert biela * math.sin(fm.angulo_biela_rad(t, carrera, biela)) == pytest.approx(
        carrera / 2 * math.sin(t)
    )


def test_cadena_piñon_y_corona_dan_la_misma_velocidad_lineal() -> None:
    prim, final = 3.35, 3.0
    for rpm, marcha in ((1400, 1.9), (5000, 1.4), (9500, 0.95)):
        w_pinon = fm.velocidad_angular_pinon_rad_s(rpm, prim, marcha)
        w_corona = fm.velocidad_angular_corona_rad_s(rpm, prim, marcha, final)
        assert w_pinon == pytest.approx(final * w_corona)
        v_pinon = fm.velocidad_cadena_m_s(rpm, prim, marcha)
        assert v_pinon == pytest.approx(w_pinon * fm.RADIO_PINON_M)
        assert v_pinon == pytest.approx(fm.velocidad_cadena_desde_corona_m_s(rpm, prim, marcha, final))


def test_cadena_coherente_con_la_velocidad_de_la_moto() -> None:
    # La corona gira con la rueda: ω_corona · R = v de la moto.
    r = fm.radio_llanta_m("140/70-17")
    rpm, prim, marcha, final = 6000, 3.35, 1.4, 3.0
    v_ms = fm.velocidad_kmh(rpm, r, prim, marcha, final) / 3.6
    assert fm.velocidad_angular_corona_rad_s(rpm, prim, marcha, final) * r == pytest.approx(v_ms)


def test_cadena_crece_con_rpm_y_decrece_con_la_marcha() -> None:
    assert fm.velocidad_cadena_m_s(6000, 3.35, 1.4) == pytest.approx(
        2 * fm.velocidad_cadena_m_s(3000, 3.35, 1.4)
    )
    assert fm.velocidad_cadena_m_s(6000, 3.35, 1.1) > fm.velocidad_cadena_m_s(6000, 3.35, 1.4)
