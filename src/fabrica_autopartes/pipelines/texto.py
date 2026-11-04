"""Utilidades de normalización de texto y estimación de tokens."""

from __future__ import annotations

import hashlib
import math
import re
import unicodedata

_ESPACIOS = re.compile(r"[ \t ​]+")
_SALTOS = re.compile(r"\n{3,}")
_CORREO = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")


def normalizar(texto: str) -> str:
    texto = unicodedata.normalize("NFC", texto)
    texto = texto.replace("\r\n", "\n").replace("\r", "\n")
    lineas = [_ESPACIOS.sub(" ", linea).strip() for linea in texto.split("\n")]
    texto = "\n".join(lineas)
    return _SALTOS.sub("\n\n", texto).strip()


def hash_texto(texto: str) -> str:
    return hashlib.sha256(normalizar(texto).lower().encode("utf-8")).hexdigest()


def tokens_aprox(texto: str) -> int:
    """Estimación conservadora (≈4 caracteres por token). No reemplaza al tokenizador
    real del modelo; se usa para presupuestar el contexto."""
    return math.ceil(len(texto) / 4)


def tejas(texto: str, n: int = 5) -> set[str]:
    palabras = re.findall(r"\w+", texto.lower())
    if len(palabras) < n:
        return {" ".join(palabras)}
    return {" ".join(palabras[i : i + n]) for i in range(len(palabras) - n + 1)}


def similitud_jaccard(a: str, b: str) -> float:
    ta, tb = tejas(a), tejas(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


DOMINIOS_CORPORATIVOS = (
    "fanalca.com",
    "fanalca.com.co",
    "autopartesfanalca.com.co",
    "autopartesfanalca.com",
)


def es_correo_corporativo(correo: str, dominios: tuple[str, ...] = DOMINIOS_CORPORATIVOS) -> bool:
    dominio = correo.lower().rsplit("@", 1)[-1].rstrip(".")
    return any(dominio == d or dominio.endswith("." + d) for d in dominios)


def contiene_datos_personales(texto: str) -> bool:
    """Detecta correos no corporativos (posibles datos personales, Ley 1581 de 2012)."""
    return any(not es_correo_corporativo(m.group(0)) for m in _CORREO.finditer(texto))


def anonimizar_correos(texto: str, dominios: tuple[str, ...] = DOMINIOS_CORPORATIVOS) -> str:
    """Conserva buzones corporativos publicados y oculta cualquier otro correo."""

    def _reemplazo(m: re.Match[str]) -> str:
        correo = m.group(0)
        return correo if es_correo_corporativo(correo, dominios) else "[correo omitido]"

    return _CORREO.sub(_reemplazo, texto)
