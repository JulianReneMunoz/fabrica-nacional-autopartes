"""Saludos, cortesía y textos de memoria de IGNIS (ruta ``directo`` y ``memoria_store``).

Textos fijos y deterministas, no generados por un LLM: se pueden probar, suenan bien en voz alta y no
dependen de la red. Cada categoría tiene una o varias variantes; se elige una con un hash del hilo y del
número de turno. Nunca se usa el nombre del cliente (Ley 1581 de 2012) ni se ofrecen precios o cotizaciones.
"""

from __future__ import annotations

import re
from typing import Any, Literal

from fabrica_autopartes.pipelines.texto import partir_oraciones
from fabrica_autopartes.services.moderacion import elegir_variante, normalizar_mensaje
from fabrica_autopartes.services.redactor_ignis import (
    CIERRE_PLANO,
    ENTRADAS_DOCUMENTAL,
    SEGUIMIENTO_DATOS,
    SEGUIMIENTO_DOCUMENTAL,
    SEGUIMIENTO_FICHA,
    SEGUIMIENTO_MIXTO,
)

CategoriaCortesia = Literal[
    "saludo",
    "como_estas",
    "quien_eres",
    "humano",
    "gracias",
    "ok",
    "despedida",
    "perdon",
    "elogio",
    "no_entendi",
    "vacio",
    "fuera_tema",
]

_SALUDO = r"(?:hola|holi|hey|saludos|buenas|buenos dias|buenas tardes|buenas noches|buen dia|que tal)"
_PATRONES: list[tuple[CategoriaCortesia, re.Pattern[str]]] = [
    (
        "humano",
        re.compile(
            r"\b(?:eres|sos|es usted) (?:un |una )?(?:humano|humana|persona|persona real)\b"
            r"|\bhablo con una persona\b"
        ),
    ),
    ("saludo", re.compile(rf"^{_SALUDO}(?: {_SALUDO})*(?: ignis)?$")),
    (
        "como_estas",
        re.compile(
            rf"^(?:{_SALUDO} )*(?:como estas|como vas|como te va|que tal estas|como andas)(?: ignis)?$"
        ),
    ),
    (
        "quien_eres",
        re.compile(
            rf"^(?:{_SALUDO} )*(?:quien eres|que eres|que puedes hacer|que sabes hacer"
            r"|en que me puedes ayudar|que haces|para que sirves)(?: tu| ignis)?$"
        ),
    ),
    (
        "gracias",
        re.compile(
            r"^(?:muchas |mil |muchisimas )?gracias"
            r"(?: ignis| por (?:todo|la ayuda|tu ayuda|la informacion))?$"
            r"|^te agradezco\b"
        ),
    ),
    (
        "ok",
        re.compile(
            r"^(?:ok|okay|okey|vale|listo|perfecto|entendido|de acuerdo|dale|bueno|bien|super|claro)$"
        ),
    ),
    (
        "despedida",
        re.compile(r"^(?:chao|chau|adios|hasta luego|hasta pronto|hasta manana|nos vemos|bye)(?: ignis)?$"),
    ),
    ("perdon", re.compile(r"^(?:perdon|perdona|disculpa|disculpe|lo siento|me equivoque)\b")),
    (
        "elogio",
        re.compile(
            r"^(?:eres genial|muy buena respuesta|excelente respuesta|buena respuesta|me sirvio(?: mucho)?"
            r"|excelente|genial|que bien|eres muy buen[oa])$"
        ),
    ),
    (
        "no_entendi",
        re.compile(
            r"\b(?:no (?:te )?entendi|no te entiendo|puedes repetir|me repites|repitelo|repite"
            r"|explicame de nuevo|no me quedo claro)\b"
        ),
    ),
    (
        "fuera_tema",
        re.compile(
            r"\b(?:futbol|partido de|el clima de hoy|pronostico del tiempo|va a llover|receta|recetas|cocinar"
            r"|pelicula|peliculas|horoscopo|chiste|chistes|cancion|canciones|loteria)\b"
        ),
    ),
]
# Salvo «humano» y «fuera_tema», la cortesía solo cuenta en mensajes cortos (no en una pregunta con
# contenido).
MAX_PALABRAS_CORTESIA = 8
# Un mensaje con estas palabras es sobre Fanalca aunque traiga un término de «fuera de tema» («clima
# laboral»).
_TEMA_FANALCA = re.compile(
    r"\b(?:fanalca|honda|moto|motos|autopartes|planta|plantas|negocio|negocios|empresa|trabajar|empleo)\b"
)

