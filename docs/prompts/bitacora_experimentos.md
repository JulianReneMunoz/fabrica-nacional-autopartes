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

## S-04 · Auditoría de la skill de terceros Archify para los diagramas del README (2026-11-05)

Procedimiento: `fna-seguridad`, paso 5. Herramienta: SkillSpector v2.12.0 (`skillspector scan <ruta> --no-llm --format markdown`) sobre un clon superficial de `tt-a1i/archify` (carpeta de la skill, 206 archivos y 18 MB). Criterio de rechazo: puntuación ≥ 51.

| Skill | Puntuación | Recomendación | Hallazgos principales | Cobertura | Resultado |
|---|---|---|---|---|---|
| archify | 100/100 (CRITICAL) | DO NOT INSTALL | 36 HIGH AE1 (artefactos referenciados sin inspección completa), 16 HIGH YR4 (regla YARA de envenenamiento de metadatos de herramientas, p. ej. `assets/template.html:146`), 1 HIGH AR2 (`references/delivery-contract.md:493`), 1 HIGH AE3 (bytes NUL en `renderers/shared/diagnostics.mjs:37`) y 69 de severidad baja o media | 18,4 % | **rechazada, no se instala** |

El análisis fue parcial (185 excepciones por límite de tiempo de ejecución del analizador), pero la puntuación supera el umbral y la recomendación es no instalar. Decisión: los diagramas del README se elaboran con Mermaid, que GitHub renderiza de forma nativa y no requiere instalar herramientas de terceros. Los diagramas viven en `docs/arquitectura/diagramas/` (Markdown con bloques `mermaid`) y se incrustan en el README. No se generan HTML interactivos ni SVG exportados con variantes clara y oscura, porque dependían de Archify.


## S-05 · Excepción documentada: Engram v3.6.2 (memoria persistente) (2026-11-06)

Procedimiento: `fna-seguridad`, paso 5. Herramienta: SkillSpector v2.12.0 (`skillspector scan <ruta> --no-llm --format markdown`) sobre un clon de `Gentleman-Programming/engram` (HEAD `a957599`). Criterio de rechazo: puntuación ≥ 51. Excepción autorizada por el usuario para el plugin y el binario, solo en la versión fijada, con las condiciones de la ADR-018.

| Alcance | Puntuación | Hallazgos | Resultado |
|---|---|---|---|
| Skill `plugin/claude-code/skills/memory` | 0/100 | ninguno | aprobada |
| Plugin `plugin/claude-code` (scripts de hooks) | 71/100 | 2 HIGH TM1 (`scripts/session-start.sh:110`), 6 MEDIUM E1, 1 MEDIUM BH1 | **excepción** |
| Repositorio completo (1 082 componentes) | 100/100 (CRITICAL) | 416 hallazgos: 57 HIGH SC9, 31 HIGH PE3, 20 HIGH AS1, 15 HIGH TM1, 8 HIGH AR2, 7 HIGH P6, 6 HIGH MP3 y otros menores | **excepción** (solo se usa el binario y el plugin de Claude Code) |

Análisis manual:
- **TM1 `session-start.sh:110`:** manejo de un bloqueo de importación con `mkdir`/`rmdir`/`rm -f` sobre un directorio de bloqueo propio del plugin; no ejecuta entrada externa.
- **E1 / scripts de hooks:** llamadas `curl` al servidor local de Engram (127.0.0.1) para registrar sesión, prompts y fin de sesión. Implican que los prompts del usuario llegan al servidor local de Engram; no salen de la máquina.
- **SC9 (57):** archivos bajo carpetas ocultas (`.github/scripts`, `.github/workflows`) marcados como «artefacto oculto»; son scripts de CI del proyecto, no se instalan.
- **PE3 (31) y AR2 (8, parte):** volcados de memoria del propio desarrollo en `.engram/chunks/*.jsonl.gz` y documentación que menciona rutas de credenciales o frases de «no rechazar»; texto de datos, no código que se ejecute.
- **AS1 (20), AS2 (3), MP3 (6):** `internal/setup` y pruebas que leen o escriben la configuración de otros agentes; es el propósito de `engram setup <agente>`, que **no** se ejecuta para Claude Code. La manipulación de memoria es la función de la herramienta.
- **TM1 (15), TM2 (3), P6 (7), P2 (1), E2 (3), YR4 (2), AR3 (1):** código del almacén SQLite, consultas del panel en la nube (`internal/cloud`, no usado), pruebas, `pico.min.css` y el plugin `plugin/pi` (no instalado).
- No apareció ningún hallazgo grave fuera de estas categorías ya analizadas.

