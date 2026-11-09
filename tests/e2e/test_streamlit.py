"""Prueba extremo a extremo de la interfaz Streamlit con ``AppTest`` (sin navegador).

Se ejecuta la aplicación real contra una base construida desde la semilla y el
proveedor extractivo, y se verifica que las tres funcionalidades (Resumen, FAQ, Q&A)
producen resultados visibles.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from fabrica_autopartes.domain.modelos import Fuente, RespuestaQA
from fabrica_autopartes.services.asistente import ServicioAsistente

APP = Path(__file__).resolve().parents[2] / "frontend" / "app.py"


@pytest.fixture
def app(config_con_base, monkeypatch):  # type: ignore[no-untyped-def]
    monkeypatch.setenv("FNA_DIR_DATOS", str(config_con_base.dir_datos))
    monkeypatch.setenv("FNA_URL_BASE_DATOS", config_con_base.url_base_datos)
    monkeypatch.setenv("FNA_PROVEEDOR_LLM", "extractivo")
    at = AppTest.from_file(str(APP), default_timeout=60)
    at.run()
    assert not at.exception, at.exception
    return at


def chips(app) -> dict[str, str]:  # type: ignore[no-untyped-def]
    """Chips de métrica presentes en el HTML de los elementos markdown: etiqueta -> valor."""
    patron = re.compile(r'<span class="fna-chip-etiqueta">(.*?)</span> <b>(.*?)</b>')
    return {e: v for m in app.markdown for e, v in patron.findall(str(m.value))}


def test_panel_muestra_metricas_como_chips(app) -> None:  # type: ignore[no-untyped-def]
    c = chips(app)
    assert {"Documentos", "Fragmentos", "Tokens aprox.", "Fuentes (URL)"} <= set(c)
    assert c["Documentos"].isdigit() and int(c["Documentos"]) > 0
    assert int(c["Fragmentos"]) > 0 and int(c["Fuentes (URL)"]) > 0
    assert len(app.tabs) == 11  # incluye «🤖 Agente» (ADR-024, ADR-026)
    assert not app.metric  # las métricas ya no usan st.metric
    html = " ".join(str(m.value) for m in app.markdown)
    assert 'data-variante="dato"' in html and "fna-insignia" in html  # cifra con su procedencia


def test_encabezado_y_enlace_a_la_biblioteca(app) -> None:  # type: ignore[no-untyped-def]
    html = " ".join(str(m.value) for m in app.markdown)
    assert "fna-cabecera" in html and "Biblioteca de máquinas" in html and "#/" in html
    assert "<style>" in html and "--acento" in html  # CSS generado desde los tokens


def test_pestanas_v2_proceso_y_simulador(app) -> None:  # type: ignore[no-untyped-def]
    etiquetas = [t.label for t in app.tabs]
    assert "🔄 Proceso de datos" in etiquetas
    assert "🧩 Simulador 3D" in etiquetas
    assert {"Capturas Bronze", "Documentos Silver", "Fragmentos Gold"} <= set(chips(app))
    textos = " ".join(str(m.value) for m in app.markdown)
    assert "freno de disco" in textos
    assert "takt" in textos
    assert "motocicleta Honda" in textos  # tarjeta de la moto en la biblioteca (V2-21)
    etiquetas_enlaces = " ".join(str(b.label) for b in app.get("link_button"))
    assert "Abrir motocicleta" in etiquetas_enlaces


def test_qa_desde_boton_de_ejemplo(app) -> None:  # type: ignore[no-untyped-def]
    boton = next(b for b in app.button if b.label.startswith("¿Dónde queda la sede"))
    boton.click().run()
    assert not app.exception
    textos = " ".join(str(m.value) for m in app.markdown)
    assert "Acopi" in textos or "Yumbo" in textos


def test_resumen_y_faq(app) -> None:  # type: ignore[no-untyped-def]
    next(b for b in app.button if b.label == "Generar resumen").click().run()
    assert any("Fuentes:" in str(m.value) for m in app.markdown)
    next(b for b in app.button if b.label == "Generar FAQ").click().run()
    assert len(app.expander) >= 3
    assert not app.exception


def test_qa_muestra_tarjeta_con_insignias_y_url(app) -> None:  # type: ignore[no-untyped-def]
    next(b for b in app.button if b.label.startswith("¿Dónde queda la sede")).click().run()
    tarjetas = [str(m.value) for m in app.markdown if '<article class="fna-tarjeta"' in str(m.value)]
    assert len(tarjetas) == 1
    t = tarjetas[0]
    assert "¿Dónde queda la sede principal de Fanalca?" in t
    assert re.search(r"fna-fuente-(scraping|semilla|lectura_web)", t)  # origen real del fragmento citado
    assert re.search(r'href="https?://[^"]+"', t)
    assert "fna-chip-estado" in t and "latencia" in t


def test_qa_rechazo_se_muestra_con_estilo_de_estado(app) -> None:  # type: ignore[no-untyped-def]
    app.chat_input[0].set_value("¿Cuál es la receta del sancocho valluno?").run()
    assert not app.exception
    t = next(str(m.value) for m in app.markdown if '<article class="fna-tarjeta"' in str(m.value))
    assert "fna-rechazo" in t and "fna-fuente-no_publicado" in t
    assert "La información solicitada no se encuentra en la base de conocimiento de Fanalca." in t


def test_qa_escapa_citas_hostiles(app, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    llamadas: list[dict] = []

    def falso(self, pregunta, **kwargs):  # type: ignore[no-untyped-def]
        llamadas.append({"pregunta": pregunta, **kwargs})
        return RespuestaQA(
            pregunta=pregunta,
            respuesta="Dato <script>alert(1)</script>",
            fuentes=[
                Fuente(
                    fragmento_id="x#001", titulo="<img src=x onerror=alert(1)>", url="javascript:alert(1)"
                ),
                Fuente(fragmento_id="y#001", titulo="ok", url='https://fanalca.com/"><svg onload=alert(2)>'),
            ],
            fundamentada=True,
            confianza="media",
            version_prompt="v3",
            proveedor="extractivo",
            modelo="lexico-bm25",
            modo_contexto="seleccion",
            latencia_ms=1,
        )

    monkeypatch.setattr(ServicioAsistente, "responder", falso)
    app.chat_input[0].set_value("pregunta hostil").run()
    t = next(str(m.value) for m in app.markdown if '<article class="fna-tarjeta"' in str(m.value))
    assert "<script" not in t and "<img" not in t and "<svg" not in t
    assert 'href="javascript' not in t
    assert len(llamadas) == 1


def test_qa_no_cambia_la_llamada_al_servicio(app, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """La capa visual no altera la lógica: una pregunta produce UNA llamada con los mismos argumentos."""
    original = ServicioAsistente.responder
    llamadas: list[tuple[str, dict]] = []

    def espia(self, pregunta, **kwargs):  # type: ignore[no-untyped-def]
        llamadas.append((pregunta, kwargs))
        return original(self, pregunta, **kwargs)

    monkeypatch.setattr(ServicioAsistente, "responder", espia)
    next(b for b in app.button if b.label.startswith("¿Cuál es el horario")).click().run()
    assert len(llamadas) == 1
    pregunta, kwargs = llamadas[0]
    assert pregunta == "¿Cuál es el horario de atención?"
    assert kwargs == {
        "canal": "streamlit",
        "modo_contexto": "auto",
        "recuperador": "bm25",
        "proveedor": "extractivo",
        "modelo": "lexico-bm25",
        "version_prompt": "v3",
    }


def test_busqueda_web_solo_tras_rechazo_y_etiquetada(app, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """Fase 9 (ADR-019): el botón aparece solo tras la frase de rechazo; la búsqueda es simulada (sin red)."""
    from fabrica_autopartes.llm import busqueda_web as bw

    llamadas: list[str] = []

    def buscar(self, pregunta: str) -> bw.ResultadoBuscador:  # type: ignore[no-untyped-def]
        llamadas.append(pregunta)
        return bw.ResultadoBuscador("Dato web.", [{"dato": "Dato web", "url": "https://fanalca.com/x"}])

    monkeypatch.setattr(bw.BuscadorClaudeCode, "buscar", buscar)
    next(b for b in app.button if b.label.startswith("¿Dónde queda la sede")).click().run()
    assert not any(b.label == "Buscar en la web con Claude" for b in app.button)  # respuesta de la base
    app.chat_input[0].set_value("¿Cuál es la receta del sancocho valluno?").run()
    boton = next(b for b in app.button if b.label == "Buscar en la web con Claude")
    assert llamadas == []  # nunca automática
    boton.click().run()
    assert not app.exception
    assert llamadas == ["¿Cuál es la receta del sancocho valluno?"]
    assert any("no proviene de la base verificada" in str(w.value) for w in app.warning)
    assert any("https://fanalca.com/x" in str(t.value) for t in app.text)  # texto plano, no Markdown


def _graficas_altair(app) -> list[str]:  # type: ignore[no-untyped-def]
    """Especificaciones Vega-Lite de las gráficas de etapa (marcadas con usermeta.fna_etapa)."""
    specs = [str(getattr(g.proto, "spec", "")) for g in app.get("vega_lite_chart")]
    return [s for s in specs if "fna_etapa" in s]


def test_proceso_datos_graficas_altair_y_aviso_semilla(app) -> None:  # type: ignore[no-untyped-def]
    """Con la semilla: aviso de demostración y gráficas Altair de las etapas con datos (sin rastreo)."""
    textos = [str(i.value) for i in app.info]
    assert any("base de demostración" in t for t in textos)
    assert not any("Métricas del rastreo real" in t for t in textos)
    graficas = _graficas_altair(app)
    assert (
        len(graficas) >= 3
    )  # reducción, limpieza, fragmentos y tokens (sin rastreo ni Bronze en la semilla)
    assert any(b.label == "Regenerar gráficas desde las métricas actuales" for b in app.button)


def test_proceso_datos_aviso_rastreo_real_y_seis_graficas(app, config_con_base) -> None:  # type: ignore[no-untyped-def]
    """Con fuente mixta: aviso del rastreo real con su fecha y una gráfica por etapa."""
    import json

    import streamlit as st

    st.cache_resource.clear()  # el servicio en caché de otra prueba apunta a otro directorio de datos

    ruta = config_con_base.dir_datos / "gold" / "metricas_etapas.json"
    m = json.loads(ruta.read_text(encoding="utf-8"))
    m["fuente"] = "mixta"
    m["bronze"] = {
        "capturas": 2,
        "rastreo": {
            "fecha": "2026-11-04T23:50:26+00:00",
            "capturadas": 2,
            "omitidas_robots": 0,
            "errores": 1,
            "duplicadas": 0,
            "descubiertas_sitemap": 3,
            "visitadas": 3,
            "duracion_s": 12.5,
            "omitidas_proteccion": 1,
        },
    }
    for i, p in enumerate(m["paginas"][:2]):
        p["bytes_html"] = 1000 * (i + 1)
    ruta.write_text(json.dumps(m, ensure_ascii=False), encoding="utf-8")
    app.run()
    assert not app.exception
    textos = [str(i.value) for i in app.info]
    assert "Métricas del rastreo real del 2026-11-04 (fuente: mixta)" in textos
    assert not any("base de demostración" in t for t in textos)
    graficas = _graficas_altair(app)
    assert len(graficas) == 6
    assert any(
        "incidencia" in g for g in graficas
    )  # las incidencias del rastreo se rotulan, no solo se colorean
    assert any(b.label == "Regenerar gráficas desde las métricas actuales" for b in app.button)


def _radio_recuperador(app):  # type: ignore[no-untyped-def]
    return next(r for r in app.radio if r.label == "Recuperador")


def test_selector_recuperador_desactivado_sin_base_semantica(app) -> None:  # type: ignore[no-untyped-def]
    """Sin índice (o sin el extra, como en CI) la opción semántica queda desactivada con un aviso."""
    radio = _radio_recuperador(app)
    assert radio.disabled and radio.value == "BM25"
    assert any("make indexar" in str(i.value) for i in app.info)


def test_selector_recuperador_semantico_llega_al_servicio(config_con_base, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    import streamlit as st

    llamadas: list[dict] = []

    def falso(self, pregunta, **kwargs):  # type: ignore[no-untyped-def]
        llamadas.append(kwargs)
        return RespuestaQA(
            pregunta=pregunta,
            respuesta="La sede queda en Yumbo.",
            fuentes=[
                Fuente(fragmento_id="contacto#000", titulo="Contacto", url="https://fanalca.com/contacto/")
            ],
            fundamentada=True,
            version_prompt="v3",
            proveedor="extractivo",
            modelo="lexico-bm25",
            modo_contexto="seleccion",
            recuperador=kwargs["recuperador"],
        )

    st.cache_data.clear()
    monkeypatch.setattr(ServicioAsistente, "disponibilidad_semantica", lambda self: (True, ""))
    monkeypatch.setattr(ServicioAsistente, "responder", falso)
    monkeypatch.setenv("FNA_DIR_DATOS", str(config_con_base.dir_datos))
    monkeypatch.setenv("FNA_URL_BASE_DATOS", config_con_base.url_base_datos)
    monkeypatch.setenv("FNA_PROVEEDOR_LLM", "extractivo")
    try:
        at = AppTest.from_file(str(APP), default_timeout=60)
        at.run()
        radio = _radio_recuperador(at)
        assert not radio.disabled
        radio.set_value("Semántico").run()
        at.chat_input[0].set_value("¿Dónde queda la sede?").run()
        assert not at.exception
        assert llamadas and llamadas[-1]["recuperador"] == "semantico"
        tarjeta = next(str(m.value) for m in at.markdown if '<article class="fna-tarjeta"' in str(m.value))
        assert "semántico" in tarjeta and 'href="https://fanalca.com/contacto/"' in tarjeta
    finally:
        st.cache_data.clear()


# ------------------------------------------------------------- pestaña «Agente» (ADR-024, ADR-026)
@pytest.fixture
def app_agente(config_con_base, monkeypatch):  # type: ignore[no-untyped-def]
    """Fábrica de la app con el agente: modelo simulado y clave ficticia (sin red ni API real).

    ``FNA_ANTHROPIC_API_KEY`` se fija en el entorno (tiene prioridad sobre ``.env``), así que nunca se usa
    una clave real; ``crear_modelo_agente`` se reemplaza por el modelo simulado. La caché de recursos se
    limpia antes y después, para que el servicio (y su memoria) no se comparta con otras pruebas.
    """
    import streamlit as st

    from fabrica_autopartes.services import agente as ag

    def crear(modelo=None, clave: str = "clave-de-prueba"):  # type: ignore[no-untyped-def]
        st.cache_resource.clear()
        st.cache_data.clear()
        monkeypatch.setenv("FNA_DIR_DATOS", str(config_con_base.dir_datos))
        monkeypatch.setenv("FNA_URL_BASE_DATOS", config_con_base.url_base_datos)
        monkeypatch.setenv("FNA_PROVEEDOR_LLM", "extractivo")
        monkeypatch.setenv("FNA_PROVEEDOR_AGENTE", "anthropic")
        monkeypatch.setenv("FNA_ANTHROPIC_API_KEY", clave)
        if modelo is not None:
            monkeypatch.setattr(ag, "crear_modelo_agente", lambda config: modelo)
        at = AppTest.from_file(str(APP), default_timeout=60)
        at.run()
        assert not at.exception, at.exception
        return at

    yield crear
    st.cache_resource.clear()
    st.cache_data.clear()


def _mensajes_agente(at) -> str:  # type: ignore[no-untyped-def]
    return " ".join(str(m.value) for m in at.markdown if "fna-agente" in str(m.value))


def test_agente_responde_con_fuentes_y_chips(app_agente) -> None:  # type: ignore[no-untyped-def]
    from tests.simulados import ModeloSimulado, llamada, responder_citando_primera_url

    modelo = ModeloSimulado(guion=[llamada("sede principal", "c1"), responder_citando_primera_url("La sede")])
    at = app_agente(modelo)
    at.chat_input(key="agente_entrada").set_value("¿Dónde queda la sede principal?").run()
    assert not at.exception, at.exception
    html = _mensajes_agente(at)
    assert "La sede" in html and "Fuentes (1)" in html and 'href="https://' in html
    assert "anthropic · claude-haiku-5-5" in html  # proveedor y modelo por defecto
    assert "1 llamada" in html and "fundamentación" in html
    assert any(
        "¿Dónde queda la sede principal?" in str(t.value) for t in at.text
    )  # pregunta como texto plano


def test_agente_dos_mensajes_comparten_memoria(app_agente) -> None:  # type: ignore[no-untyped-def]
    from langchain_core.messages import HumanMessage

    from tests.simulados import ModeloSimulado, llamada, responder_citando_primera_url

    modelo = ModeloSimulado(
        guion=[
            llamada("sede principal", "c1"),
            responder_citando_primera_url("La sede"),
            llamada("teléfono de contacto", "c2"),
            responder_citando_primera_url("El teléfono"),
        ]
    )
    at = app_agente(modelo)
    hilo = at.session_state["agente_thread"]
    at.chat_input(key="agente_entrada").set_value("¿Dónde queda la sede principal?").run()
    at.chat_input(key="agente_entrada").set_value("¿Y cuál es su teléfono?").run()
    assert not at.exception, at.exception
    assert at.session_state["agente_thread"] == hilo
    humanos = [m.content for m in modelo.recibidos[-1] if isinstance(m, HumanMessage)]
    assert humanos == ["¿Dónde queda la sede principal?", "¿Y cuál es su teléfono?"]
    assert len(at.session_state["agente_historial"]) == 4  # dos preguntas y dos respuestas visibles


def test_nueva_conversacion_cambia_el_thread_id(app_agente) -> None:  # type: ignore[no-untyped-def]
    from tests.simulados import ModeloSimulado, llamada, responder_citando_primera_url

    modelo = ModeloSimulado(guion=[llamada("sede", "c1"), responder_citando_primera_url("La sede")])
    at = app_agente(modelo)
    at.chat_input(key="agente_entrada").set_value("¿Dónde queda la sede?").run()
    anterior = at.session_state["agente_thread"]
    assert anterior.startswith("streamlit-") and at.session_state["agente_historial"]
    at.button(key="agente_nueva").click().run()
    assert not at.exception, at.exception
    assert at.session_state["agente_thread"] != anterior
    assert at.session_state["agente_historial"] == []
    assert any(
        at.session_state["agente_thread"] in str(c.value) for c in at.caption
    )  # se muestra el hilo nuevo


def test_sin_clave_aviso_y_chat_desactivado(app_agente) -> None:  # type: ignore[no-untyped-def]
    at = app_agente(clave="")
    entrada = at.chat_input(key="agente_entrada")
    assert entrada.disabled
    avisos = " ".join(str(w.value) for w in at.warning)
    assert "El agente no está disponible" in avisos
    for texto in ("FNA_ANTHROPIC_API_KEY", "créditos", "make verificar-agente"):
        assert texto in avisos


def test_error_del_proveedor_se_muestra_como_aviso(app_agente) -> None:  # type: ignore[no-untyped-def]
    from fabrica_autopartes.core.excepciones import ErrorProveedorLLM
    from tests.simulados import ModeloSimulado

    modelo = ModeloSimulado(guion=[ErrorProveedorLLM("La API de Anthropic no respondió (simulado)")])
    at = app_agente(modelo)
    at.chat_input(key="agente_entrada").set_value("¿Dónde queda la sede?").run()
    assert not at.exception, at.exception  # sin traza
    assert any("no respondió (simulado)" in str(w.value) for w in at.warning)
