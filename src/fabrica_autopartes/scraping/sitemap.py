"""Lectura de sitemaps XML (índices y sitemaps de URLs), comunes en sitios WordPress."""

from __future__ import annotations

from xml.etree import ElementTree as ET

_NS = "{http://www.sitemaps.org/schemas/sitemap/0.9}"


def analizar_sitemap(xml: str) -> tuple[list[str], list[str]]:
    """Devuelve ``(sitemaps_hijos, urls)`` de un documento sitemap.

    Si el XML es inválido se devuelven listas vacías (falla segura).
    """
    try:
        raiz = ET.fromstring(xml.encode("utf-8"))
    except ET.ParseError:
        return [], []
    hijos = [e.text.strip() for e in raiz.iter(f"{_NS}sitemap/{_NS}loc") if e.text]
    if not hijos:
        hijos = [
            loc.text.strip() for s in raiz.iter(f"{_NS}sitemap") for loc in s.iter(f"{_NS}loc") if loc.text
        ]
    urls = [loc.text.strip() for u in raiz.iter(f"{_NS}url") for loc in u.iter(f"{_NS}loc") if loc.text]
    return hijos, urls
