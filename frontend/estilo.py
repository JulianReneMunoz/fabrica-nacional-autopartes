"""Estilo de la interfaz Streamlit: el mismo sistema de diseño del visor 3D.

Fuente única de verdad: ``web/src/tema/tokens.css``. Este módulo LEE esos tokens (no duplica ningún color,
tipografía, espaciado ni radio), genera el CSS estático que se inyecta una vez por ejecución y ofrece
componentes HTML (insignia de fuente, chip de métrica, tarjeta de respuesta) cuyo contenido dinámico siempre
pasa por ``html.escape``. ``unsafe_allow_html`` se usa SOLO con CSS propio y con HTML armado aquí: jamás con
texto de usuario o del corpus sin escapar.

Selectores internos de Streamlit de los que depende el CSS (``SELECTORES_STREAMLIT``): son atributos
``data-testid`` documentados por la propia interfaz de Streamlit. ``tests/unit/test_estilo_streamlit.py``
verifica que el CSS referencie únicamente los listados, que existan en el paquete de Streamlit instalado y
que la versión instalada sea la probada (``VERSION_STREAMLIT_PROBADA``): si Streamlit cambia su HTML, la
prueba falla en vez de degradar el estilo en silencio.
"""

from __future__ import annotations

import html
import re
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

RAIZ = Path(__file__).resolve().parents[1]
RUTA_TOKENS = RAIZ / "web" / "src" / "tema" / "tokens.css"
RUTA_CSS = Path(__file__).resolve().parent / "estilo.css"

# Versión menor de Streamlit con la que se validó el CSS (uv.lock fija la exacta).
VERSION_STREAMLIT_PROBADA = "1.66"

# Selectores internos de Streamlit usados por el CSS. Cualquier otro ``data-testid`` en el CSS es un error.
SELECTORES_STREAMLIT: tuple[str, ...] = (
    "stApp",
    "stHeader",
    "stToolbar",
    "stSidebar",
    "stHeading",
    "stMainBlockContainer",
    "stTabs",
    "stTab",
    "stCaptionContainer",
    "stExpander",
    "stAlert",
    "stBaseButton-primary",
    "stBaseButton-secondary",
    "stBaseLinkButton-secondary",
    "stDownloadButton",
    "stChatInput",
    "stWidgetLabel",
    "stIconMaterial",
    "stHorizontalBlock",  # columnas de las gráficas de etapas (una por fila por debajo de 1200 px)
    "stColumn",
)

TOKENS_REQUERIDOS: tuple[str, ...] = (
    "papel",
    "papel-2",
    "tinta",
    "tinta-2",
    "tinta-3",
    "reticula",
    "trazo-suave",
    "acento",
    "acento-texto",
    "acento-suave",
    "dato",
    "dato-texto",
    "dato-fondo",
    "ok",
    "ok-texto",
    "ok-fondo",
    "alerta",
    "alerta-texto",
    "alerta-fondo",
    "foco",
    "foco-inverso",
    "sans",
    "mono",
    "t-xs",
    "t-sm",
    "t-md",
    "t-lg",
    "t-xl",
    "interlineado",
    "e1",
    "e2",
    "e3",
    "e4",
    "e5",
    "radio",
    "radio-sm",
    "radio-pildora",
    "cuadricula",
    "alto-cabecera",
    "ancho-max",
    "borde",
    "borde-suave",
    "borde-punteado",
)

TEXTO_FUENTE: dict[str, str] = {
    "scraping": "scraping",
    "lectura_web": "lectura web",
    "semilla": "semilla",
    "base_conocimiento": "base de conocimiento",
    "ficha": "ficha",
    "supuesto": "supuesto didáctico",
    "no_publicado": "no publicado",
}
ALIAS_FUENTE = {"demostrativo": "supuesto", "publicado": "ficha"}
VARIANTES_CHIP = ("neutro", "dato", "supuesto", "estado")


class ErrorTokens(ValueError):
    """Los tokens del visor no se pudieron leer o están incompletos."""


