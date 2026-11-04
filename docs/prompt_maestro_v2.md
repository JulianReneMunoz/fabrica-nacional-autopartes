# PROMPT MAESTRO v2.0 — DESARROLLO INTEGRAL DE FÁBRICA NACIONAL DE AUTOPARTES S.A.S.

> **Cambios de la versión 2.0 respecto a la versión inicial:** (1) los datos provienen del web
> scraping de los sitios oficiales (https://autopartesfanalca.com.co/ y https://www.fanalca.com/) o
> de información de terceros, con el código de scraping incluido y cada etapa del proceso explicada
> con gráficas; (2) Claude Code utiliza el modelo más adecuado para cada especialidad (Opus y
> Sonnet); (3) se eliminan la ingeniería inversa, JupyterLab y los notebooks; (4) se agrega la
> Parte VIII: simulador 3D de ensamblajes y biblioteca de máquinas (método Anatomy).

## 1. Rol y nivel de especialización

Actúa como un equipo multidisciplinario de ingeniería de software conformado por:

- Arquitecto de software empresarial.
- Ingeniero de requisitos y analista de sistemas.
- Ingeniero de datos especializado en web scraping, ETL y ELT.
- Desarrollador senior de Python, APIs y aplicaciones web.
- Ingeniero de bases de datos SQL y NoSQL.
- Especialista en inteligencia artificial y sistemas multiagente.
- Ingeniero DevOps y automatización.
- Especialista en Model Context Protocol (MCP).
- Experto en OpenCode, Claude Code y desarrollo asistido por agentes.
- Ingeniero de calidad, pruebas automatizadas y seguridad.
- Arquitecto de documentación técnica mediante LaTeX, TikZ y diagramas UML.
- Docente universitario de ingeniería de software.

El objetivo es **analizar, diseñar, implementar, probar, documentar y entregar una aplicación completa y funcional para Fábrica Nacional de Autopartes S.A.S.**, utilizando los documentos adjuntos como especificación principal.

No limitar la respuesta a recomendaciones conceptuales. Se requiere construir el proyecto con código fuente, estructura de directorios, configuraciones, scripts, pruebas, documentación y procedimientos reproducibles.

---

## 2. Análisis obligatorio de documentos adjuntos

Antes de diseñar o programar, examinar exhaustivamente todos los archivos suministrados.

Documento principal de referencia:

**551462-B-1-(2026-2S)_ Taller 1 - Aplica...pdf**

También deben analizarse los demás documentos relacionados con el caso empresarial.

### Actividades obligatorias

1. Identificar el problema empresarial planteado.
2. Extraer literalmente los requisitos relevantes.
3. Identificar objetivos generales y específicos.
4. Determinar actores, usuarios y sistemas externos.
5. Identificar los datos requeridos y sus fuentes.
6. Establecer qué procesos requieren scraping.
7. Determinar los productos y entregables exigidos por el taller.
8. Identificar restricciones académicas, técnicas y empresariales.
9. Construir una matriz de requisitos funcionales y no funcionales.
10. Establecer criterios verificables de aceptación.
11. Identificar información ausente, ambigua o contradictoria.

**Regla fundamental:** no inventar requisitos atribuyéndolos a los documentos. Distinguir expresamente entre requisitos documentados, decisiones de diseño propuestas y funcionalidades opcionales.

Construir una matriz de trazabilidad con:

- Identificador del requisito.
- Documento y página de origen.
- Descripción.
- Prioridad.
- Componente responsable.
- Historia de usuario.
- Caso de uso.
- Prueba de aceptación.
- Estado de implementación.

---

## 3. Objetivo del desarrollo

Construir una solución empresarial modular, escalable, segura, documentada y reproducible que implemente todos los procesos exigidos para Fábrica Nacional de Autopartes S.A.S.

La solución deberá contemplar, según lo establecido en los documentos:

- Recolección de información mediante web scraping.
- Procesamiento, limpieza y transformación de datos.
- Persistencia en bases de datos.
- Backend y API REST.
- Frontend profesional.
- Consultas, filtros, visualizaciones y reportes.
- Automatización de procesos.
- Integración con agentes inteligentes cuando aporte valor.
- Validación y trazabilidad de datos.
- Pruebas automatizadas.
- Observabilidad y manejo de errores.
- Documentación de instalación, operación y mantenimiento.

Las funcionalidades no exigidas expresamente deberán identificarse como extensiones propuestas y justificarse antes de incorporarlas.

---

## 4. Plataforma y pila tecnológica

El entorno principal será **Windows 11**, utilizando PowerShell y, cuando exista una justificación técnica, WSL2.

Utilizar Python y `uv` como base para gestionar proyectos, dependencias y entornos virtuales.

Evaluar y justificar la selección de las siguientes tecnologías:

| Componente | Tecnología candidata |
|---|---|
| Sistema operativo | Windows 11 |
| Terminal | Windows Terminal y PowerShell |
| Control de versiones | Git y GitHub |
| Editor | Visual Studio Code |
| Gestión Python | uv |
| Consola agéntica | OpenCode |
| Consola agéntica adicional | Claude Code |
| Modelo LLM de desarrollo | Claude Opus (arquitectura, diseño mecánico, restricciones, revisión) y Claude Sonnet (implementación), mediante Claude Code |
| Integración de herramientas | MCP |
| Backend | FastAPI |
| Validación | Pydantic |
| Frontend | Streamlit o framework justificado |
| Scraping | Requests, BeautifulSoup, Scrapy, Playwright |
| Bases de datos | PostgreSQL, MongoDB o combinación justificada |
| ORM | SQLAlchemy, cuando corresponda |
| Migraciones | Alembic |
| Procesamiento | Pandas, Polars |
| Pruebas | pytest, pytest-asyncio |
| Calidad | Ruff, mypy, pre-commit |
| API | OpenAPI, Swagger, Postman |
| Contenedores | Docker Desktop |
| Visor 3D (v2.0) | Vite, React y React Three Fiber |
| Geometría procedural (v2.0) | trimesh y manifold3d (Blender CLI solo si se adopta) |
| Documentación | LaTeX, TikZ, PlantUML y Mermaid |
| Integración continua | GitHub Actions |

No utilizar Anaconda, Conda ni notebooks. No instalar herramientas innecesarias. Justificar cada selección en función de los requisitos reales.

---

## 5. Instalación completa desde cero en Windows 11

Generar un manual paso a paso para preparar una computadora con Windows 11.

Para cada herramienta incluir obligatoriamente:

1. Nombre y función.
2. Página oficial de descarga.
3. Versión recomendada y compatibilidad.
4. Requisitos previos.
5. Instalación gráfica, cuando corresponda.
6. Comando de instalación mediante PowerShell.
7. Configuración inicial.
8. Variables de entorno.
9. Verificación de instalación.
10. Errores frecuentes y soluciones.
11. Procedimiento de actualización.
12. Recomendaciones de seguridad.

Desarrollar especialmente:

- Git y autenticación con GitHub.
- Python administrado mediante `uv`.
- VS Code y extensiones.
- OpenCode.
- Claude Code.
- Node.js, si es requerido.
- Docker Desktop.
- WSL2, solamente cuando sea necesario.
- FFmpeg, para codificar los videos del recorrido automático.
- Servidores MCP.
- Motores de bases de datos.
- Compilador LaTeX.

Todos los comandos deben ser ejecutables y estar identificados con la terminal correspondiente.

No presentar pseudocomandos como si fueran instrucciones reales.

---

## 6. Configuración del proyecto mediante uv

Explicar desde cero:

- Instalación de `uv`.
- Inicialización del proyecto.
- Selección de versión Python.
- Creación del entorno virtual.
- Instalación de dependencias.
- Gestión de dependencias de desarrollo.
- Archivo `pyproject.toml`.
- Archivo `uv.lock`.
- Sincronización reproducible.
- Ejecución de scripts.
- Integración con VS Code.
- Configuración de variables de entorno.
- Gestión de secretos.

Incluir comandos reales como:

```powershell
uv init fabrica-autopartes
cd fabrica-autopartes
uv python install 3.12
uv python pin 3.12
uv add fastapi "uvicorn[standard]" pydantic-settings
uv add --dev pytest ruff mypy
uv sync
uv run pytest
```

Ampliar las dependencias según la arquitectura seleccionada.

Explicar cada instrucción, su finalidad y el resultado esperado.

---

## 7. Desarrollo mediante OpenCode y Claude Code

La implementación deberá realizarse mediante un flujo de trabajo asistido por consolas agénticas.

### OpenCode

Documentar:

- Instalación oficial y verificación.
- Configuración del proveedor LLM.
- Integración con la cuenta disponible de Claude.
- Selección de modelos compatibles.
- Configuración de permisos.
- Definición de agentes especializados.
- Gestión del contexto del proyecto.
- Reglas de desarrollo.
- Integración con MCP.
- Ejecución de tareas.
- Revisión de cambios.
- Pruebas y depuración.

### Claude Code

Documentar:

- Instalación y autenticación.
- Diferencias entre suscripción Claude y acceso API.
- Compatibilidad con Windows 11.
- Configuración del repositorio.
- Archivo `CLAUDE.md`.
- Subagentes.
- Skills.
- Hooks.
- MCP.
- Comandos y flujos de trabajo.
- Validación de cambios.

**Importante:** no asumir que una suscripción a Claude incluye automáticamente créditos de API o acceso a todos los proveedores de OpenCode. Verificar los métodos de autenticación y facturación vigentes.

### Modelos por especialidad

Cada subagente de `.claude/agents/` fija su modelo en el campo `model`: **Opus** para arquitectura,
requisitos, diseño mecánico, restricciones y revisión; **Sonnet** para scraping, LLM, implementación
3D, animaciones, controles, APIs, frontend, pruebas y documentación; **Haiku** para verificaciones
rápidas. La variable `CLAUDE_CODE_SUBAGENT_MODEL` reemplaza ese campo, por lo que debe quedar sin
definir. Una suscripción Claude Pro o Max se usa en Claude Code; OpenCode requiere una clave de API
o un proveedor local.

### Prompts operativos

Para cada fase del proyecto proporcionar:

1. Objetivo.
2. Consola utilizada.
3. Agente responsable.
4. Contexto que debe recibir.
5. Prompt completo, listo para copiar.
6. Archivos que debe generar.
7. Comandos que debe ejecutar.
8. Resultado esperado.
9. Pruebas de verificación.
10. Criterios para aprobar o rechazar el resultado.

Evitar instrucciones genéricas como «desarrolla el backend». Especificar archivos, contratos, reglas de negocio, restricciones, pruebas y criterios de aceptación.

---

## 8. Implementación de MCP

Diseñar una arquitectura de integración mediante Model Context Protocol.

Explicar:

- Arquitectura cliente-servidor.
- Hosts y clientes MCP.
- Tools, Resources y Prompts.
- JSON-RPC.
- Transportes stdio y Streamable HTTP.
- Ciclo de vida de las conexiones.
- Autenticación y autorización.
- Gestión de secretos.
- Manejo de errores.
- Auditoría.
- Seguridad frente a prompt injection.
- Aislamiento de herramientas.
- Permisos para lectura, escritura y ejecución.

Implementar servidores MCP útiles para el proyecto, seleccionados según los requisitos, por ejemplo:

- Acceso controlado al sistema de archivos.
- Integración con GitHub.
- Consulta segura de bases de datos.
- Automatización de navegador.
- Acceso a documentación.
- Herramientas de consulta de la API.
- Validación de datos y procesos ETL.

Distinguir entre servidores MCP existentes y servidores desarrollados específicamente para el proyecto.

Para cada servidor proporcionar instalación, configuración, registro en OpenCode o Claude Code, ejemplo de invocación y prueba funcional.

No conceder permisos indiscriminados a los agentes.

---

## 9. Skills, especificaciones y gobierno del desarrollo

Incorporar y evaluar las herramientas y metodologías:

- Skills.
- Egram.
- Archify.
- OpenSpec.
- SkillSpector.
- Medallion.

Antes de instalar cualquiera de ellas, verificar:

- Nombre oficial.
- Repositorio y mantenedor.
- Propósito.
- Compatibilidad.
- Método de instalación.
- Licencia.
- Estado de mantenimiento.
- Riesgos de seguridad.

No inventar paquetes, repositorios o comandos de instalación.

Si un nombre corresponde a varias herramientas, documentar la ambigüedad y seleccionar únicamente la alternativa verificada.

Aplicar:

**OpenSpec:** especificaciones, propuestas de cambio, requisitos, tareas y validación de implementación.

**Archify:** documentación y análisis arquitectónico, si la herramienta identificada ofrece realmente esas capacidades.

**SkillSpector:** inspección y evaluación de skills, según las capacidades verificadas.

**Medallion:** arquitectura de datos Bronze, Silver y Gold, cuando resulte adecuada para el flujo de scraping y análisis.

**Egram:** identificar y documentar la herramienta exacta antes de integrarla.

Diseñar skills específicas del proyecto para:

- Analizar requisitos.
- Generar código.
- Revisar arquitectura.
- Implementar scraping.
- Validar datos.
- Construir APIs.
- Ejecutar pruebas.
- Auditar seguridad.
- Generar documentación.

Cada skill debe tener responsabilidades, entradas, salidas, restricciones y criterios de validación.

---

## 10. Arquitectura completa del sistema

Definir y justificar una arquitectura de software basada en los requisitos identificados.

Incluir:

- Diagrama de contexto.
- Diagrama de contenedores C4.
- Diagrama de componentes.
- Diagrama de despliegue.
- Diagrama de casos de uso.
- Diagrama de secuencia.
- Diagrama de actividades.
- Modelo de dominio.
- Modelo de datos.
- Flujo de scraping.
- Flujo ETL/ELT.
- Flujo de agentes inteligentes.
- Flujo de integración MCP.
- Diagrama de seguridad.

Cada diagrama debe tener una explicación técnica de sus elementos, relaciones, protocolos y responsabilidades.

Justificar las decisiones arquitectónicas mediante ADR (Architecture Decision Records).

---

## 11. Implementación del scraping

Esta fase debe desarrollarse exhaustivamente, respetando las fuentes de información identificadas en el taller.

### Análisis de fuentes

Fuentes objetivo:

- Sitio oficial de la unidad de autopartes: https://autopartesfanalca.com.co/ (inicio, nosotros,
  productos, clientes y contacto).
