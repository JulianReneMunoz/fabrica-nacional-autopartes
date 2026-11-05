# Guía operativa de desarrollo con agentes (OpenCode y Claude Code)

Generada desde `fases_agentes.yaml`. No avanzar de fase sin cumplir la condición indicada.

## F01 · Preparación del equipo

1. **Herramienta:** Windows Terminal + PowerShell 7
2. **Terminal:** PowerShell (usuario normal)
3. **Comandos:**

```powershell
winget --version
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
wsl --status
```

4. **Explicación:** Verifica el gestor de paquetes winget, habilita la ejecución de scripts firmados o locales para el usuario actual y consulta si WSL2 está presente (solo se instala si Docker Desktop lo requiere).
5. **Agente y prompt:** Ninguno (fase manual)

6. **Archivos:** —
7. **Pruebas:** winget --version devuelve una versión; Get-ExecutionPolicy -Scope CurrentUser devuelve RemoteSigned
8. **Resultado esperado:** Terminal lista para instalar herramientas.
9. **Errores frecuentes:** winget no se reconoce → Instalar o actualizar 'App Installer' desde Microsoft Store.; Los scripts .ps1 se bloquean → Repetir Set-ExecutionPolicy en la misma cuenta; desbloquear con Unblock-File.
10. **Condición para continuar:** winget operativo y política de ejecución configurada.

## F02 · Instalación de herramientas

1. **Herramienta:** winget, instaladores oficiales de uv y Claude Code, npm
2. **Terminal:** PowerShell
3. **Comandos:**

```powershell
.\scripts\instalar_herramientas.ps1
.\scripts\instalar_herramientas.ps1 -Opcionales
.\scripts\verificar_entorno.ps1
```

4. **Explicación:** Instala Git, VS Code, Node.js LTS, Ollama, uv, Claude Code y OpenCode de forma idempotente; con -Opcionales agrega GitHub CLI, MiKTeX y Docker Desktop. El verificador imprime una tabla de versiones.
5. **Agente y prompt:** Ninguno (fase manual)

6. **Archivos:** —
7. **Pruebas:** verificar_entorno.ps1 termina con 'Entorno verificado.'
8. **Resultado esperado:** git, uv, node y ollama disponibles en PATH.
9. **Errores frecuentes:** El comando instalado no se reconoce → Cerrar y abrir la terminal para recargar PATH.; opencode no se encuentra tras npm install -g → Agregar %APPDATA%\npm al PATH del usuario.
10. **Condición para continuar:** Todas las herramientas obligatorias en estado OK.

## F03 · Inicialización del repositorio

1. **Herramienta:** Git, GitHub CLI y uv
2. **Terminal:** PowerShell en la carpeta del proyecto
3. **Comandos:**

```powershell
uv sync
Copy-Item .env.example .env
gh auth login --hostname github.com --git-protocol https --web
.\scripts\publicar_github.ps1
```

4. **Explicación:** Materializa el entorno virtual desde uv.lock, prepara el archivo de secretos local (excluido por .gitignore) y publica todo el proyecto en https://github.com/JulianReneMunoz/fabrica-nacional-autopartes: el script inicializa Git (rama main), crea el primer commit, crea el repositorio con 'gh repo create' (público por defecto; -Privado para privado) y publica la rama.
5. **Agente y prompt:** Ninguno

6. **Archivos:** .venv/, .env
7. **Pruebas:** uv run python -c "import fabrica_autopartes; print('ok')"; git status sin cambios pendientes; gh repo view JulianReneMunoz/fabrica-nacional-autopartes --web abre el repositorio; La pestaña Actions muestra el flujo CI en ejecución
8. **Resultado esperado:** Repositorio versionado y entorno reproducible.
9. **Errores frecuentes:** uv sync falla por versión de Python → uv python install 3.12 y repetir uv sync.
10. **Condición para continuar:** Importación del paquete correcta y primer commit publicado.

## F04 · Análisis de requisitos

1. **Herramienta:** OpenCode (agente plan) o Claude Code (subagente analista-requisitos)
2. **Terminal:** PowerShell → opencode
3. **Comandos:**

```powershell
opencode
claude
```

