"""Ficha corporativa de Fanalca: procedencia de cada dato en el corpus, secciones y redacción sin JSON."""

from __future__ import annotations

import json

import pytest

from fabrica_autopartes.core.config import RAIZ_PROYECTO
from fabrica_autopartes.services.ficha_fanalca import (
    RUTA_FICHA,
    TEXTO_NO_PUBLICADO,
    Hito,
    cargar_ficha,
    redactar_ficha,
    seccion_ficha,
)

FRAGMENTOS = RAIZ_PROYECTO / "data" / "gold" / "fragmentos.jsonl"


def _normalizar(texto: str) -> str:
    return " ".join(texto.replace("**", " ").split())


def test_cada_dato_tiene_una_fuente_presente_en_el_corpus() -> None:
    corpus = {}
    for linea in FRAGMENTOS.read_text(encoding="utf-8").splitlines():
        fragmento = json.loads(linea)
        corpus[fragmento["id"]] = fragmento
    fuentes = cargar_ficha().todas_las_fuentes()
    assert len(fuentes) >= 20
    for fuente in fuentes:
        fragmento = corpus[fuente.fragmento_id]
        assert fragmento["url"] == fuente.url
        assert fragmento["origen"] == fuente.origen
        assert fragmento["titulo"] == fuente.titulo
        for tramo in fuente.tramos():
            assert _normalizar(tramo) in _normalizar(fragmento["texto"]), (fuente.fragmento_id, tramo)


def test_la_ficha_no_tiene_nombres_de_personas() -> None:
    texto = RUTA_FICHA.read_text(encoding="utf-8")
    for nombre in ("Joaquín", "Alberto", "Jorge", "Gómez", "Salcedo"):
        assert nombre not in texto


@pytest.mark.parametrize(
    ("pregunta", "seccion"),
    [
        ("¿Cuál es la misión y la visión de Fanalca?", "mision"),
        ("¿Dónde están las fábricas de Fanalca?", "plantas"),
        ("Listar las sedes", "plantas"),
        ("¿Qué negocios tiene Fanalca?", "negocios"),
        ("¿Cuáles son los canales de contacto?", "contacto"),
        ("¿Cuál es la historia de Fanalca?", "historia"),
        ("¿Qué es Fanalca?", "presentacion"),
        ("¿A qué se dedica?", "presentacion"),
        ("¿Quiénes son?", "presentacion"),
        ("¿Qué hace Fanalca?", "presentacion"),
        ("¿Qué hace Fanalca hoy?", "presentacion"),
        ("¿Qué hace Fanalca en sostenibilidad?", None),  # pregunta con tema: va al buscador
        ("Hola, soy Ana Gómez de Empresa X, ¿qué hace Fanalca?", None),  # no es toda la pregunta
        ("¿Qué valores tiene Fanalca?", "valores"),
        ("¿Cuál es el NIT de Fanalca?", "no_publicado"),
        ("¿Cuánto cuesta la CB190R?", "no_publicado"),
        ("¿Me haces una cotización?", "no_publicado"),
        ("¿Qué hace la Fundación Fanalca?", None),  # la Fundación es una entidad: ruta documental
        ("Qué dice el documento de la sede", None),  # pregunta sobre los documentos
    ],
)
def test_seccion_de_la_pregunta(pregunta: str, seccion: str | None) -> None:
    assert seccion_ficha(pregunta) == seccion


def _responder(pregunta: str) -> str:
    seccion = seccion_ficha(pregunta)
    assert seccion is not None
    texto, _ = redactar_ficha(pregunta, seccion)
    return texto


def test_mision_no_afirma_lo_que_no_se_sabe() -> None:
    texto = _responder("¿Cuál es la misión y la visión de Fanalca?")
    assert texto.startswith(
        "En la información de Fanalca que tengo no aparecen una misión y una visión como tal"
    )
    assert cargar_ficha().proposito.texto in texto
    assert "pilares estratégicos" in texto


def test_plantas_nombra_los_cuatro_lugares_con_su_negocio() -> None:
    texto = _responder("¿Dónde están las fábricas de Fanalca?")
    for lugar in ("Acopi, Yumbo", "Guachené", "Bogotá", "Medellín"):
        assert lugar in texto
    assert "Guachené (Cauca), de Tubos y perfiles de acero" in texto
    assert "Medellín (Antioquia), de Autopartes" in texto


