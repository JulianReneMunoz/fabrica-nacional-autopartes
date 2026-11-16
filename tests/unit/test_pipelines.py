"""Pruebas unitarias de limpieza (Silver), fragmentación y construcción Gold."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
import yaml

from fabrica_autopartes.domain.modelos import DocumentoLimpio, Fragmento
from fabrica_autopartes.pipelines import silver
from fabrica_autopartes.pipelines.calidad import validar_fragmentos
from fabrica_autopartes.pipelines.fragmentacion import fragmentar_documento
from fabrica_autopartes.pipelines.gold import construir_gold, documento_a_markdown
from fabrica_autopartes.pipelines.texto import (
    MARCA_PERFIL,
    anonimizar_correos,
    anonimizar_datos_personales,
    contiene_datos_personales,
    hash_texto,
    normalizar,
    omitir_autopresentaciones,
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


@pytest.mark.parametrize(
    ("texto", "marca", "dato"),
    [
        ("mi cédula es 1.234.567.890", "[documento omitido]", "1.234.567.890"),
        ("CC 12345678", "[documento omitido]", "12345678"),
        ("NIT 900.123.456-7", "[documento omitido]", "900.123.456-7"),
        ("llamar al +57 300 123 4567", "[teléfono omitido]", "300 123 4567"),
        ("fijo 601 234 5678", "[teléfono omitido]", "601 234 5678"),
        ("escribir a juan@gmail.com", "[correo omitido]", "juan@gmail.com"),
    ],
)
def test_anonimizar_datos_personales_oculta(texto: str, marca: str, dato: str) -> None:
    limpio = anonimizar_datos_personales(texto)
    assert marca in limpio
    assert dato not in limpio


@pytest.mark.parametrize(
    "texto",
    [
        "$ 2.192.000",
        "$2.192.000",
        "2.192.000 COP",
        "2192000 pesos",
        "escribir a ventas@fanalca.com",
        "CB 160F de 2026 con 4 unidades y versión 3.5",
    ],
)
def test_anonimizar_datos_personales_conserva(texto: str) -> None:
    assert anonimizar_datos_personales(texto) == texto


@pytest.mark.parametrize(
    ("texto", "esperado"),
    [
        ("me llamo Ana Gómez y trabajo en Empresa X", f"{MARCA_PERFIL} y {MARCA_PERFIL}"),
        ("Hola, soy Ana Gómez de Empresa X, ¿qué hace Fanalca?", f"Hola, {MARCA_PERFIL}, ¿qué hace Fanalca?"),
        ("Mi nombre es ana gómez. ¿Dónde está la sede?", f"{MARCA_PERFIL}. ¿Dónde está la sede?"),
        ("Mi empresa es Empresa X y quiero una cotización", f"{MARCA_PERFIL} y quiero una cotización"),
    ],
)
def test_omitir_autopresentaciones(texto: str, esperado: str) -> None:
    assert omitir_autopresentaciones(texto) == esperado


def test_soy_sin_nombre_propio_no_se_omite() -> None:
    texto = "soy cliente de Fanalca, ¿qué productos tienen?"
    assert omitir_autopresentaciones(texto) == texto


def test_inferir_seccion() -> None:
    assert silver.inferir_seccion("https://fanalca.com/") == "inicio"
    assert silver.inferir_seccion("https://fanalca.com/en/") == "inicio"
    assert (
        silver.inferir_seccion("https://fanalca.com/negocios/honda-motocicletas/")
        == "negocios/honda-motocicletas"
    )
    assert silver.inferir_seccion("https://fanalca.com/en/contact/") == "contacto"
    assert silver.inferir_seccion("https://fanalca.com/en/who-we-are/") == "quienes-somos"


def test_inferir_seccion_agrupa_noticias_y_negocio_singular() -> None:
    """Hallazgos del scraping real: entradas del blog y rutas /negocio/ del sitio corporativo."""
    noticia = (
        "https://fanalca.com/como-parte-de-nuestro-proposito-superior-la-seguridad-continua-siendo-"
        "la-estrategia-prioritaria-para-nuestra-unidad-de-negocio-de-honda-motocicletas/"
    )
    assert silver.inferir_seccion(noticia) == "noticias"
    assert silver.inferir_seccion("https://fanalca.com/primer-bus-a-hidrogeno-para-colombia/") == "noticias"
    assert silver.inferir_seccion("https://fanalca.com/negocio/honda-autos/") == "negocios/honda-autos"
    assert (
        silver.inferir_seccion("https://fanalca.com/en/who-we-are/why-work-at-fanalca/") == "talento-humano"
    )
    assert silver.inferir_seccion("https://fanalca.com/aviso-de-privacidad/") == "legal"
    assert silver.inferir_seccion("https://autopartesfanalca.com.co/productos/") == "autopartes/productos"


def test_secciones_hallazgos_segunda_ejecucion() -> None:
    """Informe de sostenibilidad, alias de unidades de negocio y error tipográfico del sitio."""
    assert (
        silver.inferir_seccion("https://fanalca.com/informe-sostenibilidad/capitulo-2/") == "sostenibilidad"
    )
    assert (
        silver.inferir_seccion("https://fanalca.com/en/business/honda-motorcycles/")
        == "negocios/honda-motocicletas"
    )
    assert silver.inferir_seccion("https://fanalca.com/negocios/holda-autos/") == "negocios/honda-autos"
    assert silver.inferir_seccion("https://fanalca.com/en/business/auto-parts/") == "negocios/autopartes"


def test_patrones_excluyen_paginacion_y_filtros_de_vacantes() -> None:
    patrones = [r"/(?:page|noticias|news)/\d+/?$", r"^/(?:en/)?(?:area|ciudad)/"]
    assert silver.excluida("https://fanalca.com/noticias/3/", [], patrones)
    assert silver.excluida("https://fanalca.com/ciudad/cali/", [], patrones)
    assert silver.excluida("https://fanalca.com/area/comercial/", [], patrones)
    assert not silver.excluida("https://fanalca.com/noticias/", [], patrones)
    assert not silver.excluida("https://fanalca.com/primer-bus-a-hidrogeno-para-colombia/", [], patrones)


def test_excluida_considera_consulta() -> None:
    reglas = ["elementskit_template", "/firma"]
    assert silver.excluida("https://fanalca.com/?elementskit_template=header", reglas)
    assert silver.excluida("https://fanalca.com/firma/", reglas)
    assert not silver.excluida("https://fanalca.com/nosotros/", reglas)


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
    assert "[a#000]" in (tmp_path / "base_conocimiento.txt").read_text(encoding="utf-8")


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