# ------------------------------------------------------------------ lectura de tokens
def leer_tokens(ruta: Path = RUTA_TOKENS) -> dict[str, str]:
    """Devuelve ``{nombre: valor}`` de las variables CSS del bloque ``:root`` (sin ``--``).

    Ignora comentarios (también dentro de un valor), conserva valores compuestos como ``var(--x)`` o listas de
    fuentes, y falla con ``ErrorTokens`` si falta algún token requerido.
    """
    try:
        texto = ruta.read_text(encoding="utf-8")
    except OSError as exc:
        raise ErrorTokens(f"No se pudo leer {ruta.name}: {exc}") from exc
    return parsear_tokens(texto)


def parsear_tokens(texto: str) -> dict[str, str]:
    sin_comentarios = re.sub(r"/\*.*?\*/", "", texto, flags=re.S)
    bloque = re.search(r":root\s*\{(.*?)\}", sin_comentarios, flags=re.S)
    if bloque is None:
        raise ErrorTokens("No existe el bloque :root en los tokens")
    tokens: dict[str, str] = {}
    for nombre, valor in re.findall(r"--([a-z0-9-]+)\s*:\s*([^;]+);", bloque.group(1)):
        tokens[nombre] = re.sub(r"\s+", " ", valor).strip()
    faltan = [t for t in TOKENS_REQUERIDOS if t not in tokens]
    if faltan:
        raise ErrorTokens("Tokens requeridos ausentes: " + ", ".join(faltan))
    return tokens


def tema_streamlit(tokens: Mapping[str, str]) -> dict[str, str]:
    """Valores de ``[theme]`` de ``.streamlit/config.toml`` derivados de los tokens."""
    return {
        "primaryColor": tokens["acento"],
        "backgroundColor": tokens["papel"],
        "secondaryBackgroundColor": tokens["papel-2"],
        "textColor": tokens["tinta"],
        "borderColor": tokens["trazo-suave"],
    }


# ------------------------------------------------------------------------- CSS
def generar_css(tokens: Mapping[str, str], ruta_css: Path = RUTA_CSS) -> str:
    """CSS completo: redeclara TODOS los tokens en ``:root`` y antepone ``estilo.css`` (solo ``var()``)."""
    variables = "\n".join(f"  --{n}: {v};" for n, v in tokens.items())
    return f":root {{\n{variables}\n}}\n" + ruta_css.read_text(encoding="utf-8")


def selectores_usados(css: str) -> set[str]:
    """``data-testid`` referenciados por el CSS (para la prueba de selectores)."""
    return set(re.findall(r'data-testid="([^"]+)"', css))


# ------------------------------------------------------------------ componentes HTML
def _esc(valor: object) -> str:
    return html.escape(str(valor), quote=True)


def normalizar_fuente(tipo: str) -> str | None:
    t = ALIAS_FUENTE.get(tipo, tipo)
    return t if t in TEXTO_FUENTE else None


def insignia(fuente: str, texto: str | None = None) -> str:
    """Insignia de procedencia (misma semántica que ``InsigniaFuente.tsx``): color + texto, una línea."""
    f = normalizar_fuente(fuente)
    visible = texto if texto is not None else (TEXTO_FUENTE[f] if f else fuente)
    return f'<span class="fna-insignia fna-fuente-{f or "otra"}">{_esc(visible)}</span>'


def chip(etiqueta: str, valor: object, variante: str = "neutro", ok: bool = True) -> str:
    """Chip de un número o estado (misma semántica que ``ChipDato.tsx``)."""
    if variante not in VARIANTES_CHIP:
        raise ValueError(f"Variante de chip desconocida: {variante}")
    estado = ("ok" if ok else "alerta") if variante == "estado" else None
    clases = f"fna-chip fna-chip-{variante}" + (f" fna-chip-{estado}" if estado else "")
    icono = ""
    if estado:
        icono = f'<span class="fna-chip-icono" aria-hidden="true">{"✓" if estado == "ok" else "✕"}</span>'
    extra = insignia("supuesto") if variante == "supuesto" else ""
    return (
        f'<span class="{clases}" data-variante="{variante}">{icono}'
        f'<span class="fna-chip-etiqueta">{_esc(etiqueta)}</span> <b>{_esc(valor)}</b>{extra}</span>'
    )


