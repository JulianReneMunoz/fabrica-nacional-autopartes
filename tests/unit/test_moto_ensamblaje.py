"""Ensamblaje genérico de motocicleta: integridad, despiece, límites y relaciones."""

from __future__ import annotations

import math

import pytest

from fabrica_autopartes.simulador import cinematica as cin
from fabrica_autopartes.simulador.catalogo_moto_honda import REF_DEMO, construir_moto
from fabrica_autopartes.simulador.fisica_moto import SUPUESTOS_REFERENCIA, radio_llanta_m
from fabrica_autopartes.simulador.modelos import TipoArticulacion

SUBCONJUNTOS = {
    "motor",
    "transmision",
    "chasis_tanque",
    "suspension_delantera",
    "suspension_trasera",
    "frenos",
    "ruedas",
    "electrico",
    "escape",
    "direccion",
    "carroceria",
}
REQUERIDAS = {
    "cilindro", "piston", "biela", "ciguenal", "valvula_admision", "valvula_escape", "bujia",
    "caja_cambios", "pinon", "cadena", "corona",
    "chasis", "tanque", "sillin",
    "botella_izquierda", "botella_derecha", "tubo_izquierdo", "tubo_derecho",
    "monoamortiguador", "basculante",
    "disco_delantero", "disco_trasero", "caliper_delantero", "caliper_trasero", "unidad_cbs",
    "rin_delantero", "llanta_delantera", "rin_trasero", "llanta_trasera",
    "farola", "stop", "velocimetro",
    "tubo_escape", "silenciador",
}  # fmt: skip


def _valor(clave: str) -> float:
    v = SUPUESTOS_REFERENCIA[clave].valor
    assert isinstance(v, float)
    return v


@pytest.fixture(scope="module")
def ens():  # type: ignore[no-untyped-def]
    return construir_moto()


def test_ensamblaje_integro(ens) -> None:  # type: ignore[no-untyped-def]
    assert cin.validar_ensamblaje(ens) == []
    assert ens.id == "moto_honda" and ens.nombre == "Motocicleta (referencia genérica)"
    assert ens.archivo_glb == "modelos/moto_honda.glb"


def test_ids_unicos_nodo_igual_id_y_campos(ens) -> None:  # type: ignore[no-untyped-def]
    ids = [p.id for p in ens.piezas]
    assert len(ids) == len(set(ids))
    assert set(ids) >= REQUERIDAS
    for p in ens.piezas:
        assert p.geometria.nodo_glb == p.id
        assert p.nombre and p.tipo and p.descripcion and p.funcion and p.material and p.dimensiones_m
        assert p.referencia_documental == REF_DEMO
        assert p.subconjunto in SUBCONJUNTOS
        assert any(c != 0 for c in p.direccion_despiece)
        assert 0 < p.distancia_despiece_m <= 1.0
    assert {s.id for s in ens.subconjuntos} == SUBCONJUNTOS
    assert {p.subconjunto for p in ens.piezas} == SUBCONJUNTOS


def test_sin_ciclos_y_secuencia_completa(ens) -> None:  # type: ignore[no-untyped-def]
    des = cin.secuencia_desmontaje(ens)
    assert sorted(des) == sorted(p.id for p in ens.piezas)
    pos = {pid: i for i, pid in enumerate(des)}
    for p in ens.piezas:
        assert all(pos[previa] < pos[p.id] for previa in p.retirar_antes)
    assert cin.secuencia_reensamblaje(ens) == des[::-1]
    assert pos["piston"] < pos["biela"] < pos["ciguenal"] < pos["chasis"]


def test_limites_del_piston_son_la_carrera(ens) -> None:  # type: ignore[no-untyped-def]
    carrera = _valor("carrera_mm") / 1000
    lim = ens.articulacion("j_piston").limites
    assert lim is not None
    assert lim.maximo - lim.minimo == pytest.approx(carrera, abs=1e-6)
    assert ens.parametros["carrera_m"] == pytest.approx(carrera, abs=1e-6)
    biela = ens.articulacion("j_biela").limites
    assert biela is not None
    r, longitud = carrera / 2, _valor("longitud_biela_mm") / 1000
    assert biela.maximo == pytest.approx(math.degrees(math.asin(r / longitud)), abs=1e-4)
    assert biela.minimo == -biela.maximo
    for v in ("j_valvula_admision", "j_valvula_escape"):
        lv = ens.articulacion(v).limites
        assert lv is not None and lv.minimo == 0.0 and lv.maximo > 0
    assert ens.articulacion("j_botella_izquierda").limites is not None
    assert ens.articulacion("j_basculante").limites is not None


