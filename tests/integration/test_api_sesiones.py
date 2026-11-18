"""Sesiones por HTTP (ADR-033): cookie, aislamiento entre usuarios, propiedad de los hilos, reinicio, login
CSRF, alias fuera de la base y de los logs, secreto ausente y CORS."""

from __future__ import annotations

import json
import logging
from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from fabrica_autopartes.api.dependencias import obtener_servicio
from fabrica_autopartes.api.main import crear_app
from fabrica_autopartes.core.config import Configuracion
from fabrica_autopartes.llm.extractivo import ModeloExtractivo
from fabrica_autopartes.repositories.auditoria import RepositorioAuditoria
from fabrica_autopartes.services.asistente import ServicioAsistente

CASO_2A = (
    "Trabajo en compras de repuestos, prefiero respuestas breves y me interesan las motocicletas. Recuérdalo."
)
CASO_2B = "¿Qué preferencias tengo guardadas?"
ALIAS_A = "compras-01"
ALIAS_B = "ventas-02"


def _servicio(config: Configuracion) -> ServicioAsistente:
    return ServicioAsistente(
        config, RepositorioAuditoria(config.url_base_datos), modelo_llm=ModeloExtractivo()
    )


def _app(servicio: ServicioAsistente) -> Any:
    app = crear_app()
    app.dependency_overrides[obtener_servicio] = lambda: servicio
    return app


@pytest.fixture
def servicio(config_con_base: Configuracion) -> Iterator[ServicioAsistente]:
    s = _servicio(config_con_base)
    yield s
    s.cerrar()


def _entrar(cliente: TestClient, alias: str) -> None:
    r = cliente.post("/api/v1/sesiones", json={"alias": alias})
    assert r.status_code == 201, r.text


def _texto_sse(r: Any) -> str:
    textos = []
    for linea in r.text.splitlines():
        if linea.startswith("data: ") and linea != "data: [DONE]":
            evento = json.loads(linea.removeprefix("data: "))
            if evento.get("tipo") == "oracion":
                textos.append(evento["texto"])
    return " ".join(textos)


def _stream(cliente: TestClient, mensaje: str, hilo: str) -> Any:
    return cliente.post("/api/v1/ignis/stream", json={"mensaje": mensaje, "thread_id": hilo})


def _set_cookie(r: Any) -> str:
    return "; ".join(v for k, v in r.headers.multi_items() if k.lower() == "set-cookie")


# ------------------------------------------------------------------ entrar y cookie
def test_entrar_crea_la_cookie_con_sus_atributos(servicio: ServicioAsistente) -> None:
    cliente = TestClient(_app(servicio))
    r = cliente.post("/api/v1/sesiones", json={"alias": ALIAS_A})
    assert r.status_code == 201
    assert r.json() == {"alias": ALIAS_A, "user_id_corto": servicio.sesiones.user_id_de(ALIAS_A)[:8]}
    cabecera = _set_cookie(r)
    assert "ignis_sesion=" in cabecera
    assert "HttpOnly" in cabecera and "samesite=lax" in cabecera.lower() and "Path=/" in cabecera
    assert "Max-Age=28800" in cabecera
    assert "Secure" not in cabecera  # desactivado por defecto para localhost
    assert ALIAS_A not in cabecera  # cifrada


def test_cookie_secure_configurable(config_con_base: Configuracion) -> None:
    servicio = _servicio(config_con_base.model_copy(update={"cookie_segura": True}))
    try:
        r = TestClient(_app(servicio)).post("/api/v1/sesiones", json={"alias": ALIAS_A})
        assert "Secure" in _set_cookie(r)
    finally:
        servicio.cerrar()


def test_login_csrf_con_text_plain_da_422_y_no_pone_cookie(servicio: ServicioAsistente) -> None:
    """Un formulario externo solo puede enviar text/plain o form sin preflight: no debe iniciar sesión."""
    cliente = TestClient(_app(servicio))
    for tipo in ("text/plain", "application/x-www-form-urlencoded"):
        r = cliente.post(
            "/api/v1/sesiones", content=json.dumps({"alias": ALIAS_A}), headers={"Content-Type": tipo}
        )
        assert r.status_code == 422
        assert "ignis_sesion" not in _set_cookie(r)
    assert cliente.get("/api/v1/sesiones/yo").status_code == 401


