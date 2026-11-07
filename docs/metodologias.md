# Metodologías: evidencia, aplicación y glosario

Estado de cada metodología según la evidencia del repositorio, de su historial y, cuando se indica, de la
configuración local no versionada. Resumen en el [README](../README.md#metodologías).

**Sobre la columna «Modelo».** Se distingue el desarrollo de la aplicación:
- **Desarrollo:** agente de Claude Code asignado a cada fase en [`fases_agentes.yaml`](manuales/fases_agentes.yaml),
  con el modelo de su configuración local (`.claude/agents/*.md` y `opencode.json`, no versionados). La asignación
  de un agente a una fase no prueba que ese agente ejecutara cada cambio. Los 16 commits con `Co-Authored-By`
  registran a Claude Sonnet 5.5 (sesión principal); los posteriores al 2026-11-06 no llevan esa línea y su modelo no
  es determinable desde Git.
- **Aplicación:** `claude_code` con `sonnet` en Q&A, Resumen, FAQ, `faq-visor` y la búsqueda web complementaria;
  `extractivo` como línea base y en las pruebas.

## Tabla con evidencia

| Metodología | Estado | Dónde se aplica | Por qué se usa aquí | Modelo |
|---|---|---|---|---|
| SDD, Spec-Driven Development (desarrollo guiado por especificaciones), con OpenSpec | Aplicada | [`openspec/specs/`](../openspec/specs/) (6 especificaciones); Spec-Kit no se usa | Cada funcionalidad parte de requisitos y escenarios verificables | Desarrollo: F07, `analista-requisitos` (opus) |
| Modos plan/build (planificar/construir) con aprobación humana | Aplicada (evidencia local) | `CLAUDE.md` y planes en `~/.claude/plans/`, no versionados | Separar el plan de la implementación y aprobar antes de cada fase | Desarrollo: Opus para planificar y Sonnet para construir, según `CLAUDE.md` local |
| Matriz de permisos allow/ask/deny (permitir/preguntar/denegar) | Aplicada (evidencia local) | `.claude/settings.json` y `opencode.json` locales; versionada en el historial hasta el commit `af47625` (20 allow, 4 ask, 5 deny) | Pruebas sin confirmación; commits y scraping con confirmación; `git push` y borrados denegados | Configuración de la herramienta; sin modelo |
| Memoria persistente con Engram | Parcial | [ADR-018](arquitectura/adr/ADR-018-engram-y-gga.md), [bitácora](prompts/bitacora_experimentos.md) S-05 | Conservar decisiones entre sesiones de agentes | Plugin instalado (v3.6.2), sin memorias guardadas de este proyecto: el modo automático bloquea `mem_save` |
| ReAct, Reasoning and Acting (razonar y actuar), con pruebas automáticas | Parcial | [`verificar_calidad.ps1`](../scripts/verificar_calidad.ps1), [`.gga`](../.gga), [`busqueda_web.py`](../src/fabrica_autopartes/llm/busqueda_web.py) | El agente itera cambio → pruebas → corrección; sin prompt ReAct explícito | Desarrollo: sesión principal; aplicación: `claude_code`/`sonnet` solo en la búsqueda web (hasta 8 turnos con WebSearch y WebFetch) |
| GGA, Gentleman Guardian Angel (revisión de código con IA antes de cada commit), y ruff (analizador y formateador de Python) | Aplicada | [`.gga`](../.gga), [`pyproject.toml`](../pyproject.toml), [`ci.yml`](../.github/workflows/ci.yml) | Revisar cada commit contra `AGENTS.md` y mantener un estilo único | GGA: `claude --print` sin modelo fijado en `.gga` (no determinable); ruff: sin modelo |
| Arquitectura por capas (en lugar de MVC, Model-View-Controller, modelo-vista-controlador) | Aplicada (capas; MVC no) | [`verificar_capas.py`](../scripts/verificar_capas.py), [`AGENTS.md`](../AGENTS.md) | Las interfaces solo llaman a servicios; la regla se comprueba en CI | Desarrollo: F08, `revisor-calidad` (opus) |
| TDD, Test-Driven Development (desarrollo guiado por pruebas), con AAA, Arrange-Act-Assert (preparar, actuar, afirmar) | Parcial | [`tests/`](../tests/), [`web/src/__tests__/`](../web/src/__tests__/), [`web/e2e/`](../web/e2e/) | Cada cambio llega con pruebas; no hay evidencia de prueba previa al código ni de AAA explícito | Desarrollo: F14, F15 y F22, `revisor-calidad` (opus); pruebas: `extractivo` |
| uv (gestor de paquetes y proyectos de Python) y Docker (contenedores) | Parcial (uv aplicada; Docker definido) | [`uv.lock`](../uv.lock), [`docker-compose.yml`](../docker-compose.yml), [`Dockerfile`](../infra/docker/Dockerfile) | Entorno reproducible; Docker no se ejecuta en CI ni se verificó en esta revisión | Sin modelo |
| Gitflow (flujo de ramas de Git) con PR, Pull Request (solicitud de integración), y Conventional Commits (convención de mensajes de commit) | Parcial | Ramas `add-honda-moto-machine` y `feature/busqueda-web`; 38 de 38 commits con formato `tipo: descripción` (7 con el tipo propio `datos`) | Ramas por funcionalidad e historial legible; sin `develop`, sin `release` y sin PR (integración por avance rápido) | Sin modelo |
| CI/CD, Continuous Integration / Continuous Delivery (integración y entrega continuas), con GitHub Actions | Parcial (CI sí; CD no) | [`ci.yml`](../.github/workflows/ci.yml) | Ruff, mypy, capas, pytest, Vitest y build en Ubuntu y Windows en cada push a `main`; sin despliegue | Sin modelo |
| MCP, Model Context Protocol (protocolo de contexto de modelos) | Aplicada | [`.mcp.json`](../.mcp.json), [`mcp_server/`](../src/fabrica_autopartes/mcp_server/) | Acceso de solo lectura de los agentes a la base de conocimiento | Desarrollo: F06, `revisor-calidad` (opus), y F24, `ingeniero-3d-frontend` (sonnet); aplicación: `responder_pregunta` es extractiva, sin LLM |
| Medallion Architecture (arquitectura medallón: capas Bronze/Silver/Gold, bronce/plata/oro) | Aplicada | [ADR-002](arquitectura/adr/ADR-002-medallion-archivos.md), [`pipelines/`](../src/fabrica_autopartes/pipelines/) | Separar dato crudo, limpio y listo para el LLM, con trazabilidad | Desarrollo: F09 a F11, `ingeniero-datos` (sonnet); aplicación: sin LLM |
| Responsible Web Scraping (extracción web responsable: robots.txt, pausas, User-Agent identificable) | Aplicada | [`scraping/`](../src/fabrica_autopartes/scraping/), [ADR-015](arquitectura/adr/ADR-015-proteccion-antibots.md), [`test_rastreo.py`](../tests/integration/test_rastreo.py) | Extraer solo lo permitido y sin eludir protecciones | Desarrollo: F09, `ingeniero-datos` (sonnet); aplicación: sin LLM |
| Prompt Engineering (ingeniería de instrucciones) versionado, con evaluación v1–v3 | Aplicada | [`llm/prompts/`](../src/fabrica_autopartes/llm/prompts/), [bitácora](prompts/bitacora_experimentos.md), [`evaluacion/resultados/`](../evaluacion/resultados/) | Comparar técnicas con el mismo banco de 24 preguntas | Desarrollo: F12 y F13, `ingeniero-llm` (sonnet); aplicación: `claude_code`/`sonnet`; `extractivo` como línea base y en pruebas |
| Método Anatomy (máquinas interactivas para explicar mecanismos) | Aplicada | [`fna-maquinas-anatomia`](../skills/fna-maquinas-anatomia/SKILL.md), [`plantilla/`](../web/src/componentes/plantilla/) | Una pregunta y una relación medible por máquina | Desarrollo: F21, `ingeniero-3d-frontend` (sonnet) |
| ADR, Architecture Decision Record (registro de decisión de arquitectura) | Aplicada | [`arquitectura/adr/`](arquitectura/adr/) (20) | Dejar el porqué de cada decisión estructural | Desarrollo: F08, `revisor-calidad` (opus), y fases técnicas |
| Revisión de skills con SkillSpector (escáner de seguridad para skills de agentes) | Aplicada | [bitácora](prompts/bitacora_experimentos.md) S-01 a S-07, [`fna-seguridad`](../skills/fna-seguridad/SKILL.md) | Ninguna skill o herramienta de terceros se instala sin escaneo ni análisis manual | Escáner con `--no-llm`; análisis manual en la sesión principal |
| Independent Critical Review (revisión crítica independiente) | Aplicada | [bitácora](prompts/bitacora_experimentos.md) E-04 (hallazgo H-03); fases F06, F08, F14, F15 y F22 | Un revisor que no edita código contrasta cada entrega con `AGENTS.md` | Desarrollo: `revisor-calidad` (opus) |
| Graphify — Code Knowledge Graph (grafo de conocimiento del código) | Aplicada (excepción S-08) | [`mapa_codigo.svg`](imagenes/mapa_codigo.svg), [`GRAPH_REPORT.md`](graphify/GRAPH_REPORT.md), [ADR-020](arquitectura/adr/ADR-020-graphify-mapa-del-codigo.md) | Mapa de dependencias y comunidades del código | Sin LLM: AST local con `--code-only` y `GRAPHIFY_BACKEND=none` |

## Cómo se aplicó cada una

<details>
<summary><b>SDD, Spec-Driven Development (desarrollo guiado por especificaciones), con OpenSpec</b></summary>

Seis especificaciones en `openspec/specs/` (extracción de datos, base de conocimiento, tareas LLM, interfaz de
prueba, simulador 3D y biblioteca de máquinas) fijan requisitos y escenarios. La matriz de trazabilidad
(`docs/requisitos/matriz_trazabilidad.md`) enlaza cada requisito con su prueba de aceptación.
</details>

<details>
<summary><b>Modos plan/build (planificar/construir) con aprobación humana</b></summary>

Cada fase se planificó primero (plan en `~/.claude/plans/`) y se implementó tras la aprobación explícita de la
persona responsable, con paradas acordadas para revisar capturas o inventarios antes del commit. La evidencia es
local: `CLAUDE.md` y los planes no se versionan.
</details>

<details>
<summary><b>Matriz de permisos allow/ask/deny (permitir/preguntar/denegar)</b></summary>

La configuración de Claude Code y de OpenCode permite sin preguntar pruebas, lint, tipos y lecturas de Git; pide
confirmación para commits, `uv add` y scraping; y deniega `git push`, `rm -rf`, `curl` y la lectura de `.env`. Esa
configuración se versionó hasta la limpieza del repositorio y hoy vive solo en disco.
</details>

<details>
<summary><b>Memoria persistente con Engram (parcial)</b></summary>

Engram v3.6.2 y su plugin para Claude Code se instalaron con versión fijada tras un escaneo de seguridad (ADR-018,
S-05). La memoria del proyecto no se ha llenado: el modo automático de Claude Code no puede revisar `mem_save`
porque el plugin modifica la llamada, y la memoria local de Claude Code (`MEMORY.md`) cubre ese papel.
</details>

<details>
<summary><b>ReAct, Reasoning and Acting (razonar y actuar), con pruebas automáticas (parcial)</b></summary>

En desarrollo, el agente alterna razonamiento y acciones (editar, ejecutar `verificar_calidad.ps1`, corregir) hasta
que pruebas, lint, tipos y GGA pasan. En la aplicación, solo la búsqueda web complementaria usa herramientas en varios
turnos (WebSearch y WebFetch, hasta 8 turnos); no hay un prompt con el formato ReAct explícito.
</details>

<details>
<summary><b>GGA, Gentleman Guardian Angel, y ruff</b></summary>

El hook `pre-commit` de GGA envía el diff de `*.py`, `*.ts` y `*.tsx` a Claude y bloquea el commit si incumple
`AGENTS.md`; en la fase 9 rechazó dos intentos por un prompt fuera de `llm/prompts/` y por datos personales sin
anonimizar. Ruff formatea y analiza el código Python en el hook del agente, en `verificar_calidad.ps1` y en CI.
</details>

<details>
<summary><b>Arquitectura por capas (en lugar de MVC, Model-View-Controller)</b></summary>

El flujo `scraping → pipelines → knowledge → llm → services → interfaces` solo admite importaciones hacia capas de
nivel igual o inferior, y `scripts/verificar_capas.py` lo comprueba en cada corrida. Las interfaces (API, Streamlit,
CLI y MCP) llaman únicamente a `ServicioAsistente`.
</details>

<details>
<summary><b>TDD, Test-Driven Development, con AAA, Arrange-Act-Assert (parcial)</b></summary>

Cada fase añade pruebas unitarias, de integración y E2E (pytest, Vitest y Playwright), y la paridad Python–TypeScript
se fija con casos de referencia exportados. El historial no permite afirmar que la prueba se escribió antes que el
código, y las pruebas no siguen una convención AAA explícita.
</details>

<details>
<summary><b>uv y Docker (parcial)</b></summary>

`uv` gestiona dependencias y entorno desde `uv.lock` en todas las corridas locales y en CI. Docker está definido
(`docker-compose.yml` con PostgreSQL, Ollama, API y Streamlit, e `infra/docker/Dockerfile`), pero no se ejecuta en CI
ni se verificó en esta revisión.
</details>

<details>
<summary><b>Gitflow, PR y Conventional Commits (parcial)</b></summary>

Los cambios grandes se desarrollan en ramas de funcionalidad (`add-honda-moto-machine`, `feature/busqueda-web`) y se
integran a `main` por avance rápido, sin rama `develop`, ramas `release` ni PR. Los 38 commits usan el formato
`tipo: descripción` (`feat`, `docs`, `chore` y el tipo propio `datos`).
</details>

<details>
<summary><b>CI/CD, Continuous Integration / Continuous Delivery, con GitHub Actions (parcial)</b></summary>

GitHub Actions ejecuta Ruff, mypy, verificación de capas, pytest con cobertura mínima y Vitest con la compilación del
visor en Ubuntu y Windows en cada push a `main`. No hay entrega ni despliegue automático: el sistema se ejecuta en
local.
</details>

<details>
<summary><b>MCP, Model Context Protocol</b></summary>

El servidor `fna-conocimiento` expone búsqueda, fragmentos, estadísticas, validación y consulta de piezas, todas de
solo lectura, y Claude Code lo usa durante el desarrollo. La herramienta `responder_pregunta` responde de forma
extractiva, sin invocar un LLM.
</details>

<details>
<summary><b>Medallion Architecture (arquitectura medallón)</b></summary>

Bronze guarda el HTML y un manifiesto por página; Silver limpia, segmenta, deduplica y anonimiza; Gold produce
documentos, `fragmentos.jsonl` y `base_conocimiento.txt`. Cada etapa tiene métricas y una gráfica en la pestaña
«Proceso de datos».
</details>

<details>
<summary><b>Responsible Web Scraping (extracción web responsable)</b></summary>

El rastreador respeta `robots.txt` y `Crawl-delay`, usa un User-Agent identificable, pausa al menos 2 s y se limita a
los dominios permitidos. Un dominio con desafío anti-bots se marca como protegido y se omite (ADR-015); las pruebas
usan un sitio simulado.
</details>

<details>
<summary><b>Prompt Engineering versionado, con evaluación v1–v3</b></summary>

Los prompts de Q&A, FAQ y Resumen viven en YAML con tres versiones (zero-shot, reglas con delimitación y salida JSON
con few-shot) y cada versión declara su técnica e hipótesis. La evaluación con 24 preguntas compara las versiones con
Claude y con la línea base extractiva; los resultados están en `evaluacion/resultados/`.
</details>

<details>
<summary><b>Método Anatomy</b></summary>

Cada máquina (freno, prensa, línea y motocicleta) responde una pregunta con una relación medible, con 2 a 4 controles,
cifras junto a las piezas, recorrido de menos de 30 s y modo experimento. La plantilla común está en
`web/src/componentes/plantilla/`.
</details>

<details>
<summary><b>ADR, Architecture Decision Record</b></summary>

Veinte registros con contexto, decisión, alternativas y consecuencias, desde el uso de archivos para Medallion
hasta el proveedor `claude_code`, la motocicleta de referencia, Engram y GGA, la búsqueda web complementaria y
Graphify.
</details>

<details>
<summary><b>Revisión de skills con SkillSpector</b></summary>

Cada skill o herramienta de terceros se escanea con SkillSpector (`--no-llm`) y se rechaza con 51 o más puntos, salvo
excepción documentada con análisis manual de cada hallazgo alto y versión fijada (S-05 Engram, S-06 GGA). Archify se
descartó dos veces (S-04 y S-07).
</details>

<details>
<summary><b>Independent Critical Review (revisión crítica independiente)</b></summary>

El agente `revisor-calidad`, sin permiso de edición, revisa fases completas contra `AGENTS.md` y las restricciones
del proyecto; la entrada E-04 de la bitácora registra la revisión de la motocicleta y el hallazgo H-03 corregido. GGA
añade una revisión automática en cada commit.
</details>

<details>
<summary><b>Graphify — Code Knowledge Graph (grafo de conocimiento del código)</b></summary>

Graphify (`graphifyy==0.9.102`, excepción S-08 y ADR-020) analizó por AST una copia de los `.py` de
`src/fabrica_autopartes` y los `.ts`/`.tsx` de `web/src`, sin LLM ni red: 1252 nodos, 3492 aristas y 52 comunidades
(Louvain). El README muestra una vista por paquetes derivada del grafo y el informe lista los nodos más conectados
(`ServicioAsistente`, `MaquinaMoto`, `BaseConocimiento`) y confirma que no hay ciclos de importación.
</details>

## No aplicadas

<details>
<summary><b>Metodologías sin evidencia en el repositorio</b></summary>

- **Kanban** (tablero de flujo visual) con estimación **Fibonacci** (serie de Fibonacci para puntos de historia) y
  límites de **WIP, Work In Progress** (trabajo en curso): no hay tablero, estimaciones ni límites registrados.
- **CRISP-DM, Cross-Industry Standard Process for Data Mining** (proceso estándar intersectorial para minería de
  datos): el flujo de datos sigue Medallion y no hay fases CRISP-DM documentadas.
- **Model Card** (tarjeta del modelo): el proveedor y sus métricas están en ADR-016 y en la evaluación, pero no
  existe una tarjeta del modelo.
- **Data Thinking** (pensamiento orientado a datos), **BMC, Business Model Canvas** (lienzo del modelo de negocio),
  **OKR, Objectives and Key Results** (objetivos y resultados clave) y **KPI, Key Performance Indicators**
  (indicadores clave de desempeño): no hay documentos de negocio; las métricas existentes son técnicas.
- **CPM, Critical Path Method** (método de la ruta crítica) y **Gantt Chart** (diagrama de Gantt): no hay
  cronograma ni ruta crítica registrados.
- **Archify** (diagramas de arquitectura generados por agentes): evaluada y descartada (bitácora S-04 y S-07); los
  diagramas están en Mermaid.
</details>

## Glosario de siglas

| Sigla | Nombre completo en inglés | Traducción al español |
|---|---|---|
| AAA | Arrange, Act, Assert | Preparar, actuar, afirmar |
| ADR | Architecture Decision Record | Registro de decisión de arquitectura |
| API | Application Programming Interface | Interfaz de programación de aplicaciones |
| BM25 | Best Matching 25 | Función de ranking léxico «mejor coincidencia 25» |
| BMC | Business Model Canvas | Lienzo del modelo de negocio |
| CBS | Combined Braking System | Sistema de frenado combinado |
| CI/CD | Continuous Integration / Continuous Delivery | Integración y entrega continuas |
| CLI | Command-Line Interface | Interfaz de línea de comandos |
| CPM | Critical Path Method | Método de la ruta crítica |
| CRISP-DM | Cross-Industry Standard Process for Data Mining | Proceso estándar intersectorial para minería de datos |
| E2E | End-to-End | De extremo a extremo |
| FAQ | Frequently Asked Questions | Preguntas frecuentes |
| — | Community detection (Leiden / Louvain) | Detección de comunidades: agrupa nodos muy conectados entre sí (aquí, Louvain) |
| GGA | Gentleman Guardian Angel | Ángel guardián: revisión de código con IA antes de cada commit |
| GLB | GL Transmission Format Binary | Formato binario de transmisión de modelos 3D |
| — | God node | Nodo central: el más conectado del grafo de código |
| GPU | Graphics Processing Unit | Unidad de procesamiento gráfico |
| HTML | HyperText Markup Language | Lenguaje de marcado de hipertexto |
| HTTP | HyperText Transfer Protocol | Protocolo de transferencia de hipertexto |
| IA | Artificial Intelligence (AI) | Inteligencia artificial |
| — | Knowledge Graph | Grafo de conocimiento: entidades y relaciones en forma de grafo |
| KPI | Key Performance Indicator | Indicador clave de desempeño |
| LCEL | LangChain Expression Language | Lenguaje de expresiones de LangChain |
| LLM | Large Language Model | Modelo de lenguaje de gran tamaño |
| LTS | Long-Term Support | Soporte a largo plazo |
| MCP | Model Context Protocol | Protocolo de contexto de modelos |
| MIT | Massachusetts Institute of Technology (licencia MIT) | Instituto Tecnológico de Massachusetts |
| MVC | Model-View-Controller | Modelo-vista-controlador |
| OKR | Objectives and Key Results | Objetivos y resultados clave |
| PR | Pull Request | Solicitud de integración de cambios |
| Q&A | Question and Answer | Preguntas y respuestas |
| ReAct | Reasoning and Acting | Razonar y actuar |
| REST | Representational State Transfer | Transferencia de estado representacional |
| SDD | Spec-Driven Development | Desarrollo guiado por especificaciones |
| SQL | Structured Query Language | Lenguaje de consulta estructurado |
| TDD | Test-Driven Development | Desarrollo guiado por pruebas |
| URL | Uniform Resource Locator | Localizador uniforme de recursos |
| WIP | Work In Progress | Trabajo en curso |
