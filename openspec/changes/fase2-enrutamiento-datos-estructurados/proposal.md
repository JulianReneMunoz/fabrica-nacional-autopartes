# Propuesta: enrutamiento entre documentos y datos estructurados (Fase 2)

## Why
El cambio responde a un **requisito documentado del curso**: la Fase 2 exige que el asistente enrute cada
pregunta entre documentos no estructurados y datos estructurados (SQL o CSV). Hoy el agente
(`services/agente.py`) dispone de una sola herramienta, `buscar_fragmentos`, que recupera texto.

La evidencia de la Fase 1 muestra el límite de ese diseño en las preguntas de lista, conteo y comparación:

- **P08** («¿Cuáles son las unidades de negocio de Fanalca?»): en A-11 el modelo hizo una sola búsqueda y
  encontró 2 de los 3 hechos mínimos (`docs/model_card.md`, «Limitaciones»). Los datos de cada unidad están
  repartidos en fragmentos distintos y ninguna búsqueda de k fragmentos garantiza reunirlos todos.
- Las cifras (puntos de venta, talleres, departamentos, clientes, vehículos) y los hitos con año existen
  literalmente en el corpus Gold, pero una búsqueda léxica o semántica no permite contarlos, ordenarlos ni
  compararlos de forma fiable.

## What Changes
- **Datos estructurados con evidencia literal:** tres tablas (`unidades_negocio`, `cifras`, `hitos`) en CSV
  versionados bajo `data/estructurado/`, cargadas en una base SQLite generada. Cada fila cita el `fragmento_id`
  y la URL del fragmento Gold donde el dato aparece literalmente, con su fecha de captura. Un dato que no
  aparece literal no entra.
- **Herramienta `consultar_datos`:** una sola sentencia SELECT sobre una conexión SQLite de solo lectura, con
  lista blanca de tablas, LIMIT forzado y tiempo máximo. Las filas devuelven `fragmento_id` y `url`, de modo que
  las citas siguen la regla única de A-09.
- **Enrutamiento ReAct:** el agente elige la herramienta por su descripción. Se agrega una versión nueva del
  prompt del agente (la siguiente libre del catálogo); la v2 no se modifica.
- **Activación por configuración:** `FNA_AGENTE_DATOS`, desactivada por defecto. Sin activarla, el agente, el
  prompt y la demo de la Fase 1 quedan idénticos.
- **Evaluación:** banco v3 = las 24 preguntas de v2 (P01 a P24, sin renumerar) + 8 preguntas estructuradas
  (P25 a P32); medición sin red y una ejecución real con Claude Haiku 5.5 sujeta a aprobación.
- **Arquitectura:** una ADR nueva (ADR-032) amplía la regla «el acceso a SQL pasa exclusivamente por
  `repositories/auditoria.py`» a un segundo repositorio de solo lectura en `repositories/`.

## Out of Scope
- Q&A, FAQ y resumen (`llm/cadenas.py`), el servidor MCP, la API pública y el visor 3D: no cambian.
- Sentencias de escritura (INSERT, UPDATE, DELETE, DDL), ATTACH y PRAGMA desde el modelo.
- PostgreSQL y la migración de la base de auditoría (Fase 3).
- Datos de noticias, hitos globales de Honda y cifras sin evidencia literal (lista de exclusiones en
  `design.md`).
- Scraping nuevo: los datos salen del Gold actual (`data/gold/fragmentos.jsonl`, 167 fragmentos).

## Impact
- **Esta rama (`docs/fase2-propuesta-datos`) es solo documentación:** crea únicamente los archivos de
  `openspec/changes/fase2-enrutamiento-datos-estructurados/`. No toca `src/`, `frontend/`, `tests/`, `data/` ni
  `docs/`.
- **La implementación (tareas 1 a 10 de `tasks.md`) va en otra rama** y se une a `main` después de la
  sustentación de la Fase 1, para no alterar la demo ni las cifras ya reportadas.
- Código afectado en la implementación: `core/config.py`, `services/agente.py`,
  `repositories/datos_estructurados.py` (nuevo), `llm/prompts/agente.yaml` (versión nueva), `cli.py`,
  `services/evaluacion.py`, `services/evaluacion_agente.py`, `evaluacion/preguntas_v3.yaml` (nuevo) y pruebas.
- Tipo: requisito del curso (Fase 2).
