"""Endpoints SSE y síntesis de voz WAV para el avatar 3D IGNIS (vía ``ServicioAsistente``)."""

from __future__ import annotations

import asyncio
import io
import json
import math
import re
import struct
import wave
from collections.abc import AsyncIterator
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel, Field

from fabrica_autopartes.api.dependencias import obtener_servicio
from fabrica_autopartes.api.routes.sesiones import PATRON_THREAD_ID, poner_cookie, sesion_requerida
from fabrica_autopartes.core.registro import obtener_registro
from fabrica_autopartes.services.asistente import ServicioAsistente, SesionUsuario

log = obtener_registro(__name__)
router_ignis = APIRouter(prefix="/api/v1", tags=["ignis-m2"])


class SolicitudChatIgnis(BaseModel):
    mensaje: str = Field(..., min_length=1, max_length=2000)
    # Obligatorio: con sesiones, un hilo por defecto lo reclamaría el primer usuario que lo usara (ADR-033).
    # El mismo patrón que valida el thread_id de la ruta de mensajes (PATRON_THREAD_ID).
    thread_id: str = Field(..., pattern=PATRON_THREAD_ID)


class SolicitudTTS(BaseModel):
    texto: str = Field(..., min_length=1, max_length=600)


def _generar_wav_formantes_vocoder(texto: str, sample_rate: int = 22050) -> bytes:
    """Genera una onda WAV vocalizada con envolvente silábica para Web Audio y AnalyserNode, sin red."""
    palabras = re.findall(r"\w+", texto)
    duracion = max(1.2, min(6.5, len(palabras) * 0.28))
    total_samples = int(sample_rate * duracion)
    buf = io.BytesIO()

    with wave.open(buf, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)

        frames = bytearray()
        for i in range(total_samples):
            t = i / sample_rate
            # Modulación silábica para que el escáner LED oscile con naturalidad al hablar
            envolvente = max(0.0, math.sin(2.0 * math.pi * 3.8 * t)) ** 0.6
            f0 = 115.0 + 15.0 * math.sin(2.0 * math.pi * 1.7 * t)
            senal = (
                0.55 * math.sin(2.0 * math.pi * f0 * t)
                + 0.30 * math.sin(2.0 * math.pi * (f0 * 2.0) * t)
                + 0.15 * math.sin(2.0 * math.pi * 880.0 * t)
            ) * envolvente
            muestra = int(max(-32767, min(32767, senal * 18000)))
            frames.extend(struct.pack("<h", muestra))

        wav_file.writeframes(bytes(frames))

    return buf.getvalue()


def _evento(datos: dict[str, Any]) -> str:
    return f"data: {json.dumps(datos, ensure_ascii=False)}\n\n"


FIN_STREAM = "data: [DONE]\n\n"


@router_ignis.post("/ignis/stream")
async def stream_ignis_chat(
    req: SolicitudChatIgnis,
    request: Request,
    sesion: Annotated[SesionUsuario, Depends(sesion_requerida)],
    servicio: Annotated[ServicioAsistente, Depends(obtener_servicio)],
) -> StreamingResponse:
    """Respuesta del agente por Server-Sent Events (contrato de ``web/src/ignisCliente.ts``).

    Exige la sesión (ADR-033): 401 sin cookie válida, 403 si el hilo es de otro usuario (o no tiene dueño y ya
    tiene historial), 503 sin ``IGNIS_SECRETO_SESION``. El ``user_id`` sale de la cookie.

    Eventos ``data: <json>`` con ``tipo`` en metadatos, oracion, error y fin; el flujo termina con
    ``data: [DONE]``. Los adjuntos viajan solo en ``metadatos.archivos_adjuntos`` (objetos con url
    bajo /app/).
    """
    # La propiedad del hilo se comprueba antes de abrir el flujo, para responder 403 con su código HTTP.
    await run_in_threadpool(servicio.reclamar_hilo, req.thread_id, sesion.user_id)
    try:
        # El turno es síncrono (SQLite y BM25): se ejecuta fuera del bucle de eventos.
        resultado: dict[str, Any] | None = await run_in_threadpool(
            servicio.responder_ignis, req.mensaje, req.thread_id, sesion.user_id
        )
    except Exception:
        log.exception("Fallo del agente IGNIS en el hilo %s", req.thread_id)
        resultado = None

    async def event_generator() -> AsyncIterator[str]:
        if resultado is None:
            yield _evento({"tipo": "error", "mensaje": "El agente IGNIS no pudo procesar la consulta."})
            yield _evento({"tipo": "fin"})
            yield FIN_STREAM
            return

        meta: dict[str, Any] = {
            "tipo": "metadatos",
            "thread_id": resultado["thread_id"],
            "ruta_router": resultado["ruta_router"],
            "blindaje_activado": resultado["blindaje_activado"],
            "bloqueada": resultado.get("bloqueada", False),
            "citas": resultado["citas"],
            "archivos_adjuntos": resultado["archivos_adjuntos"],
            "justificacion_router": resultado.get("justificacion_router", ""),
        }
        if "score_router" in resultado:
            meta["score_router"] = resultado["score_router"]
        yield _evento(meta)

        texto: str = resultado["respuesta"]
        for oracion in (s.strip() for s in re.split(r"(?<=[.!?])\s+", texto)):
            if oracion:
                yield _evento({"tipo": "oracion", "texto": oracion})
                await asyncio.sleep(0.08)

        yield _evento({"tipo": "fin"})
        yield FIN_STREAM

    respuesta = StreamingResponse(event_generator(), media_type="text/event-stream")
    # FastAPI no copia las cookies de la dependencia a una Response propia: la renovación se pone aquí.
    token = getattr(request.state, "token_sesion", None)
    if token:
        poner_cookie(respuesta, token, servicio.config)
    return respuesta


@router_ignis.post("/tts")
async def sintetizar_voz_ignis(req: SolicitudTTS) -> Response:
    """Endpoint POST /api/v1/tts que retorna audio WAV para la cadena robotizada de Web Audio."""
    # La síntesis es un bucle de Python (hasta ~143 000 muestras): fuera del bucle de eventos.
    wav_bytes = await run_in_threadpool(_generar_wav_formantes_vocoder, req.texto)
    return Response(content=wav_bytes, media_type="audio/wav")
