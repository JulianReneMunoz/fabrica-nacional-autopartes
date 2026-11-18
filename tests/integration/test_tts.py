"""POST /api/v1/tts con Piper (voz neuronal en el servidor): WAV válido, sesión obligatoria, 503 sin modelo,
límite de 600 caracteres, errores genéricos, carga perezosa única y una síntesis a la vez."""

from __future__ import annotations

import io
import subprocess
import sys
import threading
import time
import wave
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from fabrica_autopartes.api.dependencias import obtener_servicio
from fabrica_autopartes.api.main import crear_app
from fabrica_autopartes.core.config import RAIZ_PROYECTO, Configuracion
from fabrica_autopartes.llm.extractivo import ModeloExtractivo
from fabrica_autopartes.repositories.auditoria import RepositorioAuditoria
from fabrica_autopartes.services.asistente import ServicioAsistente
from fabrica_autopartes.services.voz import ServicioVoz

TASA = 22050


class VozSimulada:
    """Imita ``piper.PiperVoice.synthesize_wav``: escribe 0,2 s de silencio y registra la concurrencia."""

    def __init__(self, demora_s: float = 0.0, falla: bool = False) -> None:
        self.demora_s = demora_s
        self.falla = falla
        self.activas = 0
        self.max_activas = 0
        self.textos: list[str] = []
        self._lock = threading.Lock()

    def synthesize_wav(self, text: str, wav_file: wave.Wave_write, syn_config: Any = None) -> None:
        if self.falla:
            raise RuntimeError("detalle interno que no debe llegar al cliente")
        with self._lock:
            self.activas += 1
            self.max_activas = max(self.max_activas, self.activas)
            self.textos.append(text)
        time.sleep(self.demora_s)
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(TASA)
        wav_file.writeframes(b"\x00\x00" * int(TASA * 0.2))
        with self._lock:
            self.activas -= 1


def _con_archivos_de_voz(config: Configuracion) -> Configuracion:
    """La ruta del modelo existe (vacía): ``disponible()`` es verdadero y la voz real nunca se carga."""
    config.ruta_voz_onnx.parent.mkdir(parents=True, exist_ok=True)
    config.ruta_voz_onnx.write_bytes(b"")
    config.ruta_voz_json.write_text("{}", encoding="utf-8")
    return config


def _servicio(config: Configuracion, voz: VozSimulada | None = None) -> ServicioAsistente:
    servicio = ServicioAsistente(
        config, RepositorioAuditoria(config.url_base_datos), modelo_llm=ModeloExtractivo()
    )
    if voz is not None:
        servicio._voz = ServicioVoz(
            config, cargar=lambda *_: voz, configurar=lambda escala: {"length_scale": escala}
        )
    return servicio


def _cliente(servicio: ServicioAsistente, con_sesion: bool = True) -> TestClient:
    app = crear_app()
    app.dependency_overrides[obtener_servicio] = lambda: servicio
    cliente = TestClient(app)
    if con_sesion:
        assert cliente.post("/api/v1/sesiones", json={"alias": "voz-01"}).status_code == 201
    return cliente


@pytest.fixture
def voz() -> VozSimulada:
    return VozSimulada()


@pytest.fixture
def servicio(config_con_base: Configuracion, voz: VozSimulada) -> Iterator[ServicioAsistente]:
    s = _servicio(_con_archivos_de_voz(config_con_base), voz)
    yield s
    s.cerrar()


def test_tts_devuelve_un_wav_valido(servicio: ServicioAsistente, voz: VozSimulada) -> None:
    r = _cliente(servicio).post("/api/v1/tts", json={"texto": "Hola, soy IGNIS."})
    assert r.status_code == 200
    assert r.headers["content-type"] == "audio/wav"
    with wave.open(io.BytesIO(r.content)) as wav:
        assert (wav.getnchannels(), wav.getsampwidth(), wav.getframerate()) == (1, 2, TASA)
        assert wav.getnframes() > 0
    assert voz.textos == ["Hola, soy IGNIS."]


