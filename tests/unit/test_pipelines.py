"""Pruebas unitarias de limpieza (Silver), fragmentación y construcción Gold."""

from __future__ import annotations

from datetime import UTC, datetime

import yaml

from fabrica_autopartes.domain.modelos import DocumentoLimpio, Fragmento
from fabrica_autopartes.pipelines import silver
from fabrica_autopartes.pipelines.calidad import validar_fragmentos
from fabrica_autopartes.pipelines.fragmentacion import fragmentar_documento
from fabrica_autopartes.pipelines.gold import construir_gold, documento_a_markdown
from fabrica_autopartes.pipelines.texto import (
    anonimizar_correos,
    contiene_datos_personales,
    hash_texto,
    normalizar,
    similitud_jaccard,
    tokens_aprox,
)


def _doc(id_: str, texto: str, url: str = "https://fanalca.com/x/") -> DocumentoLimpio:
    return DocumentoLimpio(
        id=id_,
        url=url,
        titulo=id_,
        seccion="x",
        texto=texto,
        sha256_texto=hash_texto(texto),
        fecha_captura=datetime.now(UTC),
    )


def test_normalizar_espacios_y_saltos() -> None:
    assert normalizar("a   b\r\n\n\n\nc ") == "a b\n\nc"


def test_tokens_aprox() -> None:
    assert tokens_aprox("abcd" * 10) == 10


def test_anonimizar_correos_conserva_corporativos() -> None:
    texto = "Escribir a persona.privada@gmail.com o a fanalcambiental@fanalca.com."
    limpio = anonimizar_correos(texto)
    assert "[correo omitido]" in limpio and "fanalcambiental@fanalca.com" in limpio
    assert contiene_datos_personales(texto) and not contiene_datos_personales(limpio)


def test_inferir_seccion() -> None:
    assert silver.inferir_seccion("https://fanalca.com/") == "inicio"
    assert silver.inferir_seccion("https://fanalca.com/en/") == "inicio"
    assert (
        silver.inferir_seccion("https://fanalca.com/negocios/honda-motocicletas/")
        == "negocios/honda-motocicletas"
    )
    assert silver.inferir_seccion("https://fanalca.com/en/contact/") == "contacto"
    assert silver.inferir_seccion("https://fanalca.com/en/who-we-are/") == "quienes-somos"


def test_limpiar_texto_descarta_restos_cortos() -> None:
    texto = "# Título\n\nAceptar\n\nEste párrafo tiene suficientes palabras para quedarse.\n\n- Ítem"
    limpio = silver.limpiar_texto(texto)
    assert "Aceptar" not in limpio and "# Título" in limpio and "- Ítem" in limpio


def test_eliminar_lineas_repetidas_en_mayoria() -> None:
    comun = "Pie de página repetido en todas las páginas del sitio"
    textos = [f"# Doc {i}\n{comun}\nContenido propio número {i} del documento" for i in range(4)]
    resultado = silver.eliminar_lineas_repetidas(textos)
    assert all(comun not in t for t in resultado)
    assert all(f"Contenido propio número {i}" in t for i, t in enumerate(resultado))


def test_deduplicar_exactos_y_casi_duplicados() -> None:
    base = "La empresa fabrica tubos de acero soldados para construcción e industria en Yumbo. " * 3
    docs = [_doc("a", base), _doc("b", base), _doc("c", base + " Fin."), _doc("d", "Texto distinto " * 20)]
    unicos, descartados = silver.deduplicar(docs)
    assert [d.id for d in unicos] == ["a", "d"] and descartados == 2
    assert similitud_jaccard(base, base + " Fin.") >= 0.9


def test_semilla_tiene_procedencia(config) -> None:  # type: ignore[no-untyped-def]
    docs = silver.desde_semilla(config.dir_semilla)
    assert len(docs) >= 10
    assert all(d.origen in ("semilla", "lectura_web") for d in docs)
    assert all(d.url.startswith(("https://fanalca.com/", "https://autopartesfanalca.com.co/")) for d in docs)
    assert len({d.id for d in docs}) == len(docs)


def test_fragmentacion_respeta_encabezados_y_tamano() -> None:
    texto = (
        "# Uno\n\n"
        + ("Oración de relleno con varias palabras útiles. " * 60)
        + "\n\n## Dos\n\nTexto corto de la sección dos con ocho palabras o más."
    )
    frags = fragmentar_documento(_doc("doc", texto), tamano=500, solapamiento=50)
    assert len(frags) >= 3
    assert all(len(f.texto) <= 500 for f in frags)
    assert frags[-1].encabezado == "Uno > Dos"
    assert [f.id for f in frags] == [f"doc#{i:03d}" for i in range(len(frags))]


def test_markdown_gold_con_frontmatter() -> None:
    md = documento_a_markdown(_doc("contacto", "Texto de contacto con datos suficientes."))
    _, fm, cuerpo = md.split("---", 2)
    meta = yaml.safe_load(fm)
    assert {"fuente", "titulo", "seccion", "fecha_captura", "idioma", "tokens_aprox", "origen"} <= set(meta)
    assert "Texto de contacto" in cuerpo


def test_construir_gold_genera_artefactos(tmp_path) -> None:  # type: ignore[no-untyped-def]
    docs = [_doc("a", "# A\n\nPrimer documento con información suficiente para un fragmento válido.")]
    est = construir_gold(docs, tmp_path, empresa="Prueba")
    assert est.documentos == 1 and est.fragmentos == 1
    for nombre in ("fragmentos.jsonl", "base_conocimiento.txt", "estadisticas.json", "docs/a.md"):
        assert (tmp_path / nombre).exists()
    assert "[a#000]" in (tmp_path / "base_conocimiento.txt").read_text()


def test_validacion_detecta_errores() -> None:
    f = Fragmento(
        id="x#000",
        documento_id="x",
        url="sin-url",
        titulo="t",
        seccion="s",
        texto="<div>resto</div> y correo juan@gmail.com",
        tokens_aprox=900,
        orden=0,
    )
    informe = validar_fragmentos([f, f])
    reglas = {h.regla for h in informe.hallazgos}
    assert {"id_unico", "procedencia", "html_residual", "tamano", "datos_personales"} <= reglas
    assert not informe.aprobado
