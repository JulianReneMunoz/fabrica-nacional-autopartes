"""Voz de IGNIS con Piper en el servidor, sin red (LICENCIAS_TERCEROS.md).

- El modelo se carga una sola vez, de forma perezosa y con lock, en el primer uso (nunca al importar).
- Una síntesis a la vez (semáforo de 1): Piper usa varios núcleos por síntesis y dos en paralelo solo se
  estorban; las peticiones esperan su turno en el threadpool de FastAPI.
- Sin los archivos de la voz se lanza ``ErrorVozNoDisponible`` (503) con la instrucción para descargarla.
- La velocidad se regula con ``FNA_VOZ_LENGTH_SCALE``; el navegador reproduce a ``playbackRate`` 1.0 para no
  alterar el tono.
"""

from __future__ import annotations

import io
import threading
import wave
from collections.abc import Callable
from pathlib import Path
from typing import Any, Protocol

from fabrica_autopartes.core.config import Configuracion
from fabrica_autopartes.core.excepciones import ErrorVozNoDisponible
from fabrica_autopartes.core.registro import obtener_registro

log = obtener_registro(__name__)


class VozSintetizadora(Protocol):
    """Lo que el servicio necesita de ``piper.PiperVoice`` (permite una voz simulada en las pruebas)."""

    # ``syn_config`` es ``piper.SynthesisConfig``; se tipa ``Any`` para no importar Piper al cargar el módulo.
    def synthesize_wav(self, text: str, wav_file: wave.Wave_write, syn_config: Any = None) -> object: ...


def _cargar_piper(ruta_onnx: Path, ruta_json: Path) -> VozSintetizadora:
    from piper import PiperVoice  # importación perezosa: onnxruntime solo se carga si se usa la voz

    return PiperVoice.load(ruta_onnx, config_path=ruta_json)


def _configuracion_piper(length_scale: float) -> object:
    from piper import SynthesisConfig

    return SynthesisConfig(length_scale=length_scale)


class ServicioVoz:
    def __init__(
        self,
        config: Configuracion,
        cargar: Callable[[Path, Path], VozSintetizadora] = _cargar_piper,
        configurar: Callable[[float], object] = _configuracion_piper,
    ) -> None:
        self.config = config
        self._cargar = cargar
        self._configurar = configurar
        self._voz: VozSintetizadora | None = None
        self._lock_carga = threading.Lock()
        # Una síntesis a la vez (requisito del PR de voz): las demás esperan su turno.
        self._turno = threading.Semaphore(1)

    def disponible(self) -> bool:
        return self.config.ruta_voz_onnx.is_file() and self.config.ruta_voz_json.is_file()

    def _voz_cargada(self) -> VozSintetizadora:
        if self._voz is None:
            with self._lock_carga:
                if self._voz is None:
                    if not self.disponible():
                        raise ErrorVozNoDisponible()
                    self._voz = self._cargar(self.config.ruta_voz_onnx, self.config.ruta_voz_json)
                    log.info("Voz de Piper cargada: %s", self.config.voz_modelo)
        return self._voz

    def sintetizar(self, texto: str) -> bytes:
        """WAV PCM de 16 bits mono (22 050 Hz con las voces del proyecto) para ``texto``."""
        voz = self._voz_cargada()
        ajustes = self._configurar(self.config.voz_length_scale)
        with self._turno:
            bufer = io.BytesIO()
            with wave.open(bufer, "wb") as wav:
                voz.synthesize_wav(texto, wav, syn_config=ajustes)
            return bufer.getvalue()