def test_plantas_de_un_negocio_solo_nombran_las_suyas() -> None:
    texto = _responder("¿Dónde están las plantas de autopartes?")
    assert texto == (
        "Autopartes tiene plantas en Acopi, Yumbo (Valle del Cauca), Bogotá (Cundinamarca) "
        "y Medellín (Antioquia)."
    )
    assert "Guachené" not in texto


def test_historia_usa_todos_los_hitos_en_orden() -> None:
    ficha = cargar_ficha()
    fuente = ficha.historia.hitos[0].fuente
    hitos = [
        Hito(texto="empezaron con 12 colaboradores", fuente=fuente, con_la_fundacion=True),
        Hito(texto="En 1959 abrieron dos ensambladoras", fuente=fuente),
        Hito(texto="en 1969 llegaron las autopartes", fuente=fuente),
    ]
    corta = ficha.model_copy(update={"historia": ficha.historia.model_copy(update={"hitos": hitos})})
    texto, fuentes = redactar_ficha("¿Cuál es la historia de Fanalca?", "historia", corta)
    assert texto == (
        "Fanalca se constituyó el 31 de mayo de 1958, entre las familias Losada y Herrera, como Fábrica "
        "Nacional de Carrocerías, y empezaron con 12 colaboradores. En 1959 abrieron dos ensambladoras y en "
        "1969 llegaron las autopartes."
    )
    assert len(fuentes) == 1 + len(hitos)


def test_historia_real_en_dos_o_tres_oraciones_y_en_orden() -> None:
    texto = _responder("¿Cuál es la historia de Fanalca?")
    oraciones = [o for o in texto.split(". ") if o]
    assert 2 <= len(oraciones) <= 3
    # «12 colaboradores» va con la constitución de 1958, no con 1959.
    assert "12 colaboradores" in oraciones[0] and "1958" in oraciones[0] and "1959" not in oraciones[0]
    posiciones = [
        texto.index(marca) for marca in ("1958", "1959", "100 %", "1969", "1971", "automóviles Honda")
    ]
    assert posiciones == sorted(posiciones)


def test_negocios_nombra_los_seis() -> None:
    texto = _responder("¿Qué negocios tiene Fanalca?")
    for negocio in (
        "Honda Motocicletas",
        "Honda Autos",
        "Tubos y perfiles de acero",
        "Autopartes",
        "Ambiental",
    ):
        assert negocio in texto
    assert "Fanalvías" in texto and "6 negocios" in texto


@pytest.mark.parametrize("pregunta", ["¿Cuánto cuesta la CB190R?", "¿Me haces una cotización?"])
def test_precios_y_cotizaciones_responden_el_texto_fijo(pregunta: str) -> None:
    texto, fuentes = redactar_ficha(pregunta, "no_publicado")
    assert texto == TEXTO_NO_PUBLICADO
    assert fuentes == []


def test_presentacion_cita_sus_fuentes() -> None:
    texto, fuentes = redactar_ficha("¿Qué es Fanalca?", "presentacion")
    assert "31 de mayo de 1958" in texto and "Fábrica Nacional de Carrocerías" in texto
    ids = {f.fragmento_id for f in fuentes}
    assert {"nosotros#002", "inicio#000", "negocios-fanalvias#000"} <= ids


@pytest.mark.parametrize(
    "seccion",
    ["presentacion", "proposito", "mision", "valores", "negocios", "plantas", "contacto", "historia"],
)
def test_redaccion_sin_restos_tecnicos(seccion: str) -> None:
    texto, fuentes = redactar_ficha("pregunta", seccion)  # type: ignore[arg-type]
    assert fuentes
    assert len(texto.split()) <= 120
    assert len(texto) <= 600  # pulir_respuesta corta a 600 caracteres: la respuesta no debe quedar cortada
    assert texto[-1] in ".?!"
    for prohibido in ("{", "}", "[", "]", "http", ".json", "`", "|"):
        assert prohibido not in texto
