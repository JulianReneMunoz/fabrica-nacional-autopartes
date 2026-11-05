"""Exporta casos de referencia calculados en Python para las pruebas Vitest del frontend.

El visualizador web reimplementa en TypeScript el cálculo del freno para responder sin
latencia a los controles. Este script garantiza que ambas implementaciones coinciden:
genera ``web/src/__tests__/referencia_freno.json`` con entradas y salidas de
``fabrica_autopartes.simulador.fisica_freno.calcular`` y la secuencia de desmontaje.

Uso:  uv run python scripts/exportar_referencia_web.py
"""

from __future__ import annotations

import json
import math
from pathlib import Path

from fabrica_autopartes.simulador import cinematica as cin
from fabrica_autopartes.simulador import fisica_moto as fm
from fabrica_autopartes.simulador.catalogo_freno import construir_freno
from fabrica_autopartes.simulador.fisica_freno import EntradaFreno, calcular

CASOS = [
    {},
    {"presion_bar": 10},
    {"presion_bar": 40},
    {"presion_bar": 80, "coeficiente_friccion": 0.3},
    {"presion_bar": 25, "velocidad_kmh": 100, "diametro_piston_m": 0.06},
    {"presion_bar": 0},
]


MEDIDAS = ["140/70-17", "130/70-17", "90/80-17", "110/70-17", "100/80-14", "120/80-18"]
CASOS_MOTO = [
    {},
    {"rpm": 3000, "marcha": 1},
    {"rpm": 6000, "marcha": 3},
    {"rpm": 8000, "marcha": 5},
    {"rpm": 12000, "marcha": 2},  # sobre el corte: limitador
    {"rpm": 900, "marcha": 3},  # bajo el ralentí con marcha: ahogo
    {"rpm": 5000, "marcha": 0},  # neutro
    {"rpm": 5000, "marcha": 3, "palanca": "delantera", "fuerza_palanca_n": 80},
    {"rpm": 5000, "marcha": 3, "palanca": "trasera", "fuerza_palanca_n": 100, "cbs": False},
    {"rpm": 5000, "marcha": 3, "palanca": "trasera", "fuerza_palanca_n": 100, "cbs": True},
    {
        "rpm": 6000,
        "marcha": 4,
        "palanca": "trasera",
        "fuerza_palanca_n": 250,
        "cbs": True,
        "velocidad_inicial_kmh": 70,
    },
    {"version": "STD", "rpm": 4000, "marcha": 2, "palanca": "delantera", "fuerza_palanca_n": 400},
]


def _supuesto(clave: str) -> float | list[float] | str:
    return fm.SUPUESTOS_REFERENCIA[clave].valor


DT_DINAMICA = 0.05
# Segmentos del escenario determinista: (nombre, pasos, mando). Cada segmento empieza con un paso de dt = 0
# (el instante del cambio de mandos) para verificar que la velocidad no salta.
ESCENARIO = [
    ("neutro_ralenti", 40, {"marcha": 0, "acelerador": 0.0}),
    ("arranque_1", 60, {"marcha": 1, "acelerador": 1.0}),
    ("cambio_3", 80, {"marcha": 3, "acelerador": 0.8}),
    ("cambio_2", 40, {"marcha": 2, "acelerador": 0.3}),
    ("neutro_decae", 80, {"marcha": 0, "acelerador": 0.5}),
    ("arranque_2", 80, {"marcha": 2, "acelerador": 1.0}),
    ("limitador_neutro", 40, {"marcha": 0, "acelerador": 1.0}),
    (
        "freno_cbs",
        160,
        {
            "marcha": 2,
            "acelerador": 0.0,
            "palanca": "trasera",
            "fuerza_palanca_n": 180,
            "cbs": True,
            "freno": True,
        },
    ),
    ("soltar_y_acelerar", 120, {"marcha": 1, "acelerador": 1.0}),
    ("marcha_alta_sin_gas", 240, {"marcha": 5, "acelerador": 0.0}),
]


def _dinamica(medida: str | None) -> dict[str, object]:
    est = fm.EstadoMoto()
    pasos = []
    for nombre, n, c in ESCENARIO:
        mando = fm.MandoMoto.model_validate(c)
        for i in range(n + 1):
            dt = 0.0 if i == 0 else DT_DINAMICA
            est = fm.paso_moto(est, mando, dt, medida)
            pasos.append(
                {"segmento": nombre, "dt": dt, "mando": mando.model_dump(), "estado": est.model_dump()}
            )
    return {
        "medida": medida,
        "dt": DT_DINAMICA,
        "estado_inicial": fm.EstadoMoto().model_dump(),
        "pasos": pasos,
    }


