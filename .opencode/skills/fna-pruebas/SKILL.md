---
name: fna-pruebas
description: Ejecuta e interpreta la batería de pruebas del proyecto Fanalca (unitarias, integración, e2e, evaluación de 24 preguntas). Usar antes de cada commit o al diagnosticar fallos.
---

# Ejecución de pruebas

## Responsabilidad
Producir evidencia reproducible del estado del sistema.

## Procedimiento
1. `uv run pytest -q --cov --cov-report=term-missing` (umbral sugerido: 85 %).
2. Pruebas e2e de Streamlit: `uv run pytest tests/e2e -q`.
3. Evaluación funcional sin LLM: `uv run fabrica evaluate --proveedor extractivo`.
4. Evaluación con LLM real (requiere Ollama activo):
   `uv run fabrica evaluate --proveedor ollama --modelo llama3.2:3b --version-prompt v3`.
5. Guardar la salida en `docs/evidencias/` con fecha.

## Salidas
Resumen de aprobadas/fallidas, cobertura y ruta del informe de evaluación.

## Restricciones
Nunca reportar resultados no ejecutados. Una prueba omitida se declara como omitida.

## Validación
0 pruebas fallidas.