TEXTOS_CORTESIA: dict[str, tuple[str, ...]] = {
    "como_estas": (
        "¡Muy bien, gracias por preguntar! Listo para ayudarte. ¿Qué te gustaría saber de Fanalca?",
    ),
    "quien_eres": (
        "Soy IGNIS, el asistente virtual de Fanalca. Puedo responderte con la información pública de la "
        "empresa, contarte de sus negocios y sus plantas, darte datos de sus productos y recordar tus "
        "preferencias si me lo pides. ¿Te cuento algo en particular?",
    ),
    "humano": (
        "No, soy un asistente virtual. Aun así, haré lo posible por ayudarte como si estuviéramos "
        "conversando en persona. ¿Qué necesitas?",
    ),
    "gracias": (
        "¡Con gusto! Si necesitas algo más sobre Fanalca, aquí estoy.",
        "¡Para eso estoy! ¿Te ayudo con algo más?",
    ),
    "ok": ("¡Perfecto! ¿Te ayudo con algo más?", "Listo. Si te surge otra pregunta, aquí estoy."),
    "despedida": (
        "¡Hasta pronto! Fue un gusto ayudarte.",
        "¡Que tengas un excelente día! Aquí estaré cuando me necesites.",
    ),
    "perdon": ("¡No pasa nada! Cuéntame qué necesitas.",),
    "elogio": ("¡Gracias, me alegra que te sirva! ¿Seguimos?",),
    "vacio": ("No alcancé a entenderte. ¿Me lo puedes escribir de otra forma?",),
    "fuera_tema": (
        "Me encantaría ayudarte, pero solo tengo información de Fanalca. ¿Te interesa saber algo de sus "
        "negocios o productos?",
    ),
}
NO_ENTENDI_SIN_HISTORIAL = "Claro. ¿Qué parte quieres que te explique otra vez?"
# Frases de plantilla que no resumen nada: el «no entendí» las salta.
_FRASES_DE_PLANTILLA = {
    *ENTRADAS_DOCUMENTAL,
    SEGUIMIENTO_DOCUMENTAL,
    SEGUIMIENTO_DATOS,
    SEGUIMIENTO_FICHA,
    SEGUIMIENTO_MIXTO,
    CIERRE_PLANO,
}


def clasificar_cortesia(mensaje: str) -> CategoriaCortesia | None:
    """Categoría de cortesía del mensaje, o ``None`` si es una pregunta con contenido."""
    texto = normalizar_mensaje(mensaje)
    if not texto:
        return "vacio"
    cortos = len(texto.split()) <= MAX_PALABRAS_CORTESIA
    for categoria, patron in _PATRONES:
        if not patron.search(texto):
            continue
        if categoria == "fuera_tema":
            if _TEMA_FANALCA.search(texto):
                continue
            return categoria
        if categoria == "humano" or cortos:
            return categoria
    return None


# --- Saludos ------------------------------------------------------------------------------------------------
_MOMENTOS = (
    ("buenos dias", "buenos días"),
    ("buen dia", "buen día"),
    ("buenas tardes", "buenas tardes"),
    ("buenas noches", "buenas noches"),
)


def eco_del_saludo(mensaje: str) -> str:
    """Devuelve el saludo que usó el cliente («buenas noches» → «¡Buenas noches!»); la hora no se calcula."""
    texto = normalizar_mensaje(mensaje)
    momento = next((m for clave, m in _MOMENTOS if clave in texto), None)
    if momento and re.search(r"\bhola\b", texto):
        return f"¡Hola, {momento}!"
    if momento:
        return f"¡{momento[0].upper()}{momento[1:]}!"
    return "¡Hola!"


def _ya_saludo(historial: list[dict[str, Any]]) -> bool:
    return any(
        t.get("role") == "assistant" and (t.get("metadatos") or {}).get("cortesia") == "saludo"
        for t in historial
    )


_PLURAL_FORMATO = {"breve": "breves", "detallada": "detalladas"}
_ARTICULO_LINEA = {"motocicletas": "las", "autopartes": "las", "repuestos": "los"}


def frases_de_preferencias(prefs: dict[str, str]) -> list[str]:
    """«trabajas en compras de repuestos», «prefieres respuestas breves», «te interesan las motocicletas»."""
    frases = []
    if area := prefs.get("area_laboral"):
        frases.append(f"trabajas en {area}")
    if formato := prefs.get("formato_respuesta"):
        frases.append(f"prefieres respuestas {_PLURAL_FORMATO.get(formato, formato)}")
    if linea := prefs.get("linea_producto"):
        frases.append(f"te interesan {_ARTICULO_LINEA.get(linea, 'las')} {linea}")
    return frases


def _con_que(frases: list[str]) -> str:
    """«a, que b y que c»: cada preferencia como una cláusula («Tengo guardado que …»)."""
    if len(frases) == 1:
        return frases[0]
    return ", ".join([frases[0], *(f"que {f}" for f in frases[1:-1])]) + f" y que {frases[-1]}"


