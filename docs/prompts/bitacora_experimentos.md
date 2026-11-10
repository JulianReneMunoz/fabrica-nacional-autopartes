# Bitácora de experimentación con prompts

Protocolo: mismo banco de 24 preguntas (`evaluacion/preguntas.yaml`), misma base Gold, temperatura configurada
0,1 hasta E-06 y 0 desde E-07 (`claude_code` no la aplica; ver E-07), una variable cambiada por experimento.
Métricas definidas en `services/evaluacion.py`.
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


## E-07 · Temperatura 0 por defecto y repetición de v3 con `claude_code` (2026-11-07)

Decisión (C4): `temperatura` pasa de 0,1 a 0 en `core/config.py`, para que la salida sea lo más determinista posible.
La aplican `ollama`, `anthropic` y `openai` (salvo los modelos de razonamiento que solo aceptan el valor por
defecto); **`claude_code` no la aplica**, porque la CLI `claude -p` no tiene esa opción, y `extractivo` no es un LLM.
Cada informe registra ahora `temperatura`, `temperatura_aplicada` (`llm.proveedores.aplica_temperatura`),
`recuperador` y las fuentes citadas por pregunta. `.env.example` todavía declara `FNA_TEMPERATURA=0.1` y debe
actualizarse a mano (el archivo no es editable desde la sesión de agentes); la ejecución de esta entrada registró
0,0, es decir, el entorno local no la sobrescribe.

Repetición con la misma configuración (`claude_code` / `sonnet` / v3 / modo `auto` / BM25), aprobada por el usuario.
Como la temperatura no llega al modelo, la diferencia mide la **variabilidad entre ejecuciones**, no el efecto de T:

| Métrica | 20261107T013627Z (T configurada 0,1) | 20261107T224737Z (T configurada 0) |
|---|---|---|
| Exactitud en respondibles | 0,789 | 0,789 |
| Cobertura del contexto | 0,842 | 0,842 |
| Rechazo correcto | 1,0 | 0,8 |
| Tasa fundamentada | 0,842 | 0,789 |
| Exactitud global | 0,833 | 0,792 |
| Latencia media | 5326 ms | 5039 ms |

Cambiaron 2 de 24 preguntas, con las mismas fuentes recuperadas:
- **P20 (ausente, horario de atención):** antes, la frase de rechazo fija; ahora, «La información publicada no incluye
  el horario de atención…» más dirección, teléfono y correo. No inventa el horario, pero incumple la frase fija y
  cuenta como fallo (rechazo correcto 1,0 → 0,8).
- **P01 (sede):** sigue acertando los 4 hechos, pero añade «El contexto no indica explícitamente cuál es la "sede
  principal"…», lo que baja el puntaje automático de fundamentación por debajo del umbral (0,842 → 0,789).

Conclusión: con `claude_code`, dos ejecuciones idénticas difieren en 1 de 24 aciertos; la cifra de E-01 a E-03 tiene
ese margen de variación. Medir el efecto real de T exige un proveedor que la aplique (`anthropic` con clave de API u
`ollama`, pospuesto en la ADR-022). Las cuatro preguntas representativas están en la
[tabla Q1–Q4](../evaluacion/tabla_q1_q4.md).


## A-01 · Agente con memoria, probado con un modelo simulado (2026-11-07)

Implementación de la Fase 2 (ADR-024): `create_agent` (`langchain==1.4.9`) con la herramienta tipada
`buscar_fragmentos`, prompt de sistema `llm/prompts/agente.yaml` v1, `InMemorySaver` (`langgraph==1.2.20`) por
`thread_id` y recorte con `trim_messages` en un middleware. Proveedores `ollama` (`qwen3:8b`, solo hosts locales) y
`anthropic` (`claude-haiku-5-5`, clave `FNA_ANTHROPIC_API_KEY`), sin respaldo automático entre ellos.

Hecho (con un modelo simulado que emite `tool_calls`, sin red ni clave; `tests/unit/test_agente.py` y
`tests/integration/test_api_agente.py`, 41 pruebas):
- la herramienta rechaza `k` fuera de 1–10, consultas vacías y recuperadores desconocidos (`ValidationError`);
- el agente llama a la herramienta y la respuesta cita la URL; sin evidencia, la frase de rechazo fija;
- anclaje exigido por el código (hallazgo de GGA en el primer intento de commit): una respuesta sin llamar a la
  herramienta o sin citas válidas se reemplaza por la frase de rechazo, y las URL o ids inventados se retiran del
  texto; el contenido de cada `<fragmento>` se escapa; `FNA_AGENTE_MAX_HILOS` acota los hilos en memoria. El
  anclaje no depende solo del prompt: lo exige el código. Por eso una pregunta sobre la conversación misma («¿cuál
  fue mi pregunta anterior?») recibe la frase de rechazo, y la memoria se comprueba con un seguimiento que exige
  buscar («¿y cuál es su teléfono?»), en la prueba simulada y en la prueba real opcional;
- memoria: el segundo turno del mismo `thread_id` recibe el historial y otro `thread_id` no;
- recorte: con un límite de 200 tokens, lo enviado al modelo empieza en la última pregunta y sin resultados de
  herramienta huérfanos, mientras el estado guardado conserva los 16 mensajes;
- la pregunta de inyección del banco (P24) se bloquea sin llamar al modelo y sin guardarse en la memoria;
- el razonamiento (bloques `reasoning` o etiquetas `<think>`) nunca aparece en la respuesta;
- el límite de iteraciones devuelve un mensaje propio, no la frase de rechazo, y deja el hilo utilizable;
- errores: falta de clave u Ollama inaccesible → mensaje con la instrucción y 503; un 401 o saldo agotado de
  Anthropic → «clave FNA_ANTHROPIC_API_KEY inválida o sin créditos», distinto de «no respondió»; `thread_id` o
  pregunta inválidos → 422.

