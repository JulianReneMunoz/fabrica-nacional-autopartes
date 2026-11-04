"""Capa Silver: texto limpio, normalizado y deduplicado.

Entrada: capturas Bronze (o documentos semilla). Salida: ``data/silver/documentos.jsonl``.
"""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Iterable
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

import yaml

from fabrica_autopartes.core.registro import obtener_registro
from fabrica_autopartes.domain.modelos import DocumentoLimpio, ahora_utc
from fabrica_autopartes.pipelines.bronze import AlmacenBronze
from fabrica_autopartes.pipelines.texto import (
    anonimizar_correos,
    hash_texto,
    normalizar,
    similitud_jaccard,
)
from fabrica_autopartes.scraping.extraccion import extraer_contenido

log = obtener_registro(__name__)

# Coincidencia EXACTA por segmento de ruta (no por subcadena): evita que el título de una noticia
# que contiene "negocio" o "trabajar" se clasifique como página de negocios o de empleo.
_MAPA_SECCIONES: list[tuple[frozenset[str], str]] = [
    (
        frozenset({"quienes-somos", "who-we-are", "nosotros", "historia", "about", "about-us"}),
        "quienes-somos",
    ),
    (frozenset({"contacto", "contact", "contactenos"}), "contacto"),
    (frozenset({"sostenibilidad", "sustainability", "fundacion"}), "sostenibilidad"),
    (frozenset({"noticias", "news", "blog"}), "noticias"),
    (
        frozenset(
            {
                "trabaja-con-nosotros",
                "work-with-us",
                "empleo",
                "por-que-trabajar-en-fanalca",
                "why-work-at-fanalca",
            }
        ),
        "talento-humano",
    ),
    (frozenset({"productos", "products"}), "productos"),
    (frozenset({"clientes", "clients"}), "clientes"),
    (frozenset({"negocios", "negocio", "business"}), "negocios"),
    (
        frozenset({"aviso-de-privacidad", "privacy-notice", "politica-de-privacidad", "datos-personales"}),
        "legal",
    ),
]

# Prefijo por sitio: permite combinar varios dominios oficiales sin colisiones de identificador.
_PREFIJOS_SITIO = {"autopartesfanalca.com.co": "autopartes", "autopartesfanalca.com": "autopartes"}

LINEAS_MINIMAS_PALABRAS = 3
UMBRAL_CASI_DUPLICADO = 0.9


def prefijo_sitio(url: str) -> str:
    host = (urlparse(url).hostname or "").removeprefix("www.")
    return _PREFIJOS_SITIO.get(host, "")


def _seccion_por_ruta(ruta: str) -> str:
    """Sección a partir de la ruta: se revisa del segmento más específico al más general.

    Las páginas de un solo segmento que no corresponden a una sección conocida son entradas del
    blog del sitio corporativo (p. ej. ``/primer-bus-a-hidrogeno-para-colombia/``) y se agrupan en
    ``noticias``.
    """
    partes = [p for p in ruta.split("/") if p and p not in ("en", "es")]
    if not partes:
        return "inicio"
    for indice in range(len(partes) - 1, -1, -1):
        for claves, seccion in _MAPA_SECCIONES:
            if partes[indice] in claves:
                if seccion == "negocios" and indice < len(partes) - 1:
                    return f"negocios/{partes[-1]}"
                return seccion
    return "noticias"


def excluida(url: str, rutas_excluidas: list[str]) -> bool:
    p = urlparse(url)
    completa = p.path + ("?" + p.query if p.query else "")
    return any(excl in completa for excl in rutas_excluidas)


def inferir_seccion(url: str) -> str:
    seccion = _seccion_por_ruta(urlparse(url).path.lower().strip("/"))
    prefijo = prefijo_sitio(url)
    return f"{prefijo}/{seccion}" if prefijo else seccion


def id_documento(url: str) -> str:
    ruta = urlparse(url).path.strip("/") or "inicio"
    base = re.sub(r"[^a-z0-9]+", "-", ruta.lower()).strip("-") or "inicio"
    prefijo = prefijo_sitio(url)
    return f"{prefijo}-{base}" if prefijo else base


def eliminar_lineas_repetidas(textos: list[str], umbral: float = 0.6) -> list[str]:
    """Elimina líneas que se repiten en una fracción alta de documentos (menús, pies
    de página, avisos legales). Requiere al menos 3 documentos para activarse."""
    if len(textos) < 3:
        return textos
    conteo: Counter[str] = Counter()
    for t in textos:
        conteo.update({linea for linea in t.split("\n") if linea.strip()})
    limite = max(2, int(len(textos) * umbral))
    repetidas = {linea for linea, n in conteo.items() if n >= limite and not linea.startswith("#")}
    return ["\n".join(linea for linea in t.split("\n") if linea not in repetidas) for t in textos]