@pytest.mark.parametrize("alias", ["ana@gmail.com", "3001234567", "Ana Gómez", "ana-gomez", "ab"])
def test_alias_invalido_da_422_generico_sin_cookie(servicio: ServicioAsistente, alias: str) -> None:
    r = TestClient(_app(servicio)).post("/api/v1/sesiones", json={"alias": alias})
    assert r.status_code == 422
    assert alias not in r.text
    assert "ignis_sesion" not in _set_cookie(r)


def test_yo_renueva_la_cookie_y_sin_sesion_da_401(servicio: ServicioAsistente) -> None:
    cliente = TestClient(_app(servicio))
    assert cliente.get("/api/v1/sesiones/yo").status_code == 401
    _entrar(cliente, ALIAS_A)
    r = cliente.get("/api/v1/sesiones/yo")
    assert r.status_code == 200 and r.json()["alias"] == ALIAS_A
    assert "ignis_sesion=" in _set_cookie(r)  # 8 h deslizantes


@pytest.mark.parametrize("ruta", ["/api/v1/sesiones/yo", "/api/v1/sesiones/yo/hilos"])
def test_cookie_manipulada_da_401(servicio: ServicioAsistente, ruta: str) -> None:
    cliente = TestClient(_app(servicio))
    _entrar(cliente, ALIAS_A)
    token = cliente.cookies.get("ignis_sesion")
    assert token
    # Se limpia el almacén: cookies.set agregaría una segunda cookie y el cliente seguiría enviando la válida.
    cliente.cookies.clear()
    cliente.cookies.set("ignis_sesion", token[:-6] + ("A" if token[-6] != "A" else "B") + token[-5:])
    assert cliente.get(ruta).status_code == 401


def test_cookie_de_otro_secreto_da_401(config_con_base: Configuracion, servicio: ServicioAsistente) -> None:
    cliente = TestClient(_app(servicio))
    _entrar(cliente, ALIAS_A)
    otro = _servicio(
        config_con_base.model_copy(
            update={"secreto_sesion": SecretStr("otro-secreto-de-prueba-de-sesiones-98765")}
        )
    )
    try:
        intruso = TestClient(_app(otro))
        intruso.cookies.set("ignis_sesion", cliente.cookies["ignis_sesion"])
        assert intruso.get("/api/v1/sesiones/yo").status_code == 401
    finally:
        otro.cerrar()


def test_stream_sin_sesion_da_401(servicio: ServicioAsistente) -> None:
    assert _stream(TestClient(_app(servicio)), "Hola", "hilo-1").status_code == 401


def test_cerrar_sesion_borra_la_cookie(servicio: ServicioAsistente) -> None:
    cliente = TestClient(_app(servicio))
    _entrar(cliente, ALIAS_A)
    r = cliente.post("/api/v1/sesiones/cerrar")
    assert r.status_code == 204
    cabecera = _set_cookie(r)
    assert "ignis_sesion=" in cabecera and ("Max-Age=0" in cabecera or "expires=" in cabecera.lower())
    assert cliente.get("/api/v1/sesiones/yo").status_code == 401


# ------------------------------------------------------------------ hilos y aislamiento
def test_dos_usuarios_no_ven_hilos_mensajes_ni_preferencias_del_otro(servicio: ServicioAsistente) -> None:
    app = _app(servicio)
    ana, beto = TestClient(app), TestClient(app)
    _entrar(ana, ALIAS_A)
    _entrar(beto, ALIAS_B)

    hilo_ana = ana.post("/api/v1/sesiones/yo/hilos").json()["thread_id"]
    assert _stream(ana, CASO_2A, hilo_ana).status_code == 200

    hilos_ana = ana.get("/api/v1/sesiones/yo/hilos").json()
    assert [h["thread_id"] for h in hilos_ana] == [hilo_ana]
    assert hilos_ana[0]["turnos"] == 1 and hilos_ana[0]["ultima_ruta"] == "memoria_store"
    assert beto.get("/api/v1/sesiones/yo/hilos").json() == []

    # thread_id ajeno: 403 en los mensajes y en el stream.
    assert beto.get(f"/api/v1/sesiones/yo/hilos/{hilo_ana}/mensajes").status_code == 403
    assert _stream(beto, "Hola", hilo_ana).status_code == 403

    # Preferencias: cada usuario ve solo las suyas (caso 2B en un hilo nuevo).
    hilo_beto = beto.post("/api/v1/sesiones/yo/hilos").json()["thread_id"]
    assert "Todavía no tengo preferencias tuyas guardadas" in _texto_sse(_stream(beto, CASO_2B, hilo_beto))
    otro_hilo_ana = ana.post("/api/v1/sesiones/yo/hilos").json()["thread_id"]
    texto = _texto_sse(_stream(ana, CASO_2B, otro_hilo_ana))
    assert all(v in texto for v in ("compras de repuestos", "breve", "motocicletas"))