`fabrica agente --verificar` en este equipo: «No disponible: Ollama no responde en http://localhost:11434…». La
prueba con modelo real (`tests/integration/test_agente_real.py`) es opcional (`FNA_PRUEBAS_AGENTE_REAL=1`) y quedó
omitida.

Pendiente:
1. Activar un proveedor (Ollama con `qwen3:8b` o `FNA_ANTHROPIC_API_KEY`) y ejecutar la demostración real
   (`make agente`), con la prueba opcional.
2. Evaluar el agente con el banco de 24 preguntas y compararlo con el Q&A (E-01 a E-07), con el mismo criterio de
   aciertos y rechazos.
3. Para un despliegue con varios workers o persistente, reemplazar `InMemorySaver` por `SqliteSaver` o
   `PostgresSaver`.


## S-10 · Endurecimiento de `claude -p` (2026-11-08)

Revisión de `llm/claude_code.py` (proveedor `claude_code` del Q&A): el comando era
`claude -p … --output-format json --model … --max-turns 1` en una carpeta temporal vacía; **no desactivaba las
herramientas propias de Claude Code** (Read, Glob y Grep no piden permiso) y cargaba la configuración, los hooks, los
plugins, los servidores MCP y el CLAUDE.md del usuario. Riesgo: inyección indirecta desde un fragmento o una página
que pida leer archivos locales.

Decisión (ADR-025), con flags verificados en `claude --help` de Claude Code 2.1.319:
- Q&A: `--tools ""`, `--strict-mcp-config`, `--safe-mode`, `--restricted`, `--permission-prompts none` y
  `--no-session-persistence`.
- Búsqueda web: los mismos salvo `--tools ""` (conserva `--tools WebSearch,WebFetch`) y `--restricted` (según la
  ayuda, quita WebFetch salvo que `--tools` lo nombre; se omite por prudencia).
- Antes de la primera llamada se comprueba con `claude --help` (sin consumir cupo) que la CLI admite los flags; si
  falta alguno, `ErrorProveedorLLM` y no se ejecuta sin aislamiento. `--bare` se descartó: obliga a usar
  `ANTHROPIC_API_KEY` en lugar de la suscripción.

Pruebas sin ejecutar la CLI real (`subprocess.run` simulado, que también responde a `--help`): el comando del Q&A
incluye los seis flags y no incluye `--bare` ni `--mcp-config`; el de la búsqueda web conserva WebSearch y WebFetch con
sus cuatro flags; si la ayuda no lista un flag, o no puede leerse, no se ejecuta `claude -p`; la ayuda se consulta una
sola vez por ejecutable; se conservan la entrada estándar, la carpeta temporal y el timeout.

Verificación real (una sola llamada, aprobada por el usuario): `fabrica ask "¿Dónde queda la sede principal?"
--proveedor claude_code` → «La dirección publicada de Fanalca es Calle 13 # 31A - 80, Urbanización Industrial Acopi,
Yumbo (Valle del Cauca), Colombia…», fuentes `contacto-sitio#000` y `autopartes-contacto#000`, `fundamentada=True`,
modo `seleccion`, 4236 ms, con la CLI instalada como `claude.CMD` (npm, Windows). La combinación de flags funciona,
incluido el argumento vacío de `--tools ""`. La búsqueda web endurecida no se ejecutó con red.

Agente (ADR-024, actualización): Ollama por defecto, Anthropic como segunda opción; `claude_code` no se usa en el
agente. Las cifras de E-01 a E-07 se obtuvieron sin estos flags.


## A-02 · Claude Haiku 5.5 como proveedor principal del agente (2026-11-08)

Decisión del usuario (ADR-026): el agente usa `FNA_PROVEEDOR_AGENTE=anthropic` por defecto con
`claude-haiku-5-5`, pagado con los créditos mensuales de API del plan Max (USD 100), una bolsa aparte que no resta
cupo a Claude Code. Ollama queda como proveedor opcional en el código (no instalado; según el usuario, se probó e
instaló y luego se desinstaló sin usarse); `claude_code` no se usa en el agente (adaptador descartado por frágil).
Sin respaldo automático entre proveedores.

Hecho:
- Valor por defecto `anthropic`; sin clave, el mensaje indica cómo vincular los créditos de Max, crear la clave y
  guardarla como `FNA_ANTHROPIC_API_KEY` (nunca `ANTHROPIC_API_KEY`), y comprobarla con `make verificar-agente`.
  Las pruebas de Ollama fijan ahora su proveedor de forma explícita; una prueba nueva cubre el valor por defecto y el
  mensaje sin clave.
- `docs/arquitectura/modelos.md`: precios de Haiku, Sonnet y Opus 5.5 (consultados en noviembre de 2026), costo
  estimado por turno (≈ USD 0,001 con Haiku y ≈ USD 0,02 con Sonnet, con 3000 tokens de entrada y 300 de salida por
  llamada y 2 llamadas), uso de cada modelo y condiciones de los créditos, con sus fuentes.
- `CONTRIBUTING.md`: activación de Haiku (vinculación de créditos, clave en la Console, `Read-Host
  -AsSecureString` para guardarla sin mostrarla, `make verificar-agente`). La sección ya no documenta Ollama. Se
  corrigió además el texto sobre los créditos de Max, que había quedado sin corregir en `main` porque el PR #6 se
  integró con la versión anterior al `--amend`.

Correcciones tras la revisión de GGA (commit aparte): el docstring de `llm/proveedores.py` describe ahora los
créditos de API (Pro no los incluye; Max y Ultra sí) y los proveedores por defecto (Q&A: `FNA_PROVEEDOR_LLM`;
agente: `anthropic` con Claude Haiku 5.5; Ollama opcional); el mensaje de `ImportError` de `langchain-anthropic` ya
no sugiere `uv sync --extra anthropic` (es dependencia principal) sino sincronizar con `uv.lock`; y el `assert` de
`crear_modelo_agente` pasa a ser un `if` con `ErrorProveedorLLM`, con una prueba que lo confirma también con
`python -O`.

