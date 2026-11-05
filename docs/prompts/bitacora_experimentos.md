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

## R-01 · Redacción del registro histórico del rastreo Bronze (2026-11-05)

Archivo: `data/bronze/manifiesto.jsonl` (75 registros de rastreo real). Cada registro conserva el
`agente_usuario` con el que se realizó la petición, que incluía una sigla institucional. Para mantener
veraz el registro histórico, **no se normalizó** el User-Agent: solo se sustituyó la sigla por
«[institución omitida]» dentro del campo `agente_usuario`, y el resto del texto y de cada registro
permanece igual (se verificó, registro por registro, que `agente_usuario` es el único campo que difiere).
A partir de esta fecha el rastreador usa `FNA-KB/1.0 (+https://github.com/JulianReneMunoz/fabrica-nacional-autopartes)`,
que sigue siendo identificable. Tipo de cambio: redacción de un dato personal/institucional en un registro
histórico, no corrección de datos.

## S-03 · Auditoría de skills de terceros para el pulido visual (2026-11-05)

Procedimiento: `fna-seguridad`, paso 5. Herramienta: SkillSpector v2.12.0 (`skillspector scan <ruta> --no-llm --format markdown`) sobre clones superficiales en carpeta temporal. Criterio de rechazo: puntuación ≥ 51.

| Skill | Origen | Puntuación | Recomendación | Hallazgos | Cobertura | Resultado |
|---|---|---|---|---|---|---|
| frontend-design | anthropics/claude-plugins-official, `plugins/frontend-design` (el marketplace de anthropics/claude-code ya no contiene la carpeta y remite a este repositorio) | 13/100 | SAFE | 1 (AR2, `SKILL.md:69`, confianza 55 %) | 100 % | instalada |
| data-visualization | anthropics/knowledge-work-plugins, `data/skills/data-visualization` | 0/100 | SAFE | 0 | 100 % | instalada |
| anatomy | wheresryan22/anatomy | 100/100 | DO NOT INSTALL (CRITICAL) | 546 MEDIUM (MP2), 43 HIGH (AE1, artefactos referenciados sin inspección completa), 12 HIGH (P6), 7 HIGH (SC3), 1 HIGH (AS1, `README.md:173`) y otros de severidad media | 41,7 % | **rechazada, no se instala** |

Revisión manual: el hallazgo AR2 de frontend-design es un falso positivo (la línea trata del tono de los mensajes de error y de las pantallas vacías). Los 546 hallazgos MP2 de anatomy se concentran en los ejemplos generados (25 MB) y los 43 AE1 son límites del analizador (cobertura parcial: 91 casos `static_parse_limit`), pero la puntuación supera el umbral y la recomendación es no instalar; además, el repositorio contiene 59 scripts, un kit de Node y ejemplos de gran tamaño que no se justifican como referencia. Resultado: `frontend-design` y `data-visualization` se copian a `skills/` y se sincronizan con `.claude/skills/` y `.opencode/skills/`; `anatomy` no se copia. El método Anatomy sigue cubierto por la skill propia `fna-maquinas-anatomia`.

## E-04 · Revisión crítica independiente de la motocicleta (2026-11-05)

Revisor independiente (solo lectura) sobre la máquina `moto_honda`: pruebas en navegador de todos los controles y
estados, contraste entre `moto.ts`, `fisica_moto.py` y `referencia_moto.json`, comprobación de restricciones
(sin logotipos, validación en el backend, capas, hashes del freno) y revisión de la calidad de las pruebas.
Resultado: las verificaciones automáticas pasaban, pero el modelo, los números y la imagen no contaban siempre la
misma historia.

### Hallazgo H-03 (corregido antes de continuar)

| Id | Severidad | Hallazgo | Corrección |
|---|---|---|---|
| A1 | crítico | La cifra de potencia con unidad sin confirmar aparecía en la aplicación (ficha, pendientes y FAQ). | Se retiró del YAML y de las respuestas; solo queda como comentario; prueba que falla si reaparece. |
| A2-A4 | importante | Saltos de velocidad: cambiar de marcha, pasar a neutro y soltar el freno recalculaban la velocidad de golpe. | Velocidad como variable de estado continua (`paso_moto`); las rpm se derivan de la velocidad; casos nuevos en `referencia_moto.json`. |
| A5 | importante | «BLOQUEADA» y fuerzas de frenado visibles sin frenar o con la moto detenida. | Valores «previstos» hasta frenar; sin bloqueo con velocidad nula (también en el backend). |
| A6 | importante | La STD calculaba un disco trasero que la ficha no publica. | Marcado como supuesto didáctico y alineado el cliente con el servidor. |
| A7 | importante | El freno delantero usaba el radio de la llanta trasera. | Radio de la llanta delantera en Python y TypeScript. |
| A8-A10 | importante | El limitador no cortaba la chispa en la escena; la etiqueta de cilindrada presentaba un supuesto como dato de ficha; la cámara lenta mezclaba dos bases de tiempo. | Chispa intermitente con limitador; rótulo «150 cm³ nominal — supuesto didáctico»; escala de tiempo rotulada. |
| A11-A18 | menor | Radios de cadena distintos entre física y geometría, textos de estado, CBS que se reactivaba solo, entre otros. | Corregidos. |
| D | pruebas | Pruebas tautológicas o débiles (FAQ sin clic real, CBS sin reparto, relación de cadena fija). | Rehechas; el end-to-end ya no sobrescribe imágenes versionadas. |

Los defectos visuales (etiquetas solapadas a 1280×800, insignia partida, captura sin FAQ, despiece, piezas
flotando) pasaron a las fases 7a y 7b. Verificación posterior: los hashes del freno no cambiaron en ninguna fase.
