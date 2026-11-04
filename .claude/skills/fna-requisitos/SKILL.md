---
name: fna-requisitos
description: Analiza los documentos del Taller 1 y mantiene la matriz de trazabilidad de requisitos de Fanalca. Usar cuando se agregue, cambie o verifique un requisito, historia de usuario o criterio de aceptación.
---

# Análisis de requisitos (Fanalca, Módulo 1)

## Responsabilidad
Mantener `docs/requisitos/matriz_trazabilidad.md` y `openspec/specs/*/spec.md` coherentes con
los documentos fuente (Taller 1 y clases 1-3).

## Entradas
- Documento fuente y página (p. ej. "Taller 1, p. 1, sección 2").
- Cambio solicitado o requisito nuevo.

## Procedimiento
1. Clasificar el elemento: **documentado** (cita literal del taller), **decisión de diseño** o
   **extensión opcional**. Nunca atribuir al taller algo que no dice.
2. Asignar identificador `RF-xx` / `RNF-xx` / `EXT-xx` y prioridad (Alta/Media/Baja).
3. Redactar historia de usuario y criterio de aceptación verificable (comando o prueba).
4. Enlazar el componente responsable (`src/...`) y la prueba (`tests/...`).
5. Actualizar el estado: implementado / parcial / pendiente, solo con evidencia.

## Salidas
Filas nuevas o actualizadas en la matriz y, si aplica, un escenario en `openspec/specs/`.

## Restricciones
- Redacción impersonal. Sin inventar páginas ni citas.
- Un requisito sin prueba asociada no puede marcarse "implementado".

## Validación
`uv run pytest tests/unit -q` sigue en verde y cada `RF` de la matriz tiene una prueba existente.