@pytest.mark.parametrize(
    ("mensaje", "categoria"),
    [("Voy a quemar la sede", "amenaza_violencia"), ("me quiero matar", "crisis_personal")],
)
def test_hilo_moderado_se_titula_con_la_marca_y_no_guarda_el_texto(
    servicio: ServicioAsistente, mensaje: str, categoria: str
) -> None:
    """Un hilo que empieza con un mensaje bloqueado se titula «[mensaje moderado: …]»; el texto del cliente no
    queda ni en el título ni en el historial."""
    cliente = TestClient(_app(servicio))
    _entrar(cliente, ALIAS_A)
    hilo = cliente.post("/api/v1/sesiones/yo/hilos").json()["thread_id"]
    r = _stream(cliente, mensaje, hilo)
    assert r.status_code == 200
    meta = next(
        json.loads(linea.removeprefix("data: "))
        for linea in r.text.splitlines()
        if linea.startswith("data: {") and '"metadatos"' in linea
    )
    assert meta["bloqueada"] is True and meta["categoria_moderacion"] == categoria

    (fila,) = cliente.get("/api/v1/sesiones/yo/hilos").json()
    assert fila["titulo"] == f"[mensaje moderado: {categoria}]"
    mensajes = cliente.get(f"/api/v1/sesiones/yo/hilos/{hilo}/mensajes").json()
    assert mensajes[0]["contenido"] == f"[mensaje moderado: {categoria}]"
    historial = json.dumps([fila, mensajes], ensure_ascii=False).lower()
    assert mensaje.lower() not in historial


def test_mensajes_del_hilo_con_ruta_y_citas(servicio: ServicioAsistente) -> None:
    cliente = TestClient(_app(servicio))
    _entrar(cliente, ALIAS_A)
    hilo = cliente.post("/api/v1/sesiones/yo/hilos").json()["thread_id"]
    _stream(cliente, "Qué dice el documento de autopartes de Fanalca", hilo)
    mensajes = cliente.get(f"/api/v1/sesiones/yo/hilos/{hilo}/mensajes").json()
    assert [m["rol"] for m in mensajes] == ["user", "assistant"]
    assert mensajes[1]["ruta"] == "rag_documental"
    assert mensajes[1]["citas"] and "url" in mensajes[1]["citas"][0]


def test_hilo_viejo_sin_dueno_con_historial_no_se_asigna(servicio: ServicioAsistente) -> None:
    """Un thread_id que ya tiene historial (por ejemplo, del usuario «demo» anterior a las sesiones) no se
    entrega al primero que lo use: 403 en el stream y 404 en los mensajes (no tiene dueño)."""
    servicio._memoria().guardar_turno("hilo-viejo", "user", "consulta anterior a las sesiones")
    cliente = TestClient(_app(servicio))
    _entrar(cliente, ALIAS_A)
    assert _stream(cliente, "Hola", "hilo-viejo").status_code == 403
    assert cliente.get("/api/v1/sesiones/yo/hilos/hilo-viejo/mensajes").status_code == 404
    assert cliente.get("/api/v1/sesiones/yo/hilos").json() == []


