"""Exporta casos de referencia calculados en Python para las pruebas Vitest del frontend.

El visualizador web reimplementa en TypeScript el cálculo del freno para responder sin
latencia a los controles. Este script garantiza que ambas implementaciones coinciden:
genera ``web/src/__tests__/referencia_freno.json`` con entradas y salidas de
``fabrica_autopartes.simulador.fisica_freno.calcular`` y la secuencia de desmontaje.

Uso:  uv run python scripts/exportar_referencia_web.py
"""

from __future__ import annotations

import json
from pathlib import Path

from fabrica_autopartes.simulador import cinematica as cin
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


def main() -> None:
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
