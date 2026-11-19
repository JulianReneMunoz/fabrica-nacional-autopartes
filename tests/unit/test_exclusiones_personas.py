"""Exclusiones de IGNIS por datos personales (Ley 1581): documentos que nombran a personas naturales. No
dependen del Gold versionado (leen solo config/ignis_exclusiones.yaml), así que corren también en el CI."""

from __future__ import annotations

import yaml

from fabrica_autopartes.core.config import RAIZ_PROYECTO
from fabrica_autopartes.services.agente_ignis_m2 import RUTA_EXCLUSIONES, documentos_excluidos

EXALTACION_CONCEJO = "nuestra-fundacion-fanalca-recibe-exaltacion-de-honor-del-concejo-de-cali"
LISTADO_NOTICIAS = "noticias"
PREFIJO_PRESIDENTE = "nuestro-presidente-"


def test_la_noticia_de_la_exaltacion_del_concejo_esta_excluida() -> None:
    assert EXALTACION_CONCEJO in documentos_excluidos()


def test_el_listado_de_noticias_esta_excluido_por_la_ley_1581() -> None:
    assert LISTADO_NOTICIAS in documentos_excluidos()
    datos = yaml.safe_load(RUTA_EXCLUSIONES.read_text(encoding="utf-8"))
    (entrada,) = [e for e in datos["documentos"] if e["id"] == LISTADO_NOTICIAS]
    assert entrada["motivo"] == "Listado del blog con titulares y nombres de personas (Ley 1581)."


def test_la_entrada_del_blog_sobre_el_presidente_esta_excluida() -> None:
    """Se busca por el prefijo del id: el id completo contiene el nombre de una persona y no se escribe
    aquí."""
    datos = yaml.safe_load(RUTA_EXCLUSIONES.read_text(encoding="utf-8"))
    entradas = [e for e in datos["documentos"] if e["id"].startswith(PREFIJO_PRESIDENTE)]
    assert len(entradas) == 1
    assert entradas[0]["motivo"] == "Entrada del blog centrada en una persona natural (Ley 1581)."
    assert entradas[0]["id"] in documentos_excluidos()


def test_hay_tres_exclusiones_por_personas_naturales() -> None:
    datos = yaml.safe_load(RUTA_EXCLUSIONES.read_text(encoding="utf-8"))
    por_personas = {
        e["id"]
        for e in datos["documentos"]
        if "persona natural" in e["motivo"] or "titulares y nombres de personas" in e["motivo"]
    }
    assert len(por_personas) == 3
    assert {EXALTACION_CONCEJO, LISTADO_NOTICIAS} <= por_personas
    assert any(i.startswith(PREFIJO_PRESIDENTE) for i in por_personas)
    assert por_personas <= documentos_excluidos()


def test_la_exclusion_documenta_el_motivo_de_la_ley_1581() -> None:
    datos = yaml.safe_load(RUTA_EXCLUSIONES.read_text(encoding="utf-8"))
    entradas = [e for e in datos["documentos"] if e["id"] == EXALTACION_CONCEJO]
    assert len(entradas) == 1
    assert entradas[0]["motivo"] == "nombra a una persona natural (Ley 1581)"
    assert RUTA_EXCLUSIONES == RAIZ_PROYECTO / "config" / "ignis_exclusiones.yaml"