def test_thread_id_invalido_en_el_cuerpo_y_en_la_ruta(servicio: ServicioAsistente) -> None:
    cliente = TestClient(_app(servicio))
    _entrar(cliente, ALIAS_A)
    assert _stream(cliente, "Hola", "../../etc/passwd").status_code == 422
    assert cliente.post("/api/v1/ignis/stream", json={"mensaje": "Hola"}).status_code == 422  # obligatorio
    assert cliente.get("/api/v1/sesiones/yo/hilos/hilo%20malo/mensajes").status_code == 422


# ------------------------------------------------------------------ reinicio (casos 2A y 2B)
def test_la_sesion_y_los_hilos_sobreviven_al_reinicio_del_backend(config_con_base: Configuracion) -> None:
    primero = _servicio(config_con_base)
    with TestClient(_app(primero)) as cliente:
        _entrar(cliente, ALIAS_A)
        hilo = cliente.post("/api/v1/sesiones/yo/hilos").json()["thread_id"]
        assert _stream(cliente, CASO_2A, hilo).status_code == 200
        cookie = cliente.cookies["ignis_sesion"]

    reiniciado = _servicio(config_con_base)  # mismo dir_datos y mismo secreto, proceso «nuevo»
    try:
        cliente = TestClient(_app(reiniciado))
        cliente.cookies.set("ignis_sesion", cookie)
        assert cliente.get("/api/v1/sesiones/yo").json()["alias"] == ALIAS_A
        hilos = cliente.get("/api/v1/sesiones/yo/hilos").json()
        assert [h["thread_id"] for h in hilos] == [hilo]
        assert len(cliente.get(f"/api/v1/sesiones/yo/hilos/{hilo}/mensajes").json()) == 2
        nuevo = cliente.post("/api/v1/sesiones/yo/hilos").json()["thread_id"]
        texto = _texto_sse(_stream(cliente, CASO_2B, nuevo))
        assert all(v in texto for v in ("compras de repuestos", "breve", "motocicletas"))
    finally:
        reiniciado.cerrar()


# ------------------------------------------------------------------ privacidad del alias
def test_el_alias_no_queda_en_la_base_ni_en_el_log(
    servicio: ServicioAsistente, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.DEBUG)
    cliente = TestClient(_app(servicio))
    _entrar(cliente, ALIAS_A)
    hilo = cliente.post("/api/v1/sesiones/yo/hilos").json()["thread_id"]
    _stream(cliente, CASO_2A, hilo)
    cliente.post("/api/v1/sesiones", json={"alias": "ana@gmail.com"})  # rechazado: tampoco se registra
    servicio.cerrar()

    config = servicio.config
    for archivo in (config.ruta_sesiones, config.ruta_store, config.dir_datos / "ignis_memoria_m2.sqlite"):
        contenido = archivo.read_bytes()
        assert ALIAS_A.encode() not in contenido, archivo.name
        assert b"ana@gmail.com" not in contenido, archivo.name
    assert ALIAS_A not in caplog.text and "ana@gmail.com" not in caplog.text


# ------------------------------------------------------------------ configuración y CORS
def test_sin_secreto_las_sesiones_y_el_stream_dan_503(config_con_base: Configuracion) -> None:
    servicio = _servicio(config_con_base.model_copy(update={"secreto_sesion": None}))
    try:
        cliente = TestClient(_app(servicio))
        for r in (
            cliente.post("/api/v1/sesiones", json={"alias": ALIAS_A}),
            cliente.get("/api/v1/sesiones/yo"),
            _stream(cliente, "Hola", "hilo-1"),
        ):
            assert r.status_code == 503
            assert "IGNIS_SECRETO_SESION" in r.json()["mensaje"]
        assert cliente.get("/salud").status_code == 200  # el resto de la API sigue funcionando
    finally:
        servicio.cerrar()


def test_cors_no_permite_credenciales_a_otro_origen(servicio: ServicioAsistente) -> None:
    cliente = TestClient(_app(servicio))
    r = cliente.options(
        "/api/v1/sesiones",
        headers={"Origin": "https://otro.test", "Access-Control-Request-Method": "POST"},
    )
    assert r.headers.get("access-control-allow-origin") != "https://otro.test"
    assert "access-control-allow-credentials" not in r.headers
    r = cliente.options(
        "/api/v1/sesiones",
        headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "POST"},
    )
    assert "access-control-allow-credentials" not in r.headers