def limpiar_texto(texto: str) -> str:
    texto = normalizar(texto)
    lineas = []
    for linea in texto.split("\n"):
        if linea.startswith("#") or not linea.strip():
            lineas.append(linea)
            continue
        if len(linea.split()) < LINEAS_MINIMAS_PALABRAS and not linea.startswith("- "):
            continue  # restos de botones / etiquetas sueltas
        lineas.append(linea)
    texto = anonimizar_correos("\n".join(lineas))
    return normalizar(texto)


def deduplicar(documentos: Iterable[DocumentoLimpio]) -> tuple[list[DocumentoLimpio], int]:
    unicos: list[DocumentoLimpio] = []
    hashes: set[str] = set()
    descartados = 0
    for doc in documentos:
        if doc.sha256_texto in hashes:
            descartados += 1
            continue
        if any(similitud_jaccard(doc.texto, u.texto) >= UMBRAL_CASI_DUPLICADO for u in unicos):
            descartados += 1
            continue
        hashes.add(doc.sha256_texto)
        unicos.append(doc)
    return unicos, descartados


def desde_bronze(
    almacen: AlmacenBronze,
    metricas: list[dict] | None = None,
    rutas_excluidas: list[str] | None = None,
) -> list[DocumentoLimpio]:
    """Transforma las capturas Bronze en documentos Silver.

    Si se entrega la lista ``metricas``, se agrega una fila por página con el tamaño de
    cada etapa (bytes HTML, caracteres extraídos, caracteres limpios) para las gráficas.
    ``rutas_excluidas`` aplica las exclusiones vigentes también a capturas antiguas de Bronze,
    de modo que no es necesario borrar Bronze al ajustar la configuración.
    """
    registros = [
        r for r in almacen.ultimos_por_url().values() if not excluida(r.url_final, rutas_excluidas or [])
    ]
    extraidas = []
    for r in registros:
        pagina = extraer_contenido(almacen.leer_html(r), r.url_final)
        extraidas.append((r, pagina))
    textos = eliminar_lineas_repetidas([p.texto for _, p in extraidas])
    documentos = []
    for (r, pagina), texto in zip(extraidas, textos, strict=True):
        limpio = limpiar_texto(texto)
        descartada = len(limpio.split()) < 20
        if metricas is not None:
            metricas.append(
                {
                    "url": r.url_final,
                    "seccion": inferir_seccion(r.url_final),
                    "bytes_html": r.bytes,
                    "caracteres_extraidos": len(pagina.texto),
                    "caracteres_sin_plantilla": len(texto),
                    "caracteres_limpios": len(limpio),
                    "metodo_extraccion": pagina.metodo,
                    "descartada": descartada,
                }
            )
        if descartada:
            log.info("Descartada por poco contenido: %s", r.url_final)
            continue
        documentos.append(
            DocumentoLimpio(
                id=id_documento(r.url_final),
                url=r.url_final,
                titulo=pagina.titulo,
                seccion=inferir_seccion(r.url_final),
                idioma=pagina.idioma,
                texto=limpio,
                sha256_texto=hash_texto(limpio),
                fecha_captura=r.fecha_captura,
                origen="scraping",
            )
        )
    return documentos


def leer_markdown_con_frontmatter(ruta: Path) -> tuple[dict, str]:
    contenido = ruta.read_text(encoding="utf-8")
    if contenido.startswith("---"):
        _, fm, cuerpo = contenido.split("---", 2)
        return yaml.safe_load(fm) or {}, cuerpo.strip()
    return {}, contenido


def desde_semilla(directorio: Path) -> list[DocumentoLimpio]:
    documentos = []
    for ruta in sorted(directorio.glob("*.md")):
        meta, cuerpo = leer_markdown_con_frontmatter(ruta)
        if not meta.get("fuente"):
            continue  # README u otros archivos sin metadatos
        texto = normalizar(cuerpo)
        fecha = meta.get("fecha_consulta")
        documentos.append(
            DocumentoLimpio(
                id=ruta.stem,
                url=str(meta["fuente"]),
                titulo=str(meta.get("titulo", ruta.stem)),
                seccion=str(meta.get("seccion", inferir_seccion(str(meta["fuente"])))),
                idioma=str(meta.get("idioma", "es")),
                texto=texto,
                sha256_texto=hash_texto(texto),
                fecha_captura=datetime.fromisoformat(str(fecha)) if fecha else ahora_utc(),
                origen=str(meta.get("origen", "semilla")),  # type: ignore[arg-type]
            )
        )
    return documentos


def escribir_silver(documentos: list[DocumentoLimpio], directorio: Path) -> Path:
    directorio.mkdir(parents=True, exist_ok=True)
    ruta = directorio / "documentos.jsonl"
    with ruta.open("w", encoding="utf-8", newline="\n") as f:
        for d in documentos:
            f.write(d.model_dump_json() + "\n")
    return ruta


def leer_silver(directorio: Path) -> list[DocumentoLimpio]:
    ruta = directorio / "documentos.jsonl"
    if not ruta.exists():
        return []
    return [
        DocumentoLimpio.model_validate_json(linea)
        for linea in ruta.read_text(encoding="utf-8").splitlines()
        if linea.strip()
    ]
