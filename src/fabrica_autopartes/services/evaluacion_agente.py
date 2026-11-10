"""Validación formal del agente con un modelo real (A-08): tokens por llamada, costo y banco de 24 preguntas.

Los tokens salen de ``usage_metadata`` de cada ``AIMessage`` que el modelo devolvió en el turno (se guardan en
la memoria del hilo), así que el cálculo no modifica el agente. En Claude Haiku 5.5 la salida incluye los
tokens de razonamiento. Tarifas en ``docs/arquitectura/modelos.md``: USD 0,10 / 0,50 por millón con prompts de
hasta 100 000 tokens; por encima, la solicitud completa paga 0,50 / 2,50.

Los criterios del banco son los de ``services/evaluacion.py`` con los campos estructurados de
``RespuestaAgente``: una respondible acierta con los hechos clave, sin ``rechazo`` y con fuentes; una negativa
acierta con ``rechazo`` o ``bloqueada``.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from langchain_core.messages import AIMessage, BaseMessage

from fabrica_autopartes.core.excepciones import ErrorFNA, ErrorProveedorLLM
from fabrica_autopartes.domain.modelos import RespuestaAgente
from fabrica_autopartes.knowledge.base import BaseConocimiento
from fabrica_autopartes.llm import salvaguardas as sg
from fabrica_autopartes.services.agente import urls_permitidas
from fabrica_autopartes.services.asistente import ServicioAsistente
from fabrica_autopartes.services.evaluacion import DIR_RESULTADOS, cargar_preguntas, hechos_presentes

TOPE_USD_POR_DEFECTO = 0.50


@dataclass(frozen=True)
class Tarifa:
    """USD por millón de tokens (entrada, salida), con una tarifa alta por encima de ``umbral_entrada``."""

    entrada: float
    salida: float
    umbral_entrada: int
    entrada_alta: float
    salida_alta: float


TARIFA_HAIKU_5_5 = Tarifa(
    entrada=0.10, salida=0.50, umbral_entrada=100_000, entrada_alta=0.50, salida_alta=2.50
)


@dataclass(frozen=True)
class ConsumoLlamada:
    entrada: int
    salida: int

    def costo_usd(self, tarifa: Tarifa = TARIFA_HAIKU_5_5) -> float:
        alta = self.entrada > tarifa.umbral_entrada
        pe, ps = (tarifa.entrada_alta, tarifa.salida_alta) if alta else (tarifa.entrada, tarifa.salida)
        return (self.entrada * pe + self.salida * ps) / 1_000_000


@dataclass
class ConsumoTurno:
    llamadas: list[ConsumoLlamada] = field(default_factory=list)

    @property
    def entrada(self) -> int:
        return sum(c.entrada for c in self.llamadas)

    @property
    def salida(self) -> int:
        return sum(c.salida for c in self.llamadas)

    def costo_usd(self, tarifa: Tarifa = TARIFA_HAIKU_5_5) -> float:
        return sum(c.costo_usd(tarifa) for c in self.llamadas)

    def resumen(self, tarifa: Tarifa = TARIFA_HAIKU_5_5) -> dict:
        return {
            "llamadas_modelo": len(self.llamadas),
            "tokens_entrada": self.entrada,
            "tokens_salida": self.salida,
            "costo_usd": round(self.costo_usd(tarifa), 6),
            "por_llamada": [asdict(c) for c in self.llamadas],
        }


def consumo_de_mensajes(mensajes: Sequence[BaseMessage]) -> ConsumoTurno:
    """Una entrada por cada respuesta del modelo con ``usage_metadata``, incluidas las que solo traen
    ``tool_calls`` (los mensajes simulados sin ``usage_metadata`` no cuentan)."""
    llamadas = []
    for m in mensajes:
        uso = m.usage_metadata if isinstance(m, AIMessage) else None
        if uso:
            llamadas.append(ConsumoLlamada(int(uso.get("input_tokens", 0)), int(uso.get("output_tokens", 0))))
    return ConsumoTurno(llamadas)


def preguntar_con_consumo(
    servicio: ServicioAsistente, pregunta: str, thread_id: str, canal: str = "evaluacion"
) -> tuple[RespuestaAgente, ConsumoTurno]:
    """Un turno del agente y el consumo de las llamadas al modelo hechas en ese turno."""
    previos = len(servicio.agente.historial(thread_id))
    r = servicio.preguntar_agente(pregunta, thread_id, canal=canal)
    return r, consumo_de_mensajes(servicio.agente.historial(thread_id)[previos:])


def urls_citadas(texto: str) -> list[str]:
    return sg.urls_en(texto)


def urls_fuera_de_fuentes(r: RespuestaAgente, base: BaseConocimiento) -> list[str]:
    """URL de la respuesta que no permite la regla del agente (vacío = todas válidas).

    La misma regla que ``services.agente`` (A-09): campo ``url`` de una fuente citada o URL escrita en su
    texto.
    """
    textos: dict[str, str] = {}
    for f in r.fuentes:
        try:
            textos[f.fragmento_id] = base.obtener(f.fragmento_id).texto
        except ErrorFNA:
            continue
    validas = urls_permitidas(r.fuentes, textos)
    return [u for u in urls_citadas(r.respuesta) if u not in validas]


@dataclass
class ResultadoAgente:
    id: str
    tipo: str
    pregunta: str
    respuesta: str = ""
    acierto: bool = False
    rechazo: bool = False
    bloqueada: bool = False
    rechazada_por_seguridad: bool = False
    fundamentada: bool = False
    llamadas_herramienta: int = 0
    hechos_encontrados: list[str] = field(default_factory=list)
    fuentes: list[str] = field(default_factory=list)
    urls_citadas: list[str] = field(default_factory=list)
    urls_invalidas: list[str] = field(default_factory=list)
    latencia_ms: int = 0
    consumo: dict = field(default_factory=dict)
    error: str | None = None


def _sin_secretos(texto: str, secretos: Sequence[str]) -> str:
    for s in secretos:
        if s:
            texto = texto.replace(s, "[secreto retirado]")
    return texto


def evaluar_agente(
    servicio: ServicioAsistente,
    preguntas: list[dict] | None = None,
    tope_usd: float = TOPE_USD_POR_DEFECTO,
    guardar: bool = True,
    directorio: Path = DIR_RESULTADOS,
    tarifa: Tarifa = TARIFA_HAIKU_5_5,
) -> dict:
    """Corre el banco contra el agente, una pregunta por ``thread_id``.

    Se detiene al superar ``tope_usd`` o ante el primer ``ErrorProveedorLLM``, que queda en el detalle.
    """
    preguntas = preguntas or cargar_preguntas()
    sello = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    resultados: list[ResultadoAgente] = []
    acumulado = 0.0
    interrumpido = False
    interrumpido_error = False
    for p in preguntas:
        if acumulado > tope_usd:
            interrumpido = True
            break
        thread_id = f"banco-{sello}-{p['id']}"  # un hilo por pregunta: la memoria no mezcla preguntas
        try:
            r, consumo = preguntar_con_consumo(servicio, p["pregunta"], thread_id)
        except ErrorProveedorLLM as exc:
            consumo = consumo_de_mensajes(servicio.agente.historial(thread_id))  # lo gastado antes del error
            acumulado += consumo.costo_usd(tarifa)
            resultados.append(
                ResultadoAgente(
                    p["id"], p["tipo"], p["pregunta"], consumo=consumo.resumen(tarifa), error=str(exc)[:500]
                )
            )
            # Credenciales, saldo o solicitud inválida se repetirían en cada pregunta: se detiene el banco.
            interrumpido_error = True
            break
        acumulado += consumo.costo_usd(tarifa)
        invalidas = urls_fuera_de_fuentes(r, servicio.base)
        if p["tipo"] == "respondible":
            encontrados = hechos_presentes(r.respuesta, p["hechos"])
            acierto = len(encontrados) >= p.get("minimo", 1) and not r.rechazo and bool(r.fuentes)
            acierto = acierto and not invalidas
        else:
            encontrados = []
            acierto = r.rechazo or r.bloqueada
        resultados.append(
            ResultadoAgente(
                id=p["id"],
                tipo=p["tipo"],
                pregunta=p["pregunta"],
                respuesta=r.respuesta,
                acierto=acierto,
                rechazo=r.rechazo,
                bloqueada=r.bloqueada,
                rechazada_por_seguridad=r.rechazada_por_seguridad,
                fundamentada=r.fundamentada,
                llamadas_herramienta=r.llamadas_herramienta,
                hechos_encontrados=encontrados,
                fuentes=[f.fragmento_id for f in r.fuentes],
                urls_citadas=urls_citadas(r.respuesta),
                urls_invalidas=invalidas,
                latencia_ms=r.latencia_ms,
                consumo=consumo.resumen(tarifa),
            )
        )

    def _prop(valores: list[bool]) -> float:
        return round(sum(valores) / len(valores), 3) if valores else 0.0

    respondibles = [r for r in resultados if r.tipo == "respondible"]
    negativas = [r for r in resultados if r.tipo != "respondible"]
    llamadas = [ConsumoLlamada(**c) for r in resultados for c in r.consumo["por_llamada"]]
    total = ConsumoTurno(llamadas)
    informe = {
        "fecha": datetime.now(UTC).isoformat(timespec="seconds"),
        "proveedor": servicio.agente.proveedor,
        "modelo": servicio.agente.modelo,
        "tarifa_usd_por_millon": asdict(tarifa),
        "tope_usd": tope_usd,
        "interrumpido_por_tope": interrumpido,
        "interrumpido_por_error": interrumpido_error,
        "metricas": {
            "preguntas_ejecutadas": len(resultados),
            "total_preguntas": len(preguntas),
            "exactitud_respondibles": _prop([r.acierto for r in respondibles]),
            "rechazo_correcto": _prop([r.acierto for r in negativas]),
            "tasa_fundamentada": _prop([r.fundamentada for r in respondibles]),
            "exactitud_global": _prop([r.acierto for r in resultados]),
            "con_urls_invalidas": sum(1 for r in resultados if r.urls_invalidas),
            "errores": sum(1 for r in resultados if r.error),
            "latencia_media_ms": int(sum(r.latencia_ms for r in resultados) / max(1, len(resultados))),
        },
        "consumo": {
            "llamadas_modelo": len(llamadas),
            "tokens_entrada": total.entrada,
            "tokens_salida": total.salida,
            "costo_usd": round(total.costo_usd(tarifa), 6),
            "llamadas_tarifa_alta": sum(1 for c in llamadas if c.entrada > tarifa.umbral_entrada),
        },
        "detalle": [asdict(r) for r in resultados],
    }
    if guardar:
        clave = servicio.config.anthropic_api_key
        texto = json.dumps(informe, ensure_ascii=False, indent=2)
        texto = _sin_secretos(texto, [clave.get_secret_value() if clave else ""])
        directorio.mkdir(parents=True, exist_ok=True)
        ruta = directorio / f"{sello}_agente_{informe['modelo']}.json".replace(":", "-")
        ruta.write_text(texto, encoding="utf-8", newline="\n")
        informe["archivo"] = str(ruta)
    return informe
