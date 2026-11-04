"""Configuración de registro de eventos (logging) en formato legible y estructurado."""

from __future__ import annotations

import logging
import sys

_FORMATO = "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s"


def configurar_registro(nivel: str = "INFO") -> None:
    """Configura el registro raíz una sola vez."""
    raiz = logging.getLogger()
    if any(getattr(h, "_fna", False) for h in raiz.handlers):
        raiz.setLevel(nivel)
        return
    manejador = logging.StreamHandler(sys.stderr)
    manejador.setFormatter(logging.Formatter(_FORMATO))
    manejador._fna = True  # type: ignore[attr-defined]
    raiz.addHandler(manejador)
    raiz.setLevel(nivel)


def obtener_registro(nombre: str) -> logging.Logger:
    return logging.getLogger(nombre)
