"""Temperatura 0 por defecto (C4) y registro de si el proveedor la aplica realmente."""

from __future__ import annotations

import pytest

from fabrica_autopartes.core.config import Configuracion
from fabrica_autopartes.llm.proveedores import aplica_temperatura
from fabrica_autopartes.services.evaluacion import informe_markdown


def test_temperatura_por_defecto_es_cero(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("FNA_TEMPERATURA", raising=False)
    assert Configuracion(_env_file=None).temperatura == 0.0  # type: ignore[call-arg]


@pytest.mark.parametrize(
    ("proveedor", "modelo", "esperado"),
    [
        ("ollama", "llama3.2:3b", True),
        ("anthropic", "claude-haiku-5-5", False),  # Claude 5.x no acepta temperature (ADR-028)
        ("anthropic", "claude-haiku-4-5", True),
        ("openai", "gpt-4o-mini", True),
        ("claude_code", "sonnet", False),
        ("extractivo", "lexico-bm25", False),
    ],
)
def test_aplica_temperatura(proveedor: str, modelo: str, esperado: bool) -> None:
    assert aplica_temperatura(proveedor, modelo) is esperado


def test_informe_registra_temperatura_y_fuentes() -> None:
    informe = {
        "fecha": "2026-11-07T00:00:00+00:00",
        "proveedor": "claude_code",
        "modelo": "sonnet",
        "version_prompt": "v3",
        "modo_contexto": "auto",
        "recuperador": "bm25",
        "temperatura": 0.0,
        "temperatura_aplicada": False,
        "metricas": {"total_preguntas": 1},
        "detalle": [
            {
                "id": "P01",
                "tipo": "respondible",
                "acierto": True,
                "fundamentada": True,
                "hechos_encontrados": ["yumbo"],
                "fuentes": ["contacto#000"],
                "respuesta": "Yumbo",
            }
        ],
    }
    md = informe_markdown(informe)
    assert "Temperatura configurada: 0.0 · aplicada: no (el proveedor no la usa)" in md
    assert "Recuperador: bm25" in md
    assert "| contacto#000 |" in md
    # Informes antiguos (sin temperatura) siguen generando Markdown válido.
    antiguo = {
        k: v for k, v in informe.items() if k not in ("recuperador", "temperatura", "temperatura_aplicada")
    }
    assert "Temperatura" not in informe_markdown(antiguo)
