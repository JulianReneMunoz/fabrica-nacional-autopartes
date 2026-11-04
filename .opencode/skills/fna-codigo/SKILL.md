---
name: fna-codigo
description: Genera o modifica código Python del proyecto Fanalca respetando la arquitectura por capas, uv, tipado y pruebas. Usar al implementar funcionalidades nuevas en src/fabrica_autopartes.
---

# Generación de código

## Responsabilidad
Implementar cambios pequeños, tipados y probados en `src/fabrica_autopartes/`.

## Entradas
Especificación en `openspec/changes/<cambio>/` (proposal, design, tasks) o tarea concreta.

## Procedimiento
1. Ubicar la capa correcta: scraping → pipelines → knowledge → llm → services → interfaces.
2. Escribir primero la prueba en `tests/unit` o `tests/integration`.
3. Implementar con anotaciones de tipo y docstrings en español.
4. Dependencias nuevas solo con `uv add <paquete>` (justificar en el PR).
5. Ejecutar `uv run pytest -q`, `uv run ruff check .`, `uv run ruff format .`, `uv run mypy`.

## Salidas
Código y pruebas en verde; resumen de archivos modificados.

## Restricciones
- No acceder a SQL fuera de `repositories/`. No llamar a `llm.cadenas` desde interfaces.
- No introducir secretos ni URLs no verificadas.

## Validación
Las cuatro órdenes anteriores terminan sin errores.