- Sitio corporativo: https://www.fanalca.com/.
- Información de terceros solo cuando sea pública, citable y se registre su procedencia.

Incluir el código completo del scraping en el repositorio y un comando único que ejecute el proceso
completo desde la consola (`uv run fabrica pipeline`: rastreo → Bronze → Silver → Gold → validación
→ gráficas). El scraping real se ejecuta en Windows 11 desde PowerShell o desde Claude Code, en la
carpeta del proyecto.

Determinar:

- Sitios web objetivo.
- Datos que deben extraerse.
- Existencia de APIs oficiales.
- Condiciones de uso.
- Restricciones de robots.txt.
- Necesidad de autenticación autorizada.
- Frecuencia de actualización.
- Volumen esperado.
- Calidad y confiabilidad de las fuentes.

No eludir CAPTCHAs, controles de acceso, restricciones contractuales ni mecanismos de protección.

### Desarrollo técnico

Implementar, según corresponda:

- Clientes HTTP.
- Parsers HTML.
- Navegación dinámica con Playwright.
- Paginación.
- Extracción de campos.
- Normalización.
- Deduplicación.
- Reintentos con backoff.
- Control de frecuencia.
- Timeouts.
- Manejo de errores.
- Registro de eventos.
- Validación de esquemas.
- Persistencia.
- Trazabilidad de procedencia.
- Programación de ejecuciones.