def test_giros_continuos_y_relaciones_compuestas(ens) -> None:  # type: ignore[no-untyped-def]
    for j in ("j_ciguenal", "j_rueda_delantera", "j_rueda_trasera"):
        a = ens.articulacion(j)
        assert a.tipo == TipoArticulacion.ROTACIONAL and a.continua
    rel = _valor("relacion_final")
    assert ens.articulacion("j_pinon").relacion == rel
    assert ens.articulacion("j_pinon").maestra == "j_rueda_trasera"
    assert ens.articulacion("j_corona").relacion == 1.0
    for j in ("j_llanta_trasera", "j_disco_trasero"):
        assert ens.articulacion(j).maestra == "j_rueda_trasera"
    res = cin.resolver_valores(ens, {"j_rueda_trasera": 30.0})
    assert res["j_pinon"] == pytest.approx(30.0 * rel)
    assert res["j_corona"] == 30.0
    for a in ens.articulaciones:
        if a.tipo in (TipoArticulacion.ROTACIONAL, TipoArticulacion.PRISMATICA):
            assert sum(c * c for c in a.eje) == pytest.approx(1.0, abs=1e-6)


def test_ruedas_usan_medidas_de_fisica_moto(ens) -> None:  # type: ignore[no-untyped-def]
    r = radio_llanta_m(
        "130/70-17"
    )  # medida genérica (supuesto didáctico); con la ficha CB 160F pasa a 140/70-17
    assert ens.pieza("llanta_trasera").dimensiones_m["radio_exterior"] == pytest.approx(r, abs=1e-5)
    assert ens.parametros["radio_llanta_trasera_m"] == pytest.approx(r, abs=1e-5)
    assert ens.pieza("rin_trasero").transformacion.posicion[1] == pytest.approx(r, abs=1e-5)


def test_diametro_exterior_de_los_neumaticos(ens) -> None:  # type: ignore[no-untyped-def]
    # D = rin·25,4 + 2·ancho·perfil/100 (mm)
    d_tra = 17 * 25.4 + 2 * 130 * 70 / 100
    d_ficha = 17 * 25.4 + 2 * 140 * 70 / 100
    d_del = 17 * 25.4 + 2 * 90 * 80 / 100
    assert d_tra == pytest.approx(613.8, abs=0.01) and d_del == pytest.approx(575.8, abs=0.01)
    tra, dele = ens.pieza("llanta_trasera"), ens.pieza("llanta_delantera")
    assert d_tra == pytest.approx(613.8, abs=0.01)
    assert tra.dimensiones_m["radio_exterior"] == pytest.approx(0.3069, abs=0.001)
    assert radio_llanta_m("140/70-17") == pytest.approx(0.3139, abs=0.001) and d_ficha == pytest.approx(
        627.8, abs=0.01
    )
    assert dele.dimensiones_m["radio_exterior"] == pytest.approx(d_del / 2000, abs=0.001)
    for pieza in (tra, dele):  # el perfil de revolución del neumático alcanza exactamente el radio exterior
        q = pieza.geometria.parametros
        radios = [v for k, v in q.items() if k.startswith("c_r")]
        assert max(radios) == pytest.approx(pieza.dimensiones_m["radio_exterior"], abs=1e-5)
    assert (
        "130/70-17" in tra.descripcion
        and "140/70-17" in tra.descripcion
        and "Ver con ficha" in tra.descripcion
    )
    assert ens.pieza("rin_trasero").transformacion.posicion[1] == pytest.approx(0.3069, abs=0.001)


