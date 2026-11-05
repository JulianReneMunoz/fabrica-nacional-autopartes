"""Recuperación léxica BM25 (Okapi) implementada sin dependencias externas.

Extensión propuesta (no exigida por el Módulo 1): permite seleccionar los fragmentos
más pertinentes cuando la base completa excede el presupuesto de contexto del modelo
local. En el Módulo 2 se sustituye o complementa con *embeddings* y una base vectorial.
"""

from __future__ import annotations

import math
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass

from fabrica_autopartes.domain.modelos import Fragmento

_PALABRAS_VACIAS = frozenset(
    [
        "a",
        "al",
        "algo",
        "algunas",
        "algunos",
        "ante",
        "antes",
        "como",
        "con",
        "contra",
        "cual",
        "cuales",
        "cuando",
        "de",
        "del",
        "desde",
        "donde",
        "dos",
        "el",
        "ella",
        "ellas",
        "ellos",
        "en",
        "entre",
        "era",
        "es",
        "esa",
        "esas",
        "ese",
        "eso",
        "esos",
        "esta",
        "estas",
        "este",
        "esto",
        "estos",
        "fue",
        "fueron",
        "ha",
        "han",
        "hasta",
        "hay",
        "la",
        "las",
        "le",
        "les",
        "lo",
        "los",
        "mas",
        "me",
        "mi",
        "mis",
        "muy",
        "no",
        "nos",
        "o",
        "otra",
        "otras",
        "otro",
        "otros",
        "para",
        "pero",
        "por",
        "que",
        "quien",
        "se",
        "sea",
        "ser",
        "si",
        "sin",
        "sobre",
        "son",
        "su",
        "sus",
        "tambien",
        "te",
        "tiene",
        "tienen",
        "un",
        "una",
        "unas",
        "uno",
        "unos",
        "y",
        "ya",
        "the",
        "of",
        "and",
        "to",
        "in",
        "for",
        "is",
        "are",
        "on",
        "with",
        "by",
        "at",
        "an",
        "or",
        "cuantos",
        "cuantas",
        "cuanto",
        "quienes",
    ]
)


def _sin_tildes(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn")


def tokenizar(texto: str) -> list[str]:
    palabras = re.findall(r"[a-z0-9]+", _sin_tildes(texto.lower()))
    resultado = []
    for p in palabras:
        if p in _PALABRAS_VACIAS or len(p) < 2:
            continue
        # raíz muy simple para plurales en español/inglés
        if len(p) > 4 and p.endswith("es"):
            p = p[:-2]
        elif len(p) > 3 and p.endswith("s"):
            p = p[:-1]
        resultado.append(p)
    return resultado


# Expansión de consultas de primer contacto: un cliente pregunta "¿dónde queda la sede?" y el sitio
# publica "Calle 13 # 31A - 80"; sin vocabulario compartido, BM25 no encuentra el fragmento. Cada grupo
# agrega términos relacionados con peso reducido (no reemplaza los términos de la pregunta).
_EXPANSIONES: tuple[tuple[frozenset[str], tuple[str, ...]], ...] = (
    (
        frozenset(
            {"donde", "queda", "ubica", "ubicada", "ubicado", "sede", "direccion", "oficina", "ubicacion"}
        ),
        ("direccion", "calle", "ubicacion", "sede", "contacto"),
    ),
    (
        frozenset({"telefono", "llamar", "contacto", "correo", "email", "whatsapp", "pbx", "comunicar"}),
        ("telefono", "correo", "contacto", "pbx"),
    ),
)
PESO_EXPANSION = 0.5


def expandir_consulta(terminos: list[str]) -> dict[str, float]:
    """Términos con su peso: 1.0 los de la pregunta y ``PESO_EXPANSION`` los agregados por sinónimos."""
    pesos = dict.fromkeys(terminos, 1.0)
    for disparadores, extra in _EXPANSIONES:
        if disparadores & set(terminos):
            for t in tokenizar(" ".join(extra)):
                pesos.setdefault(t, PESO_EXPANSION)
    return pesos


@dataclass
class Resultado:
    fragmento: Fragmento
    puntaje: float


class IndiceBM25:
    def __init__(self, fragmentos: list[Fragmento], k1: float = 1.5, b: float = 0.75) -> None:
        self.fragmentos = fragmentos
        self.k1, self.b = k1, b
        self._docs = [Counter(tokenizar(f"{f.titulo} {f.encabezado} {f.texto}")) for f in fragmentos]
        self._longitudes = [sum(d.values()) for d in self._docs]
        self._promedio = (sum(self._longitudes) / len(self._longitudes)) if self._docs else 0.0
        df: Counter[str] = Counter()
        for d in self._docs:
            df.update(d.keys())
        n = len(self._docs)
        self._idf = {t: math.log(1 + (n - f + 0.5) / (f + 0.5)) for t, f in df.items()}

    def buscar(self, consulta: str, k: int = 5) -> list[Resultado]:
        terminos = expandir_consulta(tokenizar(consulta))
        if not terminos or not self._docs:
            return []
        puntajes: list[tuple[float, int]] = []
        for i, doc in enumerate(self._docs):
            s = 0.0
            for t, peso in terminos.items():
                tf = doc.get(t, 0)
                if not tf:
                    continue
                norm = 1 - self.b + self.b * self._longitudes[i] / (self._promedio or 1)
                s += peso * self._idf.get(t, 0.0) * tf * (self.k1 + 1) / (tf + self.k1 * norm)
            if s > 0:
                puntajes.append((s, i))
        puntajes.sort(reverse=True)
        return [Resultado(self.fragmentos[i], round(s, 4)) for s, i in puntajes[:k]]
