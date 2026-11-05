"""Expansión de consultas de primer contacto (caso real: «¿Dónde queda la sede principal?»)."""

from __future__ import annotations

from fabrica_autopartes.domain.modelos import Fragmento
from fabrica_autopartes.knowledge.recuperacion import IndiceBM25, expandir_consulta, tokenizar


def _f(id_: str, texto: str) -> Fragmento:
    return Fragmento(
        id=id_,
        documento_id=id_,
        url="https://fanalca.com/",
        titulo=id_,
        seccion="x",
        texto=texto,
        tokens_aprox=len(texto.split()),
        orden=0,
    )


def test_expansion_agrega_terminos_con_peso_menor() -> None:
    pesos = expandir_consulta(tokenizar("¿Dónde queda la sede principal?"))
    assert pesos["sede"] == 1.0 and pesos["direccion"] == 0.5 and pesos["calle"] == 0.5
    assert "direccion" not in expandir_consulta(tokenizar("¿Qué productos fabrica la planta?"))


def test_pregunta_por_sede_encuentra_la_direccion_del_pie() -> None:
    fragmentos = [
        _f(
            "noticias#000", "La planta de motocicletas Honda celebra un nuevo hito de producción en Colombia."
        ),
        _f("negocios#000", "Las plantas de tubos y perfiles de acero producen para la construcción."),
        _f(
            "contacto-sitio#000",
            "# Dirección, teléfonos y correo publicados en fanalca.com\n- Calle 13 # 31A - 80, Acopi Yumbo.",
        ),
    ]
    resultados = IndiceBM25(fragmentos).buscar("¿Dónde queda la sede principal?", k=2)
    assert resultados and resultados[0].fragmento.id == "contacto-sitio#000"
