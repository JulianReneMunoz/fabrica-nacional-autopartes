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
    assert len(app.tabs) == 10
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
        "proveedor": "extractivo",
        "modelo": "lexico-bm25",
        "version_prompt": "v3",
    }