Pendiente:
- La demostración real (tres turnos en un mismo `thread_id`, con tokens, costo y latencia) y la prueba opcional
  `FNA_PRUEBAS_AGENTE_REAL=1`, cuando `make verificar-agente` indique «Disponible» y con aprobación previa del
  gasto de créditos.
- (Nota 3 de GGA) `verificar_proveedor_agente` importa `anthropic` directamente, pero el paquete no está declarado
  en `pyproject.toml`: llega como dependencia de `langchain-anthropic`. Declararlo con su versión o hacer la
  consulta a través del cliente de LangChain. Relacionado: el extra opcional `anthropic` de `pyproject.toml` es
  redundante, porque `langchain-anthropic` ya es dependencia principal.
- (Nota 5 de GGA) En `crear_modelo` (Q&A con `anthropic`), `max_tokens` está fijo en 1024; el agente usa
  `FNA_AGENTE_MAX_TOKENS`. Convertirlo en una constante con nombre o en una configuración.


## A-03 · Pulido de la Fase 3: agente en Streamlit, GitHub Actions y docker-compose (2026-11-08)

**Parte A, pestaña «🤖 Agente» en Streamlit** (`frontend/app.py`, solo a través de `ServicioAsistente`):
`st.chat_message` y `st.chat_input` con el historial de la sesión; `thread_id` único por sesión
(`streamlit-<uuid>`, en `st.session_state`) y botón «Nueva conversación»; el servicio se crea una sola vez
(`st.cache_resource`), así que la memoria del agente persiste entre recargas. Cada respuesta muestra las fuentes
como enlaces seguros (solo `http(s)`), si está fundamentada, proveedor y modelo (`anthropic · claude-haiku-5-5`
por defecto), las llamadas a la herramienta y la latencia (`estilo.respuesta_agente_html`, con el texto escapado).
Al abrir la pestaña se llama a `verificar_agente(consultar=False)`, sin red ni consumo de créditos: sin clave, un
aviso con la instrucción y el chat desactivado; un `ErrorProveedorLLM` al preguntar se muestra como aviso, no como
traza. Pruebas e2e con `AppTest` y el modelo simulado (clave ficticia en el entorno, nunca la de `.env`):
respuesta con fuentes y chips, memoria compartida entre dos mensajes de la sesión, «Nueva conversación» cambia el
`thread_id`, sin clave aviso y chat desactivado, y error del proveedor como aviso.

**Parte B, GitHub Actions** (`.github/workflows/ci.yml`). El último CI de `main` (run 42524024614, commit
`7824354`) emitió dos anotaciones: «Node.js 20 is deprecated… actions/checkout@v4, astral-sh/setup-uv@v6,
actions/setup-node@v4» y «The ubuntu-latest label will migrate to Ubuntu 26 beginning October 19, 2026»
(`actions/runner-images#14748`). Versiones verificadas con `gh api` (`releases/latest`, `git/ref/tags/…` y el
`runs.using` de cada `action.yml`):

| Action | Antes (Node) | Última publicada (fecha) | Después en el workflow (Node) |
|---|---|---|---|
| `actions/checkout` | `v4` (node20) | `v7.0.1` (2026-07-20) | `v7` (node24); la etiqueta `v7` apunta al mismo commit que `v7.0.1` |
| `astral-sh/setup-uv` | `v6` (node20) | `v10.3.3` (2026-10-28) | `v10.3.3` (node24); **no existe la etiqueta móvil `v10`** (`git/ref/tags/v10` → 404), así que se fija la versión exacta |
| `actions/setup-node` | `v4` (node20) | `v7.1.0` (2026-10-08) | `v7` (node24); la etiqueta `v7` apunta al mismo commit que `v7.1.0` |

Los parámetros usados (`enable-cache` en setup-uv; `node-version`, `cache` y `cache-dependency-path` en setup-node)
siguen existiendo en esas versiones. `node-version: 22` es la versión de Node con la que se compila el visor, no el
entorno de las actions, y no cambia.

Ubuntu: el log de ese mismo run muestra que la etiqueta de Ubuntu por defecto ya ejecutaba `ubuntu-26.04` (Ubuntu 26.04.1 LTS, imagen
20261101.186.1) con el CI en verde. Se fija `ubuntu-26.04` en los dos trabajos de Linux para que el entorno sea
explícito y desaparezca el aviso. Consecuencia: el check de la matriz pasa a llamarse
`calidad-y-pruebas (ubuntu-26.04)`; `main` no tiene protección configurada (404), así que no bloquea merges, y se
actualizaron `CONTRIBUTING.md` y la ADR-021. `windows-latest` no recibió avisos y no cambia. Sintaxis: `actionlint`
no está instalado; el YAML se validó con `yaml.safe_load` (dos trabajos, disparadores `push` y `pull_request`).

