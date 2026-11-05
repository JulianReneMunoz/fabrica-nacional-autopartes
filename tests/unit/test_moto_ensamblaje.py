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
    for pieza in (tra, dele):  # el toro (radio mayor + radio menor) reproduce el radio exterior
        q = pieza.geometria.parametros
        assert q["radio_mayor"] + q["radio_menor"] == pytest.approx(
            pieza.dimensiones_m["radio_exterior"], abs=1e-5
        )
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
        assert cubo.geometria.primitiva == "cilindro" and cubo.geometria.nodo_glb == cubo.id
        disco = ens.pieza(f"disco_{tag}")
        # el cubo llega al radio interior del disco y cubre su plano axial (no flota)
        assert cubo.geometria.parametros["radio"] > disco.geometria.parametros["radio_interior"]
        z, mitad = cubo.transformacion.posicion[2], cubo.geometria.parametros["largo"] / 2
        assert z - mitad <= disco.transformacion.posicion[2] <= z + mitad
        assert {f"rin_{tag}", f"disco_{tag}"} <= set(cubo.retirar_antes)
    corona = ens.pieza("corona")
    cubo_t = ens.pieza("cubo_trasero")
    z, mitad = cubo_t.transformacion.posicion[2], cubo_t.geometria.parametros["largo"] / 2
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