### Pipeline de datos

Implementar una arquitectura Medallion cuando esté justificada:

**Bronze:** información original y metadatos de extracción.

**Silver:** información limpia, validada, normalizada y deduplicada.

**Gold:** información preparada para consultas, indicadores y reportes.

Crear código completo, pruebas con HTML de ejemplo, scripts de ejecución y mecanismos de recuperación ante fallos.

Evitar que las pruebas dependan exclusivamente de sitios externos en producción.

Todo el procesamiento de la información alimenta las etapas siguientes: la base de conocimiento
semántica (fragmentos con procedencia) y el sistema de preguntas y respuestas.

---

## 12. Base de datos y persistencia

Diseñar el modelo de datos de acuerdo con los documentos.

Entregar:

- Modelo entidad-relación o modelo documental.
- Diccionario de datos.
- Colecciones o tablas.
- Tipos de datos.
- Relaciones.
- Índices.
- Restricciones.
- Validaciones.
- Migraciones.
- Datos de prueba.
- Políticas de respaldo.
- Estrategias de recuperación.
- Control de duplicados.
- Auditoría de operaciones.

Justificar el uso de PostgreSQL, MongoDB o una arquitectura híbrida.

No utilizar simultáneamente varias bases de datos sin una necesidad técnica demostrada.

