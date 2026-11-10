"""Salvaguardas posteriores a la generación (controles contra respuestas no fundamentadas).

1. Análisis tolerante del JSON devuelto por el modelo.
2. Verificación de citas: toda fuente citada debe existir en el contexto entregado.
3. Verificación léxica de fundamentación: proporción de términos de la respuesta que
   aparecen en los fragmentos citados (o en todo el contexto si no hay citas); los ids y
   las URL citados no cuentan como términos.
4. Detección de intentos de inyección en la pregunta del usuario.
"""

from __future__ import annotations

import json
import re
from typing import Any

from fabrica_autopartes.knowledge.recuperacion import tokenizar
from fabrica_autopartes.llm.extractivo import RECHAZO

_INYECCION = re.compile(
    r"ignor(a|ar|e)\s+(todas\s+)?(las\s+|tus\s+)?(instrucciones|reglas)|olvida\s+(las\s+|tus\s+)?reglas|"
    r"ignore (all|previous|the) instructions|system prompt|prompt de sistema|"
    r"act[uú]a como|revela (tu|el) (prompt|mensaje)|jailbreak|modo desarrollador",
    re.I,
)
UMBRAL_FUNDAMENTACION = 0.6
# URL en texto libre: termina en un espacio, cierre de paréntesis o corchete, comillas, coma o punto y coma.
URL = re.compile(r"https?://[^\s)\]>,;\"'`]+")


def normalizar_url(url: str) -> str:
    """Sin el punto final de la frase ni la barra final (``https://x.co/a/.`` → ``https://x.co/a``)."""
    return url.rstrip(".").rstrip("/")


def urls_en(texto: str) -> list[str]:
    """URL presentes en ``texto``, normalizadas con ``normalizar_url`` y en orden de aparición."""
    return [normalizar_url(m.group(0)) for m in URL.finditer(texto)]


def quitar_urls(texto: str) -> str:
    return URL.sub(" ", texto)


def analizar_json(texto: str) -> dict[str, Any] | None:
    limpio = texto.strip()
    limpio = re.sub(r"^```(?:json)?\s*|\s*```$", "", limpio, flags=re.S)
    try:
        valor = json.loads(limpio)
        return valor if isinstance(valor, dict) else None
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", limpio, re.S)
        if m:
            try:
                valor = json.loads(m.group(0))
                return valor if isinstance(valor, dict) else None
            except json.JSONDecodeError:
                return None
    return None


def extraer_citas_texto(texto: str) -> list[str]:
    ids: list[str] = []
    for m in re.finditer(r"\[([^\]]+)\]", texto):
        for parte in m.group(1).split(","):
            parte = parte.strip()
            if re.fullmatch(r"[a-z0-9][a-z0-9\-]*#\d{3}", parte) and parte not in ids:
                ids.append(parte)
    return ids


def quitar_citas(texto: str) -> str:
    return re.sub(r"\s*\[[a-z0-9\-]+#\d{3}(?:,\s*[a-z0-9\-]+#\d{3})*\]", "", texto).strip()


def es_rechazo(texto: str) -> bool:
    t = texto.lower()
    return RECHAZO.lower()[:45] in t or "no se encuentra en la base de conocimiento" in t


def puntaje_fundamentacion(respuesta: str, contexto: str) -> float:
    """Proporción de términos de la respuesta presentes en ``contexto``.

    Los ids entre corchetes y las URL de la respuesta no cuentan como términos (A-09): son citas, no
    contenido.
    """
    terminos = set(tokenizar(quitar_urls(quitar_citas(respuesta))))
    if not terminos:
        return 0.0
    vocab = set(tokenizar(contexto))
    return round(len(terminos & vocab) / len(terminos), 3)


def detectar_inyeccion(pregunta: str) -> bool:
    return bool(_INYECCION.search(pregunta))