def test_cubos_unen_rin_disco_y_giran_con_la_rueda(ens) -> None:  # type: ignore[no-untyped-def]
    for tag, tag_f in (("delantero", "delantera"), ("trasero", "trasera")):
        cubo = ens.pieza(f"cubo_{tag}")
        art = ens.articulacion(f"j_cubo_{tag}")
        assert art.maestra == f"j_rueda_{tag_f}" and art.relacion == 1.0
        assert cubo.geometria.primitiva == "revolucion" and cubo.geometria.nodo_glb == cubo.id
        disco = ens.pieza(f"disco_{tag}")
        # el cubo llega al radio interior del disco y cubre su plano axial (no flota)
        assert cubo.dimensiones_m["radio_maximo"] > disco.geometria.parametros["radio_interior"]
        z, mitad = cubo.transformacion.posicion[2], cubo.dimensiones_m["largo_axial"] / 2
        assert z - mitad <= disco.transformacion.posicion[2] <= z + mitad
        assert {f"rin_{tag}", f"disco_{tag}"} <= set(cubo.retirar_antes)
    corona = ens.pieza("corona")
    cubo_t = ens.pieza("cubo_trasero")
    z, mitad = cubo_t.transformacion.posicion[2], cubo_t.dimensiones_m["largo_axial"] / 2
    assert z - mitad <= corona.transformacion.posicion[2] <= z + mitad


def test_cinematica_de_la_horquilla_y_la_rueda(ens) -> None:  # type: ignore[no-untyped-def]
    base = cin.transformaciones(ens)
    comp = cin.transformaciones(ens, {"j_botella_izquierda": 0.1})
    d_rueda = comp["rin_delantero"][:3, 3] - base["rin_delantero"][:3, 3]
    assert math.hypot(*d_rueda) == pytest.approx(0.1, abs=1e-6)
    d_der = comp["botella_derecha"][:3, 3] - base["botella_derecha"][:3, 3]
    assert math.hypot(*d_der) == pytest.approx(0.1, abs=1e-6)
    with pytest.raises(cin.ErrorEnsamblaje):
        cin.resolver_valores(ens, {"j_botella_izquierda": 0.5})


def test_advertencia_y_procedencia(ens) -> None:  # type: ignore[no-untyped-def]
    adv = ens.advertencia.lower()
    assert "genérica" in adv and "no es un diseño industrial" in adv and "réplica" in adv
    assert "no valida propiedades mecánicas" in adv
    assert set(ens.procedencia_parametros) == set(ens.parametros)
    assert set(ens.procedencia_parametros.values()) == {"demostrativo"}
    assert "holgura_pastilla" not in ens.parametros


def test_sin_marcas_comerciales(ens) -> None:  # type: ignore[no-untyped-def]
    texto = " ".join(f"{p.nombre} {p.descripcion} {p.funcion}" for p in ens.piezas).lower()
    assert "honda" not in texto


def test_construccion_determinista() -> None:
    a, b = construir_moto(), construir_moto()
    assert a.model_dump_json() == b.model_dump_json()


# ----------------------------------------------------------------- fase 7a: fidelidad 3D
NUEVAS = {
    "direccion": ["tija_superior", "manubrio", "manija_freno", "manija_embrague", "puno_izquierdo",
                  "puno_derecho", "espejo_izquierdo", "espejo_derecho"],
    "carroceria": ["guardabarros_delantero", "guardabarros_trasero", "cubierta_izquierda", "cubierta_derecha",
                   "colin", "tapa_tanque", "porta_placa"],
    "motor": ["carter", "culata", "tapa_motor_izquierda", "tapa_motor_derecha", "filtro_aire",
              "cuerpo_aceleracion"],
    "transmision": ["pedal_cambios", "tensor_izquierdo", "tensor_derecho", "cubrecadena"],
    "frenos": ["bomba_freno", "manguera_freno", "pedal_freno"],
    "chasis_tanque": ["estribo_izquierdo", "estribo_derecho", "caballete_lateral", "cuna_chasis_derecha",
                      "subchasis"],
    "electrico": ["direccional_delantera_izquierda", "direccional_delantera_derecha",
                  "direccional_trasera_izquierda", "direccional_trasera_derecha", "bateria"],
    "suspension_trasera": ["basculante_brazo_izquierdo", "basculante_travesano"],
}  # fmt: skip