---

## 13. Backend y API REST

Implementar el backend completo con FastAPI, cuando esta tecnología sea adecuada.

Incluir:

- Estructura modular.
- Modelos de dominio.
- DTO y esquemas Pydantic.
- Servicios.
- Repositorios.
- Endpoints.
- Validación de entrada.
- Autenticación y autorización cuando corresponda.
- Manejo centralizado de excepciones.
- Paginación.
- Búsqueda y filtros.
- Registro de auditoría.
- Documentación OpenAPI.
- Pruebas unitarias y de integración.

Proporcionar contratos de entrada y salida para cada endpoint.

Verificar los endpoints mediante Swagger y Postman.

---

## 14. Frontend empresarial

Desarrollar una interfaz profesional y funcional.

La elección entre Streamlit y otro framework debe justificarse a partir de las necesidades del proyecto.

Implementar las vistas y operaciones identificadas en los documentos.

Considerar, cuando corresponda:

- Inicio y navegación.
- Dashboard.
- Consulta de datos.
- Gestión de registros.
- Ejecución y seguimiento del scraping.
- Estado de procesos ETL.
- Búsquedas y filtros.
- Indicadores.
- Reportes.
- Exportación de resultados.
- Administración de usuarios.
- Consulta de errores.
- Visualización de auditorías.

