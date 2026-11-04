---
name: fna-seguridad
description: Audita seguridad del proyecto Fanalca: secretos, inyección de prompts, permisos de agentes y MCP, scraping ético y datos personales. Usar antes de publicar el repositorio o integrar herramientas de terceros.
---

# Auditoría de seguridad

## Procedimiento
1. Secretos: `git grep -nE "(sk-|api[_-]?key\s*=\s*['\"][A-Za-z0-9])"` debe estar vacío; `.env` fuera de Git.
2. Inyección: ejecutar las pruebas `test_deteccion_inyeccion` y `test_qa_bloquea_inyeccion_sin_invocar_modelo`.
3. Permisos: revisar `opencode.json` (`bash` en `ask` por defecto, `git push` en `deny`) y
   `.claude/settings.json` (lectura de `.env` denegada).
4. MCP: confirmar que `fna-conocimiento` solo expone herramientas `read_only_hint=True`.
5. Skills de terceros: `skillspector scan <ruta-o-repo>` antes de instalar (rechazar puntuación ≥ 51).
6. Scraping: robots.txt respetado y User-Agent identificable (`tests/integration/test_rastreo.py`).
7. Datos personales: `uv run fabrica validate` sin hallazgos `datos_personales`.

## Salidas
Informe con hallazgos, severidad y acción correctiva.

## Restricciones
Solo lectura; no ejecuta herramientas ofensivas ni pruebas contra sistemas de terceros.

## Validación
Todos los puntos verificados con evidencia.
