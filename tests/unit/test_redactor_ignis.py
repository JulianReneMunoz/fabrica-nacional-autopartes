"""Redactor extractivo de IGNIS: ficha de la moto, estadísticas y respuestas documentales en oraciones
completas."""

from __future__ import annotations

import json
from typing import Any

import pytest
import yaml

from fabrica_autopartes.core.config import RAIZ_PROYECTO
from fabrica_autopartes.domain.modelos import Fragmento
from fabrica_autopartes.services.redactor_ignis import (
    ENTRADAS_DOCUMENTAL,
    fuentes_datos_moto,
    redactar_documental,
    redactar_estadisticas,
    redactar_ficha_moto,
)


@pytest.fixture(scope="module")
def catalogo() -> dict[str, Any]:
    datos: dict[str, Any] = yaml.safe_load(
        (RAIZ_PROYECTO / "data" / "catalogo" / "motos_honda.yaml").read_text(encoding="utf-8")
    )
    return datos


def test_frenos_por_version_con_el_texto_exacto(catalogo: dict[str, Any]) -> None:
    assert redactar_ficha_moto("¿Qué frenos tiene la CB160F?", catalogo) == (
        "Según su ficha, los frenos de la CB 160F son: la versión STD, delantero de disco, sin CBS; la "
        "versión DLX, delantero de disco, trasero de disco, con CBS. No está publicado el freno trasero "
        "de la versión STD."
    )


def test_cb_160_cuenta_como_la_cb_160f(catalogo: dict[str, Any]) -> None:
    texto = redactar_ficha_moto("¿Y la CB 160?", catalogo)
    assert texto.startswith("La ficha de la CB 160F indica")
    assert "Honda 4T" in texto


def test_otro_modelo_dice_que_solo_tiene_la_cb_160f(catalogo: dict[str, Any]) -> None:
    texto = redactar_ficha_moto("¿Cuántos hp tiene la CB 190R?", catalogo)
    assert texto == "Por ahora solo tengo la ficha de la CB 160F. ¿Quieres que te cuente sobre ella?"


def test_dato_no_publicado_se_dice_sin_deducirlo(catalogo: dict[str, Any]) -> None:
    texto = redactar_ficha_moto("¿Cuál es el cilindraje de la CB 160F?", catalogo)
    assert texto == "El dato de cilindraje de la CB 160F no está publicado en las fuentes que tengo."
    assert "160 cc" not in texto


def test_valores_exactos_de_la_herramienta(catalogo: dict[str, Any]) -> None:
    texto = redactar_ficha_moto("¿Qué datos tiene la ficha estructurada de la CB 160F?", catalogo)
    modelo = catalogo["modelos"][0]
    for valor in (modelo["motor"]["tipo"]["valor"], str(modelo["motor"]["regimen_potencia"]["valor"])):
        assert valor in texto
    assert modelo["llantas"]["trasera"]["valor"] in texto
    for prohibido in ("{", "}", "`", ".yaml", "Pydantic", "determinista"):
        assert prohibido not in texto


def test_fuentes_de_la_moto_van_en_metadatos(catalogo: dict[str, Any]) -> None:
    fuentes = fuentes_datos_moto(catalogo, "data/catalogo/motos_honda.yaml")
    assert fuentes["archivo"] == "data/catalogo/motos_honda.yaml"
    assert fuentes["origen"] == "demostrativo"
    assert fuentes["urls"] == ["https://motos.honda.com.co/"]


def test_estadisticas_con_la_cifra_del_tema() -> None:
    datos = json.loads((RAIZ_PROYECTO / "data" / "gold" / "estadisticas.json").read_text(encoding="utf-8"))
    texto = redactar_estadisticas("Compara la sostenibilidad del documento con las estadísticas", datos)
    assert f"{datos['documentos']} documentos" in texto
    assert f"{datos['secciones']['sostenibilidad']} de sus {datos['fragmentos']} textos" in texto


def _fragmento(i: int, texto: str) -> Fragmento:
    return Fragmento(
        id=f"doc#{i:03d}", documento_id="doc", url=f"https://ejemplo-fna.test/{i}", titulo=f"Doc {i}",
        seccion="empresa", texto=texto, tokens_aprox=len(texto.split()), orden=i,
    )  # fmt: skip


def test_documental_usa_oraciones_completas_y_cita_solo_lo_usado() -> None:
    fragmentos = [
        _fragmento(0, "## Fundación\nLa Fundación Fanalca nace en el 2003 para construir cultura ciudadana."),
        _fragmento(1, "- Autor de la entrada: Persona Ficticia\nINICIO | NOSOTROS | NEGOCIOS | CONTACTO"),
        _fragmento(2, "Las plantas de autopartes están en Yumbo, Bogotá y Medellín, según el sitio."),
    ]
    texto, usados = redactar_documental(
        "¿Qué hace la Fundación Fanalca?", fragmentos, [f.texto for f in fragmentos]
    )
    assert texto.split(". ")[0] + "." in ENTRADAS_DOCUMENTAL or texto.startswith(ENTRADAS_DOCUMENTAL)
    assert "La Fundación Fanalca nace en el 2003 para construir cultura ciudadana." in texto
    assert "Autor de la entrada" not in texto and "Persona Ficticia" not in texto
    assert [f.id for f in usados] == ["doc#000"]


def test_en_la_ruta_mixta_solo_cuenta_el_tema() -> None:
    """Una oración que solo comparte «estructurado» con la pregunta no se elige; la del tema, sí."""
    fragmentos = [
        _fragmento(
            0, "Una buena pregunta, un prompt bien estructurado, marca la diferencia en la respuesta."
        ),
        _fragmento(1, "Fanalca presenta cada año su informe de sostenibilidad con indicadores ambientales."),
    ]
    pregunta = "Compara lo que dice el corpus sobre sostenibilidad con las cifras de los datos estructurados."
    texto, usados = redactar_documental(pregunta, fragmentos, [f.texto for f in fragmentos])
    assert "prompt" not in texto
    assert "informe de sostenibilidad" in texto
    assert [f.id for f in usados] == ["doc#001"]

    # Con «estructurados» y un tema que la oración no trata, la coincidencia en «estructurado» no basta.
    solo_estructurado, _ = redactar_documental(
        "¿Qué datos estructurados hay sobre las plantas?", fragmentos[:1], [fragmentos[0].texto]
    )
    assert solo_estructurado == ""


def test_documental_sin_oraciones_pertinentes_queda_vacio() -> None:
    fragmentos = [_fragmento(0, "Honda es la marca número uno en motocicletas a nivel mundial.")]
    texto, usados = redactar_documental(
        "¿Quién ganó el último partido de fútbol?", fragmentos, [fragmentos[0].texto]
    )
    assert texto == "" and usados == []