Si se implementa un asistente conversacional con IA, definir claramente sus fuentes, permisos, herramientas MCP, límites de actuación y controles contra respuestas no fundamentadas.

No añadir módulos ficticios para aparentar una aplicación más completa.

---

## 15. Proceso de la información explicado con gráficas

Registrar métricas en cada etapa del pipeline y generar una gráfica por etapa en `docs/graficas/`:

1. Rastreo responsable: URL descubiertas (sitemap), visitadas, capturadas y descartadas.
2. Capa Bronze: HTML capturado por página.
3. Reducción del HTML al conocimiento: bytes, texto extraído, texto sin plantilla y texto limpio.
4. Capa Silver: limpieza por página.
5. Capa Gold: fragmentos por sección.
6. Capa Gold: tamaño de los fragmentos frente al límite de contexto.

Las gráficas indican la fuente de datos (scraping, lectura web o semilla) y la fecha de generación,
se regeneran con `uv run fabrica graficas` y se explican en Streamlit, en el README y en el manual.

---

## 16. Pruebas y aseguramiento de calidad

Construir una estrategia integral que contemple:

- Pruebas unitarias.
- Pruebas de integración.
- Pruebas de API.
- Pruebas de scraping.
- Pruebas de validación de datos.
- Pruebas end-to-end.
- Pruebas de seguridad.
- Pruebas de rendimiento cuando correspondan.
- Pruebas de aceptación.
- Pruebas de regresión.

Utilizar pytest y herramientas complementarias justificadas.

Definir indicadores de cobertura y calidad, sin inventar resultados de ejecución.

Para cada prueba proporcionar código, comando, resultado esperado y criterio de aceptación.

Incluir integración continua con GitHub Actions.

---

## 17. Estructura del repositorio y código completo

Generar un repositorio profesional que contenga todos los archivos necesarios.

Incluir como mínimo, ajustándolo a la arquitectura real:

```text
fabrica-nacional-autopartes/
├── README.md
├── pyproject.toml
├── uv.lock
├── .python-version
├── .gitignore
├── .env.example
├── CLAUDE.md
├── AGENTS.md
├── docs/
│   ├── arquitectura/
│   ├── requisitos/
│   ├── diagramas/
│   ├── manuales/
│   └── latex/
├── src/
│   └── fabrica_autopartes/
│       ├── api/
│       ├── core/
│       ├── domain/
│       ├── services/
│       ├── repositories/
│       ├── scraping/
│       ├── pipelines/
│       ├── models/
│       └── agents/
├── frontend/
├── web/
├── scripts/
├── data/
│   ├── bronze/
│   ├── silver/
│   └── gold/
├── tests/
│   ├── unit/
│   ├── integration/
│   └── e2e/
├── mcp/
├── skills/
├── openspec/
├── infra/
├── .github/
│   └── workflows/
└── docker-compose.yml
```

La estructura es una propuesta inicial y debe ajustarse a los requisitos.

**No entregar solamente árboles de directorios o fragmentos ilustrativos.**

Generar el contenido íntegro de los archivos necesarios, con imports consistentes, rutas correctas, dependencias declaradas y código ejecutable.

Si el entorno permite crear archivos, entregar un ZIP del proyecto.

---

## 18. Manual completo en LaTeX

Generar un proyecto LaTeX compilable y su correspondiente PDF, cuando las herramientas disponibles lo permitan.

El manual debe ser exhaustivo, académico, técnico y reproducible.

### Capítulos mínimos

1. Introducción y contexto empresarial.
2. Objetivos y alcance.
3. Análisis de los documentos.
4. Ingeniería de requisitos.
5. Proceso de la información y gráficas por etapa.
6. Arquitectura de software.
7. Pila tecnológica.
8. Preparación de Windows 11.
9. Instalación y configuración de uv.
10. Instalación y configuración de OpenCode.
11. Instalación y configuración de Claude Code.
12. Integración de modelos LLM.
13. Arquitectura y configuración MCP.
14. Skills y herramientas de especificación.
15. Gestión del proyecto con Git y GitHub.
16. Desarrollo de scraping.
17. Arquitectura Medallion y procesamiento de datos.
18. Diseño de bases de datos.
19. Implementación del backend.
20. Implementación del frontend.
21. Automatización mediante agentes.
22. Pruebas y aseguramiento de calidad.
23. Seguridad.
24. Despliegue.
25. Operación y mantenimiento.
26. Solución de problemas.
27. Validación contra los requisitos del taller.
28. Conclusiones técnicas.
29. Bibliografía y referencias.
30. Anexos.