def fila_chips(chips: Iterable[str]) -> str:
    return '<div class="fna-lecturas">' + "".join(chips) + "</div>"


def url_segura(url: str) -> bool:
    """Solo enlaces http(s): descarta ``javascript:``, ``data:`` y similares."""
    try:
        partes = urlsplit(url.strip())
    except ValueError:
        return False
    return partes.scheme in ("http", "https") and bool(partes.netloc)


def enlace(url: str, texto: str | None = None) -> str:
    """Enlace escapado; una URL no segura se muestra como texto plano, sin ``href``."""
    visible = _esc(texto if texto else url)
    if not url_segura(url):
        return visible
    return f'<a href="{_esc(url.strip())}" target="_blank" rel="noopener noreferrer">{visible}</a>'


def _negrita(texto_escapado: str) -> str:
    """``**negrita**`` sobre texto YA escapado (las etiquetas introducidas son fijas)."""
    return re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", texto_escapado)


def markdown_a_html(texto: str) -> str:
    """Subconjunto mínimo y SEGURO de Markdown (párrafos, listas con guion y **negrita**).

    Escapa primero todo el texto y solo después introduce etiquetas fijas.
    """
    bloques = [b for b in re.split(r"\n\s*\n", texto.strip()) if b.strip()]
    salida: list[str] = []
    for bloque in bloques:
        lineas = [ln for ln in bloque.split("\n") if ln.strip()]
        es_lista = all(re.match(r"\s*[-*] ", ln) for ln in lineas)
        escapadas = [
            re.sub(
                r"\*\*(.+?)\*\*",
                r"<strong>\1</strong>",
                html.escape(re.sub(r"^\s*[-*] ", "", ln) if es_lista else ln),
            )
            for ln in lineas
        ]
        if es_lista:
            salida.append("<ul>" + "".join(f"<li>{ln}</li>" for ln in escapadas) + "</ul>")
        else:
            salida.append("<p>" + "<br>".join(escapadas) + "</p>")
    return "".join(salida)


def cabecera_html(url_visor: str, titulo: str = "Asistente de conocimiento") -> str:
    """Barra superior negra con la marca y la navegación hacia el visor 3D."""
    base = url_visor if url_visor.endswith("/") else url_visor + "/"
    enlaces = [
        ("Biblioteca de máquinas", base + "#/"),
        ("Freno", base + "#/maquina/freno"),
        ("Motocicleta", base + "#/maquina/moto_honda"),
    ]
    items = "".join(
        f'<a href="{_esc(u)}" target="_blank" rel="noopener noreferrer">{_esc(t)}</a>' for t, u in enlaces
    )
    return (
        '<header class="fna-cabecera">'
        f'<span class="fna-marca"><b>FNA</b> · {_esc(titulo)} · v2.0</span>'
        f'<nav aria-label="Visor 3D">{items}</nav></header>'
    )


def encabezado_html(titulo: str, bajada: str) -> str:
    return f'<h1 class="fna-titular">{_esc(titulo)}</h1><p class="fna-bajada">{_esc(bajada)}</p>'


