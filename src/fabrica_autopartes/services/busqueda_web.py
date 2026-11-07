"""Servicio de búsqueda web complementaria (fase 9, ADR-019).

Reglas: nunca automática (la llama la persona usuaria tras la frase de rechazo); la detección de
inyección se aplica ANTES de buscar (P24 nunca dispara búsqueda); límite de consultas por ventana de
tiempo; cada hallazgo se registra en ``data/revision/hallazgos_web.jsonl`` como pendiente de revisión
humana y nunca entra a la base.
"""

from __future__ import annotations

import json
import threading
import time
from collections import deque
from datetime import UTC, datetime
from pathlib import Path

from fabrica_autopartes.core.excepciones import ErrorLimiteBusquedaWeb, ErrorPreguntaBloqueada
from fabrica_autopartes.domain.modelos import HallazgoWeb, RespuestaWeb
from fabrica_autopartes.llm.busqueda_web import BuscadorClaudeCode, BuscadorWeb, fecha_hoy
from fabrica_autopartes.llm.salvaguardas import detectar_inyeccion
from fabrica_autopartes.pipelines.texto import anonimizar_correos

SIN_RESULTADOS = "No se encontró en la web información con fuente verificable para esta pregunta."
MAX_CONSULTAS = 5
VENTANA_S = 600.0


class ServicioBusquedaWeb:
    def __init__(
        self,
        archivo_hallazgos: Path,
        buscador: BuscadorWeb | None = None,
        max_consultas: int = MAX_CONSULTAS,
        ventana_s: float = VENTANA_S,
    ) -> None:
        self.archivo_hallazgos = archivo_hallazgos
        self.buscador: BuscadorWeb = buscador or BuscadorClaudeCode()
        self.max_consultas = max_consultas
        self.ventana_s = ventana_s
        self._marcas: deque[float] = deque()
        self._candado = threading.Lock()

    def _reservar_cupo(self) -> None:
        ahora = time.monotonic()
        with self._candado:
            while self._marcas and ahora - self._marcas[0] > self.ventana_s:
                self._marcas.popleft()
            if len(self._marcas) >= self.max_consultas:
                raise ErrorLimiteBusquedaWeb(
                    f"Se alcanzó el límite de {self.max_consultas} búsquedas web "
                    f"cada {self.ventana_s / 60:.0f} min."
                )
            self._marcas.append(ahora)

    def _registrar(self, pregunta: str, hallazgos: list[HallazgoWeb]) -> None:
        if not hallazgos:
            return
        self.archivo_hallazgos.parent.mkdir(parents=True, exist_ok=True)
        registrado = datetime.now(UTC).isoformat(timespec="seconds")
        with self.archivo_hallazgos.open("a", encoding="utf-8", newline="\n") as f:
            for h in hallazgos:
                fila = {
                    "estado": "pendiente_revision",
                    "pregunta": pregunta,
                    **h.model_dump(),
                    "registrado": registrado,
                }
                f.write(json.dumps(fila, ensure_ascii=False) + "\n")

    def buscar(self, pregunta: str) -> RespuestaWeb:
        pregunta = anonimizar_correos(pregunta.strip())  # Ley 1581: también la pregunta que se registra
        if detectar_inyeccion(pregunta):
            # Antes de cualquier búsqueda: el buscador no se invoca y no se consume cupo.
            raise ErrorPreguntaBloqueada(
                "La pregunta contiene instrucciones que intentan cambiar el comportamiento del sistema; "
                "no se realiza la búsqueda web."
            )
        self._reservar_cupo()
        inicio = time.perf_counter()
        resultado = self.buscador.buscar(pregunta)
        fecha = fecha_hoy()
        # Ley 1581: los correos no corporativos se anonimizan antes de guardar o mostrar cualquier texto web.
        hallazgos = [
            HallazgoWeb(dato=anonimizar_correos(h["dato"]), url=h["url"], fecha_consulta=fecha)
            for h in resultado.hallazgos
        ]
        self._registrar(pregunta, hallazgos)
        encontrado = bool(hallazgos)
        return RespuestaWeb(
            pregunta=pregunta,
            respuesta=anonimizar_correos(resultado.respuesta or SIN_RESULTADOS)
            if encontrado
            else SIN_RESULTADOS,
            hallazgos=hallazgos,
            encontrado=encontrado,
            fecha_consulta=fecha,
            proveedor=self.buscador.proveedor,
            modelo=self.buscador.modelo,
            version_prompt=self.buscador.version_prompt,
            latencia_ms=int((time.perf_counter() - inicio) * 1000),
        )
