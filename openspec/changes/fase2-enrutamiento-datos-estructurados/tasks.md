# Tareas

Implementación en una rama aparte, que se une a `main` después de la sustentación de la Fase 1 (ver
`proposal.md`). Puntos Fibonacci con el criterio de `docs/kanban.md` (estimación relativa). **10 tareas,
37 puntos (estimación).** El orden es el de la tabla; la columna «Depende de» marca la ruta crítica.

| # | Tarea | Puntos | Depende de |
|---|---|---|---|
| 1 | ADR-032 y regla de SQL en AGENTS.md | 2 | — |
| 2 | CSV, comando de carga y prueba de integridad | 5 | 1 |
| 3 | Repositorio de solo lectura con pruebas de seguridad | 5 | 2 |
| 4 | Herramienta `consultar_datos` y `FNA_AGENTE_DATOS` | 5 | 3 |
| 5 | Prompt nuevo del agente | 3 | 4 |
| 6 | Banco v3 y métricas de enrutamiento | 5 | 2 |
| 7 | Medición sin red | 3 | 5, 6 |
| 8 | Ejecución real con Haiku 5.5 (requiere aprobación) | 5 | 7 |
| 9 | Documentación: Model Card, kanban y matriz de trazabilidad | 2 | 8 |
| 10 | Revisión independiente (revisor-calidad) | 2 | 9 |

## 1. Arquitectura
- [ ] 1.1 Redactar ADR-032 (segundo repositorio SQL de solo lectura, herramienta `consultar_datos`, activación
  por `FNA_AGENTE_DATOS`) y ajustar en AGENTS.md la regla «el acceso a SQL pasa exclusivamente por
  `repositories/auditoria.py`» para incluir `repositories/datos_estructurados.py` — verificar:
  `git diff --name-only main` muestra solo `docs/arquitectura/adr/ADR-032-*.md` y `AGENTS.md`

## 2. Datos
- [ ] 2.1 Crear `data/estructurado/unidades_negocio.csv`, `cifras.csv` e `hitos.csv` con las 28 filas de
  `design.md` §2 — verificar: `uv run --no-sync pytest tests/unit/test_datos_estructurados.py -k integridad -q`
- [ ] 2.2 Comando `fabrica datos construir` que genera `data/estructurado/datos.db` (no versionada; agregar a
  `.gitignore`) — verificar: `uv run --no-sync fabrica datos construir` y
  `uv run --no-sync pytest tests/unit/test_datos_estructurados.py -k carga -q`

## 3. Repositorio
- [ ] 3.1 `repositories/datos_estructurados.py`: conexión `mode=ro`, `query_only`, authorizer con lista blanca,
  una sentencia, LIMIT 50 y tiempo máximo — verificar:
  `uv run --no-sync pytest tests/unit/test_datos_estructurados.py -k seguridad -q` (casos: DROP, INSERT, ATTACH,
  PRAGMA, `sqlite_master`, `;` encadenado, CTE recursiva sin fin)

## 4. Herramienta y configuración
- [ ] 4.1 `agente_datos` y `agente_datos_timeout_ms` en `core/config.py`; `crear_herramienta_datos()` en
  `services/agente.py` con artefacto `fragmento_id/titulo/url`; registro condicionado en `_construir()` —
  verificar: `uv run --no-sync pytest tests/unit/test_agente.py -k datos -q` y `uv run --no-sync mypy`

## 5. Prompt
- [ ] 5.1 Versión nueva del prompt del agente en `llm/prompts/agente.yaml` (siguiente libre; v2 sin cambios) con
  técnica e hipótesis — verificar: `uv run --no-sync pytest tests/unit -k "catalogo or prompt" -q`

## 6. Evaluación
- [ ] 6.1 `evaluacion/preguntas_v3.yaml` (P01 a P24 de v2 sin cambios + P25 a P32), banco `v3` en
  `services/evaluacion.py` y métrica de enrutamiento en `services/evaluacion_agente.py` — verificar:
  `uv run --no-sync pytest tests/unit/test_banco_gold.py -q`

## 7. Medición sin red
- [ ] 7.1 Banco v3 con el agente simulado, `FNA_AGENTE_DATOS` en `false` y en `true` — verificar:
  `uv run --no-sync pytest -q` y el informe JSON en `evaluacion/resultados/`

## 8. Ejecución real (requiere aprobación explícita; costo estimado hasta USD 0,08)
- [ ] 8.1 Dos corridas del banco v3 con `claude-haiku-5-5`: línea base y datos activados; entrada en
  `docs/prompts/bitacora_experimentos.md` — verificar: los dos JSON en `evaluacion/resultados/` y
  `uv run --no-sync pytest tests/unit/test_banco_gold.py -q`

## 9. Documentación
- [ ] 9.1 Actualizar `docs/model_card.md` (P08 y limitaciones), `docs/kanban.md` y la matriz de trazabilidad —
  verificar: `uv run --no-sync ruff check . && uv run --no-sync ruff format --check .`

## 10. Revisión
- [ ] 10.1 Revisión con el subagente revisor-calidad contra AGENTS.md y esta propuesta; archivar el cambio
  (`openspec/changes/archive/`) al integrar — verificar: `uv run --no-sync pytest -q`,
  `uv run --no-sync mypy` y `cd web; npm test`
