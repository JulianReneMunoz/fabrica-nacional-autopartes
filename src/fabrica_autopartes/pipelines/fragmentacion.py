"""Fragmentación (*chunking*) semántica guiada por encabezados Markdown.

Los encabezados son fronteras naturales de fragmento: primero se divide por ``#``/``##``/
``###`` y luego, si una sección excede el tamaño objetivo, se subdivide con
``RecursiveCharacterTextSplitter`` (separadores: párrafo → línea → oración → palabra).
"""

from __future__ import annotations

from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter

from fabrica_autopartes.domain.modelos import DocumentoLimpio, Fragmento
from fabrica_autopartes.pipelines.texto import normalizar, tokens_aprox

_ENCABEZADOS = [("#", "h1"), ("##", "h2"), ("###", "h3")]


def fragmentar_documento(
    doc: DocumentoLimpio, tamano: int = 1200, solapamiento: int = 150
) -> list[Fragmento]:
    por_encabezado = MarkdownHeaderTextSplitter(
        headers_to_split_on=_ENCABEZADOS, strip_headers=False
    ).split_text(doc.texto)
    divisor = RecursiveCharacterTextSplitter(
        chunk_size=tamano,
        chunk_overlap=solapamiento,
        separators=["\n\n", "\n", ". ", "; ", ", ", " ", ""],
    )
    fragmentos: list[Fragmento] = []
    for seccion in por_encabezado:
        encabezado = " > ".join(seccion.metadata[k] for k in ("h1", "h2", "h3") if k in seccion.metadata)
        for pieza in divisor.split_text(seccion.page_content):
            texto = normalizar(pieza)
            if len(texto.split()) < 8:
                continue
            orden = len(fragmentos)
            fragmentos.append(
                Fragmento(
                    id=f"{doc.id}#{orden:03d}",
                    documento_id=doc.id,
                    url=doc.url,
                    titulo=doc.titulo,
                    seccion=doc.seccion,
                    encabezado=encabezado,
                    idioma=doc.idioma,
                    texto=texto,
                    tokens_aprox=tokens_aprox(texto),
                    orden=orden,
                    origen=doc.origen,
                )
            )
    return fragmentos