ORIGINALES = {
    "cilindro", "piston", "biela", "ciguenal", "valvula_admision", "valvula_escape", "bujia",
    "caja_cambios", "pinon", "cadena", "corona", "chasis", "cuna_chasis", "pipa_direccion", "tanque",
    "sillin", "puente_horquilla", "tubo_izquierdo", "botella_izquierda", "tubo_derecho",
    "botella_derecha", "monoamortiguador", "basculante", "rin_delantero", "llanta_delantera",
    "rin_trasero", "llanta_trasera", "cubo_delantero", "cubo_trasero", "disco_delantero",
    "caliper_delantero", "disco_trasero", "caliper_trasero", "unidad_cbs", "farola", "stop",
    "velocimetro", "tubo_escape", "silenciador",
}  # fmt: skip
ARTICULACIONES_ORIGINALES = {
    "j_cilindro", "j_piston", "j_biela", "j_ciguenal", "j_valvula_admision", "j_valvula_escape",
    "j_bujia", "j_caja_cambios", "j_pinon", "j_cadena", "j_corona", "j_chasis", "j_cuna_chasis",
    "j_pipa", "j_tanque", "j_sillin", "j_puente", "j_tubo_izquierdo", "j_tubo_derecho",
    "j_botella_izquierda", "j_botella_derecha", "j_monoamortiguador", "j_basculante",
    "j_rueda_delantera", "j_llanta_delantera", "j_rueda_trasera", "j_llanta_trasera",
    "j_cubo_delantero", "j_cubo_trasero", "j_disco_delantero", "j_caliper_delantero",
    "j_disco_trasero", "j_caliper_trasero", "j_unidad_cbs", "j_farola", "j_stop", "j_velocimetro",
    "j_tubo_escape", "j_silenciador",
}  # fmt: skip


def test_piezas_nuevas_por_subconjunto_y_total(ens) -> None:  # type: ignore[no-untyped-def]
    assert len(ens.piezas) >= 70 and len(ens.articulaciones) == len(ens.piezas)
    for sub, ids in NUEVAS.items():
        for pid in ids:
            assert ens.pieza(pid).subconjunto == sub, pid


def test_ids_originales_se_conservan(ens) -> None:  # type: ignore[no-untyped-def]
    assert {p.id for p in ens.piezas} >= ORIGINALES
    assert {a.id for a in ens.articulaciones} >= ARTICULACIONES_ORIGINALES


def test_conectividad_ninguna_pieza_flota(ens) -> None:  # type: ignore[no-untyped-def]
    from fabrica_autopartes.simulador.generacion import construir_escena, verificar_conectividad

    _, mallas = construir_escena(ens)
    assert verificar_conectividad(ens, mallas) == []
    raices = [p.id for p in ens.piezas if "montada_en" not in p.metadatos]
    assert raices == ["chasis"]


def test_conectividad_detecta_una_pieza_flotando(ens) -> None:  # type: ignore[no-untyped-def]
    from fabrica_autopartes.simulador.generacion import construir_escena, verificar_conectividad

    copia = ens.model_copy(deep=True)
    _, mallas = construir_escena(copia)
    p = copia.pieza("bateria")
    x, y, z = p.transformacion.posicion
    p.transformacion = p.transformacion.model_copy(update={"posicion": (x, y - 0.05, z)})
    errores = verificar_conectividad(copia, mallas)
    assert len(errores) == 1 and "bateria flota" in errores[0] and "chasis" in errores[0]
    assert "mm" in errores[0]


def test_conectividad_rechaza_ciclos_y_montajes_inexistentes(ens) -> None:  # type: ignore[no-untyped-def]
    from fabrica_autopartes.simulador.generacion import verificar_conectividad

    copia = ens.model_copy(deep=True)
    copia.pieza("chasis").metadatos["montada_en"] = "bateria"
    assert any("ciclo" in e for e in verificar_conectividad(copia, {}))
    copia2 = ens.model_copy(deep=True)
    copia2.pieza("bateria").metadatos["montada_en"] = "no_existe"
    assert any("inexistente" in e for e in verificar_conectividad(copia2, {}))


