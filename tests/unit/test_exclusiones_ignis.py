"""Exclusiones de IGNIS (config/ignis_exclusiones.yaml) contra el corpus Gold: todo documento cuyos
fragmentos solo traen metadatos del blog («Autor/Publicación/Categoría de la entrada», con nombres de
personas) debe estar excluido, y cada exclusión debe existir en el corpus. Los archivos del corpus no se
borran."""

from __future__ import annotations

import json
import re

import yaml

from fabrica_autopartes.core.config import RAIZ_PROYECTO

FRAGMENTOS = RAIZ_PROYECTO / "data" / "gold" / "fragmentos.jsonl"
EXCLUSIONES = RAIZ_PROYECTO / "config" / "ignis_exclusiones.yaml"
_METADATOS_BLOG = re.compile(r"(autor|publicaci[oó]n|categor[ií]a) de la entrada", re.IGNORECASE)


def _palabras_de_contenido(texto: str) -> int:
    """Palabras que quedan al quitar las líneas de metadatos del blog."""
    resto = " ".join(linea for linea in texto.split("\n") if not _METADATOS_BLOG.search(linea))
    return len(re.findall(r"[^\W\d_]+", resto))


def _corpus() -> dict[str, list[dict[str, str]]]:
    documentos: dict[str, list[dict[str, str]]] = {}
    for linea in FRAGMENTOS.read_text(encoding="utf-8").splitlines():
        fragmento = json.loads(linea)
        documentos.setdefault(fragmento["documento_id"], []).append(fragmento)
    return documentos


def _excluidos() -> set[str]:
    datos = yaml.safe_load(EXCLUSIONES.read_text(encoding="utf-8"))
    return {entrada["id"] for entrada in datos["documentos"]}


def test_todo_documento_sin_contenido_esta_excluido() -> None:
    sin_contenido = {
        documento
        for documento, fragmentos in _corpus().items()
        if all(_palabras_de_contenido(f["texto"]) == 0 for f in fragmentos)
    }
    assert sin_contenido, "la prueba debe encontrar los listados del blog del corpus"
    faltantes = sorted(sin_contenido - _excluidos())
    assert not faltantes, f"documentos sin contenido que IGNIS no excluye: {faltantes}"


def test_cada_exclusion_existe_en_el_corpus_y_tiene_motivo() -> None:
    corpus = _corpus()
    datos = yaml.safe_load(EXCLUSIONES.read_text(encoding="utf-8"))
    for entrada in datos["documentos"]:
        assert entrada["id"] in corpus, entrada["id"]
        assert entrada["motivo"].strip()
