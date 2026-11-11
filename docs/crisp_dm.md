# CRISP-DM: mapeo retrospectivo del proyecto

El proyecto no se planificó con CRISP-DM (Cross-Industry Standard Process for Data Mining). Este documento es un
**mapeo retrospectivo**: ubica las etapas que ya ocurrieron en las seis fases del modelo y enlaza la evidencia de
cada una (especificaciones, ADR, entradas de la [bitácora](prompts/bitacora_experimentos.md) y PR). No agrega
trabajo nuevo.

## Relación con Medallion

- **Medallion** (Bronze, Silver, Gold; [ADR-002](arquitectura/adr/ADR-002-medallion-archivos.md)) es una
  **arquitectura de datos**: define dónde vive cada estado del dato y qué transformación lo produce.
- **CRISP-DM** es un **modelo de proceso**: define qué preguntas se responden en cada fase del ciclo de vida, desde el
  negocio hasta el despliegue, y admite volver a fases anteriores.
- Medallion cubre sobre todo la fase 3 (preparación) y parte de la fase 2 (comprensión de los datos, con las métricas
  y gráficas de cada etapa). Las fases 1, 4, 5 y 6 no tienen equivalente en Medallion.
- Las dos se complementan: CRISP-DM explica por qué se volvió a los datos después de evaluar (A-08 → banco v2) y
  Medallion explica en qué capa se hizo cada cambio.

## Mapeo de fases

| Fase CRISP-DM | Etapas reales del proyecto | Evidencia |
|---|---|---|
| 1. Comprensión del negocio | Análisis del Taller 1 y de las clases: necesidad de un canal de comunicación automatizado y preciso; reglas de negocio (respuesta solo desde el contexto, frase de rechazo fija, citas, Ley 1581) | [`analisis_documentos.md`](requisitos/analisis_documentos.md), [matriz de trazabilidad](requisitos/matriz_trazabilidad.md), [`openspec/specs/`](../openspec/specs/), [`AGENTS.md`](../AGENTS.md) |
| 2. Comprensión de los datos | Fuentes permitidas (autopartesfanalca.com.co y fanalca.com), robots.txt y `Crawl-delay`, sitio protegido por anti-bots, redes sociales excluidas, métricas del rastreo | [ADR-010](arquitectura/adr/ADR-010-fuentes-redes-sociales.md), [ADR-015](arquitectura/adr/ADR-015-proteccion-antibots.md), bitácora R-01, [`scraping/`](../src/fabrica_autopartes/scraping/), [`01_rastreo.png`](graficas/01_rastreo.png), [`02_bronze_paginas.png`](graficas/02_bronze_paginas.png) |
| 3. Preparación de los datos | Bronze (HTML y manifiesto), Silver (limpieza, segmentación, deduplicación y anonimización), Gold (167 fragmentos); HTML crudo fuera del control de versiones | [ADR-002](arquitectura/adr/ADR-002-medallion-archivos.md), [`pipelines/`](../src/fabrica_autopartes/pipelines/), [flujo Medallion](arquitectura/diagramas/02_flujo_medallion.md), bitácora R-02, [`04_limpieza_paginas.png`](graficas/04_limpieza_paginas.png), [`06_tokens_fragmento.png`](graficas/06_tokens_fragmento.png) |
| 4. Modelado | Prompts versionados v1 a v3; recuperadores BM25, semántico e híbrido; agente con memoria y herramienta tipada; Claude Haiku 5.5 como proveedor | [ADR-005](arquitectura/adr/ADR-005-contexto-completo-bm25.md), [ADR-009](arquitectura/adr/ADR-009-prompts-versionados.md), [ADR-023](arquitectura/adr/ADR-023-base-semantica-nomic-chroma.md), [ADR-024](arquitectura/adr/ADR-024-agente-con-memoria.md), [ADR-026](arquitectura/adr/ADR-026-haiku-proveedor-principal-agente.md), [ADR-031](arquitectura/adr/ADR-031-recuperador-hibrido-agente.md); bitácora E-05, E-06, A-01; PR #4, #6, #21 |
| 5. Evaluación | Línea base extractiva (E-00), Claude por `claude_code` (E-01 a E-07), validación real del agente (A-08), corrección de citas y de la métrica (A-09), banco v2 (A-10) y recuperador híbrido (A-11) | [`evaluacion/resultados/`](../evaluacion/resultados/), [Model Card](model_card.md), [KPI](kpi_okr.md); PR #18 a #21 |
| 6. Despliegue | API FastAPI, Streamlit, CLI y servidor MCP de solo lectura; `docker-compose.yml` definido; CI en GitHub Actions. Sin despliegue en producción: el sistema se ejecuta en local | [ADR-006](arquitectura/adr/ADR-006-streamlit.md), [ADR-007](arquitectura/adr/ADR-007-fastapi.md), [ADR-008](arquitectura/adr/ADR-008-mcp-propio.md), [ADR-012](arquitectura/adr/ADR-012-postgresql-despliegue.md), [ADR-022](arquitectura/adr/ADR-022-ollama-pospuesto.md), [`ci.yml`](../.github/workflows/ci.yml), [`docker-compose.yml`](../docker-compose.yml); PR #11 |

## Iteraciones observadas (retrospectivo)

CRISP-DM es cíclico. En el historial aparecen estas vueltas atrás:

| Desde | Hacia | Motivo | Evidencia |
|---|---|---|---|
| 5. Evaluación (A-08) | 3. Preparación y 1. Negocio | Los fallos de P02, P07 y P15 se debían a un banco desalineado con el Gold; se creó el banco v2 sin tocar el v1 | Bitácora A-08 y A-10, PR #20 |
| 5. Evaluación (A-08, A-10) | 4. Modelado | P11 fallaba por la recuperación BM25; se adoptó el recuperador híbrido | Bitácora A-10 y A-11, ADR-031, PR #21 |
| 5. Evaluación (A-08) | 5. Evaluación | La métrica de fundamentación penalizaba las URL; se corrigió la fórmula | Bitácora A-09, PR #19 |
| 6. Despliegue (prueba real en Streamlit) | 4. Modelado | Haiku 5.5 rechazaba `temperature`; se ajustaron los parámetros | [ADR-028](arquitectura/adr/ADR-028-compatibilidad-claude-haiku-5-5.md), PR #15 |

## Fases pendientes

Las tareas del [tablero](kanban.md) caen en las fases 4 (prompt v3 para P08, `modelo_llm` del Q&A), 5 (métrica
`ausentes_sin_dato_inventado`, `evaluar_recuperacion` con el banco v2) y 1 (cumplimiento de la Ley 1581 con el log
opcional).
