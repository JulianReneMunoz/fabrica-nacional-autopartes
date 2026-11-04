"""Pruebas del modelo de componentes, articulaciones, cinemática, despiece y física (v2.0)."""

from __future__ import annotations

import math

import numpy as np
import pytest
from pydantic import ValidationError

from fabrica_autopartes.simulador import cinematica as cin
from fabrica_autopartes.simulador.catalogo_freno import ParametrosFreno, construir_freno
from fabrica_autopartes.simulador.fisica_freno import EntradaFreno, calcular
from fabrica_autopartes.simulador.modelos import Articulacion, LimitesMovimiento, TipoArticulacion


@pytest.fixture(scope="module")
def ens():  # type: ignore[no-untyped-def]
    return construir_freno()


# ------------------------------------------------------------------ integridad
def test_ensamblaje_integro(ens) -> None:  # type: ignore[no-untyped-def]
    assert cin.validar_ensamblaje(ens) == []


def test_identificadores_unicos_y_campos_obligatorios(ens) -> None:  # type: ignore[no-untyped-def]
    ids = [p.id for p in ens.piezas]
    assert len(ids) == len(set(ids)) == 15
    for p in ens.piezas:
        assert p.nombre and p.tipo and p.descripcion and p.funcion and p.referencia_documental
        assert p.dimensiones_m and p.geometria.nodo_glb == p.id


def test_jerarquia_cubre_todas_las_piezas(ens) -> None:  # type: ignore[no-untyped-def]
    raiz = cin.jerarquia(ens)
    hojas = [h.id for s in raiz.hijos for h in s.hijos]
    assert sorted(hojas) == sorted(p.id for p in ens.piezas)
    assert {s.id for s in raiz.hijos} == {"rotacion", "pinza", "fijacion"}


def test_detecta_ciclo_de_desmontaje(ens) -> None:  # type: ignore[no-untyped-def]
    roto = ens.model_copy(deep=True)
    roto.pieza("tornillo_soporte_1").retirar_antes.append("soporte_pinza")
    assert any("Ciclo" in e for e in cin.validar_ensamblaje(roto))


def test_detecta_referencias_rotas(ens) -> None:  # type: ignore[no-untyped-def]
    roto = ens.model_copy(deep=True)
    roto.piezas[0].relacionadas.append("inexistente")
    assert any("inexistente" in e for e in cin.validar_ensamblaje(roto))


def test_parametros_invalidos_se_rechazan() -> None:
    with pytest.raises(ValidationError):
        ParametrosFreno(diametro_disco=0.20, radio_interior_disco=0.09)  # anillo demasiado estrecho
    with pytest.raises(ValidationError):
        ParametrosFreno(espesor_disco=-0.01)


def test_articulacion_exige_eje_unitario_y_limites() -> None:
    with pytest.raises(ValidationError):
        Articulacion(
            id="j_x",
            nombre="x",
            tipo=TipoArticulacion.PRISMATICA,
            padre=None,
            hijo="a",
            eje=(0, 0, 2),
            limites=LimitesMovimiento(minimo=0, maximo=1),
        )
    with pytest.raises(ValidationError):
        Articulacion(id="j_x", nombre="x", tipo=TipoArticulacion.ROTACIONAL, padre=None, hijo="a")
    with pytest.raises(ValidationError):
        LimitesMovimiento(minimo=1, maximo=0)


# ------------------------------------------------------------------ cinemática
def test_rotacion_de_rueda_arrastra_disco_y_esparragos(ens) -> None:  # type: ignore[no-untyped-def]
    t0 = cin.transformaciones(ens)
    t90 = cin.transformaciones(ens, {"j_rueda": 90.0})
    p0 = t0["esparrago_1"][:3, 3]
    p90 = t90["esparrago_1"][:3, 3]
    assert np.isclose(np.linalg.norm(p0[:2]), np.linalg.norm(p90[:2]))  # mismo radio
    assert np.isclose(np.dot(p0[:2], p90[:2]), 0, atol=1e-9)  # girado 90°
    assert np.allclose(t90["cuerpo_pinza"], t0["cuerpo_pinza"])  # la pinza no gira


def test_pinza_flotante_aprieta_por_ambas_caras(ens) -> None:  # type: ignore[no-untyped-def]
    g = ens.parametros["holgura_pastilla"]
    base = cin.transformaciones(ens)
    fren = cin.transformaciones(ens, {"j_piston": 2 * g, "j_pinza_flotante": g})
    dz_int = fren["pastilla_interna"][2, 3] - base["pastilla_interna"][2, 3]
    dz_ext = fren["pastilla_externa"][2, 3] - base["pastilla_externa"][2, 3]
    assert math.isclose(dz_int, g, abs_tol=1e-12) and math.isclose(dz_ext, -g, abs_tol=1e-12)


