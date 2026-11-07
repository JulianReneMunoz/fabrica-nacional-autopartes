"""Cadenas LCEL (LangChain Expression Language) para las tres tareas del Módulo 1:
Resumen, FAQ y Q&A. Cada cadena es ``plantilla | modelo | analizador``.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.output_parsers import StrOutputParser

from fabrica_autopartes.core.config import Configuracion
from fabrica_autopartes.domain.modelos import (
    Fuente,
    ItemFAQ,
    RespuestaQA,
    ResultadoFAQ,
    ResultadoResumen,
)
from fabrica_autopartes.knowledge.base import BaseConocimiento
from fabrica_autopartes.llm import salvaguardas as sg
from fabrica_autopartes.llm.catalogo_prompts import obtener_prompt
from fabrica_autopartes.llm.extractivo import RECHAZO
from fabrica_autopartes.llm.proveedores import crear_modelo

ENFOQUE_GENERAL = "general: identidad, negocios, presencia y contacto"


@dataclass
class Opciones:
    proveedor: str
    modelo: str
    version_prompt: str
    modo_contexto: str
    recuperador: str = "bm25"


def _opciones(config: Configuracion, **sobrescritos: str | None) -> Opciones:
    proveedor = sobrescritos.get("proveedor") or config.proveedor_llm
    modelo = sobrescritos.get("modelo") or ("lexico-bm25" if proveedor == "extractivo" else config.modelo_llm)
    if proveedor == "claude_code":
        from fabrica_autopartes.llm.claude_code import modelo_claude_code

        modelo = modelo_claude_code(modelo)  # registra el modelo realmente usado (p. ej. "sonnet")
    return Opciones(
        proveedor=proveedor,
        modelo=modelo,
        version_prompt=sobrescritos.get("version_prompt") or config.version_prompt,
        modo_contexto=sobrescritos.get("modo_contexto") or config.modo_contexto,
        recuperador=sobrescritos.get("recuperador") or config.recuperador,
    )


def _ms(inicio: float) -> int:
    return int((time.perf_counter() - inicio) * 1000)


# --------------------------------------------------------------------------- Q&A
def ejecutar_qa(
    pregunta: str,
    base: BaseConocimiento,
    config: Configuracion,
    modelo_llm: BaseChatModel | None = None,
    **sobrescritos: str | None,
) -> RespuestaQA:
    op = _opciones(config, **sobrescritos)
    vp = obtener_prompt("qa", op.version_prompt)
    inicio = time.perf_counter()

    if sg.detectar_inyeccion(pregunta):
        return RespuestaQA(
            pregunta=pregunta,
            respuesta=(
                "La solicitud contiene instrucciones que intentan modificar el comportamiento "
                "del asistente y no se procesa. Reformular la pregunta sobre la empresa."
            ),
            fundamentada=False,
            confianza="ninguna",
            version_prompt=op.version_prompt,
            proveedor=op.proveedor,
            modelo=op.modelo,
            modo_contexto="bloqueado",
            latencia_ms=_ms(inicio),
        )

    ctx = base.armar_contexto(
        pregunta,
        op.modo_contexto,
        config.presupuesto_tokens_contexto,
        config.fragmentos_seleccion,
        op.recuperador,
    )
    llm = modelo_llm or crear_modelo(config, op.proveedor, op.modelo, salida_json=vp.formato_salida == "json")
    cadena = vp.plantilla() | llm | StrOutputParser()
    bruto = cadena.invoke({"empresa": config.empresa_nombre, "contexto": ctx.texto, "pregunta": pregunta})

    ids_contexto = {f.id: f for f in ctx.fragmentos}
    confianza = "media"
    if vp.formato_salida == "json":
        datos = sg.analizar_json(bruto) or {}
        respuesta = str(datos.get("respuesta") or bruto).strip()
        citadas = [str(i) for i in datos.get("fuentes", []) if isinstance(i, str)]
        confianza = str(datos.get("confianza", "media")).lower()
    else:
        respuesta = bruto.strip()
        citadas = sg.extraer_citas_texto(respuesta)
        respuesta = sg.quitar_citas(respuesta) if citadas else respuesta

    validas = [i for i in citadas if i in ids_contexto]
    rechazo = sg.es_rechazo(respuesta)
    texto_ref = " ".join(ids_contexto[i].texto for i in validas) if validas else ctx.texto
    puntaje = sg.puntaje_fundamentacion(respuesta, texto_ref)
    fundamentada = (not rechazo) and puntaje >= sg.UMBRAL_FUNDAMENTACION
    if citadas and len(validas) < len(citadas):
        fundamentada = False  # citas inventadas
    if rechazo:
        respuesta, confianza = RECHAZO, "ninguna"
    if confianza not in ("alta", "media", "baja", "ninguna"):
        confianza = "media"

    return RespuestaQA(
        pregunta=pregunta,
        respuesta=respuesta,
        fuentes=[
            Fuente(fragmento_id=i, titulo=ids_contexto[i].titulo, url=ids_contexto[i].url) for i in validas
        ],
        fundamentada=fundamentada,
        confianza=confianza,  # type: ignore[arg-type]
        version_prompt=op.version_prompt,
        proveedor=op.proveedor,
        modelo=op.modelo,
        modo_contexto=ctx.modo,
        latencia_ms=_ms(inicio),
    )


# --------------------------------------------------------------------------- FAQ
_PAR_PR = re.compile(r"P:\s*(.+?)\s*\nR:\s*(.+?)(?=\nP:|\Z)", re.S)


def ejecutar_faq(
    base: BaseConocimiento,
    config: Configuracion,
    n_preguntas: int = 8,
    modelo_llm: BaseChatModel | None = None,
    **sobrescritos: str | None,
) -> ResultadoFAQ:
    op = _opciones(config, **sobrescritos)
    vp = obtener_prompt("faq", op.version_prompt)
    inicio = time.perf_counter()
    ctx = base.armar_contexto(None, "completo", config.presupuesto_tokens_contexto)
    llm = modelo_llm or crear_modelo(config, op.proveedor, op.modelo, salida_json=vp.formato_salida == "json")
    bruto = (vp.plantilla() | llm | StrOutputParser()).invoke(
        {"empresa": config.empresa_nombre, "contexto": ctx.texto, "n": n_preguntas}
    )
    ids = {f.id for f in ctx.fragmentos}
    advertencias: list[str] = []
    items: list[ItemFAQ] = []
    if vp.formato_salida == "json":
        datos = sg.analizar_json(bruto) or {}
        for it in datos.get("faq", []):
            if not isinstance(it, dict) or not it.get("pregunta"):
                continue
            fuentes = [f for f in it.get("fuentes", []) if f in ids]
            if not fuentes:
                advertencias.append(f"Descartada por falta de citas válidas: {it.get('pregunta')}")
                continue
            items.append(ItemFAQ(pregunta=it["pregunta"], respuesta=it.get("respuesta", ""), fuentes=fuentes))
    else:
        for p, r in _PAR_PR.findall(bruto):
            citas = [c for c in sg.extraer_citas_texto(r) if c in ids]
            items.append(ItemFAQ(pregunta=p.strip(), respuesta=sg.quitar_citas(r.strip()), fuentes=citas))
        if not items:
            advertencias.append("La salida no siguió el formato P:/R:; se devuelve texto crudo.")
            items.append(ItemFAQ(pregunta="(salida sin formato)", respuesta=bruto.strip()))
    return ResultadoFAQ(
        items=items[:n_preguntas],
        version_prompt=op.version_prompt,
        proveedor=op.proveedor,
        modelo=op.modelo,
        latencia_ms=_ms(inicio),
        advertencias=advertencias,
    )


# ----------------------------------------------------------------------- Resumen
def ejecutar_resumen(
    base: BaseConocimiento,
    config: Configuracion,
    enfoque: str = ENFOQUE_GENERAL,
    modelo_llm: BaseChatModel | None = None,
    **sobrescritos: str | None,
) -> ResultadoResumen:
    op = _opciones(config, **sobrescritos)
    vp = obtener_prompt("resumen", op.version_prompt)
    inicio = time.perf_counter()
    ctx = base.armar_contexto(None, "completo", config.presupuesto_tokens_contexto)
    llm = modelo_llm or crear_modelo(config, op.proveedor, op.modelo)
    texto = (vp.plantilla() | llm | StrOutputParser()).invoke(
        {"empresa": config.empresa_nombre, "contexto": ctx.texto, "enfoque": enfoque}
    )
    return ResultadoResumen(
        resumen=texto.strip(),
        enfoque=enfoque,
        version_prompt=op.version_prompt,
        proveedor=op.proveedor,
        modelo=op.modelo,
        latencia_ms=_ms(inicio),
    )
