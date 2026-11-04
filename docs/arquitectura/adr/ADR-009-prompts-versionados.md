# ADR-009 · Prompts versionados en YAML con técnica e hipótesis

- **Estado:** aceptada
- **Contexto:** la rúbrica valora la documentación del proceso de experimentación con prompts.
- **Decisión:** `llm/prompts/{qa,faq,resumen}.yaml` con v1 (línea base zero-shot), v2 (reglas + delimitación XML + defensa ante inyección) y v3 (salida JSON + few-shot + citas verificables). Una versión evaluada no se edita: se agrega una nueva.
- **Consecuencias:** las evaluaciones guardan la versión usada; el laboratorio de prompts compara versiones lado a lado.