### Diagramas

Utilizar TikZ para representar:

- Arquitectura general.
- Componentes.
- Flujo de scraping.
- Arquitectura Medallion.
- Interacción entre agentes.
- MCP.
- Despliegue.
- Secuencia de ejecución.
- Flujo de instalación.
- Ciclo de vida del desarrollo.
- Simulador 3D (ver Parte VIII, sección 41).

Todos los diagramas deben ser legibles, estar correctamente etiquetados y explicados.

Incluir bloques de código con sintaxis resaltada, tablas, referencias cruzadas, índice general, índice de figuras y bibliografía.

---

## 19. Guía operativa de desarrollo con agentes

Esta sección es prioritaria.

Construir un procedimiento cronológico que permita desarrollar toda la aplicación desde cero mediante OpenCode y Claude Code.

Para cada etapa incluir:

**Paso 1.** Herramienta que se utilizará.

**Paso 2.** Terminal desde la cual se ejecutará.

**Paso 3.** Comando exacto.

**Paso 4.** Explicación del comando.

**Paso 5.** Prompt que debe enviarse al agente.

**Paso 6.** Archivos que debe crear o modificar.

**Paso 7.** Pruebas que deben ejecutarse.

**Paso 8.** Resultado esperado.

**Paso 9.** Errores frecuentes y correcciones.

**Paso 10.** Condición necesaria para continuar.

Desarrollar estas etapas:

- Preparación del equipo.
- Instalación de herramientas.
- Inicialización del repositorio.
- Análisis de requisitos.
- Configuración de agentes.
- Integración MCP.
- Generación de especificaciones.
- Diseño de arquitectura.
- Implementación de scraping.
- Construcción de pipelines.
- Implementación de persistencia.
- Construcción de API.
- Desarrollo del frontend.
- Integración de componentes.
- Pruebas.
- Corrección de defectos.
- Despliegue.
- Documentación final.

No avanzar automáticamente a una etapa si las verificaciones anteriores no han sido satisfactorias.

---

## 20. README profesional

Generar un `README.md` apto para un repositorio público o privado de GitHub.

Debe incluir:

- Nombre y descripción del proyecto.
- Contexto y problema.
- Objetivos.
- Alcance.
- Arquitectura.
- Tecnologías.
- Requisitos previos.
- Instalación.
- Configuración.
- Ejecución.
- Scraping.
- Procesamiento de datos.
- API.
- Frontend.
- MCP.
- Agentes.
- Pruebas.
- Estructura del repositorio.
- Seguridad.
- Limitaciones.
- Resolución de problemas.
- Licencias.
- Referencias.

No incluir contraseñas, tokens ni información empresarial confidencial.

---

## 21. Entregables finales obligatorios

Entregar, cuando las herramientas de ejecución y creación de archivos estén disponibles:

1. Proyecto completo en ZIP.
2. Código fuente funcional.
3. Backend.
4. Frontend.
5. Scrapers.
6. Pipelines de datos.
7. Esquemas y migraciones.
8. Configuraciones MCP.
9. Skills del proyecto.
10. Configuraciones de OpenCode y Claude Code.
11. Gráficas por etapa del proceso de datos y videos del recorrido automático.
12. Scripts de instalación y ejecución.
13. Archivo `pyproject.toml` y lockfile.
14. Pruebas automatizadas.
15. Colección Postman.
16. Documentación OpenAPI.
17. README profesional.
18. Manual LaTeX completo.
19. Diagramas TikZ.
20. PDF compilado del manual.
21. Matriz de trazabilidad.
22. Guía cronológica de ejecución.
23. Evidencias reales de las verificaciones realizadas.

Si alguna integración no puede ejecutarse por falta de credenciales, servicios externos o restricciones del entorno, indicar expresamente qué quedó implementado, qué fue probado y qué requiere validación posterior.

---

## 22. Reglas estrictas de ejecución

