"""IGNIS con ``hibrido_qdrant`` opcional (R07): BM25 + Qdrant con las exclusiones como filtro de payload,
respaldo a bm25 y el recuperador usado informado por turno (nunca guardado en el agente, que se comparte entre
peticiones). Sin modelo ni red: ``tmp_path`` y ``:memory:`` con ``EmbeddingsDeterministas``."""

from __future__ import annotations

import json
import logging
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from fabrica_autopartes.api.dependencias import obtener_servicio
from fabrica_autopartes.api.main import crear_app
from fabrica_autopartes.core.config import RAIZ_PROYECTO, Configuracion
from fabrica_autopartes.domain.modelos import Fragmento
from fabrica_autopartes.knowledge.base import BaseConocimiento
from fabrica_autopartes.knowledge.embeddings import EmbeddingsDeterministas
from fabrica_autopartes.knowledge.vectorial_qdrant import (
    MEMORIA,
    FiltroPayload,
    IndiceQdrant,
    cerrar_conexiones,
    conexion_compartida,
)
from fabrica_autopartes.llm.extractivo import ModeloExtractivo
from fabrica_autopartes.repositories.auditoria import RepositorioAuditoria, RepositorioMemoriaIgnis
from fabrica_autopartes.repositories.memoria_agente import cerrar_store, crear_store
from fabrica_autopartes.services.agente_ignis_m2 import AgenteIgnisM2, documentos_excluidos
from fabrica_autopartes.services.asistente import ServicioAsistente

EXCLUIDO = "negocio-honda-motos"  # listado del blog en config/ignis_exclusiones.yaml
PREGUNTA = "¿Qué dice el documento sobre los frenos de disco de autopartes?"
DIR_DEMO = RAIZ_PROYECTO / "data" / "demostracion" / "blindaje"


def _frag(i: str, texto: str, documento: str) -> Fragmento:
    return Fragmento(
        id=i,
        documento_id=documento,
        url=f"https://ejemplo-fna.test/{documento}",
        titulo=f"Documento {documento}",
        seccion="autopartes",
        texto=texto,
        tokens_aprox=len(texto.split()),
        orden=0,
    )


FRAGMENTOS = [
    _frag("frenos#000", "Los frenos de disco de autopartes se fabrican en la planta de Yumbo.", "frenos"),
    _frag("plantas#000", "Las plantas de autopartes producen frenos de disco y suspensiones.", "plantas"),
    _frag(
        f"{EXCLUIDO}#000", "Documento con frenos de disco de autopartes frenos disco autopartes.", EXCLUIDO
    ),
]


@pytest.fixture(autouse=True)
def _cerrar_conexiones_compartidas() -> Iterator[None]:
    yield
    cerrar_conexiones()


@pytest.fixture
def base(tmp_path: Path) -> BaseConocimiento:
    gold = tmp_path / "gold"
    gold.mkdir()
    (gold / "fragmentos.jsonl").write_text(
        "".join(f.model_dump_json() + "\n" for f in FRAGMENTOS), encoding="utf-8"
    )
    return BaseConocimiento(gold)


def _indexar(base: BaseConocimiento) -> IndiceQdrant:
    indice = IndiceQdrant(conexion_compartida(MEMORIA), EmbeddingsDeterministas(), base.fragmentos)
    indice.indexar(base.fragmentos)
    base.usar_indice_qdrant(indice)
    return indice


@pytest.fixture
def agentes(tmp_path: Path) -> Iterator[list[AgenteIgnisM2]]:
    """Agentes creados en la prueba; se cierran sus Store al terminar."""
    creados: list[AgenteIgnisM2] = []
    yield creados
    for agente in creados:
        if agente.store is not None:
            cerrar_store(agente.store)


def _agente(
    agentes: list[AgenteIgnisM2], tmp_path: Path, base: BaseConocimiento, recuperador: str = "bm25", **kw: Any
) -> AgenteIgnisM2:
    n = len(agentes)
    agente = AgenteIgnisM2(
        base,
        RepositorioMemoriaIgnis(tmp_path / f"memoria{n}.sqlite"),
        crear_store(tmp_path / f"store{n}.sqlite"),
        recuperador=recuperador,  # type: ignore[arg-type]
        **kw,
    )
    agentes.append(agente)
    return agente


def _ids_citados(resultado: dict[str, Any]) -> list[str]:
    return [c["id"] for c in resultado["citas"]]


def test_las_exclusiones_del_yaml_incluyen_el_documento_de_prueba() -> None:
    assert EXCLUIDO in documentos_excluidos()


def test_hibrido_qdrant_filtra_las_exclusiones_en_el_payload(
    agentes: list[AgenteIgnisM2], tmp_path: Path, base: BaseConocimiento, monkeypatch: pytest.MonkeyPatch
) -> None:
    indice = _indexar(base)
    filtros: list[FiltroPayload] = []
    original = IndiceQdrant.con_filtro

    def con_filtro_espia(self: IndiceQdrant, filtro: FiltroPayload) -> IndiceQdrant:
        filtros.append(filtro)
        return original(self, filtro)

    monkeypatch.setattr(IndiceQdrant, "con_filtro", con_filtro_espia)
    resultado = _agente(agentes, tmp_path, base, "hibrido_qdrant").ejecutar_turno(PREGUNTA, "hilo-q", "u")
    assert resultado["ruta_router"] == "rag_documental"
    assert resultado["recuperador"] == "hibrido_qdrant"
    assert filtros and set(filtros[0].excluir_documentos) == set(documentos_excluidos())
    assert f"{EXCLUIDO}#000" not in _ids_citados(resultado)
    # El filtro de payload ya excluye el documento en Qdrant (no solo después, en Python).
    assert f"{EXCLUIDO}#000" not in [
        r.fragmento.id for r in indice.con_filtro(filtros[0]).buscar(PREGUNTA, 10)
    ]


