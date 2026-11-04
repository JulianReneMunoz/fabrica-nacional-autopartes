"""Capa Gold: Markdown enriquecido con *frontmatter* YAML, fragmentos JSONL y el
archivo de texto limpio consolidado (``base_conocimiento.txt``), que constituye la
"memoria" del asistente en el Módulo 1 (se inyecta en el prompt de sistema).
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import yaml

from fabrica_autopartes.domain.modelos import DocumentoLimpio, EstadisticasBase, Fragmento, ahora_utc
from fabrica_autopartes.pipelines.fragmentacion import fragmentar_documento
from fabrica_autopartes.pipelines.texto import tokens_aprox


def documento_a_markdown(doc: DocumentoLimpio) -> str:
    frontmatter = {
        "id": doc.id,
        "fuente": doc.url,
        "titulo": doc.titulo,
        "seccion": doc.seccion,
        "fecha_captura": doc.fecha_captura.isoformat(),
        "idioma": doc.idioma,
        "tokens_aprox": tokens_aprox(doc.texto),
        "origen": doc.origen,
        "sha256_texto": doc.sha256_texto,
    }
    fm = yaml.safe_dump(frontmatter, allow_unicode=True, sort_keys=False).strip()
    return f"---\n{fm}\n---\n\n{doc.texto}\n"


def consolidar(fragmentos: list[Fragmento], empresa: str) -> str:
    """Construye el archivo de texto limpio con marcadores de fuente citables."""
    lineas = [
        f"BASE DE CONOCIMIENTO — {empresa}",
        f"Generada: {ahora_utc().isoformat(timespec='seconds')}",
        f"Fragmentos: {len(fragmentos)}",
        "",
    ]
    for f in fragmentos:
        lineas.append(f"[{f.id}] ({f.seccion} | {f.url})")
        lineas.append(f.texto)
        lineas.append("")
    return "\n".join(lineas).strip() + "\n"


def construir_gold(
    documentos: list[DocumentoLimpio],
    directorio: Path,
    empresa: str,
    tamano: int = 1200,
    solapamiento: int = 150,
) -> EstadisticasBase:
    dir_docs = directorio / "docs"
    dir_docs.mkdir(parents=True, exist_ok=True)
    for viejo in dir_docs.glob("*.md"):
        viejo.unlink()

    fragmentos: list[Fragmento] = []
    for doc in documentos:
        (dir_docs / f"{doc.id}.md").write_text(documento_a_markdown(doc), encoding="utf-8")
        fragmentos.extend(fragmentar_documento(doc, tamano, solapamiento))

    with (directorio / "fragmentos.jsonl").open("w", encoding="utf-8") as fh:
        for f in fragmentos:
            fh.write(f.model_dump_json() + "\n")
    (directorio / "base_conocimiento.txt").write_text(consolidar(fragmentos, empresa), encoding="utf-8")

    estadisticas = EstadisticasBase(
        documentos=len(documentos),
        fragmentos=len(fragmentos),
        tokens_aprox=sum(f.tokens_aprox for f in fragmentos),
        secciones=dict(Counter(f.seccion for f in fragmentos)),
        origenes=dict(Counter(f.origen for f in fragmentos)),
        urls=sorted({d.url for d in documentos}),
        generado_en=ahora_utc(),
    )
    (directorio / "estadisticas.json").write_text(
        json.dumps(estadisticas.model_dump(mode="json"), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return estadisticas