Versión fijada y verificación de integridad:
- Release oficial `v3.6.2`, Windows amd64. SHA-256 del zip: `2e1b2355ce6e21c14733e3dd7736a88a729f84fa9ec26f0f87747e71922a4491` (coincide con `checksums.txt` del release).
- SHA-256 de `engram.exe`: `59b3468a33e4b07d5bfbc3bb5ba8cf59220c9408fc02478c6cbb1ed161f0c973`; `engram version` → `engram 3.6.2`.
- Ruta: `%LOCALAPPDATA%\engram\bin` (añadida al PATH de usuario). Sin permisos globales añadidos; el plugin lo instala el usuario con `claude plugin marketplace add Gentleman-Programming/engram` y `claude plugin install engram`.
- Cualquier actualización exige repetir este análisis.


## S-06 · Excepción documentada: GGA v2.10.1 (Gentleman Guardian Angel) (2026-11-06)

Procedimiento: `fna-seguridad`, paso 5, con SkillSpector v2.12.0 sobre `Gentleman-Programming/gentleman-guardian-angel`. Criterio de rechazo: puntuación ≥ 51. Excepción autorizada por el usuario solo para la versión fijada.

| Herramienta | Puntuación | Hallazgos principales | Resultado |
|---|---|---|---|
| gentleman-guardian-angel (73 hallazgos) | 100/100 | 12 HIGH SC2 (descarga de scripts externos), 6 HIGH TM1, 4 HIGH PE3, 1 HIGH TM2, 1 HIGH YR1 y 49 MEDIUM | **excepción** |

Análisis manual:
- **SC2 (12):** `curl … | sh` aparece en `.github/workflows/ci.yml:48` (instalación de ShellSpec en CI del proyecto), `release.yml:29`, y como **texto de ayuda** en `lib/providers.sh:82` (instrucciones para instalar Cursor Agent) y en la documentación. Ningún flujo de `install.sh` ni de `bin/gga` descarga o ejecuta scripts remotos.
- **YR1 `README.md:79`:** coincidencia con la regla de persistencia por el comando de instalación que añade `PATH` a `~/.bashrc`; `install.sh` no modifica `~/.bashrc` (solo lo sugiere).
- **TM1 / TM2 / PE3:** líneas de documentación, `Makefile` y pruebas ShellSpec (`spec/`) sin ejecución en la instalación.
- **Código revisado a mano (`install.sh`, `bin/gga`, `lib/*.sh`):** `install.sh` copia `bin/gga`, `lib/providers.sh`, `cache.sh` y `pr_mode.sh` a `%USERPROFILE%\bin`, crea `gga.bat`, ajusta `VERSION` y `LIB_DIR` con `sed` y no cambia el PATH. En tiempo de uso, `gga run` envía el diff preparado y `AGENTS.md` a `claude --print` y consulta `api.github.com/repos/.../releases/latest` (2 s) para el aviso de versión.

Versión fijada:
- Tag `v2.10.1` = commit `1124c3672f082c56b033c4e23a30e95d0e8cd593` (el que se instala). El análisis se hizo sobre `fbf1091da170a33d42cb97577a9813e652e98a4a` (HEAD de `main`, un commit posterior que solo cambia `.github/workflows/release.yml`); `git diff 1124c36 fbf1091 -- install.sh bin lib` está vacío, por lo que el código instalado es idéntico al revisado.
- `gga version` → `gga v2.10.1`. Hook `pre-commit` instalado con `gga install` (en `.git/hooks`, no versionado); configuración versionada en `.gga` (sin secretos).
- Prueba del hook: commit de un archivo `.py` pequeño en una rama temporal (descartada): revisión `PASSED` en 19 s.
- Cualquier actualización exige repetir este análisis.


## S-07 · Archify: nueva revisión de la instalación de usuario y decisión de no usarla (2026-11-06)

Procedimiento: `fna-seguridad`, paso 5, con el criterio de excepción aplicado a Engram y GGA (S-05, S-06): la
herramienta solo se usa si nada ejecutable toca red, credenciales o persistencia fuera de su carpeta.

