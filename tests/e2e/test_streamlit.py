"""Prueba extremo a extremo de la interfaz Streamlit con ``AppTest`` (sin navegador).

Se ejecuta la aplicación real contra una base construida desde la semilla y el
proveedor extractivo, y se verifica que las tres funcionalidades (Resumen, FAQ, Q&A)
producen resultados visibles.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

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


def test_panel_muestra_metricas(app) -> None:  # type: ignore[no-untyped-def]
    etiquetas = {m.label for m in app.metric}
    assert {"Documentos", "Fragmentos", "Tokens aprox.", "Fuentes (URL)"} <= etiquetas
    assert len(app.tabs) == 10


def test_pestanas_v2_proceso_y_simulador(app) -> None:  # type: ignore[no-untyped-def]
    etiquetas = [t.label for t in app.tabs]
    assert "🔄 Proceso de datos" in etiquetas
    assert "🧩 Simulador 3D" in etiquetas
    assert {"Capturas Bronze", "Documentos Silver", "Fragmentos Gold"} <= {m.label for m in app.metric}
    textos = " ".join(str(m.value) for m in app.markdown)
    assert "freno de disco" in textos
    assert "takt" in textos


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
