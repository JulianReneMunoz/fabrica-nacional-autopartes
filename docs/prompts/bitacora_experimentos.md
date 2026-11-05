# Bitácora de experimentación con prompts

Protocolo: mismo banco de 24 preguntas (`evaluacion/preguntas.yaml`), misma base Gold, temperatura 0,1,
una variable cambiada por experimento. Métricas definidas en `services/evaluacion.py`.
Toda cifra de esta bitácora proviene de un archivo en `evaluacion/resultados/`.

## Catálogo
| Versión | Técnica | Hipótesis |
|---|---|---|
| v1 | Zero-shot básico | Sin reglas, el modelo completa con conocimiento propio y alucina datos ausentes. |
| v2 | Zero-shot + rol + reglas + delimitación XML + defensa ante inyección | Las reglas y la frase de rechazo fija reducen alucinaciones. |
| v3 | Salida JSON + few-shot (2 ejemplos) + citas verificables + confianza | Las citas permiten validar automáticamente la fundamentación. |

## E-00 · Línea base extractiva (sin LLM) — ejecutado 2026-11-04
Proveedor `extractivo` (selección de oraciones por solapamiento léxico). No interpreta instrucciones: sirve para
verificar el arnés de evaluación y medir la **cobertura del contexto** (si los hechos están disponibles).

| Prompt | Modo | Exactitud respondibles | Cobertura contexto | Rechazo correcto | Fundamentadas |
|---|---|---|---|---|---|
| v1 | completo | 0,632 | 1,0 | 0,4 | 0,842 |
| v1 | selección | 0,684 | 1,0 | 0,4 | 0,842 |
| v2 | completo | 0,632 | 1,0 | 0,4 | 0,842 |
| v2 | selección | 0,684 | 1,0 | 0,4 | 0,842 |
| v3 | completo | 0,632 | 1,0 | 0,4 | 0,842 |
| v3 | selección | 0,684 | 1,0 | 0,4 | 0,842 |

Lectura: la cobertura de 1,0 confirma que el corpus contiene los hechos de las 19 preguntas respondibles; los
fallos de la línea base son de *selección/generación*, no de datos. El rechazo correcto de 0,4 (solo inyección y
fuera de alcance) muestra por qué se necesita un LLM con reglas explícitas para los datos ausentes.

### Hallazgo H-01 (corregido antes de congelar v3)
En la primera corrida, la pregunta P10 devolvió "La planta principal está en la ciudad X.": el ejemplo
few-shot de v3 usaba la misma etiqueta `<fragmento>` que el contexto real y fue tratado como dato. Corrección:
el ejemplo pasó a formato ilustrativo `[ejemplo#000] "..."` y la línea base solo lee el bloque `<contexto>`.
Pruebas de regresión: `test_ejemplos_few_shot_no_usan_formato_de_contexto` y
`test_extractivo_ignora_ejemplos_fuera_del_contexto`. Implicación para LLM reales: los ejemplos few-shot
deben distinguirse visualmente del contexto para evitar contaminación.

## E-01 a E-03 · Claude Sonnet vía Claude Code (ejecutado el 2026-11-05)
Proveedor `claude_code` (sesión de suscripción de Claude Code, sin clave de API), modelo `sonnet`, modo `auto`,
24 preguntas, base real (scraping + lectura web: 64 documentos, 167 fragmentos, ~20 958 tokens).
```powershell
uv run fabrica evaluate --proveedor claude_code --modelo sonnet --version-prompt v1
uv run fabrica evaluate --proveedor claude_code --modelo sonnet --version-prompt v2
uv run fabrica evaluate --proveedor claude_code --modelo sonnet --version-prompt v3
```
Reportes: `evaluacion/resultados/20261105T005207Z_claude_code_sonnet_v1_auto.md`,
`20261105T005410Z_claude_code_sonnet_v2_auto.md` y `20261105T005553Z_claude_code_sonnet_v3_auto.md`.

| Prompt | Exactitud respondibles | Cobertura contexto | Rechazo correcto | Fundamentadas | Exactitud global | Latencia media |
|---|---|---|---|---|---|---|
| v1 | 0,789 | 0,842 | 0,2 | 0,895 | 0,667 | 3 855 ms |
| v2 | 0,789 | 0,842 | 1,0 | 0,789 | 0,833 | 3 523 ms |
| v3 | 0,789 | 0,842 | 1,0 | 0,842 | 0,833 | 3 537 ms |

Lectura:
- Las reglas anti-alucinación de v2 y v3 elevan el rechazo correcto de 0,2 a 1,0: con v1 el modelo completa
  datos ausentes con conocimiento general; con v2 y v3 responde la frase de rechazo fija en las 5 preguntas sin
  respuesta en la base, incluida la de inyección.