- **Instalación revisada:** `~/.agents/skills/archify` (`~/.claude/skills/archify` es un enlace simbólico a ella),
  idéntica archivo por archivo a la carpeta `archify/` de `github.com/tt-a1i/archify` en el commit
  `edf158c4e7a1d18d20cc329840f864289634c090` (2026-10-25; `package.json` declara 3.2.0, posterior al tag `v3.2.0`).
- **SkillSpector v2.12.0 (`--no-llm`):** 100/100, «DO NOT INSTALL», 154 hallazgos sobre 206 componentes, cobertura del
  18 %. Hallazgos altos: 36 AE1 (límites del analizador sobre `bin/*.mjs`, `renderers/` y `explainer/`), 16 YR4
  (fuente WOFF2 en base64 dentro de `@font-face` en `assets/template.html:146` y 15 ejemplos: falso positivo),
  1 AR2 (`references/delivery-contract.md:493`, documentación: falso positivo) y 1 AE3 (separador NUL de una clave de
  deduplicación en `renderers/shared/diagnostics.mjs:37`).
- **Revisión manual del código ejecutable (104 archivos):** `renderers/shared/brand-marks.mjs` descarga logotipos por
  HTTPS cuando un diagrama declara una marca remota (con filtros contra credenciales e IP privadas);
  `bin/preview.mjs` abre un servidor HTTP en `127.0.0.1`; `bin/open-artifact.mjs` abre el navegador; la skill crea
  carpetas `.archify/` en el directorio de trabajo. No lee credenciales ni usa `eval`.
- **Decisión:** hay código ejecutable con acceso a red y persistencia fuera de su carpeta, por lo que **no se usa**.
  Los diagramas del README siguen en Mermaid (`docs/arquitectura/diagramas/`), que GitHub renderiza de forma nativa en
  tema claro y oscuro. La instalación de usuario no se modifica; retirarla queda a decisión del usuario.


## W-01 · Búsqueda web complementaria fuera de la evaluación (2026-11-06)

La búsqueda web con Claude (ADR-019) no forma parte del banco de 24 preguntas ni de las métricas v1–v3: los resultados
de esta bitácora siguen midiendo solo la base verificada. P24 (inyección) se bloquea antes de buscar y la búsqueda
nunca se ejecuta sin una acción explícita. Las pruebas usan un buscador simulado, sin red.


## R-02 · El HTML crudo de Bronze deja de versionarse (2026-11-07)

Los 75 HTML de `data/bronze/html/` (5,0 MB) son copias literales de páginas de terceros (sitios oficiales de
Fanalca) y no hace falta versionarlos: se regeneran con `uv run fabrica pipeline`, que respeta `robots.txt`,
`Crawl-delay` y los dominios permitidos. Se retiran del índice con `git rm --cached` y se ignoran
(`data/bronze/html/` en `.gitignore`); siguen en el disco local (75 archivos antes y después). Siguen versionados
`manifiesto.jsonl`, `errores.jsonl` y `resumen_rastreo.json` (procedencia y métricas del rastreo) y la base Gold.

Como un clon nuevo trae el manifiesto sin el HTML, `construir_base` ahora informa «Bronze sin HTML en disco» con las
alternativas (`fabrica pipeline` o `--fuente semilla`) en lugar de fallar con `FileNotFoundError` o de reemplazar en
silencio la base Gold. El historial anterior conserva los HTML; quitarlos de ahí exige una decisión aparte
(repositorio privado o `git filter-repo` con push forzado).


## R-03 · Flujo de trabajo con pull requests (2026-11-07)

Los 42 commits anteriores entraron a `main` con push directo y el repositorio no tenía pull requests. Desde la rama
`chore/flujo-pull-requests`, primer PR del repositorio, todo cambio entra por PR con el CI en verde y squash merge
(ADR-021). El flujo `CI` ya se disparaba con `pull_request` además de `push` a `main`, así que no cambia. Checks
obligatorios: `calidad-y-pruebas (ubuntu-latest)`, `calidad-y-pruebas (windows-latest)` y `visor-web`. Se agregan
`.github/pull_request_template.md`, `CONTRIBUTING.md` y la regla de ramas en `AGENTS.md` (archivo de reglas de GGA).
No se crean PR retroactivos para los commits anteriores.


## R-04 · Makefile y Ollama pospuesto (2026-11-07)