- Priorizar los requisitos de los documentos adjuntos.
- No inventar contenido documental.
- No inventar URLs, paquetes, comandos ni resultados.
- Utilizar fuentes oficiales para instalaciones.
- Mantener compatibilidad con Windows 11.
- Utilizar `uv` como gestor principal de Python.
- Implementar código modular y mantenible.
- Evitar secretos en el repositorio.
- Respetar licencias y condiciones de scraping.
- Incorporar seguridad desde el diseño.
- Documentar las decisiones técnicas.
- Mantener trazabilidad entre requisitos, código y pruebas.
- No sustituir la implementación por pseudocódigo.
- No declarar funcional un componente sin evidencia de prueba.
- No afirmar que se ejecutaron comandos que no fueron ejecutados.
- Diferenciar componentes terminados, parcialmente implementados y pendientes.

## 23. Orden de respuesta y desarrollo

Iniciar con el análisis verificable de los documentos y la identificación del alcance.

Posteriormente:

**Fase A:** especificación y requisitos.

**Fase B:** arquitectura y selección tecnológica.

**Fase C:** instalación completa en Windows 11.

**Fase D:** configuración de OpenCode, Claude Code, MCP y skills.

**Fase E:** desarrollo incremental del sistema.

**Fase F:** integración, pruebas y correcciones.

**Fase G:** documentación LaTeX, README y diagramas.

**Fase H:** empaquetado y entrega.

El resultado debe permitir que una persona con conocimientos básicos de programación pueda reproducir la instalación, seguir los comandos y comprender cómo los agentes inteligentes participan en la construcción de una aplicación empresarial real.

**Objetivo final: entregar un sistema funcional, reproducible, verificable y documentado para Fábrica Nacional de Autopartes S.A.S., cumpliendo los requisitos del taller académico y utilizando un flujo profesional de ingeniería de software asistido por inteligencia artificial.**

---

# PARTE VIII — VERSIÓN 2.0: SIMULADOR 3D DE ENSAMBLAJES Y BIBLIOTECA DE MÁQUINAS

Esta parte amplía el sistema sin reemplazar lo anterior. Streamlit continúa como interfaz empresarial
principal y enlaza o incrusta el visor 3D. Se conservan Windows 11, `uv`, FastAPI, PostgreSQL y MCP.

## 28. Objetivo de la versión 2.0

Construir un simulador 3D web de ensamblajes de autopartes, con el **freno de disco** como caso
principal, integrado con la base de conocimiento (RAG) y con una biblioteca de máquinas interactivas
alimentada por los datos obtenidos mediante web scraping. El simulador es **demostrativo y
educativo**: no reemplaza documentación técnica del fabricante, software CAD ni análisis de ingeniería.

## 29. Modelos de Claude por especialidad

Mantener Claude Code CLI como consola principal:

| Especialidad | Modelo | Subagente |
|---|---|---|
| Arquitectura del sistema e integración | Opus | `arquitecto-sistema` |
| Diseño mecánico, articulaciones y restricciones | Opus | `arquitecto-mecanico-3d` |
| Requisitos y trazabilidad | Opus | `analista-requisitos` |
| Revisión independiente | Opus | `revisor-calidad` |
| Scraping, Medallion y gráficas | Sonnet | `ingeniero-datos` |
| Prompts, LangChain y RAG | Sonnet | `ingeniero-llm` |
| Implementación 3D, animaciones, controles, API, frontend y pruebas | Sonnet | `ingeniero-3d-frontend` |
| Documentación | Sonnet | `documentador` |
| Verificaciones rápidas | Haiku | `verificador-rapido` |

No utilizar modelos de Claude como sustituto de un motor geométrico, un sistema de física o un
software CAD.

## 30. Modelo de componentes

Cada pieza declara: identificador estable, nombre, tipo, descripción, función, material
(demostrativo), dimensiones, geometría, transformación (posición y rotación), punto de anclaje,
subconjunto, piezas relacionadas, articulaciones, dirección y distancia de despiece, piezas que deben
retirarse antes, visibilidad, metadatos y referencia documental. Las piezas se agrupan en
subconjuntos y estos en un ensamblaje con jerarquía navegable.

## 31. Articulaciones

Tipos: **fija, rotacional, prismática, esférica y compuesta**. Cada articulación define padre, hijo,
eje unitario, origen, límites (o movimiento continuo), unidad, valor inicial y procedencia. Las
compuestas declaran una articulación maestra y una relación de transmisión. El backend rechaza
valores fuera de límites, no finitos o de articulaciones inexistentes.

## 32. Vista de despiece y reensamblaje

La posición de despiece es `posición ensamblada + dirección unitaria · distancia · factor`, con factor
en [0, 1], de modo que el proceso es exactamente reversible. El orden de desmontaje se obtiene por
ordenamiento topológico de `retirar_antes`; el reensamblaje usa el orden inverso.

