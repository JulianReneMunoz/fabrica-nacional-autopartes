# ADR-025 · Endurecimiento de la invocación de `claude -p`

- **Estado:** aceptada (2026-11-08); verificada con una llamada real. Detalle en la entrada S-10 de
  `docs/prompts/bitacora_experimentos.md`.
- **Contexto:** el proveedor `claude_code` (`llm/claude_code.py`, ADR-016) y la búsqueda web complementaria
  (`llm/busqueda_web.py`, ADR-019) ejecutan la CLI de Claude Code (`claude -p`) con la sesión de la suscripción. El
  aislamiento dependía de una carpeta temporal vacía, de `--max-turns` y de una instrucción en el texto. En el Q&A
  **no se desactivaban las herramientas propias de Claude Code**: Read, Glob y Grep no piden permiso y aceptan rutas
  absolutas, y además se cargaban la configuración, los hooks, los plugins, los servidores MCP y la memoria
  (CLAUDE.md) del usuario. Riesgo: **inyección indirecta**. Un contenido descargado (un fragmento del corpus o una
  página web) con instrucciones como «lee `~/.ssh/…`» o «ejecuta…» podía disponer de herramientas para hacerlo.
- **Decisión:** usar solo flags que figuran en `claude --help` de la versión instalada (Claude Code 2.1.319) y
  comprobarlos antes de ejecutar.

  | Flag | Q&A (`ChatClaudeCode`) | Búsqueda web (`BuscadorClaudeCode`) | Motivo |
  |---|---|---|---|
  | `--tools ""` | sí | no: `--tools WebSearch,WebFetch` (y `--allowedTools`, igual que antes) | El Q&A no necesita ninguna herramienta; la búsqueda web, solo esas dos |
  | `--strict-mcp-config` (sin `--mcp-config`) | sí | sí | Ningún servidor MCP del usuario (engram, fna-conocimiento…) |
  | `--safe-mode` | sí | sí | Sin CLAUDE.md, skills, plugins, hooks ni comandos o agentes propios; la autenticación y las herramientas integradas funcionan normalmente |
  | `--restricted` | sí | **no** | Ignora los archivos de configuración del usuario, del proyecto y locales; la ayuda indica que quita WebFetch salvo que `--tools` lo nombre, y se omite en la búsqueda web por prudencia |
  | `--permission-prompts none` | sí | sí | Lo que pediría permiso se deniega automáticamente |
  | `--no-session-persistence` | sí | sí | La sesión no se guarda en disco |
  | `-p`, `--output-format json`, `--model`, `--max-turns`, `cwd` temporal vacío y timeout | sin cambios | sin cambios | Ya existían (300 s y 1 turno en el Q&A; 120 s y 8 turnos en la búsqueda web) |

  - **Comprobación previa:** antes de la primera llamada se lee `claude --help`, que no consume cupo, y se exige que
    aparezcan los flags de esa invocación (resultado en caché por ejecutable y conjunto de flags). Si falta alguno o la
    ayuda no puede leerse, se lanza `ErrorProveedorLLM` y **no se ejecuta `claude -p` sin aislamiento**. `--max-turns`
    no figura en la ayuda (se acepta como opción oculta) y no entra en la comprobación.
  - **Descartado `--bare`:** la ayuda indica que con él la autenticación es «strictly ANTHROPIC_API_KEY… OAuth and
    keychain are never read», lo que dejaría de usar la suscripción. `--setting-sources ""` se descartó porque la
    ayuda no indica si admite una lista vacía; `--restricted` cubre lo mismo de forma explícita.
- **Verificación real** (una sola llamada, aprobada por el usuario, 2026-11-08):
  `fabrica ask "¿Dónde queda la sede principal?" --proveedor claude_code`, con la CLI instalada como `claude.CMD` (npm)
  en Windows. Respuesta: «La dirección publicada de Fanalca es Calle 13 # 31A - 80, Urbanización Industrial Acopi,
  Yumbo (Valle del Cauca), Colombia…», con las fuentes `contacto-sitio#000` y `autopartes-contacto#000`,
  `fundamentada=True` y 4236 ms. La combinación de flags se acepta, incluido el argumento vacío de `--tools ""` a
  través de `cmd.exe`. La búsqueda web no se ejecutó (solo se verificó su comando en pruebas).
- **Consecuencias:**
  - Las cifras de E-01 a E-07 se obtuvieron sin estos flags. `--safe-mode` y `--restricted` no cambian el modelo ni el
    prompt de la tarea, pero una evaluación futura con `claude_code` debe registrarlo como condición distinta.
  - Una actualización de Claude Code que renombre o quite un flag detiene el proveedor con un mensaje claro, en lugar
    de ejecutarlo sin protección.
  - La memoria del usuario (CLAUDE.md global) ya no entra en las respuestas del Q&A.
- **Alternativas:** dejar la instrucción en el texto (insuficiente ante inyección indirecta); `--disallowedTools` con
  una lista de herramientas (frágil ante herramientas nuevas; `--tools ""` es una lista de permitidas vacía); `--bare`
  (rompe la autenticación con la suscripción); retirar el proveedor `claude_code` (se pierde la evaluación sin clave
  de API).