def test_tts_exige_sesion(servicio: ServicioAsistente) -> None:
    assert (
        _cliente(servicio, con_sesion=False).post("/api/v1/tts", json={"texto": "Hola."}).status_code == 401
    )


def test_tts_limita_el_texto_a_600_caracteres(servicio: ServicioAsistente) -> None:
    cliente = _cliente(servicio)
    assert cliente.post("/api/v1/tts", json={"texto": "a" * 600}).status_code == 200
    assert cliente.post("/api/v1/tts", json={"texto": "a" * 601}).status_code == 422
    assert cliente.post("/api/v1/tts", json={"texto": ""}).status_code == 422


def test_sin_modelo_responde_503_con_la_instruccion(config_con_base: Configuracion) -> None:
    servicio = _servicio(config_con_base)  # voz real, sin archivos en dir_voces
    try:
        r = _cliente(servicio).post("/api/v1/tts", json={"texto": "Hola."})
        assert r.status_code == 503
        assert r.json()["mensaje"] == "Falta la voz: ejecuta scripts/descargar_voz.py"
    finally:
        servicio.cerrar()


def test_un_fallo_de_piper_responde_500_generico(config_con_base: Configuracion) -> None:
    servicio = _servicio(_con_archivos_de_voz(config_con_base), VozSimulada(falla=True))
    try:
        r = _cliente(servicio).post("/api/v1/tts", json={"texto": "Hola."})
        assert r.status_code == 500
        assert "detalle interno" not in r.text and "Traceback" not in r.text
    finally:
        servicio.cerrar()


def test_carga_perezosa_unica_y_una_sintesis_a_la_vez(config_con_base: Configuracion) -> None:
    config = _con_archivos_de_voz(config_con_base)
    voz = VozSimulada(demora_s=0.05)
    cargas: list[Path] = []

    def cargar(onnx: Path, _json: Path) -> VozSimulada:
        cargas.append(onnx)
        time.sleep(0.05)  # ventana para que varios hilos intenten cargar a la vez
        return voz

    servicio_voz = ServicioVoz(config, cargar=cargar, configurar=lambda escala: escala)
    with ThreadPoolExecutor(max_workers=4) as pool:
        resultados = list(pool.map(servicio_voz.sintetizar, [f"Oración {i}." for i in range(4)]))

    assert len(cargas) == 1  # el modelo se carga una sola vez
    assert voz.max_activas == 1  # semáforo de 1: nunca dos síntesis simultáneas
    assert len(resultados) == 4 and all(r.startswith(b"RIFF") for r in resultados)


def test_fna_voz_dir_vacio_usa_data_voces(config: Configuracion, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FNA_VOZ_DIR", "")  # como queda en .env.example
    vacia = Configuracion(_env_file=None, dir_datos=config.dir_datos)  # type: ignore[call-arg]
    assert vacia.voz_dir is None
    assert vacia.dir_voces == config.dir_datos / "voces"


def test_importar_la_api_no_carga_piper() -> None:
    codigo = "import sys, fabrica_autopartes.api.main; print('piper' in sys.modules)"
    salida = subprocess.run(
        [sys.executable, "-c", codigo], capture_output=True, text=True, check=True, timeout=120
    )
    assert salida.stdout.strip().splitlines()[-1] == "False"


# ------------------------------------------------------------------ modelo real (solo si está descargado)
MODELO_REAL = RAIZ_PROYECTO / "data" / "voces" / "es_MX-claude-high.onnx"


@pytest.mark.skipif(not MODELO_REAL.is_file(), reason="Voz no descargada: scripts/descargar_voz.py")
def test_voz_real_es_mx_claude_high(config: Configuracion) -> None:
    real = config.model_copy(update={"voz_dir": MODELO_REAL.parent, "voz_modelo": "es_MX-claude-high"})
    datos = ServicioVoz(real).sintetizar("Hola, soy IGNIS, la asistente de Fanalca.")
    with wave.open(io.BytesIO(datos)) as wav:
        assert (wav.getnchannels(), wav.getsampwidth(), wav.getframerate()) == (1, 2, TASA)
        assert wav.getnframes() / wav.getframerate() > 1.0  # habla de verdad, no un silencio corto