## 33. Caso principal: freno de disco

Freno con pinza flotante: cubo, disco ventilado, espárragos, soporte, cuerpo de pinza, pistón,
pastillas interna y externa, pasadores guía y tornillos. Cálculo simplificado y separado de la
animación: `A = π·d²/4`, `F = p·A`, `F_f = 2·μ·F`, `T = F_f·r_e`, inercia equivalente de un cuarto de
vehículo, deceleración, condición de bloqueo y distancia de detención. Todos los parámetros se
marcan como demostrativos.

## 34. Generación procedural

Generar la geometría por código Python ejecutable desde la CLI (`uv run fabrica simulador generar`) y
exportar GLB con manifiesto (hash, volúmenes, límites, procedencia). Evaluar Blender CLI y CadQuery y
justificar la elección; usar Blender solo si se adopta. Documentar procedencia y licencia de cualquier
modelo 3D externo.

## 35. Visor web

Funciones obligatorias: órbita, zoom, selección, árbol de componentes, panel de información, modos
(ensamblado, despiece, reensamblaje, frenado), control de velocidad y cámara lenta, visibilidad y
aislamiento, transparencia, vista de sección, reinicio de cámara, exportación de captura PNG y
lecturas de posición y ángulo de la pieza seleccionada.

## 36. Integración RAG

Desde el visor se pregunta por la pieza seleccionada. La respuesta distingue **información
documentada** (fragmentos de la base con URL y origen) de **información del modelo de demostración**.
No generar procedimientos de reparación ni de seguridad crítica: estas preguntas se rechazan con un
mensaje fijo.

## 37. API REST del simulador

Rutas bajo `/api/v1/simulador` con validación Pydantic: ensamblajes, jerarquía, piezas,
articulaciones, despiece, secuencias, parámetros de animación, cinemática, cálculo del freno,
preguntas, estados guardados y eventos. El backend no confía en valores geométricos enviados por el
cliente sin validarlos.

## 38. Persistencia

Tablas de estados visuales guardados y de eventos del simulador mediante Alembic, compatibles con
SQLite (desarrollo) y PostgreSQL (despliegue, servicio `postgres` de `docker-compose.yml`).

## 39. Biblioteca de máquinas (método Anatomy)

Generar un menú de tarjetas que proporcionen información a partir de lo obtenido con el web scraping.
Cada tarjeta: pregunta como título, una línea, relación medible, datos de la empresa con URL y botón
«Abrir máquina». Cada máquina aplica el método Anatomy:

1. Instalar la skill (`npx skills add wheresryan22/anatomy -g -a claude-code`) y revisarla.
2. Elegir una pregunta y una relación medible.
3. Construir primero la lógica del mecanismo (con pruebas).
4. Reglas de legibilidad: 2–4 controles, correr/pausar/reiniciar, cámara lenta, cifras junto a las
   piezas e idea principal en una frase.
5. Estilo coherente y sobrio.
6. Revisión crítica.
7. Recorrido automático de menos de 30 s, grabable como video.
8. Construcción en paralelo de varias máquinas.
9. Sitio de biblioteca con tarjetas y modo experimento (predecir, ejecutar y comparar).

Máquinas iniciales: freno de disco (3D), prensa de estampado (`F = L·t·τ`) y línea de ensamble de
chasises (`takt = tiempo disponible / demanda`, demanda tomada de la base de conocimiento).

## 40. Pruebas de la versión 2.0

Jerarquía, identificadores, transformaciones, límites, reversibilidad del despiece, carga y
validez del modelo GLB, API, persistencia en PostgreSQL, frontend (Vitest y Playwright) y
rendimiento (fotogramas por segundo).

## 41. Documentación LaTeX con TikZ

Diagramas de: arquitectura del simulador, jerarquía del ensamblaje, modelo de componentes,
articulaciones, flujo de generación procedural, secuencias de desmontaje y reensamblaje, integración
RAG, interacción frontend-backend y modelo de persistencia.

## 42. Restricciones de la versión 2.0

- No utilizar Anaconda ni notebooks.
- No presentar geometría simplificada como diseño industrial certificado.
- No afirmar que una animación visual valida automáticamente las propiedades mecánicas.
- No generar procedimientos de reparación o seguridad crítica sin respaldo técnico adecuado.
- El backend no debe confiar en valores geométricos enviados por el cliente sin validarlos.
- Documentar la procedencia y licencia de cualquier modelo 3D externo.
- Evitar dependencias de servicios externos que no sean indispensables.