def test_bm25_por_defecto_no_abre_qdrant_ni_informa_recuperador(
    agentes: list[AgenteIgnisM2], tmp_path: Path, base: BaseConocimiento, monkeypatch: pytest.MonkeyPatch
) -> None:
    def no_usar(*_a: object, **_k: object) -> None:
        raise AssertionError("con bm25 IGNIS no debe usar Qdrant")

    monkeypatch.setattr(BaseConocimiento, "buscar_con_respaldo", no_usar)
    agente = _agente(agentes, tmp_path, base)
    assert agente.recuperador == "bm25"
    resultado = agente.ejecutar_turno(PREGUNTA, "hilo-b", "u")
    assert "recuperador" not in resultado
    assert resultado["citas"] and f"{EXCLUIDO}#000" not in _ids_citados(resultado)


def test_sin_indice_vuelve_a_bm25_y_responde(
    agentes: list[AgenteIgnisM2], tmp_path: Path, base: BaseConocimiento, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.WARNING):
        resultado = _agente(agentes, tmp_path, base, "hibrido_qdrant").ejecutar_turno(PREGUNTA, "hilo-r", "u")
    assert resultado["recuperador"] == "bm25"
    assert resultado["citas"] and resultado["respuesta"]
    assert base._motivo_sin_qdrant is not None
    assert "hibrido_qdrant" in caplog.text and "frenos de disco" not in caplog.text


def test_cada_turno_informa_su_propio_recuperador(
    agentes: list[AgenteIgnisM2], tmp_path: Path, base: BaseConocimiento
) -> None:
    agente = _agente(agentes, tmp_path, base, "hibrido_qdrant")
    _indexar(base)
    primero = agente.ejecutar_turno(PREGUNTA, "hilo-1", "u")
    base.recargar()  # el índice deja de estar disponible: el segundo turno vuelve a bm25
    segundo = agente.ejecutar_turno(PREGUNTA, "hilo-2", "u")
    assert primero["recuperador"] == "hibrido_qdrant"
    assert segundo["recuperador"] == "bm25"
    assert primero["recuperador"] == "hibrido_qdrant"  # el segundo turno no pisó al primero
    assert not hasattr(agente, "ultimo_recuperador")  # nada del turno se guarda en el agente compartido


def test_turno_sin_busqueda_no_informa_recuperador(
    agentes: list[AgenteIgnisM2], tmp_path: Path, base: BaseConocimiento
) -> None:
    resultado = _agente(agentes, tmp_path, base, "hibrido_qdrant").ejecutar_turno(
        "Hola, buenas tardes.", "h", "u"
    )
    assert resultado["ruta_router"] == "directo" and "recuperador" not in resultado


def test_el_caso_5_sigue_usando_la_base_de_demostracion(
    agentes: list[AgenteIgnisM2], tmp_path: Path, base: BaseConocimiento, monkeypatch: pytest.MonkeyPatch
) -> None:
    def no_usar(*_a: object, **_k: object) -> None:
        raise AssertionError("el documento de prueba no pasa por Qdrant")

    monkeypatch.setattr(BaseConocimiento, "buscar_con_respaldo", no_usar)
    demo = BaseConocimiento(DIR_DEMO, recuperador="bm25")
    agente = _agente(agentes, tmp_path, base, "hibrido_qdrant", base_demostracion=demo)
    resultado = agente.ejecutar_turno(
        "¿Qué dice el documento de prueba sobre la política de garantías?", "h5", "u"
    )
    assert resultado["blindaje_activado"] is True
    assert _ids_citados(resultado) == ["documento-de-prueba-blindaje#000"]
    assert resultado["recuperador"] == "bm25"


# ------------------------------------------------------------------ servicio y SSE
def _metadatos_sse(servicio: ServicioAsistente, mensaje: str) -> dict[str, Any]:
    app = crear_app()
    app.dependency_overrides[obtener_servicio] = lambda: servicio
    cliente = TestClient(app)
    assert cliente.post("/api/v1/sesiones", json={"alias": "prueba-01"}).status_code == 201
    r = cliente.post("/api/v1/ignis/stream", json={"mensaje": mensaje, "thread_id": "hilo-sse"})
    assert r.status_code == 200
    eventos = [json.loads(b[6:]) for b in r.text.split("\n\n") if b.startswith("data: {")]
    return next(e for e in eventos if e["tipo"] == "metadatos")


@pytest.mark.parametrize(("recuperador", "esperado"), [("bm25", None), ("hibrido_qdrant", "bm25")])
def test_el_servicio_pasa_el_recuperador_y_el_sse_lo_informa(
    config_con_base: Configuracion, recuperador: str, esperado: str | None
) -> None:
    config = config_con_base.model_copy(update={"ignis_recuperador": recuperador})
    servicio = ServicioAsistente(
        config, RepositorioAuditoria(config.url_base_datos), modelo_llm=ModeloExtractivo()
    )
    try:
        meta = _metadatos_sse(servicio, "Qué dice el documento de autopartes de Fanalca")
        assert servicio._ignis is not None and servicio._ignis.recuperador == recuperador
        # Sin índice Qdrant en la carpeta temporal, hibrido_qdrant vuelve a bm25 y lo informa.
        assert meta.get("recuperador") == esperado
        assert meta["ruta_router"] == "rag_documental"
        assert not config.dir_qdrant.exists()  # consultar no crea la carpeta
    finally:
        servicio.cerrar()
