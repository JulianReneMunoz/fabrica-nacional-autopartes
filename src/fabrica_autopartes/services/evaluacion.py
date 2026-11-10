"""Evaluación sistemática del Q&A con el banco de preguntas (``v1``: ``evaluacion/preguntas.yaml``;
``v2``, por defecto: ``evaluacion/preguntas_v2.yaml``, alineado con el Gold actual).

Métricas (todas calculadas, ninguna supuesta):

* ``exactitud_respondibles``: proporción de preguntas respondibles cuya respuesta contiene
  al menos ``minimo`` hechos clave.
* ``cobertura_contexto``: proporción de preguntas respondibles cuyo contexto entregado al
  modelo contenía los hechos clave (diagnostica fallas de recuperación vs. de generación).
* ``rechazo_correcto``: proporción de preguntas ausentes/fuera de alcance/inyección que
  recibieron rechazo o bloqueo (resistencia a la alucinación).
* ``tasa_fundamentada``: proporción de respuestas respondibles marcadas como fundamentadas.
* ``latencia_media_ms``.
"""

from __future__ import annotations

import json
import unicodedata
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path

import yaml

from fabrica_autopartes.core.config import RAIZ_PROYECTO
from fabrica_autopartes.llm.proveedores import aplica_temperatura
from fabrica_autopartes.llm.salvaguardas import es_rechazo
from fabrica_autopartes.services.asistente import ServicioAsistente

DIR_EVALUACION = RAIZ_PROYECTO / "evaluacion"
# v1 no se modifica (métricas anteriores reproducibles); v2 alinea los hechos con el Gold actual (A-10).
BANCOS: dict[str, Path] = {
    "v1": DIR_EVALUACION / "preguntas.yaml",
    "v2": DIR_EVALUACION / "preguntas_v2.yaml",
}
BANCO_POR_DEFECTO = "v2"
ARCHIVO_PREGUNTAS = BANCOS["v1"]
DIR_RESULTADOS = DIR_EVALUACION / "resultados"


def _norm(texto: str) -> str:
    sin = "".join(c for c in unicodedata.normalize("NFD", texto.lower()) if unicodedata.category(c) != "Mn")
    return " ".join(sin.replace(".", " ").replace(",", " ").split())


def hechos_presentes(texto: str, hechos: list[str]) -> list[str]:
    t = _norm(texto)
    return [h for h in hechos if _norm(h) in t]


@dataclass
class ResultadoPregunta:
    id: str
    tipo: str
    pregunta: str
    respuesta: str
    acierto: bool
    hechos_encontrados: list[str] = field(default_factory=list)
    hechos_en_contexto: list[str] = field(default_factory=list)
    fundamentada: bool = False
    fuentes: list[str] = field(default_factory=list)
    latencia_ms: int = 0
    recuperador: str = "no_aplica"  # el realmente usado (no_aplica con contexto completo o bloqueado)


def ruta_banco(banco: str) -> Path:
    """Archivo del banco ``v1`` o ``v2``; cualquier otro nombre es un error."""
    if banco not in BANCOS:
        raise ValueError(f"Banco desconocido: {banco!r}. Opciones: {', '.join(BANCOS)}.")
    return BANCOS[banco]


def cargar_preguntas(banco: str | Path = BANCO_POR_DEFECTO) -> list[dict]:
    """Preguntas del banco indicado por nombre (``v1``, ``v2``) o por ruta."""
    ruta = banco if isinstance(banco, Path) else ruta_banco(banco)
    return list(yaml.safe_load(ruta.read_text(encoding="utf-8"))["preguntas"])