def tarjeta_respuesta(
    *,
    pregunta: str,
    respuesta: str,
    fundamentada: bool,
    confianza: str,
    modo_contexto: str,
    proveedor: str,
    modelo: str,
    version_prompt: str,
    latencia_ms: int,
    fuentes: Iterable[Any],
    origenes: Mapping[str, str] | None = None,
    es_rechazo: bool = False,
    recuperador: str = "no_aplica",
) -> str:
    """Tarjeta HTML de una respuesta del Q&A. ``fuentes`` expone ``fragmento_id``, ``titulo`` y ``url``."""
    origenes = origenes or {}
    fuentes = list(fuentes)
    chips = [
        chip("fundamentación", "con respaldo" if fundamentada else "sin respaldo", "estado", ok=fundamentada),
        chip("confianza", confianza),
        chip("contexto", modo_contexto),
        chip("recuperador", {"bm25": "BM25", "semantico": "semántico"}.get(recuperador, "no aplica")),
        chip("modelo", f"{proveedor} · {modelo} · {version_prompt}"),
        chip("latencia", f"{latencia_ms} ms", "dato"),
    ]
    if es_rechazo:
        cuerpo = (
            '<div class="fna-respuesta fna-rechazo">'
            f"{insignia('no_publicado')}<span>{_esc(respuesta)}</span></div>"
        )
    else:
        cuerpo = f'<div class="fna-respuesta">{markdown_a_html(respuesta)}</div>'
    citas = ""
    if fuentes:
        filas = "".join(
            "<li>"
            + insignia(origenes.get(f.fragmento_id, "base_conocimiento"))
            + f"<code>{_esc(f.fragmento_id)}</code> "
            + enlace(f.url, f.titulo or f.url)
            + f'<span class="fna-url">{_esc(f.url)}</span></li>'
            for f in fuentes
        )
        citas = f'<h4 class="fna-rotulo">Fuentes ({len(fuentes)})</h4><ul class="fna-citas">{filas}</ul>'
    return (
        '<article class="fna-tarjeta" aria-label="Respuesta del asistente">'
        '<h4 class="fna-rotulo">Pregunta</h4>'
        f'<p class="fna-pregunta">{_esc(pregunta)}</p>'
        '<h4 class="fna-rotulo">Respuesta</h4>'
        f"{cuerpo}{fila_chips(chips)}{citas}</article>"
    )


def ficha_dato(origen: str, texto: str, url: str = "") -> str:
    """Dato con insignia de procedencia, texto y, si existe, su URL (todo escapado)."""
    destino = f" — {enlace(url)}" if url else ""
    return f'<div class="fna-ficha">{insignia(origen)}{_negrita(_esc(texto))}{destino}</div>'


# ------------------------------------------------------------------------ gráficas
def grafica_barras(
    valores: Mapping[str, int], tokens: Mapping[str, str], etiqueta_valor: str = "fragmentos"
) -> Any:
    """Barras horizontales con UNA sola escala (azul de datos), etiqueta directa y paleta de los tokens."""
    import altair as alt
    import pandas as pd

    df = pd.DataFrame({"categoria": list(valores), etiqueta_valor: list(valores.values())})
    base = alt.Chart(df).encode(
        y=alt.Y(
            "categoria:N",
            sort="-x",
            title=None,
            axis=alt.Axis(
                labelLimit=260, labelFont=tokens["mono"], labelFontSize=11, labelColor=tokens["tinta-2"]
            ),
        ),
        x=alt.X(
            f"{etiqueta_valor}:Q",
            title=etiqueta_valor,
            axis=alt.Axis(grid=True, gridColor=tokens["reticula"]),
        ),
    )
    barras = base.mark_bar(color=tokens["dato"])
    texto = base.mark_text(
        align="left", dx=4, font=tokens["mono"], fontSize=11, color=tokens["tinta"]
    ).encode(text=f"{etiqueta_valor}:Q")
    return (
        (barras + texto)
        .properties(height=max(120, 20 * len(df)))
        .configure_view(stroke=None)
        .configure_axis(
            domainColor=tokens["tinta"],
            tickColor=tokens["tinta"],
            titleColor=tokens["tinta-2"],
            titleFont=tokens["mono"],
        )
    )


def inyectar_estilo(html_propio: str = "") -> None:
    """Inyecta el CSS propio (estático) y, en el MISMO elemento, HTML propio ya escapado (la cabecera).

    Un solo elemento evita que un contenedor vacío de Streamlit empuje la barra superior por el ``gap``.
    """
    import streamlit as st

    st.markdown(f"<style>{generar_css(leer_tokens())}</style>{html_propio}", unsafe_allow_html=True)
