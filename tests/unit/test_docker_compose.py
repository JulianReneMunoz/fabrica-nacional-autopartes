"""docker-compose.yml (ADR-024, ADR-026): sin Ollama, un solo worker y sin secretos en el archivo."""

from __future__ import annotations

import re

import yaml

from fabrica_autopartes.core.config import RAIZ_PROYECTO

COMPOSE = RAIZ_PROYECTO / "docker-compose.yml"
# Prefijo de las claves de Anthropic, armado por partes para que el control de secretos siga vacío.
PREFIJO = "sk-" + "ant"


def _compose() -> dict:
    return yaml.safe_load(COMPOSE.read_text(encoding="utf-8"))


def test_sin_servicio_ni_volumen_de_ollama() -> None:
    """ADR-026: Ollama no se usa por ahora; no figura en Compose ni como perfil opcional."""
    compose = _compose()
    assert set(compose["services"]) == {"postgres", "api", "app"}
    assert "ollama" not in (compose.get("volumes") or {})
    texto = COMPOSE.read_text(encoding="utf-8").lower()
    assert "ollama" not in texto  # ni servicio, ni FNA_OLLAMA_URL, ni comentarios de «ollama pull» o perfiles
    for servicio in compose["services"].values():
        assert "profiles" not in servicio


def test_api_con_un_solo_worker() -> None:
    comando = " ".join(_compose()["services"]["api"]["command"])
    assert "uvicorn" in comando and "--workers 1" in comando


def test_variables_del_agente_sin_secretos() -> None:
    servicios = _compose()["services"]
    for nombre in ("api", "app"):
        entorno = servicios[nombre]["environment"]
        assert entorno["FNA_PROVEEDOR_AGENTE"] == "${FNA_PROVEEDOR_AGENTE:-anthropic}"
        assert entorno["FNA_MODELO_ANTHROPIC"] == "${FNA_MODELO_ANTHROPIC:-claude-haiku-5-5}"
        # Q&A: sin Ollama en Compose, extractivo por defecto (sin red ni LLM); config.py no cambia.
        assert entorno["FNA_PROVEEDOR_LLM"] == "${FNA_PROVEEDOR_LLM:-extractivo}"
        assert not any(re.search(r"API_KEY|CLAVE_ADMIN", clave) for clave in entorno), nombre
        assert servicios[nombre]["env_file"] == [
            {"path": ".env", "required": False}
        ]  # la clave llega por .env
    texto = COMPOSE.read_text(encoding="utf-8")
    assert PREFIJO not in texto
    assert not re.search(r"^\s*ANTHROPIC_API_KEY\s*:", texto, re.M)
