"""Modelo extractivo determinista (sin LLM).

Propósito: línea base reproducible y modo fuera de línea para pruebas automatizadas,
CI y demostraciones sin GPU. **No** sustituye a un LLM: no redacta, solo selecciona las
oraciones del contexto con mayor solapamiento léxico con la consulta. Implementa la
interfaz ``BaseChatModel`` de LangChain para usarse en las mismas cadenas LCEL.
"""

from __future__ import annotations

import json
import re
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult

from fabrica_autopartes.knowledge.recuperacion import tokenizar

RECHAZO = "La información solicitada no se encuentra en la base de conocimiento de Fanalca."
_FRAG = re.compile(r'<fragmento id="([^"]+)"[^>]*>\n?(.*?)\n?</fragmento>', re.S)
_CTX = re.compile(r"<contexto>(.*)</contexto>", re.S)
_PREG = re.compile(r"<pregunta>(.*?)</pregunta>", re.S)


def _oraciones(texto: str) -> list[str]:
    limpio = re.sub(r"^#+\s*", "", texto, flags=re.M)
    partes = re.split(r"(?<=[.!?])\s+|\n+", limpio)
    return [p.strip(" -") for p in partes if len(p.split()) >= 5]


class ModeloExtractivo(BaseChatModel):
    umbral: float = 0.34
    max_oraciones: int = 2

    @property
    def _llm_type(self) -> str:
        return "extractivo-fna"

    def _generate(
        self, messages: list[BaseMessage], stop: Any = None, run_manager: Any = None, **kwargs: Any
    ) -> ChatResult:
        sistema = str(messages[0].content)
        humano = str(messages[-1].content)
        bloque = _CTX.search(sistema)  # solo el contexto real, nunca los ejemplos few-shot
        fragmentos = _FRAG.findall(bloque.group(1) if bloque else sistema)
        tarea = "QA"
        m = re.search(r"TAREA:\s*(\w+)", sistema)
        if m:
            tarea = m.group(1).upper()
        if tarea == "FAQ":
            salida = self._faq(fragmentos, sistema)
        elif tarea == "RESUMEN":
            salida = self._resumen(fragmentos)
        else:
            pm = _PREG.search(humano)
            pregunta = pm.group(1) if pm else humano
            salida = self._qa(pregunta, fragmentos, json_salida="JSON" in sistema)
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=salida))])

    # ------------------------------------------------------------------ tareas
    def _qa(self, pregunta: str, fragmentos: list[tuple[str, str]], json_salida: bool) -> str:
        consulta = set(tokenizar(pregunta))
        candidatas: list[tuple[float, str, str]] = []
        for fid, texto in fragmentos:
            for o in _oraciones(texto):
                tokens = set(tokenizar(o))
                if not consulta or not tokens:
                    continue
                cobertura = len(consulta & tokens) / len(consulta)
                candidatas.append((cobertura, o, fid))
        candidatas.sort(key=lambda c: c[0], reverse=True)
        elegidas = [c for c in candidatas[: self.max_oraciones] if c[0] >= self.umbral]
        if not elegidas:
            respuesta, fuentes, confianza = RECHAZO, [], "ninguna"
        else:
            respuesta = " ".join(o if o.endswith(".") else o + "." for _, o, _ in elegidas)
            fuentes = sorted({fid for _, _, fid in elegidas})
            confianza = "alta" if elegidas[0][0] >= 0.6 else "media"
        if json_salida:
            return json.dumps(
                {"respuesta": respuesta, "fuentes": fuentes, "confianza": confianza},
                ensure_ascii=False,
            )
        return respuesta + (f" [{', '.join(fuentes)}]" if fuentes else "")

    def _faq(self, fragmentos: list[tuple[str, str]], sistema: str) -> str:
        m = re.search(r"Redacta (\d+)|crea (\d+)", sistema)
        n = int(next(g for g in m.groups() if g)) if m else 5
        items = []
        vistos: set[str] = set()
        for fid, texto in fragmentos:
            seccion = fid.split("#")[0]
            if seccion in vistos:
                continue
            oraciones = _oraciones(texto)
            if not oraciones:
                continue
            vistos.add(seccion)
            tema = seccion.replace("-", " ").replace("en ", "").strip()
            items.append(
                {
                    "pregunta": f"¿Qué información hay sobre {tema}?",
                    "respuesta": " ".join(oraciones[:2]),
                    "fuentes": [fid],
                }
            )
            if len(items) >= n:
                break
        if "JSON" in sistema:
            return json.dumps({"faq": items}, ensure_ascii=False)
        return "\n".join(f"P: {i['pregunta']}\nR: {i['respuesta']} [{i['fuentes'][0]}]" for i in items)

    def _resumen(self, fragmentos: list[tuple[str, str]]) -> str:
        oraciones: list[str] = []
        ids: list[str] = []
        for fid, texto in fragmentos:
            primera = _oraciones(texto)[:1]
            if primera and primera[0] not in oraciones:
                oraciones.append(primera[0])
                ids.append(fid)
            if len(oraciones) >= 8:
                break
        cuerpo = "\n".join(f"- {o}" for o in oraciones)
        return f"**Resumen extractivo (sin LLM)**\n\n{cuerpo}\n\nFuentes: {', '.join(ids)}"
