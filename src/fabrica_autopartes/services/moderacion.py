"""Moderación básica de IGNIS (caso 6 del OpenSpec ``casos-validacion-ignis``): se ejecuta antes del router.

Reglas deterministas con el léxico de ``config/moderacion.yaml`` (sin tildes). Un mensaje bloqueado no pasa
por búsqueda, herramientas ni citas, y recibe un texto fijo, calmado y respetuoso que nunca repite el mensaje
del cliente. En el historial y la auditoría se guarda la categoría, no el texto (lo hace el agente).
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel

from fabrica_autopartes.core.config import RAIZ_PROYECTO
from fabrica_autopartes.llm.salvaguardas import detectar_inyeccion
from fabrica_autopartes.pipelines.texto import sin_tildes

RUTA_LEXICO = RAIZ_PROYECTO / "config" / "moderacion.yaml"

CategoriaModeracion = Literal[
    "insulto_a_ignis",
    "groserias_repetidas",
    "frustracion_con_servicio",
    "datos_de_terceros",
    "insulto_y_datos_de_terceros",
    "amenaza_violencia",
    "odio_discriminacion",
    "acoso_sexual",
    "manipulacion",
    "crisis_personal",
    "pausa",
]

# Textos fijos por categoría (variantes): calma, sin sermones, como máximo unas 40 palabras y siempre una
# salida.
TEXTOS_MODERACION: dict[str, tuple[str, ...]] = {
    "insulto_a_ignis": (
        "Entiendo que estés molesto y quiero ayudarte. ¿Me cuentas qué necesitas sobre Fanalca y lo intento "
        "de nuevo?",
        "Siento no haberte ayudado como esperabas. Dime qué buscas y lo intento otra vez.",
    ),
    "groserias_repetidas": (
        "Prefiero que sigamos con respeto para poder ayudarte bien. Cuando quieras, pregúntame lo que "
        "necesites sobre Fanalca.",
    ),
    "frustracion_con_servicio": (
        "Lamento mucho que hayas tenido una mala experiencia. Puedo darte los canales oficiales de atención "
        "y garantías para que revisen tu caso. ¿Te los comparto?",
    ),
    "datos_de_terceros": (
        "No puedo compartir datos personales de nadie, así lo protege la ley de protección de datos. Sí "
        "puedo darte los canales oficiales de contacto de Fanalca. ¿Te los comparto?",
    ),
    "insulto_y_datos_de_terceros": (
        "Entiendo que estés molesto. No puedo compartir datos personales de nadie, pero sí los canales "
        "oficiales de contacto de Fanalca. ¿Te los comparto?",
    ),
    "amenaza_violencia": (
        "No puedo ayudar con eso. Si alguien está en peligro, llama ya a la línea de emergencias 123.",
    ),
    "odio_discriminacion": (
        "No puedo responder a mensajes que ofenden a personas o grupos. Si quieres, sigo ayudándote con "
        "información de Fanalca.",
    ),
    "acoso_sexual": ("Ese tema no lo puedo tratar. Estoy aquí para ayudarte con información de Fanalca.",),
    "manipulacion": (
        "No puedo cambiar mis reglas, pero con gusto te ayudo con lo que necesites saber de Fanalca.",
    ),
    "crisis_personal": (
        "Siento mucho que estés pasando por esto; gracias por contármelo. Hay personas que pueden "
        "acompañarte: en Colombia puedes llamar gratis a la Línea 192, opción 4, de salud mental del "
        "Ministerio de Salud. Si estás en peligro, llama al 123.",
    ),
    "pausa": (
        "Voy a hacer una pausa en esta conversación. Cuando quieras retomarla con respeto, aquí estaré para "
        "ayudarte.",
    ),
}

# Categorías que nunca se cambian por la pausa: la seguridad va primero.
_SIEMPRE_CON_SU_TEXTO = {"crisis_personal", "amenaza_violencia"}
# Bloqueos seguidos (contando el actual) a partir de los cuales se responde con la pausa.
BLOQUEOS_PARA_PAUSA = 3
DISTANCIA_MAXIMA_AMENAZA = 4
# Enclíticos que siempre son el objetivo («matarte», «quemarles»).
_ENCLITICOS_PERSONA = {"te", "le", "les", "nos"}
# Enclíticos que pueden ser una cosa («explotarla»): solo son el objetivo con verbos contra personas.
_ENCLITICOS_AMBIGUOS = {"lo", "la", "los", "las"}


class LexicoModeracion(BaseModel):
    version: int
    crisis_personal: list[str]
    amenaza_verbos: list[str]
    amenaza_verbos_contra_personas: list[str]
    amenaza_formas: list[str]
    amenaza_objetivos: list[str]
    amenaza_frases: list[str]
    manipulacion: list[str]
    acoso_sexual: list[str]
    odio_discriminacion: list[str]
    insultos: list[str]
    groserias: list[str]
    frustracion_con_servicio: list[str]
    terceros_datos: list[str]
    terceros_personas: list[str]


@lru_cache(maxsize=4)
def cargar_lexico(ruta: Path = RUTA_LEXICO) -> LexicoModeracion:
    return LexicoModeracion.model_validate(yaml.safe_load(ruta.read_text(encoding="utf-8")))


@dataclass(frozen=True)
class Moderacion:
    categoria: CategoriaModeracion | None
    bloqueada: bool
    texto: str


SIN_BLOQUEO = Moderacion(categoria=None, bloqueada=False, texto="")


def normalizar_mensaje(mensaje: str) -> str:
    """Minúsculas, sin tildes y solo letras y números separados por un espacio."""
    return " ".join(re.findall(r"[a-z0-9ñ]+", sin_tildes(mensaje)))


def _tiene(texto: str, frases: list[str]) -> bool:
    return any(f" {f} " in f" {texto} " for f in frases)


def _cuenta(texto: str, frases: list[str]) -> int:
    relleno = f" {texto} "
    return sum(relleno.count(f" {f} ") for f in frases)


def _verbo_de_amenaza(
    palabras: list[str], i: int, lexico: LexicoModeracion
) -> Literal["no", "si", "objetivo"]:
    """``"objetivo"`` si la palabra ya trae el objetivo (enclítico), ``"si"`` si es un verbo de amenaza que
    necesita un objetivo cerca y ``"no"`` en otro caso."""
    palabra = palabras[i]
    if palabra in lexico.amenaza_formas:
        # «¿Se quemó la planta?» es impersonal o reflexivo; «les quemo la sede» sí es una amenaza.
        return "si" if i == 0 or palabras[i - 1] != "se" else "no"
    for verbo in lexico.amenaza_verbos:
        if not palabra.startswith(verbo):
            continue
        resto = palabra[len(verbo) :]
        if resto == "":
            return "si"
        if resto in _ENCLITICOS_PERSONA:
            return "objetivo"
        if resto in _ENCLITICOS_AMBIGUOS:
            return "objetivo" if verbo in lexico.amenaza_verbos_contra_personas else "si"
        return "no"  # «volaron», «incendio»: otra palabra que solo comparte el comienzo
    return "no"


def _es_amenaza(texto: str, lexico: LexicoModeracion) -> bool:
    """Verbo de amenaza con una persona o una instalación como objetivo, a 4 palabras o menos (ver el
    YAML)."""
    if _tiene(texto, lexico.amenaza_frases):
        return True
    palabras = texto.split()
    objetivos = set(lexico.amenaza_objetivos)
    for i in range(len(palabras)):
        tipo = _verbo_de_amenaza(palabras, i, lexico)
        if tipo == "objetivo":
            return True
        if tipo == "si":
            cerca = (
                palabras[max(0, i - DISTANCIA_MAXIMA_AMENAZA) : i]
                + palabras[i + 1 : i + 1 + DISTANCIA_MAXIMA_AMENAZA]
            )
            if objetivos.intersection(cerca):
                return True
    return False


def _pide_datos_de_terceros(texto: str, lexico: LexicoModeracion) -> bool:
    return _tiene(texto, lexico.terceros_datos) and _tiene(texto, lexico.terceros_personas)


def _respuestas(historial: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [t.get("metadatos") or {} for t in historial if t.get("role") == "assistant"]


def _ultima_categoria(historial: list[dict[str, Any]]) -> str | None:
    respuestas = _respuestas(historial)
    return respuestas[-1].get("categoria_moderacion") if respuestas else None


def clasificar(mensaje: str, historial: list[dict[str, Any]] | None = None) -> CategoriaModeracion | None:
    """Categoría del mensaje o ``None`` si es una pregunta normal (las mayúsculas y los «!» sin insultos no
    son agresión). El orden da prioridad a la seguridad: crisis y amenazas primero."""
    lexico = cargar_lexico()
    texto = normalizar_mensaje(mensaje)
    if not texto:
        return None
    if _tiene(texto, lexico.crisis_personal):
        return "crisis_personal"
    if _es_amenaza(texto, lexico):
        return "amenaza_violencia"
    if detectar_inyeccion(mensaje) or _tiene(texto, lexico.manipulacion):
        return "manipulacion"
    if _tiene(texto, lexico.acoso_sexual):
        return "acoso_sexual"
    if _tiene(texto, lexico.odio_discriminacion):
        return "odio_discriminacion"
    insulto = _tiene(texto, lexico.insultos)
    if _pide_datos_de_terceros(texto, lexico):
        return "insulto_y_datos_de_terceros" if insulto else "datos_de_terceros"
    groserias = _cuenta(texto, lexico.groserias)
    previa = _ultima_categoria(historial or [])
    if groserias >= 2 or (groserias and previa in {"insulto_a_ignis", "groserias_repetidas"}):
        return "groserias_repetidas"
    if insulto or groserias:
        return "insulto_a_ignis"
    if _tiene(texto, lexico.frustracion_con_servicio):
        return "frustracion_con_servicio"
    return None


def bloqueos_seguidos(historial: list[dict[str, Any]]) -> int:
    """Respuestas bloqueadas consecutivas al final del historial del hilo."""
    n = 0
    for meta in reversed(_respuestas(historial)):
        if not meta.get("bloqueada"):
            break
        n += 1
    return n


def elegir_variante(variantes: tuple[str, ...], semilla: str) -> str:
    """Variante determinista: la misma semilla (hilo y turno) da siempre el mismo texto."""
    indice = int(hashlib.sha256(semilla.encode("utf-8")).hexdigest(), 16) % len(variantes)
    return variantes[indice]


def moderar(mensaje: str, historial: list[dict[str, Any]] | None = None, semilla: str = "") -> Moderacion:
    """Moderación antes del router. ``historial`` es el del hilo (``obtener_historial``, con metadatos) y
    ``semilla`` elige la variante del texto (hilo y número de turno). Con ``BLOQUEOS_PARA_PAUSA`` bloqueos
    seguidos (contando el actual) responde la pausa; la conversación no se cierra y un mensaje respetuoso
    sigue normal."""
    historial = historial or []
    categoria = clasificar(mensaje, historial)
    if categoria is None:
        return SIN_BLOQUEO
    if categoria not in _SIEMPRE_CON_SU_TEXTO and bloqueos_seguidos(historial) >= BLOQUEOS_PARA_PAUSA - 1:
        categoria = "pausa"
    texto = elegir_variante(TEXTOS_MODERACION[categoria], semilla)
    return Moderacion(categoria=categoria, bloqueada=True, texto=texto)