El repositorio no tenía `Makefile` (`git ls-files` sin coincidencias). Se crea con los objetivos `help` (por
defecto), `instalar`, `calidad`, `pruebas-web`, `api`, `app`, `pipeline`, `validar-moto`, `enlaces` y `graphify`,
equivalentes a `scripts/*.ps1`. Las recetas usan solo `uv run --no-sync ...` y `cd web && ...`, válidos en sh y en
cmd; `help` usa `$(info)` para no depender del shell. `graphify` llama a `scripts/graphify_codigo.py`, que aplica el
modo de la ADR-020 (copia temporal sin pruebas, `--code-only`, `GRAPHIFY_BACKEND=none`) y rechaza una salida dentro
del repositorio.

Verificación con GNU Make 4.4.1: `make help` y `make -n` en los 10 objetivos (Git Bash); `make help`,
`make validar-moto` («Ensamblaje íntegro»), `make enlaces` (0 enlaces rotos) y `make pruebas-web` (113 pruebas) desde
PowerShell; `make graphify` reprodujo S-08 (113 archivos, 1252 nodos, 3492 aristas). `pipeline` no se ejecutó
(requiere red y aprobación).

Ollama queda pospuesto (ADR-022): sin objetivo en el `Makefile`, sin instalación y sin dependencias nuevas. La
auditoría de entregables del curso marcó como faltantes de la Fase 1 los embeddings (C6), el índice vectorial (C7)
y el modelo de embeddings descargado (C1), y de la Fase 2 el agente con `create_agent` (C5) y la memoria
(`InMemorySaver`, `thread_id`, `trim_messages`). El retiro del proveedor `ollama` del código queda para un PR aparte.


## S-08 · Excepción documentada: Graphify (graphifyy 0.9.102) para el mapa del código (2026-11-07)

Procedimiento: `fna-seguridad`, paso 5. Herramienta: SkillSpector v2.12.0 (`--no-llm`) sobre el paquete instalado
con `uv tool` (`graphifyy==0.9.102`, `%APPDATA%\uv\tools\graphifyy\Lib\site-packages\graphify`). Criterio de rechazo:
puntuación ≥ 51. Excepción por revisión manual aprobada por el usuario, solo para la versión fijada y el modo de uso
descrito en la ADR-020.

| Alcance | Puntuación | Hallazgos | Cobertura | Resultado |
|---|---|---|---|---|
| Paquete `graphify` (239 componentes) | 100/100 (CRITICAL) | 148 HIGH (59 TM1, 33 AR2, 23 PE3, 6 SC8, 5 SC9, 4 RA1, 4 SSRF1, 3 E2, 3 AS1 y otros 8), 163 MEDIUM, 2 LOW | 87,6 % | **excepción** |

Análisis manual de los hallazgos altos:
- **TM1 (59) y AR2 (33, en su mayoría):** `skill*.md`, `skills/*/references/*.md` y textos de ayuda; son las skills que
  `graphify install` copiaría a la configuración de los agentes. No se instalan ni se ejecutan.
- **PE3 (23):** `detect.py:140` y extractores: patrones que **excluyen** archivos sensibles (`id_rsa`, `.npmrc`,
  `.git-credentials`) del análisis; no leen credenciales.
- **SC8/SC9 (11):** `__pycache__/*.pyc` compilados en esta máquina por `uv` al instalar (no figuran en el `RECORD` del
  paquete).
- **E2 y AST5 (`__main__.py:782`, `:805`):** el proceso se relanza a sí mismo con `PYTHONHASHSEED=0` para que la salida
  sea reproducible; `detect.py:1413` ejecuta `git ls-files` con el entorno heredado.
- **SSRF1 (4), `llm.py:3390` y `security.py:169`:** protecciones contra direcciones de metadatos de la nube y contra
  DNS rebinding en `safe_fetch`.
- **AS1 (`install.py:251`), RA1, TM1 (`hooks.py:481`):** instalación en carpetas de agentes, `CLAUDE.md` y hooks de Git;
  esos comandos (`install`, `claude install`, `hook install`) no se ejecutan, para no tocar `.claude/` ni el hook de GGA.
- **Red:** solo `llm.py` (APIs de proveedores LLM y CLI de Claude) y `security.py` (`add <url>`); el modo usado no los
  invoca. Sin telemetría (`querylog.py` desactivado por omisión).

Modo de uso aprobado: `graphify extract <copia del código> --code-only --out <carpeta temporal>` con
`GRAPHIFY_BACKEND=none` (sin LLM, sin red), sobre una copia de solo `.py`, `.ts` y `.tsx` de `src/` y `web/src/` (sin
pruebas, datos, documentos, `.env`, `.claude`, `node_modules`, `.venv` ni `dist`). La salida se genera fuera del
repositorio; solo se versionan el SVG y el informe depurados. Cualquier actualización exige repetir la revisión.

