# CLAUDE.md

Las reglas comunes para todos los agentes están en @AGENTS.md (fuente única de verdad).
El prompt maestro vigente es `docs/prompt_maestro_v2.md`.

## Consola principal y modelos por especialidad
Claude Code CLI es la consola principal (Windows 11, PowerShell, carpeta
`C:\fabrica-nacional-autopartes`). Cada subagente de `.claude/agents/` fija su modelo en el campo
`model` del frontmatter:

| Especialidad | Subagente | Modelo |
|---|---|---|
| Requisitos y trazabilidad | analista-requisitos | opus |
| Arquitectura, ADR, integración | arquitecto-sistema | opus |
| Diseño mecánico 3D, articulaciones, restricciones | arquitecto-mecanico-3d | opus |
| Revisión independiente | revisor-calidad | opus |
| Scraping, Medallion, gráficas por etapa | ingeniero-datos | sonnet |
| Prompts, LangChain, RAG del simulador | ingeniero-llm | sonnet |
| Generación GLB, API del simulador, visor 3D, animaciones, controles, pruebas | ingeniero-3d-frontend | sonnet |
| Documentación, LaTeX, guías | documentador | sonnet |
| Verificaciones rápidas | verificador-rapido | haiku |

- La variable `CLAUDE_CODE_SUBAGENT_MODEL`, si se define, reemplaza el campo `model` de todos los
  subagentes: dejarla sin definir para respetar esta tabla.
- Sesión principal: `claude --model opus` para planificar y `/model sonnet` para implementar. El
  alias combinado de planificación (Opus) e implementación (Sonnet) se verifica con `/model`
  en la versión instalada antes de usarlo.
- Los modelos de Claude no sustituyen el motor geométrico (trimesh + manifold3d), el cálculo físico
  (`simulador/fisica_freno.py`) ni un software CAD.

## Específico de Claude Code
- Skills del proyecto: `.claude/skills/` (copia sincronizada de `skills/`; regenerar con
  `uv run python scripts/sincronizar_skills.py`). Incluye `fna-simulador-3d` y
  `fna-maquinas-anatomia`.
- Skill externa Anatomy (global): `npx skills add wheresryan22/anatomy -g -a claude-code`;
  invocar con `/anatomy`. Revisar su `SKILL.md` antes del primer uso.
- Servidores MCP del proyecto: `.mcp.json` (`fna-conocimiento`, solo lectura; incluye
  `consultar_pieza`).
- Hooks: `.claude/settings.json` ejecuta `ruff format` sobre archivos Python editados.
- `uv run fabrica pipeline` accede a la red (scraping real): requiere aprobación explícita.
- Flujo por tarea: leer especificación en `openspec/` → plan (Opus) → implementar (Sonnet) →
  `uv run pytest -q` → `uv run ruff check .` → `uv run mypy` → `cd web; npm test` → revisión
  (revisor-calidad) → resumir cambios y evidencias.
