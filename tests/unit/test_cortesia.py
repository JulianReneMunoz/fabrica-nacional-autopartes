"""Cortesía de IGNIS (services/cortesia.py): categorías, saludo con eco, «no entendí» y textos sin nombres."""

from __future__ import annotations

import re
from typing import Any

import pytest

from fabrica_autopartes.services.cortesia import (
    AUTOPRESENTACION_SIN_PREFERENCIAS,
    AVISO_PRIVACIDAD,
    MEMORIA_NO_DISPONIBLE,
    NO_ENTENDI_SIN_HISTORIAL,
    SIN_PREFERENCIAS,
    TEXTOS_CORTESIA,
    clasificar_cortesia,
    responder_cortesia,
    responder_saludo,
)
from fabrica_autopartes.services.redactor_ignis import ENTRADAS_DOCUMENTAL, SEGUIMIENTO_DOCUMENTAL


@pytest.mark.parametrize(
    ("mensaje", "categoria"),
    [
        ("¿Va a llover hoy?", "fuera_tema"),
        ("¿Quién ganó el último partido de fútbol?", "fuera_tema"),
        ("¿Cómo es el clima laboral en Fanalca?", None),
        ("¿Trabajar en Fanalca es como en una película?", None),
        ("Hola, buenas tardes.", "saludo"),
        ("Muchas gracias", "gracias"),
        ("ok", "ok"),
        ("¿Eres humano?", "humano"),
        ("No entendí", "no_entendi"),
        ("😀😀", "vacio"),
        ("Hola, soy Ana Gómez de Empresa X, ¿qué hace Fanalca?", None),
        ("Necesito el plano 3d de autopartes de Fanalca", None),
    ],
)
def test_clasificacion(mensaje: str, categoria: str | None) -> None:
    assert clasificar_cortesia(mensaje) == categoria


@pytest.mark.parametrize(
    ("mensaje", "eco"),
    [
        ("Buenas noches", "¡Buenas noches!"),
        ("buenos días", "¡Buenos días!"),
        ("Hola, buenas tardes.", "¡Hola, buenas tardes!"),
        ("hola", "¡Hola!"),
    ],
)
def test_el_saludo_devuelve_el_del_cliente(mensaje: str, eco: str) -> None:
    for semilla in ("hilo:0", "hilo:1", "otro:0"):
        assert responder_saludo(mensaje, [], semilla, {}).startswith(eco)


def test_el_segundo_saludo_no_vuelve_a_presentarse() -> None:
    historial = [
        {"role": "user", "content": "Hola", "metadatos": {}},
        {"role": "assistant", "content": "¡Hola! Soy IGNIS…", "metadatos": {"cortesia": "saludo"}},
    ]
    for semilla in ("hilo:1", "hilo:2", "hilo:3"):
        assert "Soy IGNIS" not in responder_saludo("Hola", historial, semilla, {})


def test_el_saludo_con_preferencias_las_recuerda_sin_presentarse() -> None:
    prefs = {"formato_respuesta": "breve", "linea_producto": "motocicletas"}
    assert responder_saludo("hola", [], "h:0", prefs) == (
        "¡Hola de nuevo! Recuerdo que prefieres respuestas breves y que te interesan las motocicletas. "
        "¿Por dónde empezamos hoy?"
    )


def _documental(contenido: str) -> list[dict[str, Any]]:
    return [
        {"role": "user", "content": "¿Qué hace la Fundación Fanalca?", "metadatos": {}},
        {"role": "assistant", "content": contenido, "metadatos": {"ruta": "rag_documental"}},
    ]


@pytest.mark.parametrize("entrada", ENTRADAS_DOCUMENTAL)
def test_no_entendi_no_repite_la_entrada_documental(entrada: str) -> None:
    dato = "La Fundación Fanalca nace en el 2003 para construir cultura ciudadana."
    historial = _documental(f"{entrada} {dato} {SEGUIMIENTO_DOCUMENTAL}")
    texto = responder_cortesia("no_entendi", "No entendí", historial, "h:2")
    assert texto == f"Claro, te lo explico de otra forma. {dato}"
    assert entrada not in texto


def test_no_entendi_sin_oracion_util_pide_aclarar() -> None:
    historial = _documental(f"{ENTRADAS_DOCUMENTAL[1]} {SEGUIMIENTO_DOCUMENTAL}")
    assert responder_cortesia("no_entendi", "No entendí", historial, "h:2") == NO_ENTENDI_SIN_HISTORIAL


def _todos_los_textos() -> list[str]:
    textos = [t for variantes in TEXTOS_CORTESIA.values() for t in variantes]
    textos += [SIN_PREFERENCIAS, AUTOPRESENTACION_SIN_PREFERENCIAS, AVISO_PRIVACIDAD, MEMORIA_NO_DISPONIBLE]
    textos += [responder_saludo("Buenas noches", [], f"h:{n}", {}) for n in range(4)]
    return textos


# Palabras con mayúscula permitidas fuera del inicio de oración: marcas y nombres de la empresa, no de
# personas.
_MAYUSCULAS_PERMITIDAS = {"IGNIS", "Fanalca", "Honda", "Ley", "Soy"}


def test_ningun_texto_de_cortesia_tiene_nombres_de_personas() -> None:
    for texto in _todos_los_textos():
        for oracion in re.split(r"(?<=[.!?])\s+", texto):
            palabras = re.findall(r"[¡¿«]?([^\W\d_]+)", oracion)
            for palabra in palabras[1:]:  # la primera de cada oración va en mayúscula
                if palabra[0].isupper():
                    assert palabra in _MAYUSCULAS_PERMITIDAS, (palabra, texto)
