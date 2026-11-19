"""Router por reglas de IGNIS (R08): las palabras clave «cb» y «fanalca» ya no deciden la ruta por sí solas
(observación 5 del hook del PR anterior). Las rutas de la batería de 20 preguntas no cambian."""

from __future__ import annotations

import json

import pytest

from fabrica_autopartes.core.config import RAIZ_PROYECTO
from fabrica_autopartes.services.agente_ignis_m2 import _es_pregunta_de_moto, decidir_ruta_router

BATERIA = json.loads(
    (RAIZ_PROYECTO / "tests" / "fixtures" / "ignis_bateria.json").read_text(encoding="utf-8")
)
# Las preguntas agresivas las bloquea la moderación antes del router: no pasan por decidir_ruta_router.
SIN_MODERACION = [p for p in BATERIA if p["categoria"] != "agresiva"]


@pytest.mark.parametrize("pregunta", SIN_MODERACION, ids=[p["pregunta"][:40] for p in SIN_MODERACION])
def test_las_rutas_de_la_bateria_no_cambian(pregunta: dict[str, str]) -> None:
    assert decidir_ruta_router(pregunta["pregunta"]).ruta == pregunta["ruta"]


@pytest.mark.parametrize(
    ("mensaje", "es_moto"),
    [
        ("¿Cuál es el cilindraje de la CB 160F?", True),
        ("¿Qué trae la cb160f?", True),
        ("Háblame de la moto CB 190R", True),
        ("¿Qué motocicletas vende Fanalca?", True),
        ("¿Qué es el CBS?", False),
        ("¿Qué es un cb?", False),
        ("¿Qué hace el motor eléctrico?", False),
    ],
)
def test_moto_se_detecta_por_palabras_completas(mensaje: str, es_moto: bool) -> None:
    assert _es_pregunta_de_moto(mensaje) is es_moto


def test_la_palabra_fanalca_sola_no_vuelve_mixta_la_pregunta() -> None:
    decision = decidir_ruta_router("¿Cuántas unidades de negocio tiene Fanalca?")
    assert decision.ruta == "herramienta_estructurada"


def test_las_preguntas_mixtas_siguen_siendo_mixtas() -> None:
    assert (
        decidir_ruta_router("¿Cuántas unidades de negocio tiene Fanalca según sus documentos?").ruta
        == "mixto"
    )
    assert decidir_ruta_router("Compara la sostenibilidad con las estadísticas").ruta == "mixto"