**Parte C, `docker-compose.yml`.** Ollama no figura en Compose, ni siquiera como perfil opcional (ADR-026: no se
usa por ahora): se retiraron el servicio `ollama`, su volumen, `FNA_OLLAMA_URL`, el `depends_on` de la API y los
comentarios de `ollama pull`. El código que admite Ollama como proveedor opcional no cambia. La API se lanza con
`uvicorn … --workers 1`, porque la memoria del agente vive en el proceso (ADR-024); Streamlit es otro proceso, con
memoria propia. La API y Streamlit comparten las variables del agente (ancla YAML): `FNA_PROVEEDOR_AGENTE`
(`anthropic` por defecto) y `FNA_MODELO_ANTHROPIC` (`claude-haiku-5-5` por defecto), sin valores secretos; la clave
llega solo por `env_file: .env` como `FNA_ANTHROPIC_API_KEY`. Validación con Docker 29.9.2 y Compose v5.6.1:
`docker compose config --quiet` (válido) y `--services` → `postgres`, `api` y `app`. No se usó
`docker compose config` sin `--quiet`, porque imprimiría las variables de `.env`, clave incluida.
Q&A en Compose: el valor por defecto de `config.py` (`FNA_PROVEEDOR_LLM=ollama`, `core/config.py:105`) no tiene
servidor en Compose, y `claude_code` no está en la imagen. Por eso el ancla `&entorno_fna` define
`FNA_PROVEEDOR_LLM: ${FNA_PROVEEDOR_LLM:-extractivo}`: el Q&A usa `extractivo` por defecto (sin red ni LLM), y
`anthropic` se elige definiendo `FNA_PROVEEDOR_LLM` en `.env`. `config.py` no cambia. Resuelto: Compose fija
FNA_PROVEEDOR_LLM=extractivo por defecto.
`tests/unit/test_docker_compose.py` comprueba que no hay servicio ni volumen de Ollama, que la API usa un solo
worker, el valor de `FNA_PROVEEDOR_LLM` en `api` y `app`, y que el archivo no contiene secretos.

Al crear el ruleset `proteger-main`, los checks exigidos deben ser `calidad-y-pruebas (ubuntu-26.04)`,
`calidad-y-pruebas (windows-latest)` y `visor-web`.

Pendientes:
- El valor por defecto de FNA_PROVEEDOR_LLM en config.py sigue siendo ollama, aunque Ollama no se usa (ADR-026);
  evaluarlo en otro PR con su ADR.
- Validación con modelo real antes de la entrega: una ejecución de tests/integration/test_agente_real.py con
  FNA_PRUEBAS_AGENTE_REAL=1 y Claude Haiku 5.5 (3 turnos, incluido "¿Y cuál es su teléfono?") y el banco de 24
  preguntas; requiere FNA_ANTHROPIC_API_KEY y aprobación antes de gastar créditos. Las pruebas simuladas validan el
  código, no el comportamiento del modelo real.


## A-04 · Decisión del proveedor del agente registrada en Engram (C3) (2026-11-08)

Para el entregable C3 («decisión registrada en Engram»), la decisión principal del agente se guardó en Engram una
sola vez (`mem_save`): observación **id 19**, título «Proveedor del agente: Claude Haiku 5.5 vía API (ADR-026)»,
tipo `decision`, `topic_key` `decision/proveedor-agente`, proyecto `fabrica-nacional-autopartes`, estado `active`.
`mem_search` («proveedor agente Haiku ADR-026») la devuelve como único resultado.

Contenido: Claude Haiku 5.5 vía API como proveedor del agente (ADR-026), con las alternativas descartadas y sus
motivos, y las restricciones (clave solo como `FNA_ANTHROPIC_API_KEY`, sin auto-reload, pruebas con modelo
simulado). Entre las alternativas figura **DeepSeek**, que la ADR-026 no registra: según el usuario, se descartó
fuera del repositorio el 8/11/2026 porque exigía comprar créditos aparte, mientras que el plan Max ya incluye
créditos de API de Anthropic sin costo adicional; además, mantener un solo proveedor simplifica las pruebas y la
documentación.

Incidencias: el primer `mem_save` no guardó nada (`unknown_session`: un hook agrega el identificador de la sesión de
Claude Code, que Engram no tenía registrado). Se registró la sesión con `mem_session_start`; con la ruta de Windows,
Engram asignó el proyecto «unknown», así que se volvió a registrar con la ruta que el propio Engram detecta
(`/mnt/c/fabrica-nacional-autopartes`, proyecto por remoto de Git) y el guardado se hizo con el proyecto explícito.


## R-05 · `extractivo` como proveedor por defecto del Q&A (2026-11-08)

Decisión del usuario (ADR-027): `proveedor_llm` pasa de `ollama` a `extractivo` en `core/config.py`. Análisis previo,
solo leyendo código y documentación: el valor por defecto solo afecta a un clon nuevo sin `.env`, porque el CI fija
`FNA_PROVEEDOR_LLM: extractivo` en el paso de pytest (y `tests/conftest.py` usa `extractivo`) y `docker-compose.yml`
fija `${FNA_PROVEEDOR_LLM:-extractivo}`. En un clon nuevo, `ollama` fallaba (sin servidor), `claude_code` exige la
CLI con sesión del plan (consume cupo), `anthropic` exige clave y créditos, y `extractivo` funciona sin instalación,
red ni costo (exactitud global 0,625 frente a 0,792–0,833 con `claude_code`).

Pruebas nuevas (`tests/unit/test_proveedor_qa_defecto.py`): el valor por defecto es `extractivo` con
`delenv("FNA_PROVEEDOR_LLM")` y `Configuracion(_env_file=None)`; la variable lo sobrescribe; y el Q&A responde con el
valor por defecto sin modelo inyectado ni red. Se comprobó que aíslan el valor: con `config.py` en `ollama` y
`FNA_PROVEEDOR_LLM=extractivo` en el entorno (como en el CI), fallan 2 de las 3 pruebas.

Pendiente (otro PR): `modelo_llm` vale `llama3.2:3b` por defecto; con `FNA_PROVEEDOR_LLM=anthropic` ese nombre se
enviaría a la API y la solicitud fallaría, así que hoy hay que definir también `FNA_MODELO_LLM` con un modelo Claude.


## R-06 · Agentes de desarrollo: Claude Code y Antigravity CLI (2026-11-08)