def test_freno_no_declara_montajes_y_valida_igual() -> None:
    from fabrica_autopartes.simulador.catalogo_freno import construir_freno
    from fabrica_autopartes.simulador.generacion import verificar_conectividad

    freno = construir_freno()
    assert all("montada_en" not in p.metadatos for p in freno.piezas)
    assert verificar_conectividad(freno) == []


def test_puntos_duros_proporciones(ens) -> None:  # type: ignore[no-untyped-def]
    from fabrica_autopartes.simulador.puntos_duros_moto import PUNTOS, tabla_puntos_duros

    assert PUNTOS.eje_delantero[0] - PUNTOS.eje_trasero[0] == pytest.approx(1.30, abs=1e-6)
    assert ens.parametros["distancia_entre_ejes_m"] == pytest.approx(1.30, abs=1e-3)
    sillin = ens.pieza("sillin")
    alturas = [v for k, v in sillin.geometria.parametros.items() if k.startswith("c_y")]
    assert max(alturas) + sillin.transformacion.posicion[1] == pytest.approx(0.79, abs=0.005)
    ux, uy = PUNTOS.eje_horquilla
    assert math.degrees(math.atan2(ux, -uy)) == pytest.approx(26.0, abs=1e-6)
    dx = PUNTOS.eje_delantero[0] - PUNTOS.pipa[0]
    dy = PUNTOS.eje_delantero[1] - PUNTOS.pipa[1]
    assert dx * uy - dy * ux == pytest.approx(0.0, abs=1e-9)
    nombres = {n for n, _, _ in tabla_puntos_duros()}
    esperados = {"eje_delantero", "eje_trasero", "pipa_direccion", "pivote_basculante",
                 "amortiguador_superior", "amortiguador_inferior", "soporte_motor_delantero"}  # fmt: skip
    assert esperados <= nombres
    for n, x, y in tabla_puntos_duros():
        assert ens.parametros[f"punto_{n}_x_m"] == pytest.approx(x, abs=1e-5)
        assert ens.parametros[f"punto_{n}_y_m"] == pytest.approx(y, abs=1e-5)


def test_cilindro_inclinado_y_piston_recorren_la_carrera(ens) -> None:  # type: ignore[no-untyped-def]
    inc = math.radians(ens.parametros["inclinacion_cilindro_grados"])
    eje = ens.articulacion("j_piston").eje
    assert eje[0] == pytest.approx(math.sin(inc), abs=1e-5)
    assert eje[1] == pytest.approx(math.cos(inc), abs=1e-5)
    base = cin.transformaciones(ens)
    abajo = cin.transformaciones(ens, {"j_piston": -ens.parametros["carrera_m"]})
    d = abajo["piston"][:3, 3] - base["piston"][:3, 3]
    assert math.hypot(*d) == pytest.approx(ens.parametros["carrera_m"], abs=1e-6)
    c = ens.pieza("cilindro").transformacion.posicion
    p = ens.pieza("piston").transformacion.posicion
    assert math.hypot(p[0] - c[0], p[1] - c[1]) < 0.1


def test_trayectoria_de_la_cadena_en_los_parametros(ens) -> None:  # type: ignore[no-untyped-def]
    q = ens.parametros
    assert q["cadena_dientes_pinon"] == 14 and q["cadena_dientes_corona"] == 42
    assert q["cadena_radio_paso_corona_m"] / q["cadena_radio_paso_pinon_m"] == pytest.approx(
        q["relacion_final"]
    )
    d = math.hypot(
        q["cadena_pinon_x_m"] - q["cadena_corona_x_m"], q["cadena_pinon_y_m"] - q["cadena_corona_y_m"]
    )
    assert q["cadena_entre_centros_m"] == pytest.approx(d, abs=1e-5)
    assert ens.pieza("pinon").geometria.parametros["n_dientes"] == 14
    assert ens.pieza("corona").geometria.parametros["n_dientes"] == 42
