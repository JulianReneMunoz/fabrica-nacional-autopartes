"""Preferencias de largo plazo de un usuario (ADR-033, casos 2A y 2B del OpenSpec ``casos-validacion-ignis``).

- Solo se guardan **valores canónicos de vocabularios cerrados**: nunca texto libre del usuario. Así ningún
  nombre, empresa, correo, teléfono ni documento puede llegar al Store (Ley 1581 de 2012).
- La memoria solo se activa con una orden explícita («recuérdalo», «recuerda que», «guárdalo», «guarda esto»,
  «guarda que», «guarda mis») o con la consulta «¿qué preferencias tengo?», y la orden solo desvía la
  pregunta si trae preferencias reconocidas o una autopresentación. «Prefiero» o «me interesa» por sí
  solos no la desvían.
- El Store usa el namespace ``("preferencias", user_id)``, con ``user_id`` seudónimo, y se lee con
  ``search()``.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Literal

from langgraph.store.base import BaseStore

from fabrica_autopartes.pipelines.texto import anonimizar_datos_personales, omitir_autopresentaciones

ESPACIO_PREFERENCIAS = "preferencias"

ClavePreferencia = Literal["area_laboral", "formato_respuesta", "linea_producto"]

# Orden de presentación y etiqueta legible de cada clave.
ETIQUETAS: dict[ClavePreferencia, str] = {
    "area_laboral": "área laboral",
    "formato_respuesta": "formato de respuesta",
    "linea_producto": "línea de producto",
}

# Vocabularios cerrados: forma normalizada (minúsculas, sin tildes) → valor canónico guardado.
AREAS_LABORALES: dict[str, str] = {
    "compras de repuestos": "compras de repuestos",
    "compras": "compras",
    "ventas": "ventas",
    "posventa": "posventa",
    "postventa": "posventa",
    "servicio tecnico": "servicio técnico",
    "logistica": "logística",
    "mantenimiento": "mantenimiento",
    "garantias": "garantías",
}
FORMATOS: dict[str, str] = {
    "breves": "breve",
    "cortas": "breve",
    "concisas": "breve",
    "detalladas": "detallada",
    "extensas": "detallada",
    "completas": "detallada",
}
LINEAS: dict[str, str] = {
    "motocicletas": "motocicletas",
    "motos": "motocicletas",
    "autopartes": "autopartes",
    "repuestos": "repuestos",
}

# Sobre texto normalizado (sin tildes): «guárdalo» → «guardalo». «Guarda» suelto no es una orden
# («¿Fanalca guarda relación con Honda?»).
_ORDEN_GUARDAR = re.compile(
    r"\b(?:recuerdal[oa]|recuerda\s+que|guardal[oa]|guarda\s+(?:esto|esta|que|mis?))\b"
)
_CONSULTA = re.compile(r"\bque\s+preferencias\s+tengo\b")
# Preguntas por datos personales del propio usuario: IGNIS no los guarda, así que responde el aviso de la
# Ley 1581 sin buscar en el corpus. Cada frase va anclada al final de la pregunta: al quitar tildes,
# «¿Dónde trabajó el fundador…?» queda como «donde trabajo el fundador…» y no debe dar el aviso.
_PREGUNTA_DATO_PERSONAL = re.compile(
    r"\b(?:como\s+me\s+llamo|donde\s+trabajo|cual\s+es\s+mi\s+nombre)(?:\s+yo)?\s*(?:\?|$)"
)
_AREA = re.compile(
    r"\btrabajo\s+en\s+(?:el\s+area\s+de\s+|la\s+seccion\s+de\s+|el\s+departamento\s+de\s+)?"
    r"(?P<area>[a-z ]+?)(?=\s+y\s|[,.;:!?]|$)"
)
_FORMATO = re.compile(r"\bprefiero\s+(?:las\s+|unas\s+)?respuestas\s+(?P<formato>[a-z]+)")
_LINEA = re.compile(r"\bme\s+interesa(?:n)?\s+(?:mucho\s+)?(?:las\s+|los\s+|la\s+|el\s+)?(?P<linea>[a-z]+)")


def _normalizar(texto: str) -> str:
    """Minúsculas, sin tildes y con espacios simples (la «ñ» se conserva: su tilde combinante es U+0303)."""
    descompuesto = unicodedata.normalize("NFD", texto.lower())
    sin_tildes = "".join(c for c in descompuesto if unicodedata.category(c) != "Mn" or c == "\u0303")
    return re.sub(r"\s+", " ", unicodedata.normalize("NFC", sin_tildes)).strip()


def pregunta_dato_personal(mensaje: str) -> bool:
    """«¿Cómo me llamo?», «¿Dónde trabajo?» o «¿Cuál es mi nombre?»: datos que IGNIS no guarda (Ley 1581)."""
    return bool(_PREGUNTA_DATO_PERSONAL.search(_normalizar(mensaje)))


def tiene_autopresentacion(mensaje: str) -> bool:
    """«Me llamo…», «mi nombre es…», «soy Nombre…», «trabajo en…» o «mi empresa es…» (``pipelines.texto``)."""
    return omitir_autopresentaciones(mensaje) != mensaje


# «Trabajo en <área del vocabulario>» sobre el texto original (con o sin tildes): no es un dato personal.
_AREAS_ALTERNATIVAS = "|".join(
    sorted({re.escape(v) for par in AREAS_LABORALES.items() for v in par}, key=len, reverse=True)
)
_AREA_ORIGINAL = re.compile(
    r"(?i)\btrabajo\s+en\s+(?:el\s+[áa]rea\s+de\s+|la\s+secci[óo]n\s+de\s+|el\s+departamento\s+de\s+)?"
    rf"(?:{_AREAS_ALTERNATIVAS})\b"
)


def descarta_datos_personales(mensaje: str) -> bool:
    """Verdadero si, sin la frase «trabajo en <área reconocida>», queda una autopresentación (nombre o
    empresa) que no se guarda: la respuesta debe decirlo (Ley 1581 de 2012)."""
    return tiene_autopresentacion(_AREA_ORIGINAL.sub("", mensaje))


def extraer_preferencias(mensaje: str) -> dict[ClavePreferencia, str]:
    """Preferencias reconocidas en el mensaje, solo con valores de los vocabularios cerrados.

    «Trabajo en compras de repuestos» guarda el área; «trabajo en Empresa X» no guarda nada porque «empresa x»
    no está en la lista. Los datos de contacto se ocultan antes de buscar (defensa adicional).
    """
    texto = _normalizar(anonimizar_datos_personales(mensaje))
    prefs: dict[ClavePreferencia, str] = {}
    if (m := _AREA.search(texto)) and (area := AREAS_LABORALES.get(m.group("area").strip())):
        prefs["area_laboral"] = area
    if (m := _FORMATO.search(texto)) and (formato := FORMATOS.get(m.group("formato"))):
        prefs["formato_respuesta"] = formato
    if (m := _LINEA.search(texto)) and (linea := LINEAS.get(m.group("linea"))):
        prefs["linea_producto"] = linea
    return prefs


def decidir_memoria(mensaje: str) -> Literal["guardar", "consultar"] | None:
    """Ruta de memoria del mensaje, o ``None`` si la pregunta debe seguir su ruta normal.

    - ``consultar``: «¿qué preferencias tengo?».
    - ``guardar``: orden explícita **y** (preferencias reconocidas o autopresentación). Con
      autopresentación y sin preferencias, la respuesta explica que no se guardan datos personales
      (Ley 1581 de 2012).
    - ``None``: sin orden, o con una orden que no trae nada que guardar («Recuerda que la garantía cubre
      motores, ¿cuánto dura?»).
    """
    texto = _normalizar(mensaje)
    if _CONSULTA.search(texto):
        return "consultar"
    if _ORDEN_GUARDAR.search(texto) and (extraer_preferencias(mensaje) or tiene_autopresentacion(mensaje)):
        return "guardar"
    return None


def _espacio(user_id: str) -> tuple[str, str]:
    if not user_id:
        raise ValueError("user_id vacío")
    return (ESPACIO_PREFERENCIAS, user_id)


def guardar_preferencias(store: BaseStore, user_id: str, prefs: dict[ClavePreferencia, str]) -> None:
    """Guarda cada preferencia como un ítem del namespace del usuario (una clave del vocabulario por ítem)."""
    espacio = _espacio(user_id)
    for clave, valor in prefs.items():
        store.put(espacio, clave, {"valor": valor})


def consultar_preferencias(store: BaseStore, user_id: str) -> dict[ClavePreferencia, str]:
    """Preferencias del usuario recuperadas con ``search()`` sobre su namespace.

    ``search()`` filtra por prefijo de namespace; además se exige ``item.namespace == espacio`` para que un
    ``user_id`` nunca reciba ítems de otro aunque compartan prefijo («u1» y «u10»).
    """
    espacio = _espacio(user_id)
    encontradas = {
        item.key: item.value.get("valor")
        for item in store.search(espacio, limit=50)
        if tuple(item.namespace) == espacio
    }
    return {clave: valor for clave in ETIQUETAS if isinstance(valor := encontradas.get(clave), str) and valor}


def describir_preferencias(prefs: dict[ClavePreferencia, str]) -> str:
    """«área laboral: compras de repuestos; formato de respuesta: breve; …» en el orden de ``ETIQUETAS``."""
    return "; ".join(f"{ETIQUETAS[clave]}: {prefs[clave]}" for clave in ETIQUETAS if clave in prefs)