El README («Herramientas de desarrollo») registra los agentes que se usan para desarrollar el proyecto: Claude Code
como principal y Antigravity CLI 1.5.3 como agente secundario. Datos indicados por el usuario, no verificados por el
agente en este repositorio:
- Antigravity CLI 1.5.3, instalado por el usuario según la guía del curso; la versión la comprobó el usuario con
  `agy --version`.
- Que lee `AGENTS.md` proviene de la documentación pública de Google, no de una verificación en este repositorio.
- Es un binario de Google, no una skill; el escaneo con SkillSpector queda **pendiente** según `fna-seguridad`.
- Se usa solo como agente de desarrollo secundario y no forma parte de la aplicación.

Por no tener escaneo de seguridad documentado, Antigravity va en un párrafo aparte y no en la tabla de herramientas de
desarrollo, cuyo texto introductorio indica «versión fijada tras un escaneo de seguridad documentado». No se ejecutó
`agy` ni ningún otro agente o proveedor.


## A-05 · Compatibilidad con Claude Haiku 5.5 (2026-11-08)

Hallazgo de la prueba real (el usuario, en Streamlit): la primera pregunta al agente con Claude Haiku 5.5 falló con
un 400 de Anthropic, «temperature: Extra inputs are not permitted» (request_id `req_011CgrZ1YPt63B8jXatHpBYJ`), y
el error se mostró como traza. Causa, comprobada sin red: con `temperature=0`, `langchain-anthropic` 1.7.9 la mueve
a `extra_body` y la envía; esa versión solo la retira para `claude-fable-5` y `claude-sonnet-5-5`.

Correcciones (ADR-028), sin llamadas reales a la API ni a `claude -p`:
- No se envían temperature, top_p ni top_k a los modelos Claude 5.x (agente y Q&A con `anthropic`); T=0 no se fija
  con Haiku 5.5 y el determinismo se guía con el prompt. Los demás proveedores conservan `FNA_TEMPERATURA`.
- `traducir_error_anthropic()`: 400 → «La API de Anthropic rechazó la solicitud (400): …» con el `request_id`;
  credenciales y red siguen separados. Conectado en el agente y en `_proveedor_disponible` (Q&A).
- Agente: `stop_reason` `refusal` y `max_tokens` con mensajes propios, solo en el turno actual; Streamlit los dibuja
  como rechazo, sin fuentes.
- `agente_max_tokens`: 1024 → 16000 (ejemplo de la guía oficial), con límite de 32000. El razonamiento adaptativo
  está activo por defecto y se cobra como salida; el costo real por turno se medirá en la prueba real con Haiku y se
  registrará en esta bitácora.

Pruebas nuevas (`tests/unit/test_haiku_5_5.py` y dos en `test_estilo_streamlit.py`): la solicitud de Haiku 5.5 no
lleva parámetros de muestreo, ni en el cuerpo ni en `extra_body`; el `AnthropicInvalidRequestError` real de
`langchain_anthropic`, encadenado a un `BadRequestError` como en la traza, llega como `ErrorProveedorLLM` en el
agente y en el Q&A; `refusal` y `max_tokens` no marcan el turno siguiente; Streamlit los muestra sin fuentes.
Mutación: con `git stash` de `src/` y `frontend/` (sin `tests/`), fallan 16 de las 55 pruebas de esos dos archivos;
tras `git stash pop`, pasan las 55.

Pendientes: refusal en el Q&A (`cadenas.py`) y `max_tokens` fijo de `crear_modelo`, en el PR de `modelo_llm`; la
prueba real después del merge, a cargo del usuario.


## A-06 · Preguntas de seguimiento en el agente: prompt v2 y log de diagnóstico (2026-11-08)

Prueba real del usuario en Streamlit (Claude Haiku 5.5, mismo hilo): el turno 1, «¿Dónde queda la sede
principal?», hizo 1 llamada a `buscar_fragmentos` y respondió con 4 fuentes; el turno 2, «¿Y cuál es su
teléfono?», hizo 0 llamadas, tardó unos 1,4 s y devolvió la frase de rechazo, dos veces igual.

Diagnóstico sin red (ADR-029): el modelo respondió sin buscar y la garantía de anclaje (`_resultado` en
`services/agente.py`) reemplazó la respuesta por la frase de rechazo. El recorte del historial podría haber quitado
el turno 1 si las firmas de los bloques de razonamiento fueran grandes, pero con fragmentos reales y firmas supuestas
de 2000 caracteres el turno 1 suma unos 1523 tokens y se conserva; queda sin confirmar. La auditoría guarda la
respuesta ya reemplazada, así que no se sabe qué respondió el modelo.

Cambios (opciones (a) y (d), aprobadas): prompt del agente v2 por defecto, con búsqueda en cada turno, reformulación
del seguimiento como consulta autocontenida y URL en texto plano, sin Markdown (en la prueba real, Haiku escribió
un enlace Markdown con la URL como texto); la v1 se conserva. Log local de diagnóstico (INFO): `thread_id`, mensajes y tokens aproximados enviados
en cada llamada al modelo, y por turno las llamadas a la herramienta, si se reemplazó la respuesta y la respuesta
original recortada a 500 caracteres; sin clave ni encabezados, y no se guarda en la base.

Pruebas (`tests/unit/test_agente_seguimiento.py`, sin red): el seguimiento sin búsqueda sigue en rechazo; la v2 va
por defecto y su prompt pide buscar en cada turno y citar sin Markdown; un seguimiento reformulado responde con
fuente; la v1 se conserva; el log tiene los campos pedidos, recorta a 500 caracteres y no contiene secretos (con un
manejador propio, porque el proyecto ejecuta pytest con `-p no:logging`). Mutación: con `git stash` de `src/`,
fallan 2 de las 5 (prompt v2 y log); las otras 3 pasan por diseño, porque documentan la garantía de anclaje, el
guion del modelo simulado y la v1.