Resultado (2026-11-07): 113 archivos (70 `.py`, 16 `.ts`, 27 `.tsx`), 1252 nodos, 3492 aristas y 52 comunidades,
detectadas con Louvain de `networkx` (Leiden requiere `graspologic`, que no está instalado). `graphify export svg`
requiere `matplotlib` y `scipy`, ausentes en el entorno de la herramienta; en lugar de instalarlos, la vista
`docs/imagenes/mapa_codigo.svg` agrupa `graph.json` por paquete (18 módulos, 51 pares con dependencias) con el
`matplotlib` del proyecto. La salida no contiene rutas absolutas, nombres de usuario, correos ni secretos.


## S-09 · `trust_remote_code` de nomic-embed-text-v1.5 con revisión fijada (2026-11-07)

`nomic-ai/nomic-embed-text-v1.5` declara en `config.json` un `auto_map` hacia
`nomic-ai/nomic-bert-2048--modeling_hf_nomic_bert.NomicBertModel`: cargarlo con `trust_remote_code=True` ejecuta
código Python descargado de Hugging Face. Medidas (ADR-023):

| Repositorio | Revisión fijada | Archivo | SHA-256 |
|---|---|---|---|
| `nomic-ai/nomic-embed-text-v1.5` | `e9b6763023c676ca8431644204f50c2b100d9aab` | `model.safetensors` (546 938 168 bytes) | — |
| `nomic-ai/nomic-bert-2048` | `7710840340a098cfb869c4f65e87cf2b1b70caca` | `configuration_hf_nomic_bert.py` | `f7871694b8de3d3df4ac6640313d5799ce323261a0fb90c5cc567ecc34a0039e` |
| `nomic-ai/nomic-bert-2048` | `7710840340a098cfb869c4f65e87cf2b1b70caca` | `modeling_hf_nomic_bert.py` | `3b24a366c4cc31b869466ccfb7bbb8879e138c97f8de06c83d4fa1e31a21f149` |

- La revisión del modelo se pasa en `revision` y la del código remoto en `code_revision` (`model_kwargs` y
  `config_kwargs`); el módulo cargado queda en
  `~/.cache/huggingface/modules/transformers_modules/nomic_hyphen_ai/nomic_hyphen_bert_hyphen_2048/7710840340…`.
  Sin las revisiones fijadas, `EmbeddingsNomic` se niega a cargar.
- Revisión manual de los dos `.py` antes del primer uso: solo importan `torch`, `transformers`, `einops`,
  `safetensors` y bibliotecas estándar (`megablocks`, opcional y no instalado); sin `subprocess`, sockets, `eval` ni
  `exec`. `torch.load` (pickle) solo se usa si existe `pytorch_model.bin`, que la revisión fijada no publica (solo
  `model.safetensors`).
- Sin red por omisión: `local_files_only=True`; la descarga se hace solo con `fabrica indexar-vectores --descargar`
  (la descarga inicial se hizo una vez, con aprobación, el 2026-11-07, con `EmbeddingsNomic(solo_local=False)`). El modelo es público: `HF_TOKEN` no es necesario.
- Incompatibilidad encontrada: con `sentence-transformers` 6.2.0 y `transformers` 5.22.2, el código remoto falla
  (`'NomicBertModel' object has no attribute 'get_extended_attention_mask'`). La revisión fijada es la última del
  repositorio (2025-04-29); se fijan `sentence-transformers==5.7.0` y `transformers==4.57.6` en lugar de modificar el
  código de terceros.

Instalación (`uv sync --extra semantica-gpu`, índice `pytorch-cu130`): `torch==2.14.1+cu130` (descarga de 1,9 GiB),
verificado con `torch.cuda.is_available()` = `True`, `NVIDIA GeForce RTX 5070 Ti Laptop GPU` y `sm_120` en
`get_arch_list()`. `.venv` pasa de 684 a 4135 MiB (+3451 MiB; `torch`, 2934 MiB); modelo, 523 MiB en la caché de
Hugging Face; índice `data/vectores/`, 3,3 MiB. La variante `semantica-cpu` se comprobó solo por resolución
(`uv sync --extra semantica-cpu --dry-run`: reemplaza `torch==2.14.1+cu130` por `torch==2.14.1+cpu`). El servidor MCP
en ejecución bloquea `fabrica-mcp.exe`, así que la instalación se completó con `--no-install-project --inexact`.


