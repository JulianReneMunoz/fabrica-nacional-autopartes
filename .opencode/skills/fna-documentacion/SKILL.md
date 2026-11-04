---
name: fna-documentacion
description: Genera y actualiza la documentación del proyecto Fanalca (README, manual LaTeX con TikZ, ADR, matriz de trazabilidad) en redacción impersonal. Usar al cerrar una funcionalidad o preparar la entrega.
---

# Generación de documentación

## Procedimiento
1. README: secciones obligatorias del enunciado; comandos copiados de ejecuciones reales.
2. Manual: `docs/latex/main.tex` y capítulos en `docs/latex/capitulos/`. Compilar con
   `latexmk -pdf -interaction=nonstopmode main.tex` (MiKTeX o TeX Live).
3. Diagramas: TikZ dentro del manual; fuentes Mermaid/PlantUML en `docs/diagramas/`.
4. Evidencias: anexar salidas reales de `pytest`, `ruff`, `mypy` y evaluación.

## Restricciones
- Redacción impersonal: sin "yo", "nosotros", "el equipo", "el estudiante"; preferir "se" e infinitivos.
- No incluir resultados no ejecutados ni secretos.

## Validación
El PDF compila sin errores y las referencias cruzadas se resuelven.
