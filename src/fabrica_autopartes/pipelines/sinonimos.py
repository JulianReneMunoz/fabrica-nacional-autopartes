"""Expansión determinista de consultas de IGNIS: términos que el cliente usa y que el sitio de Fanalca nombra
de otra forma. El sitio no usa «misión» ni «visión»: publica el propósito superior, los pilares estratégicos y
los valores corporativos. Solo la usa IGNIS; el buscador común del M1 no cambia (sus métricas deben
reproducirse)."""

from __future__ import annotations

import re

from fabrica_autopartes.pipelines.texto import sin_tildes

SINONIMOS: dict[str, tuple[str, ...]] = {
    "mision": ("propósito superior", "pilares estratégicos", "valores corporativos", "nosotros"),
    "vision": ("propósito superior", "pilares estratégicos", "valores corporativos", "nosotros"),
    "filosofia": ("propósito superior", "valores corporativos"),
    "quienes son": ("nosotros", "propósito superior"),
    "a que se dedica": ("negocios", "nosotros"),
    "a que se dedican": ("negocios", "nosotros"),
    "fabricas": ("plantas de producción",),
    "sedes": ("plantas de producción",),
}


def expandir_consulta(consulta: str) -> str:
    """Consulta original más los términos equivalentes (sin repetir), separados por espacios."""
    texto = " ".join(re.findall(r"[a-z0-9ñ]+", sin_tildes(consulta)))
    extra: list[str] = []
    for clave, terminos in SINONIMOS.items():
        if re.search(rf"\b{clave}\b", texto):
            extra.extend(t for t in terminos if t not in extra)
    return f"{consulta} {' '.join(extra)}".strip() if extra else consulta