def _referencia_moto() -> dict[str, object]:
    carrera_m = float(_supuesto("carrera_mm")) / 1000  # type: ignore[arg-type]
    biela_m = float(_supuesto("longitud_biela_mm")) / 1000  # type: ignore[arg-type]
    prim = float(_supuesto("relacion_primaria"))  # type: ignore[arg-type]
    marchas = list(_supuesto("relaciones_marcha"))  # type: ignore[arg-type]
    final = float(_supuesto("relacion_final"))  # type: ignore[arg-type]
    llantas = [
        {
            "medida": m,
            "diametro_mm": fm.diametro_llanta_mm(m),
            "radio_m": fm.radio_llanta_m(m),
        }
        for m in MEDIDAS
    ]
    velocidades = []
    for medida in ("140/70-17", "130/70-17"):
        radio = fm.radio_llanta_m(medida)
        for rpm in (1400, 3000, 6000, 9500):
            for i, g in enumerate(marchas, start=1):
                velocidades.append(
                    {
                        "medida": medida,
                        "rpm": rpm,
                        "marcha": i,
                        "relacion_total": fm.relacion_total(prim, g, final),
                        "velocidad_kmh": fm.velocidad_kmh(rpm, radio, prim, g, final),
                    }
                )
    cilindradas = [
        {"diametro_mm": d, "carrera_mm": c, "cilindrada_cm3": fm.cilindrada_cm3(d, c)}
        for d, c in ((57.0, 58.7), (57.3, 57.8), (61.0, 55.0), (50.0, 49.5))
    ]
    pistones = []
    for grados in range(0, 721, 30):
        t = math.radians(grados)
        pistones.append(
            {
                "theta_grados": grados,
                "carrera_m": carrera_m,
                "biela_m": biela_m,
                "posicion_m": fm.posicion_piston_m(t, carrera_m, biela_m),
                "angulo_biela_rad": fm.angulo_biela_rad(t, carrera_m, biela_m),
                "fase": fm.fase_ciclo(grados),
            }
        )
    cadena = []
    for rpm, i in ((1400, 1), (3000, 2), (6000, 3), (9500, 5)):
        g = marchas[i - 1]
        cadena.append(
            {
                "rpm": rpm,
                "marcha": i,
                "omega_pinon_rad_s": fm.velocidad_angular_pinon_rad_s(rpm, prim, g),
                "omega_corona_rad_s": fm.velocidad_angular_corona_rad_s(rpm, prim, g, final),
                "v_cadena_m_s": fm.velocidad_cadena_m_s(rpm, prim, g),
                "v_cadena_desde_corona_m_s": fm.velocidad_cadena_desde_corona_m_s(rpm, prim, g, final),
            }
        )
    reparto = []
    for c in (
        {"palanca": "delantera", "fuerza_palanca_n": 100},
        {"palanca": "trasera", "fuerza_palanca_n": 100, "cbs": False},
        {"palanca": "trasera", "fuerza_palanca_n": 100, "cbs": True},
        {"palanca": "trasera", "fuerza_palanca_n": 333, "cbs": True},
    ):
        e = fm.EntradaMoto.model_validate(c)
        p_total = e.fuerza_palanca_n * float(_supuesto("presion_bar_por_newton"))  # type: ignore[arg-type]
        p_del, p_tras = fm.repartir_presion(e, p_total)
        reparto.append(
            {
                "entrada": e.model_dump(),
                "presion_total_bar": p_total,
                "presion_delantera_bar": p_del,
                "presion_trasera_bar": p_tras,
            }
        )
    calculos = []
    for c in CASOS_MOTO:
        e = fm.EntradaMoto.model_validate(c)
        for medida in (None, "140/70-17"):
            calculos.append(
                {
                    "entrada": e.model_dump(),
                    "medida": medida,
                    "salida": fm.calcular_moto(e, medida).model_dump(),
                }
            )
    return {
        "supuestos": {k: v.valor for k, v in fm.SUPUESTOS_REFERENCIA.items()},
        "geometria_cadena": {"radio_pinon_m": fm.RADIO_PINON_M, "radio_corona_m": fm.RADIO_CORONA_M},
        "llantas": llantas,
        "velocidades": velocidades,
        "cilindradas": cilindradas,
        "pistones": pistones,
        "cadena": cadena,
        "reparto_cbs": reparto,
        "calculos": calculos,
        "dinamica": [_dinamica(None), _dinamica("140/70-17")],
    }


def main() -> None:
    destino_moto = Path(__file__).resolve().parents[1] / "web" / "src" / "__tests__" / "referencia_moto.json"
    destino_moto.write_text(json.dumps(_referencia_moto(), indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Referencia de la motocicleta escrita en {destino_moto}")
    destino = Path(__file__).resolve().parents[1] / "web" / "src" / "__tests__" / "referencia_freno.json"
    ens = construir_freno()
    casos = []
    for c in CASOS:
        entrada = EntradaFreno.model_validate(c)
        casos.append({"entrada": entrada.model_dump(), "salida": calcular(entrada).model_dump()})
    datos = {
        "casos": casos,
        "secuencia_desmontaje": cin.secuencia_desmontaje(ens),
        "despiece_1": cin.posiciones_despiece(ens, 1.0),
        "despiece_0": cin.posiciones_despiece(ens, 0.0),
    }
    destino.write_text(json.dumps(datos, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Referencia escrita en {destino}")


if __name__ == "__main__":
    main()