4. **Explicación:** Con el agente en modo plan (solo lectura) se extraen requisitos de los PDF del taller y de las clases.
5. **Agente y prompt:** analista-requisitos

```text
Leer AGENTS.md y los PDF de docs/requisitos/fuentes/. Construir docs/requisitos/matriz_trazabilidad.csv con las columnas id;origen;descripcion;tipo;prioridad;componente;historia;caso_uso;prueba;estado. Clasificar cada fila como Documentado (citar documento y página), Diseño o Extensión. No inventar requisitos. Registrar en docs/requisitos/analisis_documentos.md la información ausente, ambigua o contradictoria. Redacción impersonal. No modificar archivos fuera de docs/requisitos/.
```

6. **Archivos:** docs/requisitos/matriz_trazabilidad.csv, docs/requisitos/analisis_documentos.md
7. **Pruebas:** uv run python scripts/generar_matriz.py
8. **Resultado esperado:** Matriz con al menos los 20 requisitos del taller y su origen.
9. **Errores frecuentes:** El agente atribuye al taller funciones no pedidas → Rechazar el cambio y exigir cita de página.
10. **Condición para continuar:** Cada requisito documentado tiene página de origen verificable.

## F05 · Configuración de agentes

1. **Herramienta:** OpenCode y Claude Code
2. **Terminal:** PowerShell
3. **Comandos:**

```powershell
opencode auth login
opencode auth list
claude
uv run python scripts/sincronizar_skills.py
```

4. **Explicación:** Autentica proveedores. En OpenCode se usa un proveedor con clave de API o Ollama local; la suscripción Claude Pro/Max solo se usa en Claude Code y claude.ai según los términos vigentes.
5. **Agente y prompt:** Ninguno

```text
Revisar opencode.json y .claude/settings.json. Confirmar que bash está en 'ask' salvo pruebas y lint, que 'git push' está denegado y que la lectura de .env está bloqueada. Listar los agentes y skills cargados y reportar diferencias con AGENTS.md. No editar archivos.
```

6. **Archivos:** .opencode/skills/, .claude/skills/
7. **Pruebas:** En OpenCode: /models muestra el modelo elegido; En Claude Code: /agents lista los 4 subagentes
8. **Resultado esperado:** Ambas consolas operan con permisos mínimos.
9. **Errores frecuentes:** OpenCode no muestra modelos de Anthropic → Usar clave de API de la Consola u otro proveedor; no usar credenciales de suscripción.; Modelo local lento o sin herramientas → Usar un modelo de código ≥14B o un proveedor en la nube para el agente; llama3.2:3b se reserva para la aplicación.
10. **Condición para continuar:** Agentes visibles y una tarea de solo lectura ejecutada con éxito.

## F06 · Integración MCP

1. **Herramienta:** Servidor MCP fna-conocimiento, Engram (opcional)
2. **Terminal:** PowerShell
3. **Comandos:**

```powershell
uv run fabrica build --fuente semilla
uv run pytest tests/integration/test_mcp.py -q
claude mcp list
engram setup opencode
```

4. **Explicación:** Construye la base para que el servidor tenga datos, prueba el protocolo por stdio y registra servidores.
5. **Agente y prompt:** revisor-calidad

```text
Usar la herramienta MCP estadisticas_base y luego buscar_fragmentos con la consulta "sede principal". Reportar los identificadores devueltos y confirmar que las herramientas son de solo lectura.
```

6. **Archivos:** —
7. **Pruebas:** 6 pruebas MCP aprobadas
8. **Resultado esperado:** El agente consulta la base sin permisos de escritura.
9. **Errores frecuentes:** El servidor no inicia → Ejecutar 'uv run fabrica-mcp' manualmente y revisar stderr.
10. **Condición para continuar:** claude mcp list muestra fna-conocimiento conectado.

## F07 · Generación de especificaciones

1. **Herramienta:** OpenSpec
2. **Terminal:** PowerShell
3. **Comandos:**

```powershell
npm install -g @fission-ai/openspec@latest
openspec init --tools claude,opencode
openspec validate --all
```

4. **Explicación:** Inicializa OpenSpec (si no existe) y valida especificaciones y cambios propuestos.
5. **Agente y prompt:** analista-requisitos