def test_limites_de_articulacion(ens) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(cin.ErrorEnsamblaje, match="fuera de límites"):
        cin.transformaciones(ens, {"j_piston": 0.01})
    with pytest.raises(cin.ErrorEnsamblaje, match="no es una articulación accionable"):
        cin.transformaciones(ens, {"j_disco_cubo": 1.0})
    with pytest.raises(cin.ErrorEnsamblaje, match="inexistente"):
        cin.transformaciones(ens, {"j_fantasma": 1.0})
    with pytest.raises(cin.ErrorEnsamblaje, match="no finito"):
        cin.transformaciones(ens, {"j_rueda": float("nan")})


def test_euler_ida_y_vuelta() -> None:
    for angulos in [(10.0, 20.0, 30.0), (-45.0, 5.0, 170.0), (0.0, 0.0, 0.0)]:
        r = cin.matriz_rotacion_euler(angulos)
        assert np.allclose(cin.euler_desde_matriz(r), angulos, atol=1e-9)


# ------------------------------------------------------------------ despiece
def test_despiece_reversible_y_monotono(ens) -> None:  # type: ignore[no-untyped-def]
    ensamblado = cin.posiciones_despiece(ens, 0.0)
    for p in ens.piezas:
        assert np.allclose(ensamblado[p.id], p.transformacion.posicion)
    medio, completo = cin.posiciones_despiece(ens, 0.5), cin.posiciones_despiece(ens, 1.0)
    for p in ens.piezas:
        d_medio = np.linalg.norm(np.subtract(medio[p.id], ensamblado[p.id]))
        d_total = np.linalg.norm(np.subtract(completo[p.id], ensamblado[p.id]))
        assert math.isclose(d_total, p.distancia_despiece_m, rel_tol=1e-9)
        assert math.isclose(d_medio, d_total / 2, rel_tol=1e-9)
    with pytest.raises(cin.ErrorEnsamblaje):
        cin.posiciones_despiece(ens, 1.5)


def test_secuencias_desmontaje_y_reensamblaje(ens) -> None:  # type: ignore[no-untyped-def]
    orden = cin.secuencia_desmontaje(ens)
    pos = {pid: i for i, pid in enumerate(orden)}
    for p in ens.piezas:
        for previa in p.retirar_antes:
            assert pos[previa] < pos[p.id], f"{previa} debe retirarse antes que {p.id}"
    assert cin.secuencia_reensamblaje(ens) == list(reversed(orden))
    assert orden[-1] == "cubo"


def test_que_retirar_primero(ens) -> None:  # type: ignore[no-untyped-def]
    assert cin.que_retirar_primero(ens, "tornillo_soporte_1") == []
    previas = cin.que_retirar_primero(ens, "disco")
    assert "soporte_pinza" in previas and "cuerpo_pinza" in previas and "cubo" not in previas


# ------------------------------------------------------------------ física
def test_fisica_formulas_de_referencia() -> None:
    r = calcular(
        EntradaFreno(
            presion_bar=10, diametro_piston_m=0.054, coeficiente_friccion=0.4, radio_efectivo_m=0.115
        )
    )
    area = math.pi * 0.054**2 / 4
    assert math.isclose(r.fuerza_piston_n, 10e5 * area, rel_tol=1e-4)
    assert math.isclose(r.par_frenado_nm, 2 * 0.4 * 10e5 * area * 0.115, rel_tol=1e-4)
    assert not r.rueda_bloqueada


def test_fisica_par_proporcional_a_presion_y_bloqueo() -> None:
    bajo, alto = calcular(EntradaFreno(presion_bar=10)), calcular(EntradaFreno(presion_bar=20))
    assert math.isclose(alto.par_frenado_nm, 2 * bajo.par_frenado_nm, rel_tol=1e-4)
    extremo = calcular(EntradaFreno(presion_bar=150))
    assert extremo.rueda_bloqueada and math.isclose(extremo.deceleracion_g, 0.9, rel_tol=1e-3)
    cero = calcular(EntradaFreno(presion_bar=0))
    assert cero.tiempo_detencion_s is None


def test_fisica_rechaza_valores_fuera_de_rango() -> None:
    with pytest.raises(ValidationError):
        EntradaFreno(presion_bar=500)
