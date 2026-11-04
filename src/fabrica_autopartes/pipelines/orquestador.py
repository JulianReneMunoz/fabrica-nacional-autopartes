"""Orquestación del pipeline Medallion: Bronze → Silver → Gold, con métricas por etapa.

Las métricas se guardan en ``data/gold/metricas_etapas.json`` y alimentan las gráficas
del proceso (``uv run fabrica graficas``) y la pestaña "Proceso de datos" de Streamlit.
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass, field
from typing import Literal

from fabrica_autopartes.core.config import Configuracion
from fabrica_autopartes.core.registro import obtener_registro
from fabrica_autopartes.domain.modelos import EstadisticasBase, Fragmento, ahora_utc
from fabrica_autopartes.pipelines import silver
from fabrica_autopartes.pipelines.bronze import AlmacenBronze
from fabrica_autopartes.pipelines.gold import construir_gold

log = obtener_registro(__name__)

Fuente = Literal["auto", "scraping", "semilla", "ambas"]


@dataclass
class ResultadoConstruccion:
    fuente_usada: str
    documentos_silver: int
    duplicados_descartados: int
    estadisticas: EstadisticasBase
    advertencias: list[str] = field(default_factory=list)
    metricas: dict = field(default_factory=dict)


def _metricas_bronze(almacen: AlmacenBronze) -> dict:
    registros = list(almacen.registros())
    errores = 0
    if almacen.errores.exists():
        errores = sum(1 for linea in almacen.errores.read_text(encoding="utf-8").splitlines() if linea)
    return {
        "capturas": len(registros),
        "bytes_totales": sum(r.bytes for r in registros),
        "estados_http": dict(Counter(str(r.estado_http) for r in registros)),
        "errores_registrados": errores,
        "rastreo": almacen.leer_resumen(),
    }


def construir_base(config: Configuracion, fuente: Fuente = "auto") -> ResultadoConstruccion:
    """Reconstruye Silver y Gold sin acceder a la red (solo lee Bronze o la semilla)."""
    almacen = AlmacenBronze(config.dir_bronze)
    advertencias: list[str] = []
    if fuente == "auto":
        fuente = "semilla" if almacen.vacio() else "scraping"
        if fuente == "semilla":
            advertencias.append(
                "Bronze vacío: se usa el corpus semilla de demostración. Ejecutar "
                "'uv run fabrica pipeline' para construir la base desde los sitios oficiales."
            )

    paginas: list[dict] = []
    documentos = []
    if fuente in ("scraping", "ambas"):
        documentos.extend(silver.desde_bronze(almacen, paginas))
    if fuente in ("semilla", "ambas"):
        semilla = silver.desde_semilla(config.dir_semilla)
        documentos.extend(semilla)
        paginas.extend(
            {
                "url": d.url,
                "seccion": d.seccion,
                "bytes_html": None,
                "caracteres_extraidos": len(d.texto),
                "caracteres_sin_plantilla": len(d.texto),
                "caracteres_limpios": len(d.texto),
                "metodo_extraccion": d.origen,
                "descartada": False,
            }
            for d in semilla
        )

    unicos, descartados = silver.deduplicar(documentos)
    silver.escribir_silver(unicos, config.dir_silver)
    log.info("Silver: %d documentos (%d duplicados descartados)", len(unicos), descartados)

    estadisticas = construir_gold(
        unicos,
        config.dir_gold,
        empresa=config.empresa_nombre,
        tamano=config.tamano_fragmento,
        solapamiento=config.solapamiento_fragmento,
    )
    fragmentos = [
        Fragmento.model_validate_json(linea)
        for linea in (config.dir_gold / "fragmentos.jsonl").read_text(encoding="utf-8").splitlines()
        if linea.strip()
    ]
    metricas = {
        "generado_en": ahora_utc().isoformat(),
        "fuente": fuente,
        "bronze": _metricas_bronze(almacen) if fuente in ("scraping", "ambas") else None,
        "paginas": paginas,
        "silver": {
            "documentos": len(unicos),
            "duplicados_descartados": descartados,
            "caracteres": sum(len(d.texto) for d in unicos),
        },
        "gold": {
            "fragmentos": len(fragmentos),
            "caracteres": sum(len(f.texto) for f in fragmentos),
            "tokens_aprox": sum(f.tokens_aprox for f in fragmentos),
            "tokens_por_fragmento": [f.tokens_aprox for f in fragmentos],
            "fragmentos_por_seccion": dict(Counter(f.seccion for f in fragmentos)),
            "tokens_por_seccion": {
                s: sum(f.tokens_aprox for f in fragmentos if f.seccion == s)
                for s in sorted({f.seccion for f in fragmentos})
            },
            "origenes": dict(Counter(f.origen for f in fragmentos)),
        },
    }
    (config.dir_gold / "metricas_etapas.json").write_text(
        json.dumps(metricas, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    log.info("Gold: %d fragmentos, ~%d tokens", estadisticas.fragmentos, estadisticas.tokens_aprox)
    return ResultadoConstruccion(
        fuente_usada=fuente,
        documentos_silver=len(unicos),
        duplicados_descartados=descartados,
        estadisticas=estadisticas,
        advertencias=advertencias,
        metricas=metricas,
    )
