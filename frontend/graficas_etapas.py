"""Gráficas interactivas (Altair) de la pestaña «Proceso de datos».

Se construyen con las series de ``pipelines.graficas.series_etapas``: los mismos cálculos que las PNG del
README y de los documentos, que no cambian. Estilo con los tokens del visor: azul para datos, naranja solo
para incidencias (con la palabra «incidencia» en la etiqueta), una sola escala por gráfica, ejes y
cuadrícula tenues y etiquetas directas al final de cada barra.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import altair as alt
import pandas as pd

ALTO_MIN, ALTO_MAX = 220, 280
MAX_PAGINAS = 10  # series por página: las de mayor tamaño (el subtítulo indica cuántas hay en total)
TAM_FUENTE = 11


def _formato(valor: float) -> str:
    return f"{valor:,.0f}".replace(",", ".")


def _alto(n_barras: int) -> int:
    return max(ALTO_MIN, min(ALTO_MAX, 26 * n_barras + 40))


def _configurar(grafica: alt.Chart | alt.LayerChart, tokens: Mapping[str, str]) -> alt.Chart | alt.LayerChart:
    return (
        grafica.configure(font=tokens.get("sans", "sans-serif"))
        .configure_view(stroke=None)
        .configure_axis(
            labelFontSize=TAM_FUENTE,
            titleFontSize=TAM_FUENTE,
            labelColor=tokens["tinta-2"],
            titleColor=tokens["tinta-2"],
            gridColor=tokens["reticula"],
            domainColor=tokens["reticula"],
            tickColor=tokens["reticula"],
        )
        .configure_legend(labelFontSize=TAM_FUENTE, titleFontSize=TAM_FUENTE, orient="top")
    )


def barras(etapa: Mapping[str, Any], tokens: Mapping[str, str]) -> alt.LayerChart:
    """Barras horizontales con etiqueta directa; las incidencias en naranja y rotuladas como tales."""
    filas = list(etapa["filas"])
    if "total" in etapa:
        filas = filas[:MAX_PAGINAS]
    df = pd.DataFrame(filas)
    df["incidencia"] = df.get("incidencia", False)
    df["incidencia"] = df["incidencia"].fillna(False).astype(bool)
    df["texto"] = [
        f"{_formato(v)} {u}" + (" · incidencia" if inc else "")
        for v, u, inc in zip(df["valor"], df["unidad"], df["incidencia"], strict=True)
    ]
    df["tipo"] = ["incidencia" if inc else "dato" for inc in df["incidencia"]]
    unidad = str(df["unidad"].iloc[0]) if len(df) else ""
    orden = list(df["etiqueta"])
    tope = float(df["valor"].max() or 1) * 1.35
    base = alt.Chart(df).encode(
        y=alt.Y("etiqueta:N", sort=orden, title=None, axis=alt.Axis(labelLimit=230, labelOverlap=False)),
        x=alt.X(
            "valor:Q",
            title=f"cantidad ({unidad})",
            scale=alt.Scale(domain=[0, tope]),
            axis=alt.Axis(grid=True, format="d", tickCount=5),
        ),
        tooltip=[alt.Tooltip("etiqueta:N", title="Elemento"), alt.Tooltip("texto:N", title="Valor")],
    )
    color = alt.Color(
        "tipo:N",
        scale=alt.Scale(domain=["dato", "incidencia"], range=[tokens["dato"], tokens["acento"]]),
        legend=None,
    )
    marcas = base.mark_bar(height={"band": 0.6}, cornerRadiusEnd=2).encode(color=color)
    etiquetas = base.mark_text(align="left", dx=4, fontSize=TAM_FUENTE, color=tokens["tinta-2"]).encode(
        text="texto:N"
    )
    return alt.layer(marcas, etiquetas).properties(height=_alto(len(df)), width="container")


def barras_pareadas(etapa: Mapping[str, Any], tokens: Mapping[str, str]) -> alt.Chart:
    """Dos series por página (texto extraído y texto limpio) con la misma escala y leyenda directa."""
    df = pd.DataFrame(etapa["filas"])
    paginas = list(dict.fromkeys(df["etiqueta"]))[:MAX_PAGINAS]
    df = df[df["etiqueta"].isin(paginas)]
    df["texto"] = [f"{_formato(v)} caracteres" for v in df["valor"]]
    tope = float(df["valor"].max() or 1) * 1.2
    return (
        alt.Chart(df)
        .mark_bar(height={"band": 0.8})
        .encode(
            y=alt.Y(
                "etiqueta:N", sort=paginas, title=None, axis=alt.Axis(labelLimit=230, labelOverlap=False)
            ),
            yOffset=alt.YOffset("serie:N", sort=["Texto extraído", "Texto limpio"]),
            x=alt.X(
                "valor:Q",
                title="caracteres por página",
                scale=alt.Scale(domain=[0, tope]),
                axis=alt.Axis(format="d", tickCount=5),
            ),
            color=alt.Color(
                "serie:N",
                scale=alt.Scale(
                    domain=["Texto extraído", "Texto limpio"], range=[tokens["dato"], tokens["dato-texto"]]
                ),
                legend=alt.Legend(title=None),
            ),
            tooltip=[
                alt.Tooltip("etiqueta:N", title="Página"),
                alt.Tooltip("serie:N", title="Serie"),
                alt.Tooltip("texto:N", title="Valor"),
            ],
        )
        .properties(height=_alto(len(paginas)), width="container")
    )


def histograma(etapa: Mapping[str, Any], tokens: Mapping[str, str]) -> alt.LayerChart:
    """Distribución de tokens por fragmento con el límite de validación como regla rotulada."""
    df = pd.DataFrame({"tokens": etapa["tokens"]})
    limite = pd.DataFrame(
        {"limite": [etapa["limite"]], "texto": [f"límite de validación ({etapa['limite']})"]}
    )
    hist = (
        alt.Chart(df)
        .mark_bar(color=tokens["dato"])
        .encode(
            x=alt.X(
                "tokens:Q",
                bin=alt.Bin(maxbins=etapa["contenedores"]),
                title="tokens aproximados por fragmento",
            ),
            y=alt.Y("count():Q", title="cantidad de fragmentos"),
            tooltip=[alt.Tooltip("count():Q", title="Fragmentos")],
        )
    )
    regla = alt.Chart(limite).mark_rule(color=tokens["tinta-2"], strokeDash=[4, 3]).encode(x="limite:Q")
    texto = (
        alt.Chart(limite)
        .mark_text(align="right", dx=-4, dy=8, baseline="top", fontSize=TAM_FUENTE, color=tokens["tinta-2"])
        .encode(x="limite:Q", y=alt.value(0), text="texto:N")
    )
    return alt.layer(hist, regla, texto).properties(height=ALTO_MAX - 20, width="container")


def grafica_etapa(
    clave: str, etapa: Mapping[str, Any], tokens: Mapping[str, str]
) -> alt.Chart | alt.LayerChart:
    if clave == "06_tokens_fragmento":
        g: alt.Chart | alt.LayerChart = histograma(etapa, tokens)
    elif clave == "04_limpieza_paginas":
        g = barras_pareadas(etapa, tokens)
    else:
        g = barras(etapa, tokens)
    # Marca para identificar la gráfica de cada etapa (pruebas AppTest); no altera el dibujo.
    return _configurar(g.properties(usermeta={"fna_etapa": clave}), tokens)


def subtitulo(etapa: Mapping[str, Any], nota: str) -> str:
    """Subtítulo pequeño: lo que mide la gráfica, la cobertura de las series por página y la fuente."""
    texto = str(etapa["subtitulo"])
    if "total" in etapa and etapa["total"] > MAX_PAGINAS:
        texto += f" · {MAX_PAGINAS} de {etapa['total']} páginas (las de mayor tamaño)"
    return f"{texto} · {nota}"


def aviso_fuente(metricas: Mapping[str, Any]) -> tuple[str, str]:
    """(tipo, texto) del aviso de procedencia: demostración solo con la semilla; si no, rastreo real."""
    fuente = str(metricas.get("fuente", ""))
    if fuente == "semilla":
        return (
            "info",
            "Las gráficas muestran la base de demostración. Ejecutar `uv run fabrica pipeline` en Windows 11 "
            "(PowerShell o Claude Code) para regenerarlas con el scraping real.",
        )
    rastreo = (metricas.get("bronze") or {}).get("rastreo") or {}
    fecha = str(rastreo.get("fecha") or metricas.get("generado_en", ""))[:10]
    return ("caption", f"Métricas del rastreo real del {fecha} (fuente: {fuente})")
