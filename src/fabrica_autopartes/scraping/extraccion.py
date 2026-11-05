"""Extracción del contenido textual relevante de una página HTML.

Estrategia en dos niveles:

1. ``trafilatura`` (extracción semántica del cuerpo principal en Markdown).
2. Respaldo con BeautifulSoup: se eliminan ``script``, ``style``, ``nav``, ``header``,
   ``footer``, formularios, avisos de *cookies* y se conservan encabezados, párrafos,
   listas y tablas.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup, Tag

_ETIQUETAS_RUIDO = [
    "script",
    "style",
    "noscript",
    "nav",
    "header",
    "footer",
    "form",
    "iframe",
    "svg",
    "button",
    "aside",
    "template",
]
_PATRON_RUIDO = re.compile(
    r"cookie|consent|gdpr|popup|modal|newsletter|share|social|breadcrumb|menu|footer|header",
    re.I,
)


@dataclass
class PaginaExtraida:
    titulo: str
    texto: str
    idioma: str
    enlaces: list[str]
    metodo: str


def _idioma(soup: BeautifulSoup, url: str) -> str:
    html = soup.find("html")
    if isinstance(html, Tag) and html.get("lang"):
        return str(html.get("lang"))[:2].lower()
    return "en" if "/en/" in urlparse(url).path else "es"


def extraer_enlaces(html: str, url_base: str) -> list[str]:
    soup = BeautifulSoup(html, "lxml")
    enlaces: list[str] = []
    for a in soup.find_all("a", href=True):
        href = str(a["href"]).strip()
        if href.startswith(("mailto:", "tel:", "javascript:", "#")):
            continue
        absoluto = urljoin(url_base, href).split("#")[0]
        if absoluto not in enlaces:
            enlaces.append(absoluto)
    return enlaces


def _texto_bs4(soup: BeautifulSoup) -> str:
    for etiqueta in soup(_ETIQUETAS_RUIDO):
        etiqueta.decompose()
    for el in soup.find_all(True):
        if not isinstance(el, Tag) or el.attrs is None:
            continue
        clases = " ".join(el.get("class") or []) + " " + str(el.get("id") or "")
        if _PATRON_RUIDO.search(clases) and el.name not in ("main", "article", "body"):
            el.decompose()
    cuerpo = soup.find("main") or soup.find("article") or soup.body or soup
    lineas: list[str] = []
    for el in cuerpo.find_all(["h1", "h2", "h3", "h4", "p", "li", "td", "th", "dd", "dt"]):
        texto = " ".join(el.get_text(" ", strip=True).split())
        if not texto:
            continue
        if el.name in ("h1", "h2", "h3", "h4"):
            nivel = int(el.name[1])
            lineas.append(f"{'#' * nivel} {texto}")
        elif el.name == "li":
            lineas.append(f"- {texto}")
        else:
            lineas.append(texto)
    return "\n\n".join(lineas)


def extraer_contenido(html: str, url: str, usar_trafilatura: bool = True) -> PaginaExtraida:
    soup = BeautifulSoup(html, "lxml")
    titulo_tag = soup.find("h1") or soup.find("title")
    titulo = " ".join(titulo_tag.get_text(" ", strip=True).split()) if titulo_tag else url
    idioma = _idioma(soup, url)
    enlaces = extraer_enlaces(html, url)

    texto = ""
    metodo = "bs4"
    if usar_trafilatura:
        try:
            import trafilatura

            extraido = trafilatura.extract(
                html,
                url=url,
                output_format="markdown",
                include_comments=False,
                include_tables=True,
                favor_precision=True,
            )
            if extraido and len(extraido.split()) >= 25:
                texto = extraido
                metodo = "trafilatura"
        except Exception:  # pragma: no cover - dependencia opcional en tiempo de ejecución
            texto = ""
    if not texto:
        texto = _texto_bs4(BeautifulSoup(html, "lxml"))
    return PaginaExtraida(titulo=titulo, texto=texto, idioma=idioma, enlaces=enlaces, metodo=metodo)


# Señales de datos de contacto en el pie de página (dirección, teléfono, correo, NIT).
_SENAL_CONTACTO = re.compile(
    r"(?i)(\b(calle|cl\.|carrera|cra\.?|kr\.?|avenida|av\.|autopista|diagonal|transversal|km|v[ií]a)\b.*\d)"
    r"|(\+?\d[\d\s().-]{6,}\d)"
    r"|([\w.+-]+@[\w-]+\.[\w.]+)"
    r"|(\b(pbx|tel[eé]fono|tel\.|nit|direcci[oó]n|sede)\b)"
)


def extraer_pie_contacto(html: str) -> list[str]:
    """Líneas con datos de contacto del pie de página (footer) de una página.

    La extracción del cuerpo descarta el pie de página y la limpieza elimina lo que se repite en todas
    las páginas; sin esta función, datos publicados solo en el pie (p. ej. la dirección de la sede)
    no llegarían a la base de conocimiento.
    """
    soup = BeautifulSoup(html, "lxml")
    pies: list[Tag] = [t for t in soup.find_all("footer") if isinstance(t, Tag)]
    for t in soup.find_all(True):
        if not isinstance(t, Tag) or t in pies:
            continue
        marca = " ".join([str(t.get("id") or ""), *[str(c) for c in (t.get("class") or [])]]).lower()
        if "footer" in marca:
            pies.append(t)
    lineas: list[str] = []
    for pie in pies:
        for linea in pie.get_text("\n").split("\n"):
            limpia = re.sub(r"\s+", " ", linea).strip(" |·-")
            if 6 <= len(limpia) <= 300 and _SENAL_CONTACTO.search(limpia) and limpia not in lineas:
                lineas.append(limpia)
    return lineas