def responder_saludo(
    mensaje: str, historial: list[dict[str, Any]], semilla: str, prefs: dict[str, str]
) -> str:
    eco = eco_del_saludo(mensaje)
    if _ya_saludo(historial):
        if eco == "¡Hola!":
            cortos = ("¡Hola otra vez! ¿En qué más te ayudo?", "¡Aquí sigo! Cuéntame qué necesitas.")
        else:
            cortos = (f"{eco} ¿En qué más te ayudo?", f"{eco} Aquí sigo, cuéntame qué necesitas.")
        return elegir_variante(cortos, semilla)
    frases = frases_de_preferencias(prefs)
    if frases:
        inicio = "¡Hola de nuevo!" if eco == "¡Hola!" else f"{eco} Qué bueno tenerte de nuevo."
        return f"{inicio} Recuerdo que {_con_que(frases)}. ¿Por dónde empezamos hoy?"
    variantes = (
        f"{eco} Soy IGNIS, el asistente virtual de Fanalca. Puedo contarte sobre la empresa, sus negocios, "
        "dónde están sus plantas o las motocicletas Honda. ¿Qué te gustaría saber?",
        f"{eco} Qué gusto saludarte. Soy IGNIS y estoy aquí para ayudarte con información de Fanalca. ¿Por "
        "dónde empezamos?",
    )
    return elegir_variante(variantes, semilla)


def resumen_de_la_ultima_respuesta(historial: list[dict[str, Any]]) -> str | None:
    """Primera oración útil de la última respuesta con contenido (sin entradas, seguimientos ni preguntas)."""
    respuestas = [
        t
        for t in historial
        if t.get("role") == "assistant" and not (t.get("metadatos") or {}).get("cortesia")
    ]
    if not respuestas:
        return None
    for oracion in partir_oraciones(str(respuestas[-1].get("content", ""))):
        if oracion in _FRASES_DE_PLANTILLA or oracion.endswith("?") or len(oracion.split()) < 6:
            continue
        return oracion
    return None


def responder_cortesia(
    categoria: CategoriaCortesia,
    mensaje: str,
    historial: list[dict[str, Any]],
    semilla: str,
    prefs: dict[str, str] | None = None,
) -> str:
    """Texto fijo de la categoría; el saludo devuelve el del cliente y no se repite la presentación en el
    hilo."""
    if categoria == "saludo":
        return responder_saludo(mensaje, historial, semilla, prefs or {})
    if categoria == "no_entendi":
        resumen = resumen_de_la_ultima_respuesta(historial)
        return f"Claro, te lo explico de otra forma. {resumen}" if resumen else NO_ENTENDI_SIN_HISTORIAL
    return elegir_variante(TEXTOS_CORTESIA[categoria], semilla)


# --- Memoria (ruta memoria_store) ------------------------------------------------------------------------
MEMORIA_NO_DISPONIBLE = (
    "Ahora mismo no puedo consultar tus preferencias guardadas. Intenta de nuevo en un momento."
)
SIN_PREFERENCIAS = (
    "Todavía no tengo preferencias tuyas guardadas. Si quieres, dime por ejemplo: «prefiero respuestas "
    "detalladas, recuérdalo»."
)
AUTOPRESENTACION_SIN_PREFERENCIAS = (
    "¡Gracias por contarme! Por cuidar tu privacidad no guardo nombres, empresas ni datos de contacto. Sí "
    "puedo recordar cómo prefieres las respuestas o qué temas te interesan."
)
AVISO_PRIVACIDAD = "Por cuidar tu privacidad, no guardé nombres, empresas ni datos de contacto."


def _etiquetas_guardadas(prefs: dict[str, str]) -> list[str]:
    """«área laboral, compras de repuestos», «respuestas breves», «te interesan las motocicletas» (caso
    2A)."""
    partes = []
    if area := prefs.get("area_laboral"):
        partes.append(f"área laboral, {area}")
    if formato := prefs.get("formato_respuesta"):
        partes.append(f"respuestas {_PLURAL_FORMATO.get(formato, formato)}")
    if linea := prefs.get("linea_producto"):
        partes.append(f"te interesan {_ARTICULO_LINEA.get(linea, 'las')} {linea}")
    return partes


def texto_preferencias_guardadas(prefs: dict[str, str], descarto_datos_personales: bool) -> str:
    partes = _etiquetas_guardadas(prefs)
    lista = partes[0] if len(partes) == 1 else f"{'; '.join(partes[:-1])}; y {partes[-1]}"
    texto = f"¡Listo, lo tendré en cuenta! Guardé tus preferencias: {lista}."
    return f"{texto} {AVISO_PRIVACIDAD}" if descarto_datos_personales else texto


def texto_preferencias_consultadas(prefs: dict[str, str]) -> str:
    return f"Claro. Tengo guardado que {_con_que(frases_de_preferencias(prefs))}."
