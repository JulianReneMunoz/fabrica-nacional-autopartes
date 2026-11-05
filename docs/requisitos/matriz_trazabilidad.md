# Matriz de trazabilidad de requisitos

Generada desde `matriz_trazabilidad.csv` con `uv run python scripts/generar_matriz.py`.

| ID | Origen | Descripción | Tipo | Prioridad | Componente | Caso de uso | Prueba de aceptación | Estado |
|---|---|---|---|---|---|---|---|---|
| RF-01 | Taller 1, p.1, §1 Investigación | Investigar la empresa e identificar fuentes públicas (sitio oficial, redes sociales, medios) | Documentado | Alta | docs/requisitos/analisis_documentos.md, config.urls_semilla | CU-01 Configurar fuentes | Revisión documental + test_dominios_permitidos | Parcial: redes sociales y medios registrados como fuentes manuales (sus términos de uso prohíben el scraping) |
| RF-02 | Taller 1, p.1, §1 Definición del alcance | Definir el tipo de preguntas de un cliente en el primer contacto (horarios, sedes, productos, historia, contacto, procesos básicos) | Documentado | Alta | evaluacion/preguntas.yaml (alcance) | CU-04 Consultar Q&A | test_banco_tiene_al_menos_20_preguntas_distintas | Implementado |
| RF-03 | Taller 1, p.1, §2 Extracción de datos | Web scraping del sitio oficial con librerías Python (requests, BeautifulSoup, Selenium) | Documentado | Alta | scraping/rastreador.py, cliente_http.py, extraccion.py, dinamico.py | CU-02 Ejecutar scraping | test_rastreo_completo_respeta_robots_y_limites | Implementado y probado con sitio simulado, ejecución contra el sitio real pendiente en el computador local |
| RF-04 | Taller 1, p.1, §2 Preprocesamiento | Limpiar el texto extraído (eliminar HTML, etc.) | Documentado | Alta | pipelines/silver.py | CU-03 Construir base | test_extraccion_elimina_ruido, test_pipeline_bronze_silver_gold_desde_rastreo | Implementado |
| RF-05 | Taller 1, p.1, §2 Segmentación | Dividir en fragmentos pequeños y semánticamente coherentes (chunks) | Documentado | Alta | pipelines/fragmentacion.py | CU-03 Construir base | test_fragmentacion_respeta_encabezados_y_tamano | Implementado |
| RF-06 | Taller 1, p.1, §2 Nota | Entregar el repositorio con todos los códigos y la base de conocimiento proveniente del scraping | Documentado | Alta | repositorio completo, data/gold | CU-03 Construir base | Inspección del ZIP + uv run fabrica build --fuente scraping | Parcial: se entrega base semilla, la base de scraping se genera con un comando en el computador local |
| RF-07 | Taller 1, p.1, §3 Selección del modelo | Elegir modelo open source vía Ollama o privado vía API | Documentado | Alta | llm/proveedores.py | CU-04 Consultar Q&A | test_crear_modelo_ollama_configurado, test_crear_modelo_sin_clave_falla | Implementado |
| RF-08 | Taller 1, p.1, §3 Framework | Usar un framework LLM (LangChain recomendado o LlamaIndex) para orquestar | Documentado | Alta | llm/cadenas.py (LCEL) | CU-04, CU-05, CU-06 | test_qa_v3_con_modelo_simulado_valida_citas | Implementado |
| RF-09 | Taller 1, p.1, §3 Prompt Engineering | Prompt robusto que responda basándose únicamente en el contexto proporcionado | Documentado | Alta | llm/prompts/qa.yaml v2-v3, llm/salvaguardas.py | CU-04 Consultar Q&A | test_prompts_v2_v3_incluyen_reglas_anti_alucinacion, test_qa_rechazo_normalizado | Implementado |
| RF-10 | Taller 1, p.1, §3 Experimentación | Experimentar con zero-shot, formato del prompt e instrucciones para evitar alucinaciones | Documentado | Alta | catálogo v1/v2/v3, laboratorio de prompts, services/evaluacion.py | CU-07 Comparar prompts | test_catalogo_tiene_tres_versiones_y_variables | Parcial: protocolo y herramientas listos, resultados con LLM real pendientes de ejecución local |
| RF-11 | Taller 1, p.1, §3 Memoria | Consolidar todo el texto limpio en el prompt de sistema (memoria del asistente) | Documentado | Alta | knowledge/base.py (modo completo) | CU-04 Consultar Q&A | test_armar_contexto_modos | Implementado |
| RF-12 | Taller 1, p.1-2, §4 Interfaz (texto parcialmente ilegible) | Interfaz de prueba (Streamlit/Gradio) que reciba una pregunta y muestre la respuesta generada | Documentado | Alta | frontend/app.py | CU-04 Consultar Q&A | test_qa_desde_boton_de_ejemplo | Implementado |
| RF-13 | Taller 1, p.2, §5 Pruebas | Formular al menos 20 preguntas distintas para evaluar precisión y coherencia | Documentado | Alta | evaluacion/preguntas.yaml (24), services/evaluacion.py | CU-08 Evaluar | test_evaluacion_extractiva_produce_metricas | Implementado (métricas con LLM real pendientes) |
| RF-14 | Taller 1, p.2, §5 Documentación | Informe con descripción del problema, planteamiento, preparación de datos, modelado y resultados | Documentado | Alta | README.md y docs/ | — | Revisión de enlaces del README | Implementado (sección de resultados con LLM real pendiente) |
| RF-15 | Taller 1, p.2, §5 Presentación | Sustentación en vivo de 15 min con demostración en Streamlit/Gradio, sin PowerPoint | Documentado | Media | docs/ | — | Ensayo con guion | Documentado |
| RF-16 | Taller 1, p.2, Rúbrica (25 %) | Implementación funcional de Resumen, FAQ y Q&A usando LangChain | Documentado | Alta | llm/cadenas.py, services/asistente.py | CU-04, CU-05, CU-06 | test_faq_y_resumen, test_qa_contrato_y_auditoria | Implementado |
| RF-17 | Taller 1, p.2, Rúbrica (25 %) | Consolidación del conocimiento en un archivo de texto limpio | Documentado | Alta | data/gold/base_conocimiento.txt | CU-03 Construir base | test_construir_gold_genera_artefactos | Implementado |
| RF-18 | Taller 1, p.2, Rúbrica (25 %) | Documentación del proceso de experimentación con los prompts | Documentado | Alta | llm/prompts/*.yaml (técnica, hipótesis), docs/prompts/bitacora_experimentos.md | CU-07 Comparar prompts | Revisión de bitácora | Parcial: bitácora con protocolo y resultados de línea base, resultados con LLM pendientes |
| RF-19 | Taller 1, p.2, Rúbrica (15 %) | Dashboard funcional, bien presentado, que muestre las tres funcionalidades | Documentado | Alta | frontend/app.py | CU-04..CU-06 | test_resumen_y_faq, test_panel_muestra_metricas | Implementado |
| RF-20 | Taller 1, p.2, Rúbrica (15 %) | Código limpio y bien organizado en GitHub | Documentado | Alta | .github/workflows/ci.yml, ruff, mypy | — | uv run ruff check . && uv run mypy | Implementado (publicación en GitHub: acción pendiente) |
| RNF-01 | Clase 2, p.2, §3 | Gestionar el proyecto con uv (pyproject.toml, uv.lock), sin pip ni requirements.txt | Documentado | Alta | pyproject.toml, uv.lock | — | CI: uv sync --locked | Implementado |
| RNF-02 | Clase 2, p.2, §4 | Arquitectura Medallion Bronze (HTML + JSONL con URL, fecha, estado, hash), Silver (texto limpio deduplicado), Gold (Markdown + metadatos) | Documentado | Alta | pipelines/bronze.py, silver.py, gold.py | CU-03 | test_markdown_gold_con_frontmatter, test_reanudacion_no_repite_capturas | Implementado |
| RNF-03 | Clase 2, p.3, Con criterio | Respetar robots.txt, User-Agent, timeout, pausas, solo datos públicos, Ley 1581 (Habeas Data) | Documentado | Alta | scraping/robots.py, cliente_http.py, pipelines/texto.py | CU-02 | test_robots_respeta_disallow, test_anonimizar_correos_conserva_corporativos | Implementado |
| RNF-04 | Clase 3, §2-§5 | Entorno agéntico: OpenCode, MCP, skills, Engram, OpenSpec, GGA | Documentado | Media | opencode.json, .mcp.json, skills/, openspec/ | — | openspec validate --all, test_mcp | Parcial: configurado y validado, Engram y GGA requieren instalación local |
| RNF-05 | Clase 3, §3 | Escanear skills de terceros con SkillSpector antes de instalar | Documentado | Media | skills/fna-seguridad | — | skillspector scan | Documentado |
| RNF-06 | Prompt maestro | Compatibilidad con Windows 11 (PowerShell) | Diseño | Alta | scripts/*.ps1 | — | Análisis sintáctico con PowerShell 7.4 | Implementado (sintaxis verificada, ejecución en Windows pendiente) |
| EXT-01 | Decisión de diseño | Selección de contexto BM25 cuando la base excede el presupuesto | Extensión | Media | knowledge/recuperacion.py | CU-04 | test_bm25_prioriza_fragmento_correcto | Implementado |
| EXT-02 | Prompt maestro / Clase 1 (Fase 3) | API REST FastAPI con OpenAPI | Extensión | Media | api/ | CU-04..CU-06 | tests/integration/test_api.py | Implementado |
| EXT-03 | Prompt maestro / Clase 3 | Servidor MCP propio de solo lectura sobre la base | Extensión | Media | mcp_server/server.py | CU-09 Consultar vía MCP | test_sesion_stdio_real | Implementado |
| EXT-04 | Decisión de diseño | Auditoría de interacciones, pipeline y evaluaciones en SQLite con Alembic | Extensión | Media | repositories/, alembic/ | CU-10 Auditar | test_migracion_alembic_crea_esquema | Implementado |
| EXT-05 | Decisión de diseño | Línea base extractiva sin LLM para pruebas y CI | Extensión | Baja | llm/extractivo.py | — | test_resumen_con_extractivo | Implementado |
| EXT-06 | Prompt maestro | Contenedores Docker (API, interfaz, Ollama) | Extensión | Baja | infra/docker/Dockerfile, docker-compose.yml | — | docker compose up --build | Pendiente de validación (sin demonio Docker en el entorno de construcción) |
| V2-01 | Prompt maestro v2, §11 | Obtener los datos por web scraping de autopartesfanalca.com.co y fanalca.com (o terceros citables) con el código incluido y un comando único | Documentado | Alta | scraping/, pipelines/orquestador.py, cli.py (pipeline) | CU-02 Ejecutar pipeline | test_metricas_y_graficas_desde_scraping | Implementado — scraping real ejecutado en Windows 11 (fanalca.com, 60 páginas) — autopartesfanalca.com.co protegido por SG-Captcha y complementado con lectura web documentada (ADR-015) |
| V2-02 | Prompt maestro v2, §15 | Explicar cada etapa del proceso de datos con gráficas en el proyecto y el repositorio | Documentado | Alta | pipelines/graficas.py, docs/graficas/, frontend/app.py (Proceso de datos) | CU-02 Ejecutar pipeline | test_graficas_desde_semilla_declaran_ausencia_de_bronze, test_pestanas_v2_proceso_y_simulador | Implementado (gráficas actuales con la base de demostración) |
| V2-03 | Prompt maestro v2, §4 y §29 | Usar Claude Code con el modelo adecuado por especialidad (Opus: arquitectura, diseño mecánico, restricciones, revisión — Sonnet: implementación) | Documentado | Alta | .claude/agents/*.md (campo model), opencode.json, CLAUDE.md | — | Revisión de frontmatter | Implementado |
| V2-04 | Prompt maestro v2, cambios | Eliminar ingeniería inversa, JupyterLab, notebooks y Anaconda del proyecto | Documentado | Alta | pyproject.toml, docs/, ADR-014 | — | Búsqueda de referencias residuales | Implementado |
| V2-05 | Prompt maestro v2, §30–§31 | Modelo de componentes con jerarquía y articulaciones fija, rotacional, prismática, esférica y compuesta | Documentado | Alta | simulador/modelos.py, catalogo_freno.py | CU-11 Explorar ensamblaje | test_ensamblaje_integro, test_articulacion_exige_eje_unitario_y_limites, test_jerarquia_cubre_todas_las_piezas | Implementado |
| V2-06 | Prompt maestro v2, §32 | Vista de despiece y reensamblaje reversible con secuencia de desmontaje | Documentado | Alta | simulador/cinematica.py, web/src/paginas/MaquinaFreno.tsx | CU-11 Explorar ensamblaje | test_despiece_reversible_y_monotono, test_secuencias_desmontaje_y_reensamblaje | Implementado |
| V2-07 | Prompt maestro v2, §33 | Freno de disco como caso principal con cálculo simplificado separado de la animación | Documentado | Alta | simulador/fisica_freno.py, web/src/modelos/freno.ts | CU-12 Simular frenado | test_fisica_formulas_de_referencia, modelos.test.ts | Implementado |
| V2-08 | Prompt maestro v2, §34 | Generación procedural por CLI de Python y exportación GLB con manifiesto | Documentado | Alta | simulador/generacion.py, web/public/modelos/ | — | test_generacion_reproducible, test_manifiesto_completo_y_mallas_cerradas | Implementado |
| V2-09 | Prompt maestro v2, §35 | Visor web con órbita, zoom, selección, árbol, ficha, modos, velocidad, visibilidad, transparencia, sección, cámara, PNG y lecturas | Documentado | Alta | web/src/ | CU-11 Explorar ensamblaje | e2e/visor.spec.ts (freno 3D) | Implementado |
| V2-10 | Prompt maestro v2, §36 | Integración RAG que separa información documentada y de demostración, sin procedimientos de reparación o seguridad | Documentado | Alta | services/simulador.py, mcp_server (consultar_pieza) | CU-13 Preguntar por pieza | test_preguntas_sobre_piezas, test_consultar_pieza_separa_modelo_y_documentado | Implementado |
| V2-11 | Prompt maestro v2, §37 | API REST del simulador con validación Pydantic de valores del cliente | Documentado | Alta | api/routes/simulador.py | — | test_cinematica_valida_limites, test_estados_validados_y_persistidos | Implementado |
| V2-12 | Prompt maestro v2, §38 | Persistencia de estados y eventos en PostgreSQL con Alembic | Documentado | Media | repositories/, alembic/versions/0002_simulador.py, docker-compose.yml | — | test_migraciones_alembic_en_postgresql, test_repositorio_en_postgresql | Implementado |
| V2-13 | Prompt maestro v2, §39 | Biblioteca de máquinas (Anatomy) con menú de tarjetas alimentado por el web scraping, recorrido < 30 s y modo experimento | Documentado | Alta | services/maquinas.py, web/src/paginas/ | CU-14 Explorar biblioteca | test_biblioteca_de_maquinas_usa_la_base, interfaz.test.tsx, e2e/recorrido.spec.ts | Implementado |
| V2-14 | Prompt maestro v2, §40 | Pruebas de jerarquía, IDs, transformaciones, límites, reversibilidad, carga del modelo, API, frontend y rendimiento | Documentado | Alta | tests/, web/src/__tests__/, web/e2e/ | — | pytest, Vitest, Playwright | Implementado |
| V2-15 | Prompt maestro v2, §28 | Streamlit como interfaz principal que enlaza e integra el visor | Documentado | Media | frontend/app.py (Simulador 3D) | CU-11 Explorar ensamblaje | test_pestanas_v2_proceso_y_simulador | Implementado |
| V2-16 | Decisión del proyecto (ADR-017) | Fichas técnicas curadas de motocicletas Honda con fuente, fecha de consulta y estado (publicado, no publicado o supuesto) | Documentado | Alta | data/catalogo/motos_honda.yaml, services/motos.py | CU-14 Explorar biblioteca | test_catalogo_yaml_cumple_el_esquema, test_validador_detecta_valor_sin_fuente | Implementado |
| V2-17 | Decisión del proyecto (ADR-017) | Cálculo didáctico de la motocicleta (velocidad, cilindrada, biela-manivela, CBS y dinámica continua) con paridad Python y TypeScript | Documentado | Alta | simulador/fisica_moto.py, web/src/modelos/moto.ts | CU-14 Explorar biblioteca | test_fisica_moto.py, test_dinamica_moto.py, referencia_moto.json (modelos.test.ts) | Implementado |
| V2-18 | Decisión del proyecto (ADR-017) | Ensamblaje 3D genérico moto_honda de 79 piezas con puntos duros únicos y prueba de conectividad de 2 mm | Documentado | Alta | simulador/catalogo_moto_honda.py, simulador/puntos_duros_moto.py, simulador/generacion.py | CU-11 Explorar ensamblaje | test_moto_ensamblaje.py, test_generacion_moto.py, simulador validar | Implementado |
| V2-19 | Decisión del proyecto (ADR-017) | API de fichas y cálculo de motocicletas con validación y respuestas deterministas con campo y fuente | Documentado | Media | api/routes/motos.py, services/motos.py | — | test_api_motos.py | Implementado |
| V2-20 | Decisión del proyecto (ADR-017) | Respuestas precalculadas de las preguntas frecuentes de Fanalca para el visor con citas (comando faq-visor) | Documentado | Media | services/faq_visor.py, cli.py, api/routes/faq_visor.py | — | test_faq_visor.py | Implementado |
| V2-21 | Decisión del proyecto (ADR-017) | Máquina de motocicleta en el visor con plantilla común, ficha técnica, preguntas frecuentes y modo experimento | Documentado | Alta | web/src/paginas/MaquinaMoto.tsx, web/src/componentes/plantilla/, web/src/maquinas/ | CU-14 Explorar biblioteca | moto.test.tsx, plantilla.test.tsx, e2e/moto.spec.ts, e2e/plantilla.spec.ts | Implementado |

## Historias de usuario

- **RF-01**: Como analista, se requiere conocer las fuentes públicas para delimitar el corpus.
- **RF-02**: Como cliente, se desea obtener información básica de la empresa.
- **RF-03**: Como ingeniero de datos, se requiere capturar el contenido textual relevante.
- **RF-04**: Como ingeniero de datos, se requiere texto sin ruido.
- **RF-05**: Como ingeniero LLM, se requieren fragmentos citables.
- **RF-06**: Como docente, se requiere revisar código y corpus.
- **RF-07**: Como ingeniero LLM, se requiere cambiar de proveedor sin reescribir cadenas.
- **RF-08**: Como ingeniero LLM, se requiere orquestación declarativa.
- **RF-09**: Como cliente, se esperan respuestas veraces.
- **RF-10**: Como ingeniero LLM, se requiere comparar versiones.
- **RF-11**: Como asistente, se requiere toda la base en contexto.
- **RF-12**: Como usuario, se desea preguntar desde una interfaz web.
- **RF-13**: Como evaluador, se requiere medir calidad.
- **RF-14**: Como docente, se requiere un informe estructurado.
- **RF-15**: Como grupo, se requiere una demo fluida.
- **RF-16**: Como usuario, se requieren las tres funcionalidades.
- **RF-17**: Como docente, se requiere un archivo único revisable.
- **RF-18**: Como docente, se requiere evidencia del proceso.
- **RF-19**: Como usuario, se requiere un panel claro.
- **RF-20**: Como docente, se requiere código mantenible.
- **RNF-01**: Como desarrollador, se requiere entorno reproducible.
- **RNF-02**: Como ingeniero de datos, se requiere reprocesar sin volver a capturar.
- **RNF-03**: Como organización, se requiere scraping legal y ético.
- **RNF-04**: Como equipo, se requiere un proceso reproducible y auditable.
- **RNF-05**: Como equipo, se requiere evitar skills maliciosas.
- **RNF-06**: Como usuario de Windows, se requieren comandos ejecutables.
- **EXT-01**: Como ingeniero LLM, se requiere evitar truncamiento.
- **EXT-02**: Como integrador, se requiere acceso programático.
- **EXT-03**: Como agente de código, se requiere consultar la base.
- **EXT-04**: Como responsable, se requiere trazabilidad.
- **EXT-05**: Como desarrollador, se requieren pruebas deterministas.
- **EXT-06**: Como operador, se requiere despliegue repetible.
- **V2-01**: Como analista, se requiere un corpus trazable a los sitios oficiales.
- **V2-02**: Como evaluador, se requiere comprender cada etapa.
- **V2-03**: Como equipo, se requiere asignar cada tarea al modelo adecuado.
- **V2-04**: Como docente, se requiere un proyecto sin notebooks.
- **V2-05**: Como usuario, se requiere navegar el ensamblaje.
- **V2-06**: Como usuario, se requiere ver el orden de desmontaje.
- **V2-07**: Como estudiante, se requiere relacionar presión y par.
- **V2-08**: Como desarrollador, se requiere un modelo reproducible.
- **V2-09**: Como usuario, se requiere inspeccionar cada pieza.
- **V2-10**: Como usuario, se requiere saber qué está documentado.
- **V2-11**: Como integrador, se requiere un contrato validado.
- **V2-12**: Como operador, se requiere un motor de despliegue.
- **V2-13**: Como visitante, se requiere aprender cómo funcionan las máquinas de la planta.
- **V2-14**: Como responsable de calidad, se requiere evidencia.
- **V2-15**: Como usuario, se requiere un único punto de entrada.
- **V2-16**: Como visitante, se requiere distinguir lo publicado de lo supuesto.
- **V2-17**: Como visitante, se requiere ver cómo el giro del motor se convierte en velocidad.
- **V2-18**: Como visitante, se requiere ver todas las partes de la motocicleta conectadas.
- **V2-19**: Como integrador, se requiere un contrato validado.
- **V2-20**: Como visitante, se requiere ver respuestas con citas sin esperar al modelo.
- **V2-21**: Como visitante, se requiere tocar los controles y ver los números junto a la pieza.