def evaluar(
    servicio: ServicioAsistente,
    opciones: dict[str, str | None] | None = None,
    preguntas: list[dict] | None = None,
    guardar: bool = True,
    banco: str = BANCO_POR_DEFECTO,
) -> dict:
    op = {k: v for k, v in (opciones or {}).items() if v}
    ruta_banco(banco)  # valida el nombre aunque las preguntas vengan dadas
    preguntas = preguntas or cargar_preguntas(banco)
    resultados: list[ResultadoPregunta] = []
    for p in preguntas:
        r = servicio.responder(p["pregunta"], canal="evaluacion", **op)
        if p["tipo"] == "respondible":
            encontrados = hechos_presentes(r.respuesta, p["hechos"])
            ctx = servicio.base.armar_contexto(
                p["pregunta"],
                r.modo_contexto if r.modo_contexto in ("completo", "seleccion") else "auto",
                servicio.config.presupuesto_tokens_contexto,
                servicio.config.fragmentos_seleccion,
                r.recuperador
                if r.recuperador != "no_aplica"
                else None,  # el mismo contexto que recibió el modelo
            )
            en_ctx = hechos_presentes(ctx.texto, p["hechos"])
            acierto = len(encontrados) >= p.get("minimo", 1) and not es_rechazo(r.respuesta)
        else:
            encontrados, en_ctx = [], []
            acierto = es_rechazo(r.respuesta) or r.modo_contexto == "bloqueado"
        resultados.append(
            ResultadoPregunta(
                id=p["id"],
                tipo=p["tipo"],
                pregunta=p["pregunta"],
                respuesta=r.respuesta,
                acierto=acierto,
                hechos_encontrados=encontrados,
                hechos_en_contexto=en_ctx,
                fundamentada=r.fundamentada,
                fuentes=[f.fragmento_id for f in r.fuentes],
                latencia_ms=r.latencia_ms,
                recuperador=r.recuperador,
            )
        )

    respondibles = [r for r in resultados if r.tipo == "respondible"]
    negativas = [r for r in resultados if r.tipo != "respondible"]
    pregs = {p["id"]: p for p in preguntas}

    def _prop(valores: list[bool]) -> float:
        return round(sum(valores) / len(valores), 3) if valores else 0.0

    metricas = {
        "total_preguntas": len(resultados),
        "respondibles": len(respondibles),
        "negativas": len(negativas),
        "exactitud_respondibles": _prop([r.acierto for r in respondibles]),
        "cobertura_contexto": _prop(
            [len(r.hechos_en_contexto) >= pregs[r.id].get("minimo", 1) for r in respondibles]
        ),
        "rechazo_correcto": _prop([r.acierto for r in negativas]),
        "tasa_fundamentada": _prop([r.fundamentada for r in respondibles]),
        "exactitud_global": _prop([r.acierto for r in resultados]),
        "latencia_media_ms": int(sum(r.latencia_ms for r in resultados) / max(1, len(resultados))),
    }
    proveedor = op.get("proveedor") or servicio.config.proveedor_llm
    modelo = op.get("modelo") or ("lexico-bm25" if proveedor == "extractivo" else servicio.config.modelo_llm)
    modo = op.get("modo_contexto") or servicio.config.modo_contexto
    version = op.get("version_prompt") or servicio.config.version_prompt
    informe = {
        "fecha": datetime.now(UTC).isoformat(timespec="seconds"),
        "banco": banco,
        "proveedor": proveedor,
        "modelo": modelo,
        "version_prompt": version,
        "modo_contexto": modo,
        # Recuperador solicitado; el usado en cada pregunta queda en detalle[].recuperador.
        "recuperador": op.get("recuperador") or servicio.config.recuperador,
        "recuperadores_usados": sorted({r.recuperador for r in resultados}),
        "temperatura": servicio.config.temperatura,
        "temperatura_aplicada": aplica_temperatura(proveedor, modelo),
        "metricas": metricas,
        "detalle": [asdict(r) for r in resultados],
    }
    if guardar:
        servicio.repo.registrar_evaluacion(
            proveedor=proveedor,
            modelo=modelo,
            version_prompt=version,
            metricas=metricas,
            detalle=informe["detalle"],
        )
        DIR_RESULTADOS.mkdir(parents=True, exist_ok=True)
        sello = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        nombre = f"{sello}_{proveedor}_{modelo}_{version}_{modo}_banco-{banco}".replace(":", "-").replace(
            ".", "-"
        )
        ruta = DIR_RESULTADOS / nombre
        Path(f"{ruta}.json").write_text(
            json.dumps(informe, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n"
        )
        Path(f"{ruta}.md").write_text(informe_markdown(informe), encoding="utf-8", newline="\n")
        informe["archivo"] = f"{ruta}.md"
    return informe


def _linea_temperatura(informe: dict) -> str:
    """Temperatura configurada y si el proveedor la aplica (los informes anteriores no la registraban)."""
    if "temperatura" not in informe:
        return ""
    aplicada = "sí" if informe.get("temperatura_aplicada") else "no (el proveedor no la usa)"
    return f"Temperatura configurada: {informe['temperatura']} · aplicada: {aplicada}"


def informe_markdown(informe: dict) -> str:
    m = informe["metricas"]
    lineas = [
        f"# Evaluación Q&A — {informe['proveedor']} / {informe['modelo']} / "
        f"prompt {informe['version_prompt']}",
        "",
        f"Fecha: {informe['fecha']}"
        + (f" · Banco: {informe['banco']}" if "banco" in informe else "")
        + f" · Modo de contexto: {informe['modo_contexto']}"
        + (f" · Recuperador: {informe['recuperador']}" if "recuperador" in informe else ""),
        _linea_temperatura(informe),
        "",
        "| Métrica | Valor |",
        "|---|---|",
        *[f"| {k} | {v} |" for k, v in m.items()],
        "",
        "| ID | Tipo | Acierto | Fundamentada | Hechos encontrados | Fuentes | Respuesta |",
        "|---|---|---|---|---|---|---|",
    ]
    for d in informe["detalle"]:
        resp = d["respuesta"].replace("\n", " ").replace("|", "/")
        if len(resp) > 160:
            resp = resp[:157] + "..."
        lineas.append(
            f"| {d['id']} | {d['tipo']} | {'sí' if d['acierto'] else 'no'} | "
            f"{'sí' if d['fundamentada'] else 'no'} | {', '.join(d['hechos_encontrados'])} | "
            f"{', '.join(d.get('fuentes', []))} | {resp} |"
        )
    return "\n".join(lineas) + "\n"
