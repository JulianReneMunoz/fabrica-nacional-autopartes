"""Respuestas precalculadas del visor para las preguntas frecuentes de Fanalca.

Se toman las preguntas ``respondible`` de ``evaluacion/preguntas.yaml`` y se responden mediante el
mismo Q&A de la API (``ServicioAsistente.responder``, equivalente a ``POST /api/v1/tareas/qa``).
El resultado, con sus citas, se guarda en ``data/gold/faq_visor.json`` para que la demostración no
dependa de la latencia del modelo. Una pregunta sin respuesta en la base conserva la frase de
rechazo; nunca se completa con conocimiento general.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fabrica_autopartes.llm.salvaguardas import es_rechazo
from fabrica_autopartes.services.asistente import ServicioAsistente
from fabrica_autopartes.services.evaluacion import cargar_preguntas

NOMBRE_ARCHIVO = "faq_visor.json"
TIPOS_INCLUIDOS = ("respondible",)
VALORES_PREDETERMINADOS = {"proveedor": "claude_code", "modelo": "sonnet", "version_prompt": "v3"}
ADVERTENCIA = (
    "Respuestas generadas con la base de conocimiento verificada y guardadas con sus citas; "
    "se regeneran con «fabrica faq-visor»."
)


def ruta_faq_visor(servicio: ServicioAsistente) -> Path:
    return servicio.config.dir_gold / NOMBRE_ARCHIVO


def generar_faq_visor(
    servicio: ServicioAsistente,
    opciones: dict[str, str | None] | None = None,
    maximo: int | None = None,
    guardar: bool = True,
) -> dict[str, Any]:
    """Responde las preguntas respondibles del banco y, opcionalmente, guarda el JSON del visor."""
    op: dict[str, str | None] = {**VALORES_PREDETERMINADOS}
    op.update({k: v for k, v in (opciones or {}).items() if v})
    # Fijo en v1: cambiar de banco regeneraría data/gold/faq_visor.json (pendiente fuera de A-10).
    preguntas = [p for p in cargar_preguntas("v1") if p.get("tipo") in TIPOS_INCLUIDOS]
    if maximo is not None:
        preguntas = preguntas[: max(0, maximo)]
    items: list[dict[str, Any]] = []
    for p in preguntas:
        r = servicio.responder(p["pregunta"], canal="faq-visor", **op)
        items.append(
            {
                "id": p["id"],
                "categoria": p.get("categoria", ""),
                "pregunta": p["pregunta"],
                "respuesta": r.respuesta,
                "rechazo": es_rechazo(r.respuesta),
                "fundamentada": r.fundamentada,
                "confianza": r.confianza,
                "fuentes": [{"fragmento_id": f.fragmento_id, "url": f.url} for f in r.fuentes],
                "latencia_ms": r.latencia_ms,
            }
        )
    resultado: dict[str, Any] = {
        "version_esquema": 1,
        "generado": datetime.now(UTC).isoformat(timespec="seconds"),
        "proveedor": op["proveedor"],
        "modelo": op["modelo"],
        "version_prompt": op["version_prompt"],
        "advertencia": ADVERTENCIA,
        "total": len(items),
        "items": items,
    }
    if guardar:
        ruta = ruta_faq_visor(servicio)
        ruta.parent.mkdir(parents=True, exist_ok=True)
        ruta.write_text(json.dumps(resultado, ensure_ascii=False, indent=2), encoding="utf-8")
        resultado["archivo"] = str(ruta)
    return resultado


def leer_faq_visor(directorio_gold: Path) -> dict[str, Any] | None:
    ruta = directorio_gold / NOMBRE_ARCHIVO
    if not ruta.exists():
        return None
    return dict(json.loads(ruta.read_text(encoding="utf-8")))