Pendiente: la prueba real tras el merge dirá si Haiku 5.5 obedece la v2 y, con el log, si el recorte de 3000 tokens
interviene.

## A-07 · `tool_use` sin `tool_result` en el historial del agente (2026-11-09)

Prueba real del usuario en Streamlit (Claude Haiku 5.5, mismo hilo): un turno hizo 2 llamadas a
`buscar_fragmentos` y respondió bien. En el turno siguiente la API devolvió un 400, «tool_use ids were found
without tool_result blocks immediately after: toolu_01SctqjrSKm1bpSnwu5AQEWM» (request_id
`req_011Cgst3PyeLQyKaCDQiTRo7`).

Diagnóstico sin red (ADR-030): los flujos normales no lo reproducen. El único mecanismo reproducido dentro del
agente es un `AIMessage` con un bloque `tool_use` en `content` que no está ni en `tool_calls` ni en
`invalid_tool_calls`. Las llamadas en `invalid_tool_calls` las responde LangChain 1.4.9 antes del middleware
(`_patch_invalid_tool_calls`). Una primera versión del diagnóstico incluyó ese caso: era un error, porque se había
comprobado solo formateando los mensajes. La prueba con el agente completo lo corrigió. **La causa exacta del 400
real sigue sin confirmar.** La reparación (a) lo evita en cualquier caso y el log (d) la confirmará en la próxima
prueba real.

Cambios (opciones (a) y (d), aprobadas):
- (a) Un `ToolMessage` sintético, con `status="error"` y «No usar como fuente», solo en la copia enviada al modelo.
  No se guarda en la memoria ni cuenta como llamada, fragmento ni fuente.
- (d) En el log local, un WARNING con el id de cada `tool_use` reparado y, por cada respuesta del modelo,
  `stop_reason`, ids de `tool_use`, `tool_calls` e `invalid_tool_calls`.
- El texto del 400 en `traducir_error_anthropic` ya no remite a la ADR-028.

Pruebas (`tests/unit/test_agente_historial_herramientas.py`, sin red y con clave ficticia), todas con bloques de
razonamiento firmados, como los de Haiku 5.5:
- el historial con el `tool_use` huérfano da el 400 en el formato de la API y la reparación lo evita;
- las llamadas paralelas y secuenciales completas no cambian;
- con el agente completo, el turno 2 se envía reparado, la memoria no guarda el sintético, el turno cuenta 1
  llamada con fuentes y el log registra el id reparado y la forma de cada respuesta;
- una llamada en `invalid_tool_calls` recibe solo el `tool_result` de LangChain, sin sintético ni WARNING.

Mutación sobre `services/agente.py`:
- quitar la reparación del middleware: falla 1 prueba;
- quitar el WARNING: falla 1 prueba;
- devolver el sintético en `ModelResponse.result`, con lo que queda en la memoria: falla 1 prueba;
- modificar `request.state` en sitio: el mutante es equivalente, porque ese cambio no llega a la memoria.

Pendiente: revisar el log de la próxima prueba real.

## A-08 · Validación formal del agente con Claude Haiku 5.5 (2026-11-09)

Objetivo: validar el agente (`anthropic` / `claude-haiku-5-5`, prompt v2) con el modelo real y medir los tokens y el
costo de cada turno. Rama `prueba-real-agente`.

Preparación (sin red y con clave ficticia):
- `RespuestaAgente.rechazo` (nuevo campo, `False` por defecto): marca la frase de rechazo fija. Las pruebas comprueban
  el rechazo con los campos estructurados y no solo comparando el texto.
- `services/evaluacion_agente.py`:
  - toma los tokens de `usage_metadata` de cada `AIMessage` del turno, guardado en la memoria del hilo;
  - incluye las respuestas que solo traen `tool_calls`, comprobado contra el estado crudo del checkpointer;
  - calcula el costo con 0,10 / 0,50 por millón y la tarifa alta (0,50 / 2,50) por llamada de más de 100 000 tokens de
    entrada;
  - corre el banco con un `thread_id` por pregunta;
  - se detiene al superar el tope de costo (USD 0,50) o ante el primer `ErrorProveedorLLM`
    (`interrumpido_por_error`);
  - retira la clave del JSON.
- `tests/integration/test_agente_real.py` hace 3 turnos en el mismo `thread_id`:
  - dirección y teléfono como seguimiento: llamada a la herramienta, al menos una URL citada y toda URL citada entre
    las fuentes devueltas;
  - P20, el horario, que no está en el corpus: `rechazo`, sin fuentes ni otras marcas.
- `scripts/evaluar_agente_real.py` corre el banco de 24 preguntas. Exige `FNA_PRUEBAS_AGENTE_REAL=1` y aborta sin
  llamar al modelo si la configuración no es `anthropic` / `claude-haiku-5-5`.
- Ambos se saltan o se abortan sin la variable. La suite normal no hace llamadas reales.

Costo estimado antes de ejecutar: unos USD 0,08 en total; el peor caso ronda USD 0,30.

### Ejecución real (2026-11-10)

Lo ejecuta el usuario en PowerShell con su clave. Resultados en `evaluacion/resultados/20261110T133238Z_agente_3_turnos.json`
y `evaluacion/resultados/20261110T133423Z_agente_claude-haiku-5-5.json`.

**Prueba de 3 turnos** (base semilla en un directorio temporal, mismo `thread_id`): 1 passed en 10,7 s.

| Turno | Pregunta | Llamadas al modelo | Entrada / salida (tokens) | Costo (USD) |
|---|---|---|---|---|
| 1 | Dirección de la sede principal | 2 | 3397 / 176 | 0,00043 |
| 2 | «¿Y cuál es su teléfono?» (seguimiento) | 2 | 5925 / 310 | 0,00075 |
| 3 | Horario de atención (P20, fuera del corpus) | 2 | 8530 / 119 | 0,00091 |
| **Total** | | **6** | **17 852 / 605** | **0,00209** |

