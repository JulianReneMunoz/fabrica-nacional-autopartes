"""Carga del catálogo de prompts versionados (archivos YAML en ``llm/prompts``)."""

from __future__ import annotations

from dataclasses import dataclass
from functools import cache
from pathlib import Path

import yaml
from langchain_core.prompts import ChatPromptTemplate

DIR_PROMPTS = Path(__file__).parent / "prompts"
TAREAS = ("qa", "faq", "resumen")


@dataclass(frozen=True)
class VersionPrompt:
    tarea: str
    version: str
    nombre: str
    tecnica: str
    hipotesis: str
    formato_salida: str
    sistema: str
    humano: str

    def plantilla(self) -> ChatPromptTemplate:
        return ChatPromptTemplate.from_messages([("system", self.sistema), ("human", self.humano)])


@cache
def catalogo(tarea: str) -> dict[str, VersionPrompt]:
    if tarea not in TAREAS:
        raise ValueError(f"Tarea desconocida: {tarea}")
    datos = yaml.safe_load((DIR_PROMPTS / f"{tarea}.yaml").read_text(encoding="utf-8"))
    return {
        v: VersionPrompt(
            tarea=tarea,
            version=v,
            nombre=d["nombre"],
            tecnica=d["tecnica"],
            hipotesis=d["hipotesis"],
            formato_salida=d["formato_salida"],
            sistema=d["sistema"],
            humano=d["humano"],
        )
        for v, d in datos["versiones"].items()
    }


def obtener_prompt(tarea: str, version: str) -> VersionPrompt:
    versiones = catalogo(tarea)
    if version not in versiones:
        raise ValueError(f"Versión '{version}' no existe para '{tarea}'. Opciones: {list(versiones)}")
    return versiones[version]
