"""Gráficas que explican cada etapa del proceso de datos (scraping → Bronze → Silver → Gold).

Se generan a partir de ``data/gold/metricas_etapas.json``; nunca con valores inventados.
Si una etapa no tiene datos (por ejemplo, Bronze cuando la base se construyó desde la
semilla), la gráfica lo declara explícitamente en lugar de dibujar barras vacías.

Uso: ``uv run fabrica graficas`` → PNG en ``docs/graficas/``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import cast

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.figure import Figure

# Paleta validada (contraste >= 3:1 frente a SUPERFICIE para marcas gráficas y >= 4.5:1 para texto;
# distinguible bajo protanopia, deuteranopia y tritanopia). Reglas de uso:
#   - UNA escala por gráfica: un tono base (AZUL) y, como máximo, NARANJA como énfasis.
#   - AZUL con NARANJA es el único par permitido (dE >= 97 en las tres simulaciones);
#     AGUA (verde) solo aparece solo: NARANJA/AGUA colapsan en protanopia y AZUL/AGUA en tritanopia.
#   - Nada se distingue solo por color: hay etiquetas directas y, en series pareadas, trama.
AZUL, NARANJA, AGUA = "#2a78d6", "#eb6834", "#13895f"
TEXTO, TEXTO_2, SUPERFICIE, REJILLA = "#0b0b0b", "#52514e", "#fcfcfb", "#e6e5e1"

NOTA = [""]  # nota de procedencia compartida por las gráficas de una ejecución

ETAPAS = [
    ("01_rastreo", "Etapa 1 · Rastreo responsable"),
    ("02_bronze_paginas", "Etapa 2 · Capa Bronze: HTML capturado por página"),
    ("03_reduccion", "Etapa 3 · Del HTML al conocimiento: tamaño por etapa"),
    ("04_limpieza_paginas", "Etapa 4 · Capa Silver: limpieza por página"),
    ("05_fragmentos_seccion", "Etapa 5 · Capa Gold: fragmentos por sección"),
    ("06_tokens_fragmento", "Etapa 6 · Capa Gold: tamaño de los fragmentos"),
]


def _estilo(ax: plt.Axes, titulo: str, subtitulo: str, nota: str = "") -> None:
    ax.set_facecolor(SUPERFICIE)
    ax.figure.set_facecolor(SUPERFICIE)
    for lado in ("top", "right", "left"):
        ax.spines[lado].set_visible(False)
    ax.spines["bottom"].set_color(REJILLA)
    ax.tick_params(colors=TEXTO_2, labelsize=8.5, length=0)
    ax.grid(axis="x", color=REJILLA, linewidth=0.8)
    ax.set_axisbelow(True)
    fig = cast(Figure, ax.get_figure())
    alto = fig.get_figheight()
    # Posiciones en pulgadas desde el borde superior: constantes para cualquier alto.
    fig.text(0.02, 1 - 0.14 / alto, titulo, fontsize=11.5, fontweight="bold", color=TEXTO, va="top")
    fig.text(0.02, 1 - 0.42 / alto, subtitulo, fontsize=8.4, color=TEXTO_2, va="top")
    if nota:
        fig.text(0.02, 1 - 0.62 / alto, nota, fontsize=7.2, color=TEXTO_2, va="top", style="italic")


def _margen_superior(fig: Figure) -> float:
    return 1 - 0.95 / fig.get_figheight()


def _sin_datos(ruta: Path, titulo: str, mensaje: str) -> None:
    fig, ax = plt.subplots(figsize=(8, 2.6))
    ax.axis("off")
    fig.set_facecolor(SUPERFICIE)
    fig.text(0.02, 0.9, titulo, fontsize=11.5, fontweight="bold", color=TEXTO, va="top")
    fig.text(0.02, 0.55, mensaje, fontsize=9.5, color=TEXTO_2, va="top", wrap=True)
    fig.savefig(ruta, dpi=160)
    plt.close(fig)


def _corto(url: str, maximo: int = 38) -> str:
    """Quita el esquema y acorta con «…» en el medio para que la etiqueta no se corte."""
    texto = url.replace("https://", "").replace("www.", "").rstrip("/")
    if len(texto) <= maximo:
        return texto
    cabeza = (maximo - 1) // 2
    return texto[:cabeza] + "…" + texto[-(maximo - 1 - cabeza) :]


def _barras_h(
    ruta: Path,
    titulo: str,
    subtitulo: str,
    etiquetas: list[str],
    valores: list[float],
    unidad: str,
    color: str = AZUL,
    colores: list[str] | None = None,
    notas: list[str] | None = None,
) -> None:
    alto = max(2.6, 0.32 * len(etiquetas) + 1.4)
    fig, ax = plt.subplots(figsize=(8, alto))
    y = range(len(etiquetas))
    ax.barh(list(y), valores, color=colores or color, height=0.55)
    ax.set_yticks(list(y), etiquetas)
    ax.invert_yaxis()
    tope = max(valores) if valores else 1
    for i, v in enumerate(valores):
        ax.text(
            v + tope * 0.01,
            i,
            f"{v:,.0f} {unidad}".replace(",", ".") + (f" · {notas[i]}" if notas and notas[i] else ""),
            va="center",
            fontsize=8,
            color=TEXTO_2,
        )
    ax.set_xlim(0, tope * (1.3 if notas else 1.18))
    ax.set_xlabel(f"cantidad ({unidad})", fontsize=8.5, color=TEXTO_2)
    _estilo(ax, titulo, subtitulo, NOTA[0])
    fig.subplots_adjust(left=0.38, right=0.97, top=_margen_superior(fig), bottom=0.75 / alto)
    fig.savefig(ruta, dpi=160)
    plt.close(fig)


def generar_graficas(ruta_metricas: Path, destino: Path) -> list[Path]:
    metricas = json.loads(ruta_metricas.read_text(encoding="utf-8"))
    destino.mkdir(parents=True, exist_ok=True)
    fuente = metricas["fuente"]
    etiqueta_fuente = {"mixta": "scraping + lectura web de dominios no rastreables"}.get(fuente, fuente)
    NOTA[0] = (
        f"Fuente de datos: {etiqueta_fuente} · generado {metricas['generado_en'][:16].replace('T', ' ')} UTC"
        + ("" if fuente in ("scraping", "ambas", "mixta") else " · regenerar tras 'uv run fabrica pipeline'")
    )
    paginas = [p for p in metricas["paginas"] if not p.get("descartada")]
    rutas: list[Path] = []

    # 1. Rastreo
    ruta = destino / "01_rastreo.png"
    bronze = metricas.get("bronze") or {}
    rastreo = bronze.get("rastreo") if bronze else None
    if rastreo:
        etiquetas = [
            "Descubiertas en sitemaps",
            "URL visitadas",
            "Capturadas (Bronze)",
            "Omitidas por robots.txt",
            "Errores HTTP / red",
            "Duplicadas por hash",
            "Omitidas por protección antibots",
        ]
        valores = [
            rastreo["descubiertas_sitemap"],
            rastreo["visitadas"],
            rastreo["capturadas"],
            rastreo["omitidas_robots"],
            rastreo["errores"],
            rastreo["duplicadas"],
            rastreo.get("omitidas_proteccion", 0),
        ]
        # Énfasis naranja solo en las incidencias; el resto en el tono base. La nota textual evita
        # depender del color para distinguirlas.
        incidencia = [False, False, False, True, True, False, True]
        protegidos = rastreo.get("hosts_protegidos") or {}
        _barras_h(
            ruta,
            ETAPAS[0][1],
            f"Resultado del rastreo en {rastreo['duracion_s']} s"
            + (f" · protegido (no se elude): {', '.join(protegidos)}" if protegidos else ""),
            etiquetas,
            valores,
            "URL",
            colores=[NARANJA if x else AZUL for x in incidencia],
            notas=["incidencia" if x and v else "" for x, v in zip(incidencia, valores, strict=True)],
        )
    else:
        _sin_datos(
            ruta,
            ETAPAS[0][1],
            "Sin rastreo registrado: la base se construyó sin capturas Bronze.\n"
            "Ejecutar 'uv run fabrica pipeline' para rastrear autopartesfanalca.com.co y fanalca.com.",
        )
    rutas.append(ruta)

    # 2. Bronze por página
    ruta = destino / "02_bronze_paginas.png"
    con_html = [p for p in metricas["paginas"] if p.get("bytes_html")]
    if con_html:
        con_html.sort(key=lambda p: p["bytes_html"], reverse=True)
        _barras_h(
            ruta,
            ETAPAS[1][1],
            "Bytes de HTML original guardado por página",
            [_corto(p["url"]) for p in con_html],
            [p["bytes_html"] / 1024 for p in con_html],
            "KB",
        )
    else:
        _sin_datos(ruta, ETAPAS[1][1], "Sin HTML en Bronze para esta construcción.")
    rutas.append(ruta)

    # 3. Reducción por etapa
    ruta = destino / "03_reduccion.png"
    etapas, valores = [], []
    if con_html:
        etapas.append("HTML capturado (Bronze)")
        valores.append(sum(p["bytes_html"] for p in con_html) / 1024)
    etapas += ["Texto extraído", "Sin plantilla del sitio", "Texto limpio (Silver)", "Fragmentos (Gold)"]
    valores += [
        sum(p["caracteres_extraidos"] for p in paginas) / 1024,
        sum(p["caracteres_sin_plantilla"] for p in paginas) / 1024,
        metricas["silver"]["caracteres"] / 1024,
        metricas["gold"]["caracteres"] / 1024,
    ]
    _barras_h(ruta, ETAPAS[2][1], "Kilobytes de contenido que sobreviven a cada etapa", etapas, valores, "KB")
    rutas.append(ruta)

    # 4. Limpieza por página (dos series: extraído vs limpio)
    ruta = destino / "04_limpieza_paginas.png"
    paginas_ord = sorted(paginas, key=lambda p: p["caracteres_extraidos"], reverse=True)[:20]
    alto = max(2.8, 0.36 * len(paginas_ord) + 1.6)
    fig, ax = plt.subplots(figsize=(8, alto))
    y = list(range(len(paginas_ord)))
    ax.barh(
        [i - 0.18 for i in y],
        [p["caracteres_extraidos"] for p in paginas_ord],
        height=0.34,
        color=AZUL,
    )
    ax.barh(
        [i + 0.18 for i in y],
        [p["caracteres_limpios"] for p in paginas_ord],
        height=0.34,
        color=NARANJA,
        hatch="////",
        edgecolor=SUPERFICIE,
        linewidth=0,
    )
    tope = max((p["caracteres_extraidos"] for p in paginas_ord), default=1)
    # Etiquetas directas sobre la primera pareja (sustituyen a la leyenda).
    if paginas_ord:
        primera = paginas_ord[0]
        for desplazo, valor, texto in (
            (-0.18, primera["caracteres_extraidos"], "Texto extraído"),
            (0.18, primera["caracteres_limpios"], "Texto limpio (Silver)"),
        ):
            ax.text(valor + tope * 0.01, desplazo, texto, va="center", fontsize=8, color=TEXTO)
    ax.set_xlim(0, tope * 1.42)
    ax.set_xlabel("caracteres por página", fontsize=8.5, color=TEXTO_2)
    ax.set_yticks(y, [_corto(p["url"]) for p in paginas_ord])
    ax.invert_yaxis()
    _estilo(ax, ETAPAS[3][1], "Caracteres por página antes y después de limpiar", NOTA[0])
    fig.subplots_adjust(left=0.38, right=0.97, top=_margen_superior(fig), bottom=0.75 / alto)
    fig.savefig(ruta, dpi=160)
    plt.close(fig)
    rutas.append(ruta)

    # 5. Fragmentos por sección
    ruta = destino / "05_fragmentos_seccion.png"
    por_seccion = sorted(metricas["gold"]["fragmentos_por_seccion"].items(), key=lambda kv: -kv[1])
    _barras_h(
        ruta,
        ETAPAS[4][1],
        "Fragmentos citables por sección del sitio",
        [k for k, _ in por_seccion],
        [v for _, v in por_seccion],
        "frag.",
        color=AGUA,
    )
    rutas.append(ruta)

    # 6. Distribución de tokens por fragmento
    ruta = destino / "06_tokens_fragmento.png"
    tokens = metricas["gold"]["tokens_por_fragmento"]
    fig, ax = plt.subplots(figsize=(8, 3.2))
    ax.hist(tokens, bins=min(20, max(5, len(tokens) // 2)), color=AZUL, edgecolor=SUPERFICIE, linewidth=2)
    ax.axvline(600, color=TEXTO_2, linestyle="--", linewidth=1)
    ax.text(
        594, ax.get_ylim()[1] * 0.92, "límite de validación (600) ", fontsize=7.5, color=TEXTO_2, ha="right"
    )
    ax.set_xlabel("tokens aproximados por fragmento", fontsize=8.5, color=TEXTO_2)
    ax.set_ylabel("cantidad de fragmentos", fontsize=8.5, color=TEXTO_2)
    ax.grid(axis="y", color=REJILLA)
    _estilo(
        ax,
        ETAPAS[5][1],
        f"{len(tokens)} fragmentos · {metricas['gold']['tokens_aprox']} tokens en total",
        NOTA[0],
    )
    ax.grid(axis="x", visible=False)
    fig.subplots_adjust(left=0.09, right=0.97, top=_margen_superior(fig), bottom=0.2)
    fig.savefig(ruta, dpi=160)
    plt.close(fig)
    rutas.append(ruta)
    return rutas
