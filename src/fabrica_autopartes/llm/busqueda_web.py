"""Búsqueda web complementaria con Claude (fase 9, ADR-019).

Solo se usa cuando la base de conocimiento no tiene la respuesta y la persona usuaria lo pide de forma
explícita. El proceso ``claude -p`` corre en una carpeta temporal vacía, con únicamente las herramientas
``WebSearch`` y ``WebFetch`` (``--tools`` + ``--allowedTools``), los flags de ``FLAGS_AISLAMIENTO_WEB``
(sin MCP, CLAUDE.md, hooks ni permisos interactivos; ADR-025), un número máximo de turnos y un límite
de tiempo. El contenido web es un DATO: las instrucciones piden no seguir instrucciones encontradas en
las páginas, respetar ``robots.txt`` y no eludir bloqueos. El resultado nunca entra a la base verificada.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from datetime import date
from typing import Protocol

from fabrica_autopartes.core.excepciones import ErrorProveedorLLM
from fabrica_autopartes.llm.catalogo_prompts import obtener_prompt
from fabrica_autopartes.llm.claude_code import (
    FLAGS_AISLAMIENTO_WEB,
    flags_requeridos,
    verificar_flags_aislamiento,
)

DOMINIOS_PREFERIDOS = ("fanalca.com", "autopartesfanalca.com.co", "motos.honda.com.co")
HERRAMIENTAS_WEB = ("WebSearch", "WebFetch")

VERSION_PROMPT = "v1"


@dataclass
class ResultadoBuscador:
    respuesta: str
    hallazgos: list[dict[str, str]] = field(default_factory=list)


class BuscadorWeb(Protocol):
    """Interfaz del buscador (las pruebas usan uno simulado, sin red)."""

    proveedor: str
    modelo: str
    version_prompt: str

    def buscar(self, pregunta: str) -> ResultadoBuscador: ...


def _extraer_json(texto: str) -> dict[str, object] | None:
    """Primer objeto JSON del texto (tolera bloques ```json y texto alrededor)."""
    m = re.search(r"\{.*\}", texto, re.S)
    if not m:
        return None
    try:
        datos = json.loads(m.group(0))
    except json.JSONDecodeError:
        return None
    return datos if isinstance(datos, dict) else None


def interpretar_salida(texto: str) -> ResultadoBuscador:
    """Convierte la salida del modelo en respuesta + hallazgos con URL http(s); descarta lo demás."""
    datos = _extraer_json(texto) or {}
    hallazgos: list[dict[str, str]] = []
    crudos = datos.get("hallazgos")
    for h in crudos if isinstance(crudos, list) else []:
        if not isinstance(h, dict):
            continue
        dato = str(h.get("dato", "")).strip()
        url = str(h.get("url", "")).strip()
        if dato and re.match(r"^https?://[^\s]+$", url):
            hallazgos.append({"dato": dato[:600], "url": url[:500]})
    return ResultadoBuscador(
        respuesta=str(datos.get("respuesta", "")).strip()[:1200], hallazgos=hallazgos[:8]
    )


def texto_prompt(pregunta: str, version: str = VERSION_PROMPT) -> str:
    """Instrucciones versionadas (``llm/prompts/busqueda_web.yaml``) con los dominios y la pregunta."""
    vp = obtener_prompt("busqueda_web", version)
    sistema = vp.sistema.format(dominios=", ".join(DOMINIOS_PREFERIDOS))
    return sistema + "\n" + vp.humano.format(pregunta=pregunta)


class BuscadorClaudeCode:
    """Claude mediante la CLI de Claude Code, limitado a WebSearch y WebFetch."""

    proveedor = "claude_code"
    version_prompt = VERSION_PROMPT

    def __init__(
        self,
        modelo: str = "sonnet",
        tiempo_espera_s: float = 120.0,
        max_turnos: int = 8,
        ejecutable: str = "claude",
    ) -> None:
        self.modelo = modelo
        self.tiempo_espera_s = tiempo_espera_s
        self.max_turnos = max_turnos
        self.ejecutable = ejecutable

    def comando(self, ruta: str) -> list[str]:
        herramientas = ",".join(HERRAMIENTAS_WEB)
        return [
            ruta,
            "-p",
            "Seguir las instrucciones recibidas por la entrada estándar.",
            "--output-format",
            "json",
            "--model",
            self.modelo,
            "--max-turns",
            str(self.max_turnos),
            "--tools",
            herramientas,
            "--allowedTools",
            herramientas,
            *FLAGS_AISLAMIENTO_WEB,  # sin MCP, CLAUDE.md, hooks ni permisos interactivos (ADR-025)
        ]

    def buscar(self, pregunta: str) -> ResultadoBuscador:
        ruta = shutil.which(self.ejecutable)
        if ruta is None:
            raise ErrorProveedorLLM("No se encontró la CLI de Claude Code ('claude') para la búsqueda web.")
        verificar_flags_aislamiento(ruta, flags_requeridos(FLAGS_AISLAMIENTO_WEB))
        entrada = texto_prompt(pregunta, self.version_prompt)
        with tempfile.TemporaryDirectory(prefix="fna-web-") as carpeta:
            try:
                proceso = subprocess.run(
                    self.comando(ruta),
                    input=entrada,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    cwd=carpeta,
                    timeout=self.tiempo_espera_s,
                    check=False,
                )
            except subprocess.TimeoutExpired as exc:
                raise ErrorProveedorLLM(
                    f"La búsqueda web no terminó en {self.tiempo_espera_s:.0f} s"
                ) from exc
        try:
            datos = json.loads(proceso.stdout)
        except json.JSONDecodeError as exc:
            raise ErrorProveedorLLM(
                f"Respuesta no válida de Claude Code (código {proceso.returncode})"
            ) from exc
        if datos.get("is_error") or proceso.returncode != 0:
            raise ErrorProveedorLLM(f"Claude Code devolvió un error: {str(datos.get('result', ''))[:300]}")
        return interpretar_salida(str(datos.get("result", "")))


def fecha_hoy() -> str:
    return date.today().isoformat()