- v3 recupera parte de la fundamentación perdida en v2 (0,842 frente a 0,789) gracias a los ejemplos few-shot
  con citas; la latencia no cambia de forma apreciable.
- La exactitud de respondibles (0,789, 15 de 19) queda cerca del techo de cobertura del contexto (0,842, 16 de 19):
  los fallos restantes provienen sobre todo de la cobertura de datos del scraping, no del prompt.
- Decisión: **v3** como versión por defecto.

### Hallazgo H-02 (corregido antes de la evaluación)
"¿Dónde queda la sede principal?" se respondía con la frase de rechazo. Causas: la dirección solo aparecía en el
pie de página (descartado por la extracción), BM25 no compartía vocabulario entre "queda/sede" y "Calle/Acopi", y
el modo completo truncaba el documento de contacto. Correcciones: documento `contacto-sitio` a partir del pie
repetido en al menos 2 páginas, expansión de consultas con peso 0,5 y documentos de contacto al inicio del
contexto. Respuesta final: Calle 13 # 31A - 80, Urbanización Industrial Acopi, Yumbo, citando
`contacto-sitio#000` y `autopartes-contacto#000`. Pruebas: `test_recuperacion_expansion.py` y
`test_scraping.py::pie de contacto`.

## S-01 · Auditoría de skills de terceros `CloudAI-X/threejs-skills` (2026-11-04)

Procedimiento: `fna-seguridad`, paso 5. Herramienta: SkillSpector v2.12.0 (`skillspector scan <ruta> --no-llm --format markdown`), sobre un clon superficial en carpeta temporal. Criterio de rechazo: puntuación ≥ 51.

| Skill | Puntuación | Severidad | Recomendación | Hallazgos | Cobertura |
|---|---|---|---|---|---|
| threejs-fundamentals | 0/100 | LOW | CAUTION | 0 | parcial (0 %) |
| threejs-geometry | 0/100 | LOW | SAFE | 0 | 100 % |
| threejs-interaction | 20/100 | LOW | SAFE | 1 (TM1, línea 114) | 100 % |
| threejs-animation | 0/100 | LOW | SAFE | 0 | 100 % |
| threejs-loaders | 0/100 | LOW | CAUTION | 0 | parcial (0 %) |
| threejs-react-three-fiber | 20/100 | LOW | CAUTION | 1 (AR2, línea 474) | parcial (0 %) |

Revisión manual de los hallazgos: ambos son falsos positivos. TM1 corresponde a un comentario sobre capas de `Raycaster`; AR2 corresponde a una nota sobre `<Canvas shadows>` en la sección de errores comunes. Ninguna línea contiene instrucciones dirigidas al agente. La recomendación CAUTION de tres skills proviene de cobertura parcial del analizador estático (límite del analizador y referencias a archivos no incluidos), no de hallazgos.

Resultado: las seis skills quedan por debajo del umbral de 51 y se copian a `skills/`, con sincronización mediante `scripts/sincronizar_skills.py` hacia `.claude/skills/` y `.opencode/skills/`. Diff: solo carpetas nuevas, sin cambios en skills existentes.

Compatibilidad de versión: las skills apuntan a three.js r186; `web/package.json` declara `three ^0.187.0`, `@react-three/fiber ^9.8.2`, `@react-three/drei ^10.7.9` y `react ^19.3.1`. Diferencia anotada: una versión menor por encima de r186; las API usadas por las skills (`Timer`, `PCFShadowMap`, `HDRLoader`, imports `three/addons/`) se mantienen. Verificar contra `node_modules` tras `npm ci` (no instalado al momento del registro).

## S-02 · Auditoría de skills de terceros `CloudAI-X/threejs-skills` (lighting, materials, postprocessing, performance) (2026-11-04)

Procedimiento: `fna-seguridad`, paso 5. Herramienta: SkillSpector v2.12.0 (`skillspector scan <ruta> --no-llm --format markdown`) sobre el mismo clon superficial de S-01. Criterio de rechazo: puntuación ≥ 51.

| Skill | Puntuación | Severidad | Recomendación | Hallazgos | Cobertura |
|---|---|---|---|---|---|
| threejs-lighting | 0/100 | LOW | SAFE | 0 | 100 % |
| threejs-materials | 0/100 | LOW | SAFE | 0 | 100 % |
| threejs-postprocessing | 0/100 | LOW | SAFE | 0 | 100 % |
| threejs-performance | 0/100 | LOW | CAUTION | 0 | parcial (0 %) |

La recomendación CAUTION de `threejs-performance` proviene de cobertura parcial del analizador estático (mismo caso que fundamentals, loaders y react-three-fiber en S-01), no de hallazgos. Resultado: las cuatro skills quedan por debajo del umbral de 51 y se copian a `skills/`, con sincronización hacia `.claude/skills/` y `.opencode/skills/`. Se usan en la fase 7a (fidelidad 3D de la moto).
