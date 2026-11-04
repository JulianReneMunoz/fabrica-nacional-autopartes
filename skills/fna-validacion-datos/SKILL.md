---
name: fna-validacion-datos
description: Valida la calidad del corpus Gold de Fanalca (procedencia, HTML residual, duplicados, datos personales, tamaño de fragmentos). Usar después de cada reconstrucción de la base.
---

# Validación de datos

## Responsabilidad
Garantizar que cada fragmento sea limpio, único, trazable y apto para el prompt.

## Entradas
`data/gold/fragmentos.jsonl`.

## Procedimiento
1. `uv run fabrica validate` (o la tool MCP `validar_corpus`).
2. Errores bloqueantes: id duplicado, fragmento sin URL de origen.
3. Advertencias: HTML residual, fragmentos > 600 tokens, correos no corporativos.
4. Comparar `estadisticas.json` con la ejecución anterior (variación de fragmentos > 30 %
   exige revisión manual).

## Salidas
Informe JSON con `aprobado`, `errores`, `advertencias` y `hallazgos`.

## Restricciones
No corrige datos en Gold a mano: las correcciones se hacen en las reglas de Silver.

## Validación
`aprobado: true` y 0 errores.