La entrada crece en cada turno porque el historial del hilo se reenvía: de 1155 tokens en la primera llamada a 4809 en
la última. Sigue lejos del umbral de 100 000.

**Banco de 24 preguntas** (base Gold del entorno del usuario, un `thread_id` por pregunta): 24/24 ejecutadas, sin
errores, sin tope alcanzado y sin URL inválidas.

| Métrica | Valor |
|---|---|
| Exactitud de respondibles | 0,789 (15/19) |
| Rechazo correcto | 0,8 (4/5) |
| Tasa fundamentada | 0,579 (11/19) |
| Exactitud global (oficial) | **0,792** (19/24) |
| Latencia media | 3298 ms |
| Consumo | 49 llamadas · 101 774 / 7057 tokens · USD 0,0137 · 0 con tarifa alta |

El costo medido de las dos ejecuciones suma unos USD 0,016, frente a los USD 0,08 estimados. Por turno resultaron unas
2 llamadas de unos 2000 tokens de entrada cada una, y no los 6000 supuestos.

### Diagnóstico de los fallos (sin red)

Se leyeron solo las 5 entradas fallidas del JSON y se contrastaron con `data/gold` y el recuperador BM25 local.

| Id | Tipo | Causa | Evidencia |
|---|---|---|---|
| P02 | respondible | **Banco desactualizado** | El hecho esperado, «651 5343», solo está en `data/seed/contacto.md`; ningún fragmento del Gold actual lo contiene. La respuesta da el teléfono publicado en `autopartes-contacto#000` (+57 310 211 23 08) y cita su URL. Está fundamentada (0,947). |
| P07 | respondible | **Banco desactualizado**, no recuperación | «1982» solo está en `data/seed/quienes-somos.md`; no aparece en ningún fragmento del Gold, en ninguna variante. El rechazo es la conducta correcta para el corpus actual. Ninguna de las 3 consultas probadas trae el dato entre los 10 primeros, porque no existe. |
| P11 | respondible | **Recuperación** | Con `bm25`, el recuperador por defecto de `buscar_fragmentos` (`ArgumentosBusqueda.recuperador`, independiente de `FNA_RECUPERADOR`), `negocios-ambiental#000` («compactadoras», «contenedores») queda en la posición 9 con la pregunta literal y en la 8 con «unidad Ambiental productos». Con `k=5` por defecto no llega al modelo. El modelo podía pedir `semantico`, pero el JSON no registra los argumentos de cada llamada, así que no se puede confirmar qué recuperador usó. Con «Fanalca Ambiental» sube al puesto 2. El agente hizo 2 búsquedas sin obtenerlo y respondió que no existe esa unidad. |
| P15 | respondible | **Filtro de citas** y **banco desactualizado** | `autopartes-contacto#002` trae `https://fanalca.com/vacantes/` en su texto, pero su campo `url` es `https://autopartesfanalca.com.co/contacto/`. `_retirar_citas_inventadas` solo acepta los campos `url`. Reproducido sin red: «se publican en https://fanalca.com/vacantes/ (fuente: …)» queda en «se publican en (fuente: …)», igual que la respuesta observada. Además, los hechos esperados («empleoscolombia», «trabaja con nosotros») solo están en `data/seed`, así que P15 fallaría aunque se corrigiera el filtro. |
| P21 | ausente | **Criterio del banco** o adherencia al prompt | Responde que no hay precios y agrega un dato fundamentado y citado («100 y hasta 250» cc, «450 puntos de venta» en `negocios-honda-motocicletas#000`), en lugar de la frase de rechazo fija. No inventa: incumple la forma exigida por la regla de negocio. |

La respuesta original del modelo en P15 no se pudo confirmar: el log de diagnóstico de ADR-029 va al stream del
proceso, no a un archivo. La revisión del log de A-07 (`tool_use` reparados) también sigue pendiente: hace falta la
salida de consola de la ejecución.

### Exactitud oficial y ajustada

- **Oficial: 0,792** (19/24), con los criterios vigentes del banco.
- **Ajustada, solo como análisis: 0,875** (21/24), si P02 y P21 se cuentan como aciertos: respuesta correcta y citada
  según el corpus actual, y rechazo de contenido con un dato fundamentado.
- Si además se cuenta P07, cuyo rechazo es correcto con el Gold actual, la exactitud sería 0,917 (22/24). No es una cifra
  oficial.
- Comparación con el Q&A (E-07 y R-05): `extractivo` 0,625; `claude_code` 0,792–0,833. El agente iguala el extremo
  inferior de `claude_code` con la métrica oficial.
  - **Nota (A-09):** el 0,625 del extractivo (informes del 2026-11-04) se midió sobre la **semilla**: sus informes solo
    citan ids de `data/seed`. Los de `claude_code` (0,792–0,833) y el del agente citan solo ids del Gold. Por eso la
    comparación con el extractivo no es válida. Con el mismo corpus (Gold), el extractivo da **0,375** y el agente
    **0,792**. Las cifras de arriba se conservan como se registraron.

### Qué mide «fundamentada» y por qué da 0,579

`fundamentada` es `puntaje_fundamentacion(respuesta, texto de los fragmentos citados) >= 0,6`. El puntaje es la
proporción de términos de la respuesta (tokenizada sin tildes, sin palabras vacías y con una raíz simple) que también
aparecen en el texto de los fragmentos citados. `quitar_citas` solo retira los ids entre corchetes. Las URL citadas se
tokenizan como términos («https», «autopartesfanalca», «contacto», …), que casi nunca están en el texto del fragmento, y
eso baja el puntaje. Las frases propias del agente («le recomiendo», «si te refieres») también bajan el puntaje.

