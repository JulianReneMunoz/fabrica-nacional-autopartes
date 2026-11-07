"""Pruebas de la API REST con TestClient (contratos, errores, autorización, auditoría)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from fabrica_autopartes.api.dependencias import obtener_servicio
from fabrica_autopartes.api.main import crear_app


@pytest.fixture
def cliente(servicio):  # type: ignore[no-untyped-def]
    app = crear_app()
    app.dependency_overrides[obtener_servicio] = lambda: servicio
    return TestClient(app)


def test_salud(cliente) -> None:  # type: ignore[no-untyped-def]
    r = cliente.get("/salud")
    assert r.status_code == 200 and r.json()["estado"] == "ok" and r.json()["fragmentos"] > 0


def test_estadisticas(cliente) -> None:  # type: ignore[no-untyped-def]
    assert cliente.get("/api/v1/base/estadisticas").json()["documentos"] >= 10


def test_busqueda_paginada(cliente) -> None:  # type: ignore[no-untyped-def]
    r = cliente.get("/api/v1/base/fragmentos", params={"q": "plantas autopartes", "tamano": 2})
    datos = r.json()
    assert r.status_code == 200 and len(datos["elementos"]) == 2 and datos["total"] >= 2
    assert datos["elementos"][0]["puntaje"] > 0


def test_filtro_por_seccion(cliente) -> None:  # type: ignore[no-untyped-def]
    datos = cliente.get("/api/v1/base/fragmentos", params={"seccion": "negocios"}).json()
    assert all(e["fragmento"]["seccion"].startswith("negocios") for e in datos["elementos"])


def test_fragmento_existente_y_404(cliente) -> None:  # type: ignore[no-untyped-def]
    assert cliente.get("/api/v1/base/fragmentos/contacto#000".replace("#", "%23")).status_code == 200
    r = cliente.get("/api/v1/base/fragmentos/no-existe%23000")
    assert r.status_code == 404 and r.json()["codigo"] == "no_encontrado"


def test_qa_contrato_y_auditoria(cliente) -> None:  # type: ignore[no-untyped-def]
    r = cliente.post("/api/v1/tareas/qa", json={"pregunta": "¿Cuál es el teléfono de contacto?"})
    assert r.status_code == 200
    cuerpo = r.json()
    assert {"respuesta", "fuentes", "fundamentada", "confianza", "version_prompt"} <= set(cuerpo)
    assert "651 5343" in cuerpo["respuesta"]
    aud = cliente.get("/api/v1/auditoria/interacciones", params={"tarea": "qa"}).json()
    assert aud["total"] == 1 and aud["elementos"][0]["canal"] == "api"


def test_qa_validacion_entrada(cliente) -> None:  # type: ignore[no-untyped-def]
    assert cliente.post("/api/v1/tareas/qa", json={"pregunta": "x"}).status_code == 422
    assert (
        cliente.post("/api/v1/tareas/qa", json={"pregunta": "hola hola", "version_prompt": "v9"}).status_code
        == 422
    )


def test_faq_y_resumen(cliente) -> None:  # type: ignore[no-untyped-def]
    faq = cliente.post("/api/v1/tareas/faq", json={"n_preguntas": 4}).json()
    assert 1 <= len(faq["items"]) <= 4
    res = cliente.post("/api/v1/tareas/resumen", json={"enfoque": "negocios"}).json()
    assert res["enfoque"] == "negocios" and res["resumen"]


def test_reconstruir_requiere_clave(cliente) -> None:  # type: ignore[no-untyped-def]
    assert cliente.post("/api/v1/pipeline/reconstruir", json={"fuente": "semilla"}).status_code == 401
    r = cliente.post(
        "/api/v1/pipeline/reconstruir", json={"fuente": "semilla"}, headers={"X-API-Key": "clave-de-prueba"}
    )
    assert r.status_code == 200 and r.json()["fragmentos"] > 0
    ejec = cliente.get("/api/v1/pipeline/ejecuciones").json()
    assert ejec[0]["estado"] == "ok" and ejec[0]["etapa"] == "construccion"


def test_openapi_documenta_endpoints(cliente) -> None:  # type: ignore[no-untyped-def]
    rutas = cliente.get("/openapi.json").json()["paths"]
    for ruta in (
        "/api/v1/tareas/qa",
        "/api/v1/tareas/faq",
        "/api/v1/tareas/resumen",
        "/api/v1/base/fragmentos",
        "/salud",
    ):
        assert ruta in rutas


def test_proveedor_inaccesible_devuelve_503(config_con_base, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """Con Ollama apagado, las tareas LLM responden 503 con un código claro (no 500)."""
    from fabrica_autopartes.services import asistente

    def caido(*_a, **_k):  # type: ignore[no-untyped-def]
        raise ConnectionRefusedError("[Errno 111] Connection refused")

    monkeypatch.setattr(asistente.cadenas, "ejecutar_qa", caido)
    servicio = asistente.ServicioAsistente(config_con_base)
    app = crear_app()
    app.dependency_overrides[obtener_servicio] = lambda: servicio
    r = TestClient(app).post("/api/v1/tareas/qa", json={"pregunta": "¿Dónde queda la sede principal?"})
    assert r.status_code == 503
    assert r.json()["codigo"] == "proveedor_llm_no_disponible"


# ---------------------------------------------------------------- recuperador (ADR-023)
def test_qa_recuperador_por_defecto_bm25(cliente) -> None:  # type: ignore[no-untyped-def]
    r = cliente.post(
        "/api/v1/tareas/qa",
        json={"pregunta": "¿Dónde queda la sede principal?", "modo_contexto": "seleccion"},
    ).json()
    assert r["recuperador"] == "bm25" and r["modo_contexto"] == "seleccion"
    completo = cliente.post(
        "/api/v1/tareas/qa", json={"pregunta": "¿Dónde queda la sede principal?", "modo_contexto": "completo"}
    ).json()
    assert completo["recuperador"] == "no_aplica"


def test_qa_recuperador_semantico_con_embeddings_deterministas(cliente, servicio) -> None:  # type: ignore[no-untyped-def]
    from fabrica_autopartes.knowledge.embeddings import EmbeddingsDeterministas, IndiceVectorialMemoria

    semantico = IndiceVectorialMemoria(servicio.base.fragmentos, EmbeddingsDeterministas())
    servicio.base.usar_recuperador_semantico(semantico)
    pregunta = "¿Cuál es el teléfono de contacto?"
    r = cliente.post(
        "/api/v1/tareas/qa",
        json={"pregunta": pregunta, "modo_contexto": "seleccion", "recuperador": "semantico"},
    )
    assert r.status_code == 200
    datos = r.json()
    assert datos["recuperador"] == "semantico"
    elegidos = {x.fragmento.id for x in semantico.buscar(pregunta, servicio.config.fragmentos_seleccion)}
    assert datos["fuentes"], "el modelo extractivo cita al menos un fragmento del contexto"
    for fuente in datos["fuentes"]:
        assert set(fuente) == {"fragmento_id", "titulo", "url"}
        assert fuente["fragmento_id"] in elegidos and fuente["url"].startswith("http")


def test_qa_recuperador_semantico_no_disponible_503(cliente, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    from fabrica_autopartes.knowledge import semantica

    monkeypatch.setattr(semantica, "extra_instalado", lambda: False)
    r = cliente.post(
        "/api/v1/tareas/qa",
        json={"pregunta": "¿Dónde queda la sede?", "modo_contexto": "seleccion", "recuperador": "semantico"},
    )
    assert r.status_code == 503
    cuerpo = r.json()
    assert cuerpo["codigo"] == "recuperador_no_disponible"
    assert "make instalar-semantica-gpu" in cuerpo["mensaje"] and "make indexar" in cuerpo["mensaje"]


def test_qa_recuperador_invalido_422(cliente) -> None:  # type: ignore[no-untyped-def]
    r = cliente.post(
        "/api/v1/tareas/qa", json={"pregunta": "¿Dónde queda la sede?", "recuperador": "vectorial"}
    )
    assert r.status_code == 422


def test_qa_semantico_con_contexto_completo_no_exige_el_indice(cliente, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """Con el contexto completo no se recupera nada: pedir 'semantico' no da 503 y se informa 'no_aplica'."""
    from fabrica_autopartes.knowledge import semantica

    monkeypatch.setattr(semantica, "extra_instalado", lambda: False)
    r = cliente.post(
        "/api/v1/tareas/qa",
        json={"pregunta": "¿Dónde queda la sede?", "modo_contexto": "completo", "recuperador": "semantico"},
    )
    assert r.status_code == 200 and r.json()["recuperador"] == "no_aplica"