## E-05 · Experimento C6: prefijos `search_query` y `search_document` (2026-11-07)

Archivo: `evaluacion/resultados/20261107T202956Z_prefijos_c6.md` (`EMBEDDINGS_DEVICE=auto` → `cuda`). Se eligen tres
pares consulta–fragmento con relevancia exclusiva (cada fragmento es relevante solo para su consulta dentro del trío)
y al menos dos hechos presentes. Un primer intento con P01–P03 fijas se descartó: P02 no tiene fragmento relevante y
P03 y P04 comparten fragmentos, de modo que la diagonal no era la única respuesta correcta.

| Consulta | Fragmento | Coseno con prefijos | Coseno sin prefijos |
|---|---|---|---|
| Q1 · ¿Dónde queda la sede principal de Fanalca? (P01) | `contacto-sitio#000` | 0,6672 | 0,6503 |
| Q2 · ¿En qué fecha se constituyó Fanalca? (P03) | `inicio#000` | 0,6873 | 0,6099 |
| Q3 · ¿Qué cubre la Garantía Total Verdadera de Honda Autos? (P09) | `negocios-holda-autos#000` | 0,7673 | 0,7817 |

| Variante | Diagonal media | Fuera de la diagonal | Margen | Aciertos top-1 |
|---|---|---|---|---|
| Con prefijos | 0,7073 | 0,5968 | 0,1105 | 3/3 |
| Sin prefijos | 0,6806 | 0,5655 | 0,1151 | 2/3 |

Con prefijos, cada consulta queda más cerca de su fragmento que de los otros dos (3/3). Sin prefijos, Q2 queda más
cerca de `contacto-sitio#000` (0,6461) que de su fragmento (0,6099). Los prefijos elevan todas las similitudes, por lo
que el margen medio casi no cambia; con 3 pares el resultado es ilustrativo, no estadístico. El índice usa siempre
prefijos, como indica el modelo.


## E-06 · Recuperadores: BM25 frente a semántico (nomic + Chroma) y tiempos por dispositivo (2026-11-07)

Archivo: `evaluacion/resultados/20261107T202956Z_recuperadores.md`. Banco de 24 preguntas; se evalúan las 19
`respondible` y se excluyen P02, P07 y P08 por no tener fragmento relevante en Gold (16 evaluadas). Relevante:
fragmento con al menos `minimo` de los `hechos` de la pregunta (criterio aprobado).

| Recuperador | hit@3 | hit@5 | MRR@10 | Rango 1 |
|---|---|---|---|---|
| BM25 (expansión de consultas) | 0,8125 | 0,9375 | 0,7646 | 11/16 |
| Semántico (nomic + Chroma) | 0,8125 | 0,8750 | 0,8281 | 13/16 |

- El semántico sube al rango 1 P11, P15 y P19 (BM25: 5, 5 y 3), pero no encuentra P01 (dirección de la sede, que BM25
  resuelve en el rango 1) y baja P03 del rango 2 al 4. Ninguno encuentra P18.
- Decisión: **BM25 sigue por defecto**. El semántico gana en MRR y pierde en hit@5, con 16 preguntas; la diferencia
  no basta para cambiar. La complementariedad sugiere una recuperación híbrida como siguiente experimento.
- Limitación del criterio: los hechos numéricos cortos coinciden por azar (por ejemplo, «450» en un fragmento sobre el
  bus a hidrógeno), lo que puede marcar como relevantes fragmentos que no responden.

Tiempo de indexación de los 167 fragmentos (codificación y carga en Chroma; 1 ejecución de calentamiento descartada,
3 repeticiones, mediana; la carga del modelo se mide aparte):

| `EMBEDDINGS_DEVICE` | Carga del modelo (s) | Repeticiones (s) | Mediana (s) |
|---|---|---|---|
| `cpu` | 1,826 | 30,168 · 16,473 · 16,226 | 16,473 |
| `cuda` (RTX 5070 Ti Laptop GPU, CUDA 13.0) | 2,218 | 1,136 · 1,172 · 1,160 | 1,160 |

La GPU indexa unas 14 veces más rápido. En CPU, la primera repetición después del calentamiento fue más lenta
(30,2 s), probablemente por la frecuencia del procesador o por la memoria; la mediana la descarta. Ambas mediciones
usan el mismo `torch==2.14.1+cu130`.
