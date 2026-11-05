---
name: fna-documentacion
description: Genera y actualiza la documentación del proyecto Fanalca (README, ADR, diagramas, matriz de trazabilidad) en redacción impersonal. Usar al cerrar una funcionalidad o preparar la entrega.
---

# Generación de documentación

## Procedimiento
1. README: secciones obligatorias del enunciado; comandos copiados de ejecuciones reales.
2. Guías: `docs/manuales/`, regeneradas con `uv run python scripts/generar_guia.py`.
3. Diagramas: Mermaid en el README y fuentes en `docs/diagramas/`.
4. Evidencias: anexar salidas reales de `pytest`, `ruff`, `mypy` y evaluación.

## Restricciones
- Redacción impersonal: sin "yo", "nosotros", "el equipo", "el estudiante"; preferir "se" e infinitivos.
- No incluir resultados no ejecutados ni secretos.

## Validación
Los enlaces relativos se resuelven y las guías generadas están al día.
