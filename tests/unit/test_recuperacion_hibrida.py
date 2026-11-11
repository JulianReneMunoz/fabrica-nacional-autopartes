"""Recuperador híbrido RRF, vuelta a bm25 y precarga del semántico (ADR-031). Sin modelos ni red."""

from __future__ import annotations

import threading

import pytest
from fastapi.testclient import TestClient

from fabrica_autopartes.core.config import Configuracion
from fabrica_autopartes.core.excepciones import ErrorConfiguracion, ErrorRecuperadorNoDisponible
from fabrica_autopartes.domain.modelos import Fragmento
from fabrica_autopartes.knowledge.base import BaseConocimiento
from fabrica_autopartes.knowledge.recuperacion import CONSTANTE_RRF, RecuperadorHibrido, Resultado
from fabrica_autopartes.services.asistente import ServicioAsistente


def _frag(i: str) -> Fragmento:
    return Fragmento(
        id=i,
        documento_id=i,
        url=f"https://ejemplo.test/{i}",
        titulo=i,
        seccion="s",
        texto=i,
        tokens_aprox=1,
        orden=0,
    )


class Fijo:
    """Recuperador falso que devuelve siempre la misma lista ordenada."""

    def __init__(self, ids: list[str]) -> None:
        self.ids = ids
        self.pedidos: list[int] = []

    def buscar(self, consulta: str, k: int = 5) -> list[Resultado]:
        self.pedidos.append(k)
        return [Resultado(_frag(i), 1.0) for i in self.ids[:k]]


# ---------------------------------------------------------------- fusión RRF
def test_rrf_suma_rangos_reciprocos_y_ordena() -> None:
    lexico, semantico = Fijo(["a", "b", "c"]), Fijo(["c", "a", "d"])
    r = RecuperadorHibrido(lexico, semantico).buscar("x", 4)
    # a: 1/61 + 1/62 · c: 1/63 + 1/61 · b: 1/62 · d: 1/63
    assert [x.fragmento.id for x in r] == ["a", "c", "b", "d"]
    assert r[0].puntaje == round(1 / (CONSTANTE_RRF + 1) + 1 / (CONSTANTE_RRF + 2), 6)
    assert lexico.pedidos == semantico.pedidos == [20]  # profundidad de cada recuperador


def test_rrf_sin_duplicados_respeta_k_y_es_determinista() -> None:
    hibrido = RecuperadorHibrido(Fijo(["a", "b"]), Fijo(["b", "a"]))
    primero = [x.fragmento.id for x in hibrido.buscar("x", 5)]
    assert primero == ["a", "b"]  # empate exacto: se ordena por id
    assert primero == [x.fragmento.id for x in hibrido.buscar("x", 5)]
    assert len(hibrido.buscar("x", 1)) == 1 and hibrido.buscar("x", 0) == []


def test_rrf_un_fragmento_en_ambos_supera_a_uno_solo_en_un_recuperador() -> None:
    r = RecuperadorHibrido(Fijo(["solo-lexico", "comun"]), Fijo(["solo-semantico", "comun"])).buscar("x", 3)
    assert r[0].fragmento.id == "comun"


# ------------------------------------------------------- base y vuelta a bm25
@pytest.fixture
def base(config_con_base: Configuracion) -> BaseConocimiento:
    return BaseConocimiento(config_con_base.dir_gold)


def test_hibrido_sin_semantico_lanza_y_buscar_con_respaldo_vuelve_a_bm25(base: BaseConocimiento) -> None:
    with pytest.raises(ErrorRecuperadorNoDisponible):
        base.recuperador("hibrido")
    resultados, usado = base.buscar_con_respaldo("sede principal", 3, "hibrido")
    assert usado == "bm25"
    assert [r.fragmento.id for r in resultados] == [
        r.fragmento.id for r in base.indice.buscar("sede principal", 3)
    ]


def test_recuperador_desconocido(base: BaseConocimiento) -> None:
    with pytest.raises(ErrorConfiguracion, match="bm25, semantico o hibrido"):
        base.recuperador("vectorial")


def test_precargar_semantico_no_lanza_y_luego_vuelve_a_bm25(base: BaseConocimiento) -> None:
    disponible, motivo = base.precargar_semantico()
    assert not disponible and motivo
    assert base.buscar_con_respaldo("sede", 2, "semantico")[1] == "bm25"


