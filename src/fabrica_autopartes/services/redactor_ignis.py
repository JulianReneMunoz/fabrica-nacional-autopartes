"""Redactor extractivo de IGNIS (respaldo sin LLM): oraciones completas y pertinentes, escritas para el
cliente.

Sin identificadores, URL, nombres de archivo ni JSON en el texto: la evidencia (citas y fuentes de datos)
viaja en los metadatos. Las plantillas usan tuteo y se eligen de forma determinista con un hash de la
pregunta.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from typing import Any

from fabrica_autopartes.domain.modelos import Fragmento
from fabrica_autopartes.pipelines.texto import limpiar_texto_scrapeado, seleccionar_oraciones, sin_tildes
from fabrica_autopartes.services.moderacion import elegir_variante

ENTRADAS_DOCUMENTAL = (
    "Te cuento lo que dice la información pública de Fanalca.",
    "Esto es lo que encontré.",
    "En pocas palabras, esto es lo que publica Fanalca.",
)
SEGUIMIENTO_DOCUMENTAL = "¿Quieres que te cuente más sobre este tema?"
SEGUIMIENTO_DATOS = "¿Te comparo este modelo con otro?"
SEGUIMIENTO_FICHA = "¿Te cuento sobre alguno de sus negocios?"
SEGUIMIENTO_MIXTO = "¿Te ayudo con algo más de este tema?"
CIERRE_PLANO = "Te dejé el plano en el panel de recursos."
# El blindaje se nota en el texto (sin repetir la instrucción): la prueba de contrato exige la marca.
AVISO_BLINDAJE = "Por seguridad, ignoré unas instrucciones ocultas en un documento: quedaron NEUTRALIZADAS."


def _con_marca_de_blindaje(oracion: str) -> bool:
    return "NEUTRALIZADA" in oracion or "ETIQUETA NEUTRALIZADA" in oracion


def oraciones_de(fragmentos: Sequence[Fragmento], textos_visibles: Sequence[str]) -> list[list[str]]:
    """Oraciones limpias de cada fragmento (sin menús, metadatos del blog ni marcas del blindaje)."""
    return [
        [o for o in limpiar_texto_scrapeado(texto) if not _con_marca_de_blindaje(o)]
        for _frag, texto in zip(fragmentos, textos_visibles, strict=True)
    ]


def redactar_documental(
    pregunta: str,
    fragmentos: Sequence[Fragmento],
    textos_visibles: Sequence[str],
    max_oraciones: int = 3,
    entradas: tuple[str, ...] | None = None,
) -> tuple[str, list[Fragmento]]:
    """Respuesta documental y fragmentos efectivamente usados (para las citas). Texto vacío = sin
    evidencia. ``entradas`` reemplaza las frases de entrada (la ruta mixta usa la suya)."""
    elegidas = seleccionar_oraciones(pregunta, oraciones_de(fragmentos, textos_visibles), max_oraciones)
    if not elegidas:
        return "", []
    usados: list[Fragmento] = []
    for indice, _ in elegidas:
        if fragmentos[indice] not in usados:
            usados.append(fragmentos[indice])
    entrada = elegir_variante(entradas or ENTRADAS_DOCUMENTAL, pregunta)
    return f"{entrada} {' '.join(o for _, o in elegidas)}", usados


# --- Ficha de motocicletas (data/catalogo/motos_honda.yaml) ------------------------------------------------
# (sección, campo) → (etiqueta, palabras de la pregunta que lo piden)
_CAMPOS_MOTO: dict[tuple[str, str], tuple[str, tuple[str, ...]]] = {
    ("motor", "tipo"): ("motor", ("motor", "tipo de motor")),
    ("motor", "cilindrada"): ("cilindraje", ("cilindraje", "cilindrada", "cc", "centimetros")),
    ("motor", "potencia"): ("potencia", ("potencia", "caballos", "hp")),
    ("motor", "regimen_potencia"): ("régimen de potencia máxima", ("potencia", "rpm", "revoluciones")),
    ("motor", "torque"): ("torque", ("torque", "par motor")),
    ("transmision", "marchas"): ("número de marchas", ("marchas", "cambios", "transmision", "caja")),
    ("suspension", "delantera"): ("suspensión delantera", ("suspension",)),
    ("suspension", "trasera"): ("suspensión trasera", ("suspension",)),
    ("llantas", "delantera"): ("llanta delantera", ("llanta", "llantas", "rin")),
    ("llantas", "trasera"): ("llanta trasera", ("llanta", "llantas", "rin")),
    ("capacidades", "tanque"): ("capacidad del tanque", ("tanque", "gasolina", "combustible")),
    ("capacidades", "peso"): ("peso", ("peso", "pesa")),
    ("electrico", "arranque"): ("arranque", ("arranque", "encendido")),
    ("electrico", "iluminacion_delantera"): ("farola", ("luces", "farola", "iluminacion")),
    ("electrico", "iluminacion_trasera"): ("luz trasera", ("luces", "stop", "iluminacion")),
    ("electrico", "instrumentos"): ("tablero", ("tablero", "velocimetro", "instrumentos")),
    ("chasis", "sillin"): ("sillín", ("sillin", "asiento")),
}
# Resumen de la ficha cuando la pregunta no pide un campo concreto (caso 3).
_RESUMEN_MOTO = [
    ("motor", "tipo"),
    ("motor", "regimen_potencia"),
    ("llantas", "trasera"),
    ("electrico", "arranque"),
]
_NO_PUBLICADOS_DEL_RESUMEN = [("motor", "cilindrada"), ("capacidades", "peso")]


def _valor(campo: dict[str, Any]) -> str:
    valor = campo.get("valor")
    unidad = campo.get("unidad")
    texto = str(valor)
    if unidad and unidad not in {"ancho/perfil-rin"} and isinstance(valor, int | float):
        texto = f"{texto} {unidad}"
    return texto


def _campo(modelo: dict[str, Any], seccion: str, nombre: str) -> dict[str, Any] | None:
    bloque = modelo.get(seccion)
    campo = bloque.get(nombre) if isinstance(bloque, dict) else None
    return campo if isinstance(campo, dict) else None


def _palabras(texto: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", sin_tildes(texto)))


def _pide(pregunta: str, claves: tuple[str, ...]) -> bool:
    texto = f" {' '.join(sorted(_palabras(pregunta)))} "
    normal = " ".join(re.findall(r"[a-z0-9]+", sin_tildes(pregunta)))
    return any(f" {c} " in f" {normal} " or (" " not in c and f" {c} " in texto) for c in claves)


def _mismo_modelo(escrito: str, nombre: str) -> bool:
    """Comparación en las dos direcciones y sin espacios: «CB 160» es la CB 160F; «CB 190R» no lo es."""
    a = sin_tildes(escrito).replace(" ", "")
    b = sin_tildes(nombre).replace(" ", "")
    return a in b or b in a


def _redactar_frenos(nombre: str, modelo: dict[str, Any]) -> str:
    """Frenos por versión con los valores exactos del catálogo; lo no publicado se dice."""
    versiones = modelo.get("frenos_por_version") or {}
    partes, faltantes = [], []
    for version, frenos in versiones.items():
        if not isinstance(frenos, dict):
            continue
        datos = []
        for posicion in ("delantero", "trasero"):
            campo = frenos.get(posicion) or {}
            if campo.get("estado") == "publicado" and campo.get("valor") is not None:
                datos.append(f"{posicion} de {str(campo['valor']).lower()}")
            else:
                faltantes.append(f"{posicion} de la versión {version}")
        cbs = frenos.get("cbs") or {}
        if cbs.get("estado") == "publicado" and cbs.get("valor") is not None:
            datos.append("con CBS" if cbs["valor"] else "sin CBS")
        if datos:
            partes.append(f"la versión {version}, {', '.join(datos)}")
    if not partes:
        return f"Los frenos de la {nombre} no están publicados en las fuentes que tengo."
    texto = f"Según su ficha, los frenos de la {nombre} son: {'; '.join(partes)}."
    if faltantes:
        texto += f" No está publicado el freno {', '.join(faltantes)}."
    return texto


def redactar_ficha_moto(pregunta: str, datos: dict[str, Any]) -> str:
    """Datos de la ficha de la moto en oraciones, con los valores exactos del catálogo; lo no publicado se
    dice."""
    modelos = datos.get("modelos") or []
    if not modelos:
        return "Por ahora no tengo fichas de motocicletas disponibles."
    modelo = modelos[0]
    nombre = modelo.get("nombre", "la moto")
    escrito = re.search(r"\b(cb|cbr|xr|xre|nt)\s?\d{2,4}[a-z]?\b", sin_tildes(pregunta))
    if escrito and not _mismo_modelo(escrito.group(0), nombre):
        return f"Por ahora solo tengo la ficha de la {nombre}. ¿Quieres que te cuente sobre ella?"

    if _pide(pregunta, ("freno", "frenos", "cbs", "abs", "disco")):
        return _redactar_frenos(nombre, modelo)

    pedidos = [clave for clave, (_, palabras) in _CAMPOS_MOTO.items() if _pide(pregunta, palabras)]
    if pedidos:
        publicados, faltantes = [], []
        for seccion, nombre_campo in pedidos:
            campo = _campo(modelo, seccion, nombre_campo)
            etiqueta = _CAMPOS_MOTO[(seccion, nombre_campo)][0]
            if campo and campo.get("estado") == "publicado" and campo.get("valor") is not None:
                publicados.append(f"{etiqueta}: {_valor(campo)}")
            else:
                faltantes.append(etiqueta)
        partes = []
        if publicados:
            partes.append(f"Según su ficha, la {nombre} tiene {'; '.join(publicados)}.")
        if faltantes:
            lista = ", ".join(faltantes)
            partes.append(f"El dato de {lista} de la {nombre} no está publicado en las fuentes que tengo.")
        return " ".join(partes)

    resumen = []
    for seccion, nombre_campo in _RESUMEN_MOTO:
        campo = _campo(modelo, seccion, nombre_campo)
        if campo and campo.get("estado") == "publicado":
            resumen.append(f"{_CAMPOS_MOTO[(seccion, nombre_campo)][0]}: {_valor(campo)}")
    faltan = [
        _CAMPOS_MOTO[clave][0]
        for clave in _NO_PUBLICADOS_DEL_RESUMEN
        if (_campo(modelo, *clave) or {}).get("estado") != "publicado"
    ]
    texto = f"La ficha de la {nombre} indica {'; '.join(resumen)}."
    if faltan:
        texto += f" Datos como el {' y el '.join(faltan)} no están publicados en las fuentes que tengo."
    return texto


def fuentes_datos_moto(datos: dict[str, Any], archivo: str) -> dict[str, Any]:
    """Procedencia de la ficha de la moto para ``metadatos.fuentes_datos``: los datos vienen de una lámina
    comercial sin URL (``demostrativo``); el sitio oficial se lista como referencia."""
    fuentes = datos.get("fuentes") or {}
    urls = sorted({f["url"] for f in fuentes.values() if isinstance(f, dict) and f.get("url")})
    return {
        "archivo": archivo,
        "descripcion": "Catálogo curado de motocicletas Honda con fuente y estado por campo",
        "origen": "demostrativo",
        "urls": urls,
    }


# --- Estadísticas de la base (data/gold/estadisticas.json) -----------------------------------------------
def redactar_estadisticas(pregunta: str, datos: dict[str, Any]) -> str:
    documentos = datos.get("documentos")
    fragmentos = datos.get("fragmentos")
    if documentos is None:
        return "Por ahora no tengo las cifras de la información publicada por Fanalca."
    texto = f"La información pública de Fanalca que consulto reúne {documentos} documentos de sus sitios web"
    secciones = datos.get("secciones") or {}
    pregunta_normal = sin_tildes(pregunta)
    tema = next(
        (s for s in secciones if "/" not in s and len(s) > 4 and s.replace("-", " ") in pregunta_normal), None
    )
    if tema and fragmentos:
        texto += f", y {secciones[tema]} de sus {fragmentos} textos tratan de {tema.replace('-', ' ')}"
    return texto + "."


def fuentes_datos_estadisticas(datos: dict[str, Any], archivo: str) -> dict[str, Any]:
    origenes = sorted((datos.get("origenes") or {}).keys())
    return {
        "archivo": archivo,
        "descripcion": f"Estadísticas de la base de conocimiento ({len(datos.get('urls') or [])} URL)",
        "origen": ", ".join(origenes) if origenes else "demostrativo",
        "urls": [],
    }