Recalculado sin red sobre las 19 respondibles del JSON: 11/19 = **0,579**, igual que el informe. Sin los tokens de las
URL serían 14/19 = 0,737 (P11, P13 y P17 superan el umbral). Es una métrica léxica de solapamiento: no verifica la
veracidad y penaliza el estilo de cita por URL que usa el agente.

### PR de corrección derivados (fuera de este PR)

1. **Banco de evaluación alineado con el Gold actual.** Actualizar los hechos de P02 (teléfono publicado), P07 (dato
   ausente: reclasificar o quitar) y P15 (`fanalca.com/vacantes`). Decidir si en una pregunta `ausente` un «no hay
   precios» con un dato citado (P21) se acepta como rechazo o se exige la frase fija. Es una versión nueva del banco, con
   las métricas anteriores conservadas.
2. **Recuperación de P11.** Evaluar un `k` mayor por defecto, una expansión de consulta para los nombres de unidades de
   negocio o el recuperador semántico. Medirlo con `evaluar_recuperacion` antes y después.
3. **Filtro de citas (P15).** Aceptar en `_retirar_citas_inventadas` las URL que aparecen en el texto de un fragmento
   devuelto, sin contarlas como fuente. Incluir una prueba con el caso reproducido.
4. **Métrica de fundamentación.** Excluir los tokens de URL en `puntaje_fundamentacion`, igual que se excluyen los ids,
   y registrar el cambio de la métrica en la bitácora. Opcional: un prompt v3 del agente que exija la frase fija en las
   preguntas sin dato (P21).

## A-09 · URL del texto de una fuente citada y fundamentación sin URL (2026-11-10)

Rama `corregir-citas-fundamentacion`, desde `12d2e65`. Corrige los dos defectos de A-08 que no dependen del banco: P15 y
la tasa fundamentada. Sin llamadas reales: pruebas con `FNA_ANTHROPIC_API_KEY=clave-ficticia ANTHROPIC_API_KEY=`.

### Cambio de política de citas (agente y evaluador)

Una sola regla, `services.agente.urls_permitidas`, que usan `_retirar_citas_inventadas` y
`evaluacion_agente.urls_fuera_de_fuentes`. Se conserva una URL de la respuesta si:
- es el campo `url` de una fuente citada, o
- está escrita literalmente en el **texto de una fuente citada** del turno.

Una URL que solo aparece en el texto de un fragmento devuelto pero no citado se retira, igual que una inventada. La URL
del texto no se agrega como fuente ni basta como cita válida: las fuentes se siguen calculando con el campo `url` o el
id. La expresión de URL quedó en un solo sitio (`salvaguardas.URL`, `urls_en` y `normalizar_url`); antes estaba repetida
en el agente y en el evaluador.

Pruebas (`tests/unit/test_agente.py`):
- el caso de P15 con las cadenas exactas queda intacto, y sin la regla nueva reproduce el fallo observado;
- una URL inventada se sigue retirando;
- la URL del texto de un fragmento no citado se retira;
- con el agente completo y la base semilla, se conserva el portal de empleo escrito en el texto del fragmento de
  contacto, sin que pase a ser fuente.

Mutación: sin pasar `urls_permitidas` al filtro, falla 1 prueba.

### Cambio de la métrica de fundamentación

`puntaje_fundamentacion` (`llm/salvaguardas.py`) quita las URL de la respuesta antes de tokenizar, como ya hacía con
los ids entre corchetes. El contexto no cambia. Prueba: una respuesta con URL citadas puntúa igual que la misma sin
ellas.

Llamadores: el agente (`services/agente.py`) y el Q&A (`llm/cadenas.py`). Efecto medido sin red:

| Medición (Gold actual, banco de 24) | Fórmula anterior | Fórmula nueva |
|---|---|---|
| Agente, JSON de A-08 (recálculo; el JSON no se modifica) | 0,579 (11/19) | **0,737 (14/19)**: P11, P13 y P17 pasan el umbral |
| Q&A `extractivo` completo (v1, v2, v3) | 0,579 | 0,579 |
| Q&A `extractivo` selección (v1, v2, v3) | 0,789 | 0,789 |

El Q&A extractivo no cambia porque ninguna de sus respuestas contiene URL (comprobado en v3, completo y selección).
La medición usó `Configuracion(_env_file=None, proveedor_llm="extractivo")` con `FNA_PROVEEDOR_LLM=extractivo` en el
comando y mostró el proveedor efectivo antes de medir. Se hizo con `guardar=False` y la auditoría en una SQLite
temporal, sin escribir en el repositorio. `claude_code` no se volvió a ejecutar.

**Todas las métricas registradas antes de A-09 usan la fórmula anterior** (E-01 a E-07, R-05, A-08) y no se comparan
directamente con las nuevas.

### Corpus de las comparaciones con el Q&A

Los ids citados en los informes guardados indican el corpus de cada medición:

| Informes | Ids citados | Corpus |
|---|---|---|
| `extractivo`, 2026-11-04 (exactitud global 0,583 completo, 0,625 selección) | solo de la semilla | `data/seed` |
| `claude_code`, 2026-11-05 a 2026-11-07 (0,792–0,833) | solo del Gold | Gold |
| Agente, A-08 (0,792) | solo del Gold | Gold |

La comparación válida, con el mismo corpus (Gold): **agente 0,792 frente a extractivo 0,375**, que es la exactitud
global del extractivo medida hoy en los 6 modos y versiones. Para `claude_code` se mantiene 0,792–0,833. La A-08 y
`modelos.md` llevan una nota con esta corrección y conservan las cifras anteriores. R-05 y ADR-027 también citan el
0,625 de la semilla y no se tocaron en este PR.

### Pendiente

P15 sigue fallando en el banco aunque se conserve la URL: los hechos esperados («empleoscolombia», «trabaja con
nosotros») solo están en la semilla. Queda para el PR del banco (A-08, punto 1).
