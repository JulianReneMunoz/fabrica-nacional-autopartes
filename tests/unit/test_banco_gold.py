"""Banco de preguntas v2 frente al Gold (A-10).

Cada hecho esperado de una respondible debe aparecer en al menos un fragmento de
``data/gold/fragmentos.jsonl`` (con la misma normalización que el evaluador) y ningún fragmento debe
contener el ``dato_ausente`` de una ausente. El banco v1 no se modifica: se comprueba que conserva sus
hechos originales.
"""

from __future__ import annotations

import json
import re

import pytest

from fabrica_autopartes.core.config import RAIZ_PROYECTO
from fabrica_autopartes.services.evaluacion import (
    BANCO_POR_DEFECTO,
    BANCOS,
    cargar_preguntas,
    hechos_presentes,
    ruta_banco,
)

ARCHIVO_GOLD = RAIZ_PROYECTO / "data" / "gold" / "fragmentos.jsonl"
RUTA_RELATIVA_GOLD = ARCHIVO_GOLD.relative_to(RAIZ_PROYECTO).as_posix()
MOTIVO_SIN_GOLD = f"Gold no disponible ({RUTA_RELATIVA_GOLD}): ejecutar `uv run fabrica build`"

V1 = cargar_preguntas("v1")
V2 = cargar_preguntas("v2")
RESPONDIBLES_V2 = [p for p in V2 if p["tipo"] == "respondible"]
AUSENTES_V2 = [p for p in V2 if p["tipo"] == "ausente"]


@pytest.fixture(scope="module")
def textos_gold() -> list[str]:
    if not ARCHIVO_GOLD.is_file():
        pytest.skip(MOTIVO_SIN_GOLD)
    lineas = ARCHIVO_GOLD.read_text(encoding="utf-8").splitlines()
    textos = [json.loads(linea)["texto"] for linea in lineas if linea.strip()]
    if not textos:
        pytest.skip(MOTIVO_SIN_GOLD)
    return textos


@pytest.mark.parametrize("pregunta", RESPONDIBLES_V2, ids=lambda p: p["id"])
def test_cada_hecho_de_respondible_v2_esta_en_el_gold(pregunta: dict, textos_gold: list[str]) -> None:
    faltantes = [h for h in pregunta["hechos"] if not any(hechos_presentes(t, [h]) for t in textos_gold)]
    assert not faltantes, f"{pregunta['id']}: hechos sin fragmento en el Gold: {faltantes}"
    assert len(pregunta["hechos"]) >= pregunta.get("minimo", 1)


@pytest.mark.parametrize("pregunta", AUSENTES_V2, ids=lambda p: p["id"])
def test_ausente_v2_no_tiene_su_dato_en_el_gold(pregunta: dict, textos_gold: list[str]) -> None:
    patrones = pregunta.get("dato_ausente") or []
    assert patrones, f"{pregunta['id']}: una ausente de v2 debe declarar dato_ausente"
    for patron in patrones:
        coincidencias = [m.group(0) for t in textos_gold if (m := re.search(patron, t, re.IGNORECASE))]
        assert not coincidencias, f"{pregunta['id']}: el Gold contiene el dato ausente: {coincidencias[:3]}"


# Un texto que sí trae el dato: evita que una expresión que nunca coincide pase la prueba del Gold.
EJEMPLOS_CON_DATO = {
    "P20": "Atendemos de lunes a viernes de 8:00 a. m. a 5:00 p. m.",
    "P21": "La motocicleta Honda de 150 cc cuesta $ 8.990.000.",
    "P22": "El correo del presidente es presidente.fanalca@gmail.com.",
}


@pytest.mark.parametrize("pregunta", AUSENTES_V2, ids=lambda p: p["id"])
def test_dato_ausente_detecta_un_texto_con_el_dato(pregunta: dict) -> None:
    ejemplo = EJEMPLOS_CON_DATO[pregunta["id"]]
    assert any(re.search(patron, ejemplo, re.IGNORECASE) for patron in pregunta["dato_ausente"])


def test_v2_conserva_ids_tipos_de_negativas_y_proporcion() -> None:
    assert [p["id"] for p in V2] == [p["id"] for p in V1]
    assert len(RESPONDIBLES_V2) == 19 and len(V2) == 24
    # P21 conserva el criterio estricto (frase de rechazo, ADR-024).
    assert next(p for p in V2 if p["id"] == "P21")["tipo"] == "ausente"


def test_cada_cambio_v2_esta_justificado() -> None:
    por_id = {p["id"]: p for p in V1}
    for p in V2:
        original = {k: v for k, v in por_id[p["id"]].items()}
        actual = {k: v for k, v in p.items() if k not in ("cambio_v2", "dato_ausente")}
        if actual != original:
            assert p.get("cambio_v2"), f"{p['id']} cambia respecto de v1 sin cambio_v2"
    assert {p["id"] for p in V2 if p.get("cambio_v2")} == {"P02", "P07", "P12", "P15", "P16"}


def test_v1_no_se_modifica() -> None:
    p02 = next(p for p in V1 if p["id"] == "P02")
    p07 = next(p for p in V1 if p["id"] == "P07")
    assert p02["hechos"] == ["651 5343"] and p07["hechos"] == ["1982"]
    assert not any("cambio_v2" in p or "dato_ausente" in p for p in V1)


def test_banco_por_defecto_y_banco_desconocido() -> None:
    assert BANCO_POR_DEFECTO == "v2" and set(BANCOS) == {"v1", "v2"}
    assert cargar_preguntas() == V2
    with pytest.raises(ValueError, match="Banco desconocido"):
        ruta_banco("v9")