```text
/opsx:propose agregar-<capacidad>. Redactar proposal.md, design.md, tasks.md y el delta de spec con Requirements y Scenarios (WHEN/THEN). Cada tarea termina con un comando de verificación ejecutable.
```

6. **Archivos:** openspec/changes/<cambio>/
7. **Pruebas:** openspec validate --all sin errores
8. **Resultado esperado:** Especificaciones validadas (evidencia: docs/evidencias/openspec_validate.txt).
9. **Errores frecuentes:** Requirement must have at least one scenario → Agregar '#### Scenario:' con viñetas **WHEN**/**THEN**.
10. **Condición para continuar:** Validación sin errores.

## F08 · Diseño de arquitectura

1. **Herramienta:** Claude Code (plan) + skill fna-arquitectura
2. **Terminal:** claude
3. **Comandos:**

```powershell
uv run python scripts/verificar_capas.py
```

4. **Explicación:** Revisa la dirección de dependencias entre capas y registra decisiones en ADR.
5. **Agente y prompt:** revisor-calidad

```text
Aplicar la skill fna-arquitectura sobre src/. Ejecutar scripts/verificar_capas.py. Si aparece una violación, proponer una inversión de dependencia (protocolo en domain/puertos.py) y el ADR asociado.
```

6. **Archivos:** docs/arquitectura/adr/ADR-0NN-*.md
7. **Pruebas:** verificar_capas.py → 0 violaciones
8. **Resultado esperado:** Arquitectura por capas verificable.
9. **Errores frecuentes:** scraping -> pipelines → Tipar el rastreador contra el protocolo AlmacenCapturas (hallazgo real corregido).
10. **Condición para continuar:** 0 violaciones de capas.

## F09 · Implementación y ejecución del scraping

1. **Herramienta:** Claude Code + subagente ingeniero-datos (Sonnet); OpenCode como alternativa
2. **Terminal:** PowerShell en C:\fabrica-nacional-autopartes (o la terminal integrada de Claude Code)
3. **Comandos:**

```powershell
uv run pytest tests/unit/test_scraping.py tests/integration/test_rastreo.py -q
uv run fabrica pipeline --max-paginas 80 --desde-cero
uv run fabrica stats
.\scripts\ejecutar_pipeline.ps1 -MaxPaginas 80 -DesdeCero -Publicar
```

4. **Explicación:** Implementa y prueba el rastreador con un sitio simulado; luego ejecuta el proceso real desde la consola del equipo con Windows 11: 'uv run fabrica pipeline' rastrea autopartesfanalca.com.co y fanalca.com (Bronze), construye Silver y Gold con '--fuente scraping', valida el corpus y genera las gráficas de cada etapa en docs/graficas. El scraping no se ejecuta dentro de un agente sin aprobación: Claude Code solicita permiso porque el comando accede a la red.
5. **Agente y prompt:** ingeniero-datos

```text
Implementar en src/fabrica_autopartes/scraping/ un rastreador BFS que: lea robots.txt antes de cada host, descubra sitemaps, respete Disallow y Crawl-delay, use User-Agent identificable, pausa mínima de 2 s, timeout de 20 s, reintentos con backoff ante 429/5xx, filtre dominios y extensiones no HTML y guarde cada captura en Bronze (HTML + JSONL con url, url_final, fecha, estado, sha256). Escribir pruebas con tests/fixtures/sitio y la biblioteca responses; ninguna prueba accede a Internet.
```

6. **Archivos:** src/fabrica_autopartes/scraping/*.py, src/fabrica_autopartes/pipelines/bronze.py, tests/integration/test_rastreo.py
7. **Pruebas:** Pruebas de scraping en verde; data/bronze/manifiesto.jsonl con capturas reales; data/gold/metricas_etapas.json con fuente 'scraping'; seis PNG en docs/graficas sin la marca 'semilla'
8. **Resultado esperado:** Capturas de los sitios oficiales en Bronze, base Gold reconstruida y gráficas por etapa.
9. **Errores frecuentes:** HTTP 403 o 429 → Aumentar FNA_PAUSA_ENTRE_PETICIONES_S; nunca rotar User-Agent ni eludir bloqueos.; Texto vacío por contenido JavaScript → uv sync --extra dinamico y usar scraping/dinamico.py.; HTTP 202 con SG-Captcha: challenge (autopartesfanalca.com.co) → Protección antibots de SiteGround: no se elude (ADR-015). El host queda registrado como protegido y la base usa la fuente mixta con la lectura web documentada.
10. **Condición para continuar:** Al menos 10 páginas capturadas sin rutas prohibidas.

## F10 · Construcción de pipelines

1. **Herramienta:** Claude Code + subagente ingeniero-datos
2. **Terminal:** claude
3. **Comandos:**

```powershell
uv run fabrica build --fuente scraping
uv run fabrica validate
```

4. **Explicación:** Genera Silver (limpieza y deduplicación) y Gold (Markdown, fragmentos y base consolidada).
5. **Agente y prompt:** ingeniero-datos

```text
Revisar data/gold/base_conocimiento.txt generado desde el scraping. Identificar líneas de menú, avisos legales o textos repetidos que sobrevivieron a la limpieza y ajustar las reglas de pipelines/silver.py (no editar Gold a mano). Agregar una prueba por cada regla nueva.
```

6. **Archivos:** src/fabrica_autopartes/pipelines/silver.py, tests/unit/test_pipelines.py
7. **Pruebas:** fabrica validate → aprobado: true
8. **Resultado esperado:** Corpus limpio y trazable.
9. **Errores frecuentes:** Fragmentos > 600 tokens → Reducir FNA_TAMANO_FRAGMENTO.
10. **Condición para continuar:** Validación aprobada y revisión humana del archivo consolidado.

## F11 · Implementación de persistencia

1. **Herramienta:** Claude Code
2. **Terminal:** PowerShell
3. **Comandos:**

```powershell
uv run alembic upgrade head
uv run pytest tests/integration/test_persistencia_y_evaluacion.py -q
```

4. **Explicación:** Aplica las migraciones del esquema de auditoría y verifica el repositorio.
5. **Agente y prompt:** ingeniero-datos

```text
Si se agrega una columna al modelo ORM, generar la migración con 'uv run alembic revision --autogenerate -m "<descripcion>"', revisarla manualmente y probar upgrade y downgrade sobre una base temporal.
```

6. **Archivos:** alembic/versions/*.py
7. **Pruebas:** test_migracion_alembic_crea_esquema
8. **Resultado esperado:** Esquema versionado.
9. **Errores frecuentes:** Tabla ya existe → Usar una base nueva o 'alembic stamp head' si el esquema se creó con create_all.
10. **Condición para continuar:** Migraciones aplicadas sin errores.

## F12 · Construcción de la API

1. **Herramienta:** Claude Code + skill fna-api
2. **Terminal:** PowerShell
3. **Comandos:**

```powershell
.\scripts\ejecutar_api.ps1
uv run fabrica openapi
```

4. **Explicación:** Levanta FastAPI con recarga y exporta el contrato OpenAPI.
5. **Agente y prompt:** ingeniero-llm

```text
Aplicar la skill fna-api para agregar el endpoint solicitado. Contrato con Pydantic, sin lógica de negocio en la ruta, errores como subclases de ErrorFNA, prueba con TestClient y actualización de la colección Postman.
```

6. **Archivos:** src/fabrica_autopartes/api/, tests/integration/test_api.py
7. **Pruebas:** http://127.0.0.1:8000/docs responde 200; Colección Postman sin fallos
8. **Resultado esperado:** API documentada y probada.
9. **Errores frecuentes:** 503 proveedor_llm_no_disponible → Iniciar Ollama (ollama serve) o configurar clave del proveedor.
10. **Condición para continuar:** Pruebas de API en verde.

## F13 · Desarrollo del frontend

1. **Herramienta:** Claude Code
2. **Terminal:** PowerShell
3. **Comandos:**

```powershell
.\scripts\ejecutar_app.ps1
uv run pytest tests/e2e -q
```

4. **Explicación:** Ejecuta Streamlit y sus pruebas extremo a extremo con AppTest.
5. **Agente y prompt:** ingeniero-llm

```text
Mejorar frontend/app.py sin romper las pruebas e2e: las pestañas Q&A, Resumen y FAQ deben quedar visibles; cada respuesta muestra fundamentación, confianza, modo de contexto y fuentes.
```

6. **Archivos:** frontend/app.py, tests/e2e/test_streamlit.py
7. **Pruebas:** 3 pruebas e2e aprobadas
8. **Resultado esperado:** Interfaz lista para la demostración.
9. **Errores frecuentes:** Puerto 8501 ocupado → uv run streamlit run frontend/app.py --server.port 8502
10. **Condición para continuar:** Demostración manual de las tres funcionalidades.

## F14 · Integración de componentes

1. **Herramienta:** Claude Code + subagente revisor-calidad
2. **Terminal:** claude
3. **Comandos:**

```powershell
uv run fabrica ask "¿Dónde queda la sede principal?" --proveedor ollama
```

4. **Explicación:** Prueba el recorrido completo con el LLM real.
5. **Agente y prompt:** revisor-calidad

```text
Ejecutar las preguntas P01, P05, P20 y P24 de evaluacion/preguntas.yaml por CLI con el proveedor ollama y prompts v1, v2 y v3. Registrar respuestas literales en docs/prompts/bitacora_experimentos.md.
```

6. **Archivos:** docs/prompts/bitacora_experimentos.md
7. **Pruebas:** P20 devuelve la frase de rechazo con v2 y v3; P24 queda bloqueada
8. **Resultado esperado:** Integración verificada con LLM real.
9. **Errores frecuentes:** JSON inválido en v3 → El analizador tolerante extrae el objeto; si persiste, bajar temperatura a 0.
10. **Condición para continuar:** Recorrido completo sin errores.

## F15 · Pruebas

1. **Herramienta:** pytest, Ruff, mypy, evaluación
2. **Terminal:** PowerShell
3. **Comandos:**

```powershell
.\scripts\verificar_calidad.ps1
uv run fabrica evaluate --proveedor ollama --version-prompt v1
uv run fabrica evaluate --proveedor ollama --version-prompt v3
```

4. **Explicación:** Ejecuta la batería de calidad y la evaluación de 24 preguntas por versión de prompt.
5. **Agente y prompt:** revisor-calidad

```text
Aplicar la skill fna-pruebas. Comparar los informes de evaluacion/resultados/ de v1 y v3: exactitud, rechazo correcto y tasa fundamentada. Explicar diferencias con ejemplos de respuestas. No inventar cifras.
```

6. **Archivos:** docs/evidencias/calidad_*.txt, evaluacion/resultados/*.md
7. **Pruebas:** 0 pruebas fallidas; Cobertura ≥ 85 %
8. **Resultado esperado:** Evidencia cuantitativa para el informe.
9. **Errores frecuentes:** Evaluación lenta → Usar --modo-contexto seleccion o un modelo más pequeño.
10. **Condición para continuar:** Métricas registradas.

## F16 · Corrección de defectos

1. **Herramienta:** Claude Code
2. **Terminal:** claude
3. **Comandos:**

```powershell
uv run pytest -q --lf
```

4. **Explicación:** Reejecuta solo las pruebas que fallaron en la última corrida.
5. **Agente y prompt:** ingeniero-llm / ingeniero-datos

```text
Reproducir el fallo con una prueba mínima, corregir la causa raíz (no la prueba) y ejecutar la batería completa. Documentar el hallazgo en el CHANGELOG del informe.
```

6. **Archivos:** Según defecto
7. **Pruebas:** uv run pytest -q
8. **Resultado esperado:** Defecto corregido con prueba de regresión.
9. **Errores frecuentes:** —
10. **Condición para continuar:** Batería en verde.

## F17 · Despliegue

1. **Herramienta:** Docker Desktop (opcional) o ejecución local
2. **Terminal:** PowerShell
3. **Comandos:**

```powershell
docker compose up --build
docker compose exec ollama ollama pull llama3.2:3b
```

4. **Explicación:** Levanta Ollama, API e interfaz en contenedores.
5. **Agente y prompt:** Ninguno

6. **Archivos:** —
7. **Pruebas:** http://localhost:8501 y http://localhost:8000/salud responden
8. **Resultado esperado:** Servicios en contenedores.
9. **Errores frecuentes:** WSL2 no instalado → wsl --install en PowerShell como administrador y reiniciar.
10. **Condición para continuar:** Servicios saludables.

## F18 · v2.0 · Diseño del modelo de componentes y articulaciones

1. **Herramienta:** Claude Code + subagente arquitecto-mecanico-3d (Opus)
2. **Terminal:** claude --model opus
3. **Comandos:**

```powershell
uv run pytest tests/unit/test_simulador.py -q
```

4. **Explicación:** Define piezas, subconjuntos, articulaciones, límites, despiece reversible y orden de desmontaje del freno de disco.
5. **Agente y prompt:** arquitecto-mecanico-3d

```text
Diseñar en src/fabrica_autopartes/simulador/ el modelo Pydantic de Pieza, Articulacion (fija, rotacional, prismática, esférica, compuesta), Subconjunto y Ensamblaje, y el catálogo del freno de disco con pinza flotante (cubo, disco, espárragos, soporte, cuerpo de pinza, pistón, pastillas, pasadores y tornillos). Toda dimensión se marca 'demostrativo'. Definir límites, retirar_antes sin ciclos y direcciones de despiece. No redactar procedimientos de reparación ni de seguridad.
```

6. **Archivos:** src/fabrica_autopartes/simulador/*.py, tests/unit/test_simulador.py
7. **Pruebas:** Jerarquía, identificadores, transformaciones, límites y reversibilidad en verde
8. **Resultado esperado:** Modelo mecánico validado y documentado.
9. **Errores frecuentes:** Ciclo en retirar_antes → Revisar dependencias; la secuencia usa orden topológico.
10. **Condición para continuar:** Revisión del revisor-calidad (Opus) sin hallazgos bloqueantes.

## F19 · v2.0 · Generación procedural del modelo 3D

1. **Herramienta:** Claude Code + subagente ingeniero-3d-frontend (Sonnet)
2. **Terminal:** PowerShell
3. **Comandos:**

```powershell
uv run fabrica simulador generar
uv run fabrica simulador validar
uv run pytest tests/integration/test_generacion_3d.py -q
```

4. **Explicación:** Genera web/public/modelos/freno_disco.glb y su manifiesto con trimesh y manifold3d desde la CLI.
5. **Agente y prompt:** ingeniero-3d-frontend

```text
Implementar simulador/generacion.py: una malla cerrada por pieza según su primitiva, material PBR, nodo GLB con el id de la pieza y manifiesto con sha256, volumen y límites. La salida debe ser reproducible (mismo hash con los mismos parámetros).
```

6. **Archivos:** src/fabrica_autopartes/simulador/generacion.py, web/public/modelos/freno_disco.glb
7. **Pruebas:** Mallas cerradas; GLB con 15 nodos; hash reproducible
8. **Resultado esperado:** Modelo GLB demostrativo y trazable.
9. **Errores frecuentes:** Malla no cerrada → Revisar operaciones booleanas de manifold3d y parámetros positivos.
10. **Condición para continuar:** simulador validar → aprobado.

## F20 · v2.0 · API del simulador, RAG y persistencia en PostgreSQL

1. **Herramienta:** Claude Code + subagentes ingeniero-3d-frontend e ingeniero-llm (Sonnet)
2. **Terminal:** PowerShell
3. **Comandos:**

```powershell
docker compose up -d postgres
uv run alembic upgrade head
uv run pytest tests/integration/test_api_simulador.py tests/integration/test_postgresql.py -q
```

4. **Explicación:** Expone /api/v1/simulador (cinemática, despiece, cálculo, preguntas, estados y eventos) y /api/v1/maquinas.
5. **Agente y prompt:** ingeniero-3d-frontend

```text
Implementar las rutas del simulador con validación Pydantic; rechazar con 422 identificadores inexistentes, valores no finitos o fuera de límites. En /preguntar separar información documentada (fragmentos con URL) de datos del modelo y rechazar preguntas de reparación o seguridad.
```

6. **Archivos:** src/fabrica_autopartes/api/routes/simulador.py, src/fabrica_autopartes/services/simulador.py, alembic/versions/0002_simulador.py
7. **Pruebas:** Pruebas de API y PostgreSQL en verde
8. **Resultado esperado:** API documentada en /docs.
9. **Errores frecuentes:** connection refused en PostgreSQL → docker compose ps; verificar FNA_URL_BASE_DATOS.
10. **Condición para continuar:** Pruebas de API en verde.

## F21 · v2.0 · Visor 3D y biblioteca de máquinas (Anatomy)

1. **Herramienta:** Claude Code + subagente ingeniero-3d-frontend (Sonnet) + skill Anatomy
2. **Terminal:** PowerShell en web/
3. **Comandos:**

```powershell
npx skills add wheresryan22/anatomy -g -a claude-code
npm ci
npm run typecheck
npm test
npm run build
```

4. **Explicación:** Construye el visor React Three Fiber y la biblioteca de máquinas con datos del scraping.
5. **Agente y prompt:** ingeniero-3d-frontend

```text
Implementar en web/ la biblioteca (tarjetas con pregunta, una línea, relación, datos de empresa con URL y botón Abrir máquina) y las máquinas freno 3D, prensa y línea. Cada máquina: 2–4 controles, correr/pausar/reiniciar, cámara lenta, cifras junto a las piezas, idea principal, revisión crítica, recorrido ?tour=1 menor a 30 s y modo experimento. El freno incluye órbita, zoom, selección, árbol, ficha, despiece/reensamblaje, visibilidad, transparencia, sección, reinicio de cámara, PNG y lecturas.
```

6. **Archivos:** web/src/**/*.tsx, web/src/modelos/*.ts, web/src/__tests__/*.ts*
7. **Pruebas:** Vitest en verde (réplica TS comparada con Python); npm run build sin errores
8. **Resultado esperado:** Visor servido por FastAPI en http://127.0.0.1:8000/app/.
9. **Errores frecuentes:** Pantalla en blanco en /app → Ejecutar npm run build; la API monta web/dist solo si existe.
10. **Condición para continuar:** Pruebas del visor en verde.

## F22 · v2.0 · Pruebas de extremo a extremo y videos del recorrido

1. **Herramienta:** Playwright con Chrome del sistema + FFmpeg
2. **Terminal:** PowerShell en web/
3. **Comandos:**

```powershell
npx playwright test --project=funcional
npx playwright test --project=recorrido
```

4. **Explicación:** Verifica biblioteca, freno 3D, prensa y línea; mide FPS; graba los recorridos en docs/videos/*.mp4.
5. **Agente y prompt:** revisor-calidad

```text
Ejecutar las pruebas de extremo a extremo y revisar las capturas de docs/capturas/v2 y los videos de docs/videos. Reportar errores de consola, textos superpuestos y cualquier cifra sin procedencia.
```

6. **Archivos:** docs/capturas/v2/*.png, docs/videos/*.mp4
7. **Pruebas:** 7 pruebas en verde; videos de menos de 30 s
8. **Resultado esperado:** Evidencias visuales para la presentación.
9. **Errores frecuentes:** ffmpeg no se reconoce → winget install --id Gyan.FFmpeg -e y reabrir la terminal.
10. **Condición para continuar:** Sin hallazgos bloqueantes.

## F23 · v2.0 · Integración en Streamlit

1. **Herramienta:** Claude Code (Sonnet)
2. **Terminal:** PowerShell
3. **Comandos:**

```powershell
.\scripts\ejecutar_api.ps1
uv run streamlit run frontend/app.py
uv run pytest tests/e2e/test_streamlit.py -q
```

4. **Explicación:** Streamlit sigue como interfaz principal: pestañas Proceso de datos (gráficas por etapa) y Simulador 3D (enlace e iframe).
5. **Agente y prompt:** ingeniero-3d-frontend

```text
Agregar las pestañas Proceso de datos y Simulador 3D. La primera muestra el flujo, las métricas y las seis gráficas con su explicación; la segunda enlaza e incrusta el visor y lista las máquinas con sus datos y URL.
```

6. **Archivos:** frontend/app.py, tests/e2e/test_streamlit.py
7. **Pruebas:** AppTest sin excepciones
8. **Resultado esperado:** Interfaz empresarial integrada.
9. **Errores frecuentes:** El iframe no carga → Iniciar la API y compilar web/; revisar FNA_URL_VISOR.
10. **Condición para continuar:** Pestañas operativas.

