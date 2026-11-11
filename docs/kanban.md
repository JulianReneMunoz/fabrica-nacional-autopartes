# Tablero Kanban

Tablero del trabajo pendiente después del PR #21 (`d55229f`). La columna «Hecho» es **retrospectiva**: resume los PR
ya integrados según `git log`. Los puntos de las tareas pendientes son una **estimación**. Dependencias y duraciones
en el [cronograma](cronograma.md).

## Reglas del tablero

- **Límite WIP de la columna «En curso»: 2.**
  - Hay una sola persona responsable que aprueba cada plan, cada commit y cada ejecución real; más de dos tareas
    abiertas dejan planes esperando aprobación.
  - Cada tarea es un PR con CI en Ubuntu y Windows (ADR-021); con dos ramas abiertas, una avanza mientras la otra
    espera el CI.
  - Varios PR editan los mismos archivos (`docs/prompts/bitacora_experimentos.md`, `docs/arquitectura/modelos.md`,
    `services/agente.py`); más de dos ramas en paralelo multiplican los conflictos de merge.
- Una tarea pasa a «Hecho» cuando su PR está integrado en `main` con el CI en verde (squash merge).
- **Criterio de los puntos (Fibonacci: 1, 2, 3, 5, 8, 13), estimación relativa:**
  - 1: cambio trivial en un solo archivo, sin pruebas nuevas.
  - 2: un artefacto pequeño (un documento o un escaneo) sin cambios de código.
  - 3: un módulo con pruebas nuevas, sin ejecución real.
  - 5: código en varios módulos con pruebas, o un cambio que exige una ejecución real aprobada.
  - 8: regenera datos versionados o repite mediciones anteriores, o un entregable largo (informe, presentación).
  - 13: varios componentes, datos regenerados y ejecución real a la vez (ninguna tarea actual llega a 13).
- Las tarjetas sin alcance definido no llevan puntos.

## Por hacer

| Tarea | Descripción | Puntos (estimación) | Origen |
|---|---|---|---|
| Métrica `ausentes_sin_dato_inventado` | Métrica paralela a la estricta: acierto si la respuesta no contiene ningún patrón `dato_ausente`. Pruebas con respuestas simuladas y recálculo sobre los informes de A-10 y A-11 | 3 | Bitácora A-11, pendiente |
| Prompt v3 del agente para P08 | Versión nueva (sin modificar v2) que pida más de una búsqueda en las preguntas de lista; medición sin red con el agente simulado y luego una ejecución real | 5 | Bitácora A-11, pendiente |
| Log de diagnóstico opcional (Ley 1581) + ADR-030 + `generar_matriz.py` | Observación de GGA en el PR #17: el log de diagnóstico del agente guarda hasta 500 caracteres del texto de la respuesta, que puede contener datos personales. Hacerlo opcional y desactivado por defecto (Ley 1581 de 2012) y anotar en ADR-030 la limitación de `_cerrar_turno_interrumpido`, y corregir `scripts/generar_matriz.py`, que falla al imprimir «→» en la consola cp1252 y escribe el .md con CRLF | 5 | PR #17, observación de GGA |
| `modelo_llm` + `refusal` + `max_tokens` del Q&A | Valor por defecto de `modelo_llm` (hoy `llama3.2:3b`), detección de `stop_reason: "refusal"` en `llm/cadenas.py` y el `max_tokens=1024` fijo de `crear_modelo` con `anthropic` | 5 | ADR-027 y ADR-028, pendientes |
| `faq_visor` y `evaluar_recuperacion` al banco v2 | Regenera `data/gold/faq_visor.json` y obliga a repetir las mediciones de E-06 | 8 | Bitácora A-10, pendiente |
| Informe LaTeX y presentación | Informe en `docs/latex/` y presentación para la sustentación, con las cifras de la [Model Card](model_card.md) y de los [KPI](kpi_okr.md) | 8 | Entrega del curso |
| Escaneo de Antigravity con SkillSpector | Escaneo y decisión documentada en la bitácora según `fna-seguridad`, paso 5 | 2 | Bitácora R-06, pendiente |
| Taller 1 | Alcance por confirmar. Fuera de la ruta crítica hasta tener el detalle | sin puntos | Entrega del curso |

Total estimado de lo que tiene puntos: 36 puntos (estimación).

## En curso (WIP 1 de 2)

| Tarea | Descripción | Rama |
|---|---|---|
| Metodologías | Model Card, KPI y OKR, este tablero, CRISP-DM, CPM y Gantt, y la actualización de `metodologias.md` | `metodologias` |

## Hecho (retrospectivo)

| PR | Fecha del merge | Tema |
|---|---|---|
| #1 a #3 | 2026-11-07 | Flujo con pull requests, Makefile y `HF_TOKEN` en `.env.example` |
| #4 y #5 | 2026-11-07 | Base semántica nomic + Chroma y cierre de la Fase 1 |
| #6 a #8 | 2026-11-07 | Agente con memoria (simulado), endurecimiento de `claude -p` y JSON no objeto |
| #9 a #14 | 2026-11-08 | Proveedor del agente, pulido de la Fase 3, Engram C3, extractivo por defecto en el Q&A, Haiku 5.5 y agentes de desarrollo |
| #15 y #16 | 2026-11-08 | Compatibilidad con Haiku 5.5 y preguntas de seguimiento (prompt v2) |
| #17 | 2026-11-09 | `tool_use` sin `tool_result` (ADR-030) |
| #18 a #21 | 2026-11-10 | Validación real (A-08), citas y fundamentación (A-09), banco v2 (A-10) y recuperador híbrido (A-11) |
