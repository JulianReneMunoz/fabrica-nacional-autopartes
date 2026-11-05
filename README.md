# Fábrica Nacional de Autopartes — Base de Conocimiento Semántico, Sistema Q&A y Simulador 3D (v2.0)

Núcleo de conocimiento para un futuro asistente virtual de **Fábrica Nacional de Autopartes (Fanalca)**:
web scraping responsable de los sitios oficiales, arquitectura de datos Medallion con gráficas por etapa,
base de conocimiento consolidada y tres tareas LLM con LangChain — **Resumen**, **FAQ** y **Q&A** —
expuestas en Streamlit, API REST, CLI y MCP. La **versión 2.0** agrega un simulador 3D de ensamblajes
(freno de disco) y una biblioteca de máquinas interactivas alimentada por los datos del scraping.

Proyecto técnico independiente. No es un canal oficial de Fanalca.
Especificación vigente: [`docs/prompt_maestro_v2.md`](docs/prompt_maestro_v2.md).

> **Estado de los datos:** el repositorio incluye una base de demostración (corpus semilla y lectura web de
> autopartesfanalca.com.co, con su URL) para que la aplicación funcione sin red. La base definitiva se obtiene
> ejecutando el scraping en el computador local con **`uv run fabrica pipeline`** (ver
> [¿Dónde se ejecuta el scraping?](#dónde-se-ejecuta-el-scraping)). La interfaz y las gráficas indican la fuente.

Repositorio: **https://github.com/JulianReneMunoz/fabrica-nacional-autopartes**

## Ruta de trabajo en Windows 11 (resumen)
```powershell
# 1. Proyecto en C:\fabrica-nacional-autopartes y entorno
cd C:\fabrica-nacional-autopartes
.\scripts\preparar_proyecto.ps1                 # uv sync, .env, base, pruebas, visor 3D
# 2. Publicar todo el proyecto en GitHub (cuenta JulianReneMunoz)
.\scripts\publicar_github.ps1                   # -Privado para un repositorio privado
# 3. Scraping real + gráficas + evidencias publicadas en GitHub
.\scripts\ejecutar_pipeline.ps1 -MaxPaginas 80 -DesdeCero -Publicar
# 4. Demostración
.\scripts\ejecutar_api.ps1                      # API y visor 3D → http://127.0.0.1:8000/app/
.\scripts\ejecutar_app.ps1                      # Streamlit → http://localhost:8501
```

## Contenido
[Contexto](#contexto-y-problema) · [Arquitectura](#arquitectura) · [Tecnologías](#tecnologías) ·
[Instalación](#instalación-windows-11) · [Scraping](#dónde-se-ejecuta-el-scraping) ·
[Proceso de datos](#proceso-de-datos-explicado-con-gráficas) · [Ejecución](#ejecución) · [API](#api) ·
[Frontend](#frontend) · [Versión 2.0](#versión-20-simulador-3d-y-biblioteca-de-máquinas) ·
[Agentes y modelos](#claude-code-modelos-por-especialidad-y-mcp) · [Pruebas](#pruebas) ·
[Estructura](#estructura-del-repositorio) · [Seguridad](#seguridad) · [Limitaciones](#limitaciones) ·
[Problemas frecuentes](#resolución-de-problemas) · [Licencias](#licencias) · [Referencias](#referencias)

## Contexto y problema
Necesidad de un canal de comunicación automatizado y preciso para Fanalca (grupo industrial de Yumbo, Valle del
Cauca, con negocios de motocicletas y autos Honda, tubería de acero, autopartes, equipos ambientales e
infraestructura vial). Un cliente que contacta por primera vez pregunta por sedes, productos, historia, contacto
y procesos básicos; las respuestas deben provenir solo de información publicada por la empresa.

## Objetivos
- Extraer por web scraping la información pública de https://autopartesfanalca.com.co/ y https://www.fanalca.com/.
- Limpiar, segmentar y consolidar el conocimiento (`data/gold/base_conocimiento.txt`) explicando cada etapa con gráficas.
- Responder preguntas **basándose únicamente en el contexto**, con rechazo explícito ante datos ausentes.
- Implementar Resumen, FAQ y Q&A con LangChain y documentar la experimentación con prompts.
- Evaluar con 24 preguntas (≥ 20 exigidas) y demostrar en Streamlit.
- v2.0: simulador 3D demostrativo del freno de disco y biblioteca de máquinas (método Anatomy).

## Alcance
| Incluido (Módulo 1) | Extensiones implementadas | Fuera de alcance |
|---|---|---|
| Scraping de los sitios oficiales, Medallion, gráficas por etapa, chunking, prompt de sistema con la base completa, Resumen/FAQ/Q&A, Streamlit, 24 preguntas | Selección BM25, API FastAPI, servidor MCP, auditoría SQLite/PostgreSQL + Alembic, línea base extractiva, Docker, simulador 3D y biblioteca de máquinas (v2.0) | Embeddings y base vectorial (Módulo 2), memoria conversacional, canales WhatsApp/Telegram (Fase 3), scraping de redes sociales, notebooks, Anaconda |

## Arquitectura
```
autopartesfanalca.com.co ┐
fanalca.com ─────────────┴─robots.txt/sitemaps─▶ Rastreador ─▶ Bronze (HTML + manifiesto + resumen)
                                                                 │ métricas por página
                                                                 ▼
                                         Silver (texto limpio, deduplicado, sin datos personales)
                                                                 ▼
                    Gold (fragmentos.jsonl, base_conocimiento.txt, metricas_etapas.json) ─▶ docs/graficas/*.png
                                                                 ▼
             BaseConocimiento ── contexto completo | selección BM25 ──▶ Cadenas LCEL (v1/v2/v3)
                                                                 ▼                         │
                                   ServicioAsistente / ServicioSimulador ◀─ salvaguardas ──┘──▶ Ollama / OpenAI / Anthropic
                 ┌──────────────┬───────────┬──────────┬──────────────┬─────────────────────────────┐
             Streamlit       FastAPI      CLI    Servidor MCP   SQLite / PostgreSQL     Visor 3D (React Three Fiber, /app)
```
Decisiones en `docs/arquitectura/adr/` (16 ADR). Diagramas en `docs/diagramas/` y en el manual.

## Tecnologías
Python 3.12 · uv · requests · BeautifulSoup + lxml · trafilatura · Playwright (opcional) · matplotlib · LangChain 1.x
(LCEL) · Ollama (`llama3.2:3b` por defecto) · OpenAI / Anthropic (opcionales) · FastAPI · Pydantic 2 · Streamlit ·
SQLAlchemy 2 + Alembic (SQLite y PostgreSQL vía psycopg) · MCP SDK 2.x · trimesh + manifold3d · Vite + React +
TypeScript + three.js + React Three Fiber · pytest · Vitest · Playwright · Ruff · mypy · GitHub Actions · LaTeX + TikZ.

## Requisitos previos
Windows 11 con PowerShell, Git, uv, Node.js LTS (OpenCode, OpenSpec y visor 3D), Ollama (o clave de API de un
proveedor), Claude Code. Opcionales: Docker Desktop (PostgreSQL y contenedores), FFmpeg (videos), MiKTeX, GitHub CLI.

## Instalación (Windows 11)
```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
.\scripts\instalar_herramientas.ps1          # winget + instaladores oficiales (idempotente)
.\scripts\verificar_entorno.ps1              # tabla de versiones
.\scripts\preparar_proyecto.ps1              # uv sync, .env, base semilla, pruebas, ollama pull
cd web; npm ci; npm run build; cd ..         # visor 3D → web/dist (servido por la API en /app)
```
Equivalente manual:
```powershell
uv sync                                      # entorno reproducible desde uv.lock
Copy-Item .env.example .env
ollama pull llama3.2:3b
uv run fabrica build
```

## Dónde se ejecuta el scraping
El scraping es parte del sistema: se ejecuta **en el computador con Windows 11, desde la consola, en la carpeta
del proyecto** (`C:\fabrica-nacional-autopartes`). No se ejecuta desde la interfaz web ni dentro de las pruebas.

```powershell
cd C:\fabrica-nacional-autopartes
uv sync
uv run fabrica pipeline --max-paginas 80     # rastreo → Bronze → Silver/Gold → validación → gráficas
uv run fabrica stats                         # verificar: origen "scraping" en los fragmentos
```
Equivalente con script: `.\scripts\ejecutar_pipeline.ps1 -MaxPaginas 80 -DesdeCero -Publicar` (sincroniza el
entorno, ejecuta el pipeline desde cero, muestra las estadísticas y publica las evidencias en GitHub). Tras ajustar
exclusiones o secciones, `.\scripts\ejecutar_pipeline.ps1 -SoloReconstruir -Publicar` reconstruye la base y las
gráficas desde el Bronze existente, sin volver a rastrear.

> **Protección antibots (ADR-015):** autopartesfanalca.com.co responde `HTTP 202` con `SG-Captcha: challenge`
> (SiteGround). El rastreador no elude el desafío: registra el host como protegido y la base se construye con
> la fuente `mixta`, es decir, todo lo capturado de fanalca.com más la lectura web documentada de
> autopartesfanalca.com.co (`origen: lectura_web`, con URL). `--sin-complemento` usa solo scraping.
- **PowerShell** es la forma directa. **Claude Code** (consola principal del proyecto) puede ejecutar el mismo
  comando desde su terminal; solicita aprobación porque accede a la red (`.claude/settings.json`). OpenCode es la
  alternativa con la misma regla (`opencode.json`, permiso `ask`).
- El agente responsable es `ingeniero-datos` (Sonnet); la fase F09 de la guía operativa trae el prompt listo.
- Tras la ejecución, versionar las evidencias: `data/bronze/manifiesto.jsonl`, `data/bronze/resumen_rastreo.json`,
  `data/gold/` y `docs/graficas/`.
- Pasos individuales: `uv run fabrica scrape --max-paginas 60`, `uv run fabrica build --fuente scraping`,
  `uv run fabrica validate`, `uv run fabrica graficas`.

Bronze conserva el HTML original y un manifiesto con URL, fecha, estado HTTP y SHA-256; la reanudación omite URL
ya capturadas. Silver elimina menús, pies de página repetidos, avisos de cookies y correos no corporativos, y
deduplica (exacto y Jaccard ≥ 0,9). Gold fragmenta por encabezados Markdown con identificadores citables
(`autopartes-productos#000`).

## Proceso de datos explicado con gráficas
`uv run fabrica pipeline` escribe `data/gold/metricas_etapas.json` y genera seis gráficas en `docs/graficas/`:

| Etapa | Gráfica | Qué muestra |
|---|---|---|
| 1. Rastreo responsable | `01_rastreo.png` | URL descubiertas en sitemaps, visitadas, capturadas y descartadas |
| 2. Bronze | `02_bronze_paginas.png` | HTML capturado por página |
| 3. Reducción | `03_reduccion.png` | Bytes de HTML → texto extraído → sin plantilla → texto limpio |
| 4. Silver | `04_limpieza_paginas.png` | Caracteres por página antes y después de limpiar |
| 5. Gold | `05_fragmentos_seccion.png` | Fragmentos por sección (insumo de la base semántica) |
| 6. Gold | `06_tokens_fragmento.png` | Tamaño de los fragmentos frente al límite de 600 tokens |

Las gráficas incluidas se generaron con la base de demostración y lo declaran en su nota; se regeneran tras el
scraping real. Streamlit las explica en la pestaña **Proceso de datos**.

## Ejecución
```powershell
.\scripts\ejecutar_app.ps1                   # Streamlit → http://localhost:8501
.\scripts\ejecutar_api.ps1                   # FastAPI → http://127.0.0.1:8000/docs · visor → /app/
uv run fabrica ask "¿Dónde queda la sede principal?"
uv run fabrica faq -n 8
uv run fabrica summary --enfoque "negocios y productos"
uv run fabrica evaluate --proveedor ollama --version-prompt v3
uv run fabrica simulador generar             # regenera web/public/modelos/freno_disco.glb
uv run fabrica simulador generar --ensamblaje moto_honda   # regenera moto_honda.glb
uv run fabrica faq-visor                     # precalcula data/gold/faq_visor.json (claude_code, sonnet, v3)
```

## API
| Método | Ruta | Descripción |
|---|---|---|
| GET | `/salud` | Disponibilidad |
| GET | `/api/v1/base/estadisticas` | Estadísticas del corpus |
| GET | `/api/v1/base/fragmentos?q=&seccion=&pagina=&tamano=` | Búsqueda BM25 / filtro paginado |
| GET | `/api/v1/base/fragmentos/{id}` | Fragmento por id |
| POST | `/api/v1/tareas/qa` · `/faq` · `/resumen` | Tareas LLM ancladas al contexto |
| GET | `/api/v1/auditoria/interacciones` | Historial paginado |
| GET / POST | `/api/v1/pipeline/ejecuciones` · `/reconstruir` | Historial y reconstrucción (`X-API-Key`) |
| GET | `/api/v1/maquinas` · `/{id}` | Biblioteca de máquinas con datos del scraping |
| GET | `/api/v1/simulador/ensamblajes[/{id}]` · `/jerarquia` · `/piezas` · `/articulaciones` | Modelo de componentes |
| GET | `/api/v1/simulador/ensamblajes/{id}/despiece?factor=` · `/secuencia?modo=` · `/animacion` | Despiece y secuencias |
| POST | `/api/v1/simulador/ensamblajes/{id}/cinematica` · `/calculo-freno` · `/preguntar` | Cálculo validado y RAG por pieza |
| GET / POST | `/api/v1/simulador/ensamblajes/{id}/estados` · `/eventos` | Persistencia de vistas y eventos |

Contrato: `docs/api/openapi.json` (`uv run fabrica openapi`). Colección: `postman/fabrica_autopartes.postman_collection.json`.

## Frontend
Streamlit es la interfaz principal. Pestañas: Panel · Proceso de datos · Q&A · Resumen · FAQ · Laboratorio de
prompts · Evaluación · Base de conocimiento · Simulador 3D · Auditoría. Cada respuesta muestra fundamentación,
confianza, modo de contexto, modelo, latencia y fuentes enlazadas. La pestaña Simulador 3D enlaza e incrusta el visor.

## Versión 2.0: simulador 3D y biblioteca de máquinas
Visor en `http://127.0.0.1:8000/app/` (código en `web/`). Biblioteca de tarjetas: pregunta, una línea, relación,
datos de la empresa con URL y origen, botón **Abrir máquina** y **Recorrido 30 s**.

| Máquina | Pregunta | Relación | Dato de la empresa |
|---|---|---|---|
| Freno de disco (3D) | ¿Cómo convierte un freno de disco la presión hidráulica en fuerza de frenado? | `T = 2·μ·p·A·r` | Productos y clientes |
| Prensa de estampado | ¿Cómo convierte una prensa una lámina en un panel estampado? | `F = L·t·τ` | Planta de Yumbo, paneles estampados |
| Línea de ensamble | ¿Cada cuánto debe salir un chasis? | `takt = disponible / demanda` | 24.000 chasises/año (base de conocimiento) |
| Motocicleta (referencia genérica) con fichas Honda | ¿Cómo convierte una motocicleta Honda el giro del motor en velocidad de la rueda y la palanca en fuerza de frenado? | `v = rpm·2π·R / (i_prim·i_marcha·i_final)` | Planta de ensamble de motocicletas en Acopi, Yumbo |

La motocicleta se abre en `#/maquina/moto_honda` (alias `#/moto`). Es un modelo genérico y esquemático de unos 150 cc,
sin logotipos ni réplica de un modelo comercial; sus parámetros son «supuesto didáctico» salvo los campos
`publicado` de la ficha seleccionada en «Ver con ficha de…». Fichas, supuestos, fuentes y ecuaciones:
[`docs/arquitectura/moto_honda.md`](docs/arquitectura/moto_honda.md) y
[`ADR-017`](docs/arquitectura/adr/ADR-017-motocicleta-referencia-fichas-honda.md). Las respuestas de Fanalca del visor
se precalculan con `uv run fabrica faq-visor`.

Freno 3D: órbita, zoom, selección, árbol, ficha de pieza, modos ensamblado/despiece/reensamblaje/frenado,
velocidad y cámara lenta, visibilidad y aislamiento, transparencia, sección, reinicio de cámara, PNG, lecturas de
posición y ángulo (locales y validadas por la API) y preguntas RAG por pieza. Cada máquina tiene 2–4 controles,
cifras junto a las piezas, idea principal, revisión crítica, modo experimento y recorrido automático (`?tour=1`).
Videos de los recorridos: `docs/videos/*.mp4`; capturas: `docs/capturas/v2/`.

> **Modelo demostrativo:** geometría procedural simplificada y parámetros demostrativos. No es un diseño
> industrial certificado, la animación no valida propiedades mecánicas y no se generan procedimientos de
> reparación ni de seguridad.

## Claude Code, modelos por especialidad y MCP
| Especialidad | Subagente | Modelo |
|---|---|---|
| Requisitos, arquitectura, diseño mecánico 3D, revisión | analista-requisitos, arquitecto-sistema, arquitecto-mecanico-3d, revisor-calidad | Opus |
| Scraping, LLM/RAG, 3D/frontend/API/pruebas, documentación | ingeniero-datos, ingeniero-llm, ingeniero-3d-frontend, documentador | Sonnet |
| Verificaciones rápidas | verificador-rapido | Haiku |

- Subagentes en `.claude/agents/` (campo `model`); espejo en `opencode.json`. Dejar sin definir
  `CLAUDE_CODE_SUBAGENT_MODEL`, que reemplaza el campo `model`.
- Servidor propio `fna-conocimiento` (solo lectura, incluye `consultar_pieza`): `uv run fabrica-mcp`.
- Skills del proyecto: `skills/` (11), sincronizadas con `uv run python scripts/sincronizar_skills.py`.
  Skill externa Anatomy: `npx skills add wheresryan22/anatomy -g -a claude-code` (`/anatomy`).
- Especificaciones: `openspec/` (7 elementos validados con `openspec validate --all`).
- Guía cronológica de 24 fases con prompts listos para copiar: `docs/manuales/guia_operativa_agentes.md`.

> Una suscripción Claude Pro/Max autentica Claude Code y claude.ai; **no** incluye créditos de API ni habilita su
> uso en herramientas de terceros como OpenCode. Para OpenCode usar Ollama u otro proveedor con clave de API.

**Claude sin clave de API (proveedor `claude_code`, ADR-016):** la aplicación invoca `claude -p` con la sesión de
Claude Code de la persona titular de la suscripción, en una carpeta temporal aislada y sin herramientas. Uso previsto:
desarrollo y evaluación local. Para usuarios finales se usa `anthropic` con clave de API.
```powershell
claude                                                   # una vez: iniciar sesión con la cuenta de la suscripción
uv run fabrica ask "¿Dónde queda la sede principal?" --proveedor claude_code --modelo sonnet
uv run fabrica evaluate --proveedor claude_code --modelo sonnet --version-prompt v3
```

## Pruebas
```powershell
uv run pytest -q --cov                       # unitarias, integración (rastreo simulado, API, MCP, Alembic, PostgreSQL, GLB), e2e
uv run ruff check . ; uv run mypy ; uv run python scripts/verificar_capas.py
cd web; npm run typecheck; npm test          # Vitest: réplica TS del cálculo comparada con Python
npx playwright test                          # extremo a extremo con Chrome + videos de los recorridos
.\scripts\verificar_calidad.ps1              # batería Python + evidencia en docs/evidencias/
```
Las pruebas no acceden a Internet (sitio simulado con `responses`) ni requieren GPU (proveedor `extractivo`).

## Estructura del repositorio
```
src/fabrica_autopartes/  core · domain · scraping · pipelines (bronze, silver, gold, graficas) · knowledge · llm
                         simulador (modelos, catalogo_freno, cinematica, fisica_freno, generacion) · repositories
                         services (asistente, simulador, maquinas) · api · mcp_server · cli.py
frontend/app.py          interfaz Streamlit
web/                     visor 3D y biblioteca de máquinas (Vite + React Three Fiber), e2e Playwright
data/seed|bronze|silver|gold   capas de datos
evaluacion/              banco de 24 preguntas y resultados
tests/unit|integration|e2e     pruebas Python
alembic/                 migraciones (0001 auditoría, 0002 simulador)
skills/ .claude/ .opencode/ opencode.json .mcp.json AGENTS.md CLAUDE.md openspec/
docs/                    prompt_maestro_v2 · requisitos · arquitectura/adr · diagramas · graficas · capturas · videos
                         prompts · manuales · api · evidencias · latex
scripts/                 PowerShell y utilidades Python
infra/docker/ docker-compose.yml (postgres, ollama, api, app) .github/workflows/ci.yml postman/
```

## Seguridad
Secretos solo en `.env` (ignorado por Git) · lectura de `.env` denegada a Claude Code · `git push` y borrados
recursivos denegados a los agentes · scraping con aprobación explícita · servidor MCP de solo lectura · detección y
bloqueo de inyección de prompts · delimitación XML del contexto · verificación de citas · anonimización de correos
no corporativos (Ley 1581 de 2012) · scraping limitado a los dominios oficiales y a robots.txt · validación en el
backend de todo valor geométrico enviado por el visor · skills de terceros revisadas antes de usarse.

## Limitaciones
- La base incluida es de demostración; el scraping real debe ejecutarse en el computador local (el entorno de
  construcción no tenía acceso de red a autopartesfanalca.com.co ni a fanalca.com).
- No se ejecutaron evaluaciones con un LLM real; las métricas registradas corresponden a la línea base extractiva.
- Docker y los scripts PowerShell no se ejecutaron en Windows; la sintaxis PowerShell se verificó con PowerShell 7.4.
- BM25 es léxico; la recuperación semántica queda para el Módulo 2.
- El rendimiento del visor se midió con render por software (SwiftShader); con GPU se esperan más fotogramas.

## Resolución de problemas
| Síntoma | Solución |
|---|---|
| `proveedor_llm_no_disponible` | Iniciar Ollama (`ollama serve`) y `ollama pull llama3.2:3b` |
| Respuestas truncadas o ignoran el contexto | Aumentar `FNA_OLLAMA_NUM_CTX` o usar `FNA_MODO_CONTEXTO=seleccion` |
| `base_conocimiento_vacia` | `uv run fabrica build` |
| `fabrica pipeline` termina con código 2 | Ninguna página capturada: revisar `data/bronze/errores.jsonl` y la conexión |
| `/app` responde 404 | Compilar el visor: `cd web; npm ci; npm run build` y reiniciar la API |
| El visor no carga datos de empresa | La API no está activa: `.\scripts\ejecutar_api.ps1` |
| `uv` no se reconoce | Cerrar y abrir la terminal |

## Licencias
Código: MIT. Contenido del corpus: propiedad de Fanalca, usado con fines académicos y citando su fuente.
Modelo 3D: generado por el propio proyecto (sin modelos externos). Dependencias con sus licencias (`uv tree`, `npm ls`).

## Referencias
LangChain · Ollama · FastAPI · Streamlit · Model Context
Protocol · uv (Astral) · OpenSpec (Fission-AI) · Engram y GGA (Gentleman-Programming) · SkillSpector (NVIDIA) ·
trimesh · manifold3d · three.js · React Three Fiber · Anatomy (wheresryan22) · RFC 9309 (robots.txt) ·
Ley 1581 de 2012.
