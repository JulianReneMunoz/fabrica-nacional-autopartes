# Tareas

Cada caso se implementa y se prueba en el PR que construye su capacidad. Este cambio solo fija los textos y los
criterios; los PR del plan citados son identificadores del plan, no números reales de GitHub.

| # | Tarea | PR del plan | Depende de |
|---|---|---|---|
| 1 | Checkpointer SqliteSaver y Store con namespace `("preferencias", user_id)` y `search()` | #28, #29 | — |
| 2 | Sesiones por usuario seudónimo y texto nuevo de 2A y 2B en `web/src/ignisCasos.ts` | #44 | 1 |
| 3 | Herramientas LangChain, router mixto y blindaje con Claude | tools, #32, #33/#35 | 1 |
| 4 | Tarjetas de los casos en Rayos-X y validación | #40 | 2, 3 |

## 1. Memoria persistente (casos 2A y 2B)
- [ ] 1.1 Guardar las preferencias del caso 2A en el Store y recuperarlas con `search()` desde otro hilo del mismo
  `user_id`; un mensaje con nombre o empresa no guarda nada — verificar:
  `uv run --no-sync pytest -q tests/integration -k "preferencias or memoria"`
- [ ] 1.2 El historial del hilo y las preferencias sobreviven a recrear el servicio con el mismo directorio de
  datos — verificar: `uv run --no-sync pytest -q tests/integration -k reinicio`

## 2. Sesiones (caso 2B entre usuarios y tras reiniciar)
- [ ] 2.1 Dos usuarios no ven los hilos ni las preferencias del otro; un `thread_id` ajeno da 403 — verificar:
  `uv run --no-sync pytest -q tests/integration -k sesiones`
- [ ] 2.2 Textos nuevos de 2A y 2B en `web/src/ignisCasos.ts` y comentario sin el pendiente del #27 — verificar:
  `cd web; npm test`

## 3. Router, herramientas y blindaje (casos 1, 3, 4A, 4B, 5 y 6)
- [ ] 3.1 Rutas `rag_documental`, `herramienta_estructurada`, `mixto` y `directo` con citas y salidas Pydantic;
  el saludo no llama herramientas — verificar: `uv run --no-sync pytest -q tests/integration/test_api_ignis.py`
- [ ] 3.2 Documento de prueba con inyección indirecta y moderación de la solicitud del caso 6 — verificar:
  `uv run --no-sync pytest -q -k "blindaje or moderacion"`

## 4. Rayos-X y validación
- [ ] 4.1 Tarjetas de los ocho casos que ejecutan la consulta en Atención y muestran la evidencia del turno —
  verificar: `cd web; npm test` y `npx playwright test`