def test_precargar_semantico_con_recuperador_inyectado(base: BaseConocimiento) -> None:
    base.usar_recuperador_semantico(Fijo([base.fragmentos[0].id]))
    assert base.precargar_semantico() == (True, "")
    assert base.buscar_con_respaldo("sede", 2, "hibrido")[1] == "hibrido"


def test_el_semantico_se_carga_una_sola_vez(base: BaseConocimiento, monkeypatch: pytest.MonkeyPatch) -> None:
    from fabrica_autopartes.knowledge import semantica

    cargas: list[int] = []

    class IndiceFalso(Fijo):
        def __init__(self, *_: object) -> None:
            cargas.append(1)
            super().__init__([])

    monkeypatch.setattr(semantica, "disponibilidad", lambda _d: (True, ""))
    monkeypatch.setattr(semantica, "EmbeddingsNomic", lambda *_a, **_k: object())
    monkeypatch.setattr(semantica, "IndiceChroma", IndiceFalso)
    hilos = [threading.Thread(target=base.precargar_semantico) for _ in range(4)]
    for h in hilos:
        h.start()
    for h in hilos:
        h.join()
    base.recuperador("semantico")
    base.buscar_con_respaldo("sede", 2, "hibrido")
    assert cargas == [1]


# ------------------------------------------------------ configuración y precarga
def test_configuracion_por_defecto_hibrido_y_variable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("FNA_AGENTE_RECUPERADOR", raising=False)
    assert Configuracion(_env_file=None).agente_recuperador == "hibrido"  # type: ignore[call-arg]
    monkeypatch.setenv("FNA_AGENTE_RECUPERADOR", "bm25")
    assert Configuracion(_env_file=None).agente_recuperador == "bm25"  # type: ignore[call-arg]
    monkeypatch.setenv("FNA_AGENTE_RECUPERADOR", "vectorial")
    with pytest.raises(ValueError):
        Configuracion(_env_file=None)  # type: ignore[call-arg]


def test_precarga_del_servicio_segun_el_recuperador(servicio: ServicioAsistente) -> None:
    servicio.config = servicio.config.model_copy(update={"agente_recuperador": "bm25"})
    assert servicio.precargar_recuperador_agente() is None
    servicio.config = servicio.config.model_copy(update={"agente_recuperador": "hibrido"})
    hilo = servicio.precargar_recuperador_agente()
    assert hilo is not None
    hilo.join(timeout=30)
    assert not hilo.is_alive()
    # Sin semántico en el directorio de prueba: la herramienta vuelve a bm25 sin volver a comprobar.
    assert servicio.base.buscar_con_respaldo("sede", 2, "hibrido")[1] == "bm25"


def test_la_api_precarga_al_arrancar_sin_bloquear(
    servicio: ServicioAsistente, monkeypatch: pytest.MonkeyPatch
) -> None:
    from fabrica_autopartes.api.dependencias import obtener_servicio
    from fabrica_autopartes.api.main import crear_app

    llamado = threading.Event()

    def precargar(en_segundo_plano: bool = True) -> None:
        assert en_segundo_plano is False  # la API ya está en su propio hilo
        llamado.set()

    monkeypatch.setattr(servicio, "precargar_recuperador_agente", precargar)
    app = crear_app()
    app.dependency_overrides[obtener_servicio] = lambda: servicio
    with TestClient(app) as cliente:  # el bloque «with» ejecuta el ciclo de vida
        assert cliente.get("/salud").status_code == 200
        assert llamado.wait(timeout=10)


def test_la_api_arranca_aunque_falle_la_precarga(
    servicio: ServicioAsistente, monkeypatch: pytest.MonkeyPatch
) -> None:
    from fabrica_autopartes.api.dependencias import obtener_servicio
    from fabrica_autopartes.api.main import crear_app

    def fallar(en_segundo_plano: bool = True) -> None:
        raise RuntimeError("fallo de prueba")

    monkeypatch.setattr(servicio, "precargar_recuperador_agente", fallar)
    app = crear_app()
    app.dependency_overrides[obtener_servicio] = lambda: servicio
    with TestClient(app) as cliente:
        assert cliente.get("/docs").status_code == 200
