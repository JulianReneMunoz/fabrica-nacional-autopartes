# Metodologías: evidencia, aplicación y glosario

Estado de cada metodología según la evidencia del repositorio, de su historial y, cuando se indica, de la
configuración local no versionada. Resumen en el [README](../README.md#metodologías).

**Sobre la columna «Modelo».** Se distingue el desarrollo de la aplicación:
- **Desarrollo:** agente de Claude Code asignado a cada fase en [`fases_agentes.yaml`](manuales/fases_agentes.yaml),
  con el modelo de su configuración local (`.claude/agents/*.md` y `opencode.json`, no versionados). La asignación
  de un agente a una fase no prueba que ese agente ejecutara cada cambio. Los 16 commits con `Co-Authored-By`
  registran a Claude Sonnet 5.5 (sesión principal); los posteriores al 2026-11-06 no llevan esa línea y su modelo no
  es determinable desde Git.
- **Aplicación:** `claude_code` con `sonnet` en Resumen, FAQ, `faq-visor` y la búsqueda web complementaria;
  `anthropic` con `claude-haiku-5-5` en el agente (ADR-026); `extractivo` como proveedor por defecto del Q&A
  (ADR-027), como línea base y en las pruebas.

## Tabla con evidencia

| Metodología | Estado | Dónde se aplica | Por qué se usa aquí | Modelo |
|---|---|---|---|---|
| SDD, Spec-Driven Development (desarrollo guiado por especificaciones), con OpenSpec | Aplicada | [`openspec/specs/`](../openspec/specs/) (6 especificaciones); Spec-Kit no se usa | Cada funcionalidad parte de requisitos y escenarios verificables | Desarrollo: F07, `analista-requisitos` (opus) |
| Modos plan/build (planificar/construir) con aprobación humana | Aplicada (evidencia local) | `CLAUDE.md` y planes en `~/.claude/plans/`, no versionados | Separar el plan de la implementación y aprobar antes de cada fase | Desarrollo: Opus para planificar y Sonnet para construir, según `CLAUDE.md` local |
| Matriz de permisos allow/ask/deny (permitir/preguntar/denegar) | Aplicada (evidencia local) | `.claude/settings.json` y `opencode.json` locales; versionada en el historial hasta el commit `af47625` (20 allow, 4 ask, 5 deny) | Pruebas sin confirmación; commits y scraping con confirmación; `git push` y borrados denegados | Configuración de la herramienta; sin modelo |
| Memoria persistente con Engram | Aplicada (modo manual) | [ADR-018](arquitectura/adr/ADR-018-engram-y-gga.md), [bitácora](prompts/bitacora_experimentos.md) S-05, A-04 y A-08 a A-11 | Conservar decisiones entre sesiones de agentes | Plugin instalado (v3.6.2); 6 observaciones del proyecto guardadas a mano (19 a 24), comprobadas con `mem_search` el 2026-11-10 |
| ReAct, Reasoning and Acting (razonar y actuar), con pruebas automáticas | Parcial | [`verificar_calidad.ps1`](../scripts/verificar_calidad.ps1), [`.gga`](../.gga), [`busqueda_web.py`](../src/fabrica_autopartes/llm/busqueda_web.py), [`agente.py`](../src/fabrica_autopartes/services/agente.py) | El agente itera cambio → pruebas → corrección; sin prompt ReAct explícito | Desarrollo: sesión principal; aplicación: el agente (`create_agent`, `anthropic`/`claude-haiku-5-5`) alterna el modelo y `buscar_fragmentos`, y `claude_code`/`sonnet` en la búsqueda web (hasta 8 turnos con WebSearch y WebFetch) |
| GGA, Gentleman Guardian Angel (revisión de código con IA antes de cada commit), y ruff (analizador y formateador de Python) | Aplicada | [`.gga`](../.gga), [`pyproject.toml`](../pyproject.toml), [`ci.yml`](../.github/workflows/ci.yml) | Revisar cada commit contra `AGENTS.md` y mantener un estilo único | GGA: `claude --print` sin modelo fijado en `.gga` (no determinable); ruff: sin modelo |
| Arquitectura por capas (en lugar de MVC, Model-View-Controller, modelo-vista-controlador) | Aplicada (capas; MVC no) | [`verificar_capas.py`](../scripts/verificar_capas.py), [`AGENTS.md`](../AGENTS.md) | Las interfaces solo llaman a servicios; la regla se comprueba en CI | Desarrollo: F08, `revisor-calidad` (opus) |
| TDD, Test-Driven Development (desarrollo guiado por pruebas), con AAA, Arrange-Act-Assert (preparar, actuar, afirmar) | Parcial | [`tests/`](../tests/), [`web/src/__tests__/`](../web/src/__tests__/), [`web/e2e/`](../web/e2e/) | Cada cambio llega con pruebas; no hay evidencia de prueba previa al código ni de AAA explícito | Desarrollo: F14, F15 y F22, `revisor-calidad` (opus); pruebas: `extractivo` |
| uv (gestor de paquetes y proyectos de Python) y Docker (contenedores) | Parcial (uv aplicada; Docker definido) | [`uv.lock`](../uv.lock), [`docker-compose.yml`](../docker-compose.yml), [`Dockerfile`](../infra/docker/Dockerfile) | Entorno reproducible; Docker no se ejecuta en CI ni se verificó en esta revisión | Sin modelo |
| Gitflow (flujo de ramas de Git) con PR, Pull Request (solicitud de integración), y Conventional Commits (convención de mensajes de commit) | Parcial (PR y Conventional Commits sí; Gitflow no) | [ADR-021](arquitectura/adr/ADR-021-flujo-pull-requests.md), [`CONTRIBUTING.md`](../CONTRIBUTING.md); 21 PR con squash merge (#1 a #21); 61 de 63 commits de `main` con formato `tipo: descripción` (7 con el tipo propio `datos`) | Cada cambio entra por PR con CI previo; historial lineal y legible; sin `develop` ni `release` | Sin modelo |
| CI/CD, Continuous Integration / Continuous Delivery (integración y entrega continuas), con GitHub Actions | Parcial (CI sí; CD no) | [`ci.yml`](../.github/workflows/ci.yml) | Ruff, mypy, capas, pytest, Vitest y build en Ubuntu y Windows en cada PR y en cada push a `main`; sin despliegue | Sin modelo |
| MCP, Model Context Protocol (protocolo de contexto de modelos) | Aplicada | [`.mcp.json`](../.mcp.json), [`mcp_server/`](../src/fabrica_autopartes/mcp_server/) | Acceso de solo lectura de los agentes a la base de conocimiento | Desarrollo: F06, `revisor-calidad` (opus), y F24, `ingeniero-3d-frontend` (sonnet); aplicación: `responder_pregunta` es extractiva, sin LLM |
| Medallion Architecture (arquitectura medallón: capas Bronze/Silver/Gold, bronce/plata/oro) | Aplicada | [ADR-002](arquitectura/adr/ADR-002-medallion-archivos.md), [`pipelines/`](../src/fabrica_autopartes/pipelines/) | Separar dato crudo, limpio y listo para el LLM, con trazabilidad | Desarrollo: F09 a F11, `ingeniero-datos` (sonnet); aplicación: sin LLM |
| Responsible Web Scraping (extracción web responsable: robots.txt, pausas, User-Agent identificable) | Aplicada | [`scraping/`](../src/fabrica_autopartes/scraping/), [ADR-015](arquitectura/adr/ADR-015-proteccion-antibots.md), [`test_rastreo.py`](../tests/integration/test_rastreo.py) | Extraer solo lo permitido y sin eludir protecciones | Desarrollo: F09, `ingeniero-datos` (sonnet); aplicación: sin LLM |
| Prompt Engineering (ingeniería de instrucciones) versionado, con evaluación v1–v3 | Aplicada | [`llm/prompts/`](../src/fabrica_autopartes/llm/prompts/), [bitácora](prompts/bitacora_experimentos.md), [`evaluacion/resultados/`](../evaluacion/resultados/) | Comparar técnicas con el mismo banco de 24 preguntas (v1 y v2) | Desarrollo: F12 y F13, `ingeniero-llm` (sonnet); aplicación: `claude_code`/`sonnet` en el Q&A (v1–v3) y `claude-haiku-5-5` en el agente (`agente.yaml` v1 y v2); `extractivo` como línea base y en pruebas |
| Método Anatomy (máquinas interactivas para explicar mecanismos) | Aplicada | [`fna-maquinas-anatomia`](../skills/fna-maquinas-anatomia/SKILL.md), [`plantilla/`](../web/src/componentes/plantilla/) | Una pregunta y una relación medible por máquina | Desarrollo: F21, `ingeniero-3d-frontend` (sonnet) |
| ADR, Architecture Decision Record (registro de decisión de arquitectura) | Aplicada | [`arquitectura/adr/`](arquitectura/adr/) (31) | Dejar el porqué de cada decisión estructural | Desarrollo: F08, `revisor-calidad` (opus), y fases técnicas |
| Revisión de skills con SkillSpector (escáner de seguridad para skills de agentes) | Aplicada | [bitácora](prompts/bitacora_experimentos.md) S-01 a S-10, [`fna-seguridad`](../skills/fna-seguridad/SKILL.md) | Ninguna skill o herramienta de terceros se instala sin escaneo ni análisis manual | Escáner con `--no-llm`; análisis manual en la sesión principal |
| Independent Critical Review (revisión crítica independiente) | Aplicada | [bitácora](prompts/bitacora_experimentos.md) E-04 (hallazgo H-03); fases F06, F08, F14, F15 y F22 | Un revisor que no edita código contrasta cada entrega con `AGENTS.md` | Desarrollo: `revisor-calidad` (opus) |
| Graphify — Code Knowledge Graph (grafo de conocimiento del código) | Aplicada (excepción S-08) | [`mapa_codigo.svg`](imagenes/mapa_codigo.svg), [`GRAPH_REPORT.md`](graphify/GRAPH_REPORT.md), [ADR-020](arquitectura/adr/ADR-020-graphify-mapa-del-codigo.md) | Mapa de dependencias y comunidades del código | Sin LLM: AST local con `--code-only` y `GRAPHIFY_BACKEND=none` |
| Model Card (tarjeta del modelo) | Aplicada (retrospectivo) | [`model_card.md`](model_card.md) | Reunir uso previsto, datos, evaluación, costos, limitaciones y riesgos del agente en un solo documento | Documenta `anthropic`/`claude-haiku-5-5`; cifras de A-08, A-10 y A-11 |
| KPI, Key Performance Indicators (indicadores clave de desempeño), y OKR, Objectives and Key Results (objetivos y resultados clave) | Parcial (KPI aplicados, retrospectivo; umbrales y OKR en propuesta) | [`kpi_okr.md`](kpi_okr.md) | Seguir exactitud, alucinaciones, URL inválidas, costo, latencia y fundamentación contra un umbral | Sin modelo; valores medidos con `claude-haiku-5-5` |
| Kanban (tablero de flujo visual) con estimación Fibonacci y límite de WIP, Work In Progress (trabajo en curso) | Aplicada (puntos como estimación) | [`kanban.md`](kanban.md) | Ordenar el trabajo pendiente con un máximo de 2 tareas en curso | Sin modelo |
| CRISP-DM, Cross-Industry Standard Process for Data Mining (proceso estándar intersectorial para minería de datos) | Aplicada (mapeo retrospectivo) | [`crisp_dm.md`](crisp_dm.md) | Ubicar las etapas reales en las seis fases y explicar las vueltas de la evaluación a los datos y al modelado | Sin modelo |
| CPM, Critical Path Method (método de la ruta crítica), y Gantt Chart (diagrama de Gantt) | Aplicada (realizado retrospectivo; planificado como estimación) | [`cronograma.md`](cronograma.md) | Identificar las tareas sin holgura hasta la sustentación (fecha por confirmar) | Sin modelo; Gantt en Mermaid, sin herramientas instaladas |

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
<summary><b>Memoria persistente con Engram (modo manual)</b></summary>

Engram v3.6.2 y su plugin para Claude Code se instalaron con versión fijada tras un escaneo de seguridad (ADR-018,
S-05). Las memorias se guardan en **modo manual**: el modo automático de Claude Code no puede revisar `mem_save`
porque el plugin modifica la llamada. Cada guardado registra antes la sesión con `mem_session_start` en
`/mnt/c/fabrica-nacional-autopartes`, la ruta que Engram detecta, y usa el proyecto `fabrica-nacional-autopartes`
de forma explícita. Con la ruta de Windows, Engram asigna el proyecto «unknown» (A-04).

| Observación | Contenido | Entrada de la bitácora |
|---|---|---|
| 19 | Proveedor del agente: Claude Haiku 5.5 vía API (ADR-026) | A-04 |
| 20 | Validación real del agente con Haiku 5.5, costo medido y fallos | A-08 |
| 21 | URL del texto de las fuentes citadas y fundamentación sin URL | A-09 |
| 22 | Banco de preguntas v2 alineado con el Gold | A-10 |
| 23 | El CI reconstruye `data/gold` desde la semilla antes de pytest | A-10 (corrección) |
| 24 | Recuperador híbrido RRF fijo por configuración en el agente (ADR-031) | A-11 |

Los ids se comprobaron con `mem_search` y `mem_context` el 2026-11-10. La bitácora solo registra el id de la 19
(A-04). La memoria local de Claude Code (`MEMORY.md`) sigue guardando las convenciones de trabajo del equipo.
</details>

<details>
<summary><b>ReAct, Reasoning and Acting (razonar y actuar), con pruebas automáticas (parcial)</b></summary>

En desarrollo, el agente alterna razonamiento y acciones (editar, ejecutar `verificar_calidad.ps1`, corregir) hasta
que pruebas, lint, tipos y GGA pasan. En la aplicación, el agente (`create_agent`, ADR-024) alterna llamadas al modelo
y a `buscar_fragmentos` hasta responder, con un tope de iteraciones (`recursion_limit`). La búsqueda web complementaria
usa WebSearch y WebFetch en hasta 8 turnos. No hay un prompt con el formato ReAct explícito.
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

Los 42 commits anteriores a la ADR-021 se integraron a `main` sin PR: ramas de funcionalidad
(`add-honda-moto-machine`, `feature/busqueda-web`) y avance rápido. Desde la ADR-021 (2026-11-07), cada cambio entra
por PR, con CI previo y squash merge: 21 PR (#1 a #21) hasta `d55229f`. No hay rama `develop` ni ramas `release`, así
que Gitflow no se aplica. De los 63 commits de `main`, 61 usan el formato `tipo: descripción` (`feat`, `fix`, `docs`,
`chore` y el tipo propio `datos`, este en 7). Los dos restantes son títulos de PR sin tipo: «banco v2 gold (#20)» y
«fix/json no objeto (#8)».
</details>

<details>
<summary><b>CI/CD, Continuous Integration / Continuous Delivery, con GitHub Actions (parcial)</b></summary>

GitHub Actions ejecuta Ruff, mypy, verificación de capas, pytest con cobertura mínima del 85 % y Vitest con la
compilación del visor en Ubuntu y Windows en cada PR y en cada push a `main`. No hay entrega ni despliegue automático: el sistema se ejecuta en
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
con few-shot) y cada versión declara su técnica e hipótesis. El prompt del agente (`agente.yaml`) tiene v1 y v2
(ADR-029). La evaluación con 24 preguntas (banco v1 y, desde A-10, banco v2) compara las versiones con Claude y con la
línea base extractiva. Los resultados están en `evaluacion/resultados/`, y los del agente se resumen en la
[Model Card](model_card.md).
</details>

<details>
<summary><b>Método Anatomy</b></summary>

Cada máquina (freno, prensa, línea y motocicleta) responde una pregunta con una relación medible, con 2 a 4 controles,
cifras junto a las piezas, recorrido de menos de 30 s y modo experimento. La plantilla común está en
`web/src/componentes/plantilla/`.
</details>

<details>
<summary><b>ADR, Architecture Decision Record</b></summary>

Treinta y un registros con contexto, decisión, alternativas y consecuencias. Van desde el uso de archivos para
Medallion hasta el proveedor `claude_code`, la motocicleta de referencia, Engram y GGA, la búsqueda web
complementaria, Graphify, el flujo con PR, el agente con Claude Haiku 5.5 y el recuperador híbrido (ADR-031).
</details>

<details>
<summary><b>Revisión de skills con SkillSpector</b></summary>

Cada skill o herramienta de terceros se escanea con SkillSpector (`--no-llm`) y se rechaza con 51 o más puntos, salvo
excepción documentada con análisis manual de cada hallazgo alto y versión fijada (S-05 Engram, S-06 GGA y S-08
Graphify). Archify se descartó dos veces (S-04 y S-07) y el descarte se reafirmó el 2026-11-10 (ver «No aplicadas»).
El escaneo de Antigravity CLI sigue pendiente (R-06 y [tablero](kanban.md)).
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

<details>
<summary><b>Model Card (retrospectivo)</b></summary>

La [Model Card](model_card.md) del agente reúne la configuración (Claude Haiku 5.5, prompt v2, recuperador híbrido),
el uso previsto y lo que queda fuera de alcance, los datos (Gold de 167 fragmentos, bancos v1 y v2), la evaluación de
A-08, A-10 y A-11, los costos medidos, las limitaciones (P08, P18, criterio estricto de las ausentes, variación sin
temperatura), los riesgos con su mitigación y el comando para reproducir la evaluación. Se redactó a posteriori sobre
ejecuciones ya registradas y no hizo llamadas reales.
</details>

<details>
<summary><b>KPI y OKR (KPI retrospectivos; umbrales y OKR en propuesta)</b></summary>

[`kpi_okr.md`](kpi_okr.md) define seis KPI sobre métricas ya medidas: exactitud global, alucinaciones en ausentes, URL
inválidas, costo por pregunta, latencia mediana y tasa fundamentada. Cada uno lleva su valor de A-11, su fuente y un
umbral propuesto. Los tres OKR (confiabilidad, cumplimiento y entrega) son una propuesta para la fase siguiente. El
KPI de alucinaciones es todavía una medición manual.
</details>

<details>
<summary><b>Kanban con Fibonacci y límite WIP (puntos como estimación)</b></summary>

El [tablero](kanban.md) tiene las columnas Por hacer, En curso y Hecho, y un límite de 2 tareas en curso, justificado
por la aprobación humana de cada paso, la espera del CI y los archivos compartidos entre PR. Las tareas pendientes
llevan puntos Fibonacci (estimación) con un criterio explícito. La columna «Hecho» resume los PR #1 a #21
(retrospectivo).
</details>

<details>
<summary><b>CRISP-DM (mapeo retrospectivo)</b></summary>

[`crisp_dm.md`](crisp_dm.md) ubica las etapas reales en las seis fases de CRISP-DM, enlaza la evidencia de cada una y
registra las vueltas atrás (de la evaluación al banco v2, al recuperador híbrido y a la métrica de fundamentación).
También explica la relación con Medallion: Medallion es la arquitectura de datos de la fase de preparación y CRISP-DM
es el proceso completo. El proyecto no se planificó con CRISP-DM.
</details>

<details>
<summary><b>CPM y Gantt (realizado retrospectivo; planificado como estimación)</b></summary>

El [cronograma](cronograma.md) calcula la ruta crítica de las tareas pendientes, con duraciones estimadas, holguras y
un plan nivelado al límite WIP de 2, en días relativos (D+N) hasta la sustentación, cuya fecha está por confirmar.
Incluye dos diagramas de Gantt en Mermaid: los PR #1 a #21 con la fecha del merge según `git log` (retrospectivo) y
las tareas pendientes (estimación).
</details>

## No aplicadas

<details>
<summary><b>Metodologías sin evidencia en el repositorio</b></summary>

- **Data Thinking** (pensamiento orientado a datos) y **BMC, Business Model Canvas** (lienzo del modelo de negocio):
  no hay documentos de negocio; las métricas existentes son técnicas.
- **Archify** (diagramas de arquitectura generados por agentes): evaluada y descartada (bitácora S-04 y S-07). El
  descarte se reafirmó el 2026-11-10: el escaneo dio 100/100 («DO NOT INSTALL») y la revisión manual encontró código
  ejecutable con acceso a red, un servidor local y persistencia fuera de su carpeta, lo que incumple el criterio de
  excepción aplicado a Engram y GGA. Mermaid cubre la necesidad, incluido el Gantt del [cronograma](cronograma.md).
  Cualquier reconsideración exige un escaneo nuevo de la versión vigente con SkillSpector.
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
