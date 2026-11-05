# Fase 10 · README profesional y limpieza del repositorio

Agregar al plan una **fase 10**, después de la fase 9, en la rama `add-honda-moto-machine` y en commits separados.
Va al final porque el README necesita las capturas del frontend ya estandarizado (7b). Ningún cálculo, prueba
funcional ni comportamiento de la aplicación cambia.

## Regla general

El repositorio queda **solo técnico**. Deben desaparecer del árbol de trabajo versionado:
- el informe académico;
- los documentos del curso;
- la rúbrica;
- los datos personales;
- las indicaciones dirigidas al estudiante o al docente.

**Todo se borra solo de Git** (`git rm --cached` + `.gitignore`), **nunca del disco**. El usuario conserva sus
copias locales.

## Paso 1 · Inventario (sin borrar nada)

Antes de tocar archivos, mostrar al usuario una tabla con: ruta, motivo y acción propuesta (quitar de Git,
editar o conservar). Debe cubrir:

1. **Carpeta `.claude/`** (agentes, skills, settings). Se quita del repositorio y se añade a `.gitignore`, pero
   **se conserva en el disco**, porque Claude Code la necesita para trabajar. Señalar qué pruebas o scripts
   dependen de que esté versionada; esas pruebas deben ajustarse para que el CI siga en verde.
2. **Carpeta de documentos del curso** (la que se llama «documentos» o equivalente, con los PDF del taller y de
   las clases). Se quita de Git y se añade a `.gitignore`.
3. **El informe:** identificar qué archivos lo componen y proponerlo al usuario antes de quitarlo. Candidatos:
   - el manual LaTeX y `main.pdf`;
   - capítulos de rúbrica, validación contra el taller y guion de la demostración;
   - `docs/requisitos/analisis_documentos.md`;
   - prompts maestros con referencias al curso;
   - bitácoras con contenido académico.
4. **Datos personales y académicos** en todo el árbol versionado: nombres de personas, correos personales,
   teléfonos, códigos o identificaciones de estudiante, nombres de docentes, códigos de curso, universidad y
   semestre. Incluye código, comentarios, metadatos de LaTeX, `pyproject.toml`, `package.json`, `CITATION`,
   capturas y PDF. Listar cada aparición con archivo y línea.
   - El correo corporativo publicado por la empresa en su sitio oficial no es un dato personal y puede quedar.
   - Las URL públicas del repositorio también pueden quedar.
5. **Otros candidatos** que el usuario debe decidir: `.opencode/`, `CLAUDE.md`, `AGENTS.md`, `openspec/`,
   `docs/prompts/` y `opencode.json`. Proponer y esperar la decisión.

**Detenerse aquí** y esperar la aprobación del usuario sobre la tabla antes de modificar nada.

## Paso 2 · Limpieza (tras la aprobación)

- Aplicar exactamente lo aprobado, con `git rm --cached` y entradas en `.gitignore`.
- Sustituir los datos personales por textos neutros, sin cambiar el comportamiento del código.
- Ajustar pruebas, CI, scripts y referencias internas (README, enlaces, `generar_matriz.py`,
  `sincronizar_skills.py`) que apunten a lo eliminado.
- Ejecutar `.\scripts\verificar_calidad.ps1` completo. Todo debe pasar.
- Hacer un commit local: `chore: repositorio solo técnico (sin informe, documentos del curso ni datos personales)`.

**Advertencia obligatoria para el usuario:** los archivos y datos que ya se publicaron siguen visibles en el
**historial** de GitHub. Quitarlos del historial exige reescribirlo (`git filter-repo`) y hacer un **push
forzado**, que es irreversible. **No hacerlo sin una aprobación explícita y separada.** Solo explicar las
opciones:
1. dejar el historial como está;
2. reescribirlo después de integrar la rama;
3. poner el repositorio privado mientras se decide.

## Paso 3 · Diagramas con Archify

1. Instalar Archify (`tt-a1i/archify`) siguiendo la regla de `fna-seguridad`:
   - clonar en una carpeta temporal;
   - ejecutar `skillspector scan <ruta> --no-llm` (solo continuar si la puntuación es < 51);
   - copiar a `skills/` y sincronizar.

   Registrar el resultado como **S-04** en la bitácora técnica. Confirmar el funcionamiento con
   `node bin/archify.mjs doctor`.
2. Generar **un diagrama por pregunta**, con solo componentes que existen en el código (si un componente no se
   puede demostrar, se omite):
   - **Arquitectura de ejecución:** Streamlit, visor React/three.js, FastAPI, servicios, base de conocimiento,
     PostgreSQL/SQLite, servidor MCP, proveedor LLM vía Claude Code.
   - **Flujo de datos Medallion:** rastreo con robots.txt y detección anti-bots → Bronze → Silver (limpieza,
     secciones, contacto del pie) → Gold (documentos, fragmentos, `base_conocimiento.txt`) → gráficas por etapa.
   - **Secuencia de una pregunta Q&A:** detección de inyección → recuperación BM25 con expansión → prompt v3 →
     Claude → respuesta con citas o frase de rechazo; y el botón opcional de búsqueda web (fase 9).
   - **Arquitectura del simulador 3D:** catálogo de ensamblajes → generación GLB → API del simulador → visor
     (`moto.ts`, paridad con `fisica_moto.py` vía `referencia_moto.json`).
   - **Ciclo de vida del dato de ficha técnica:** publicado / no_publicado / supuesto didáctico → «Ver con
     ficha de…».
3. Guardar cada diagrama en `docs/arquitectura/diagramas/` como HTML interactivo y como **SVG exportado**, con
   variantes clara y oscura. El README incrusta el SVG, porque el HTML de Archify no se renderiza dentro de
   GitHub, y enlaza al HTML.
4. Para los diagramas de flujo funcional (usuario → pestaña → API → resultado), usar además **Mermaid** dentro
   del README, porque GitHub lo renderiza de forma nativa.

## Paso 4 · Capturas del sistema

Con la aplicación real (Playwright, 1920×1080), guardar en `docs/capturas/readme/`:
- biblioteca;
- freno, prensa, línea y moto (ensamblada, despiece y corte del motor);
- ficha técnica y FAQ desplegadas;
- Streamlit: Q&A con citas, Resumen, FAQ, Proceso de datos y laboratorio de prompts;
- Swagger de la API (`/docs`).

Además: un GIF corto (< 10 s) o el enlace al MP4 del recorrido de la moto. Optimizar las imágenes (PNG < 400 KB
cada una). **Ninguna captura debe mostrar datos personales.**

## Paso 5 · README.md profesional (solo técnico)

Estructura:

1. Título, descripción técnica de una línea e insignias: CI de GitHub Actions, Python 3.12, uv, FastAPI,
   React/three.js, MCP.
2. Captura principal (la moto o la biblioteca) y enlace al video del recorrido.
3. **Características**: base de conocimiento por web scraping responsable, Q&A con citas y rechazo
   anti-alucinación, Resumen y FAQ, biblioteca de máquinas 3D con física verificable, fichas técnicas con
   fuente y estado, API REST, servidor MCP, búsqueda web complementaria opcional.
4. **Arquitectura**: diagrama Archify de ejecución + tabla de capas (domain, services, api, frontend, pipelines,
   simulador) y la regla de dependencias.
5. **Flujos**: Medallion, secuencia Q&A y flujo del usuario (Mermaid + SVG de Archify).
6. **Capturas**: galería en tabla de dos columnas.
7. **Inicio rápido en Windows 11**: requisitos (Python 3.12, uv, Node LTS, Git, Claude Code), instalación,
   `uv sync`, `npm ci`/`npm run build`, ejecución de la API y de Streamlit, URL.
8. **Uso**: tabla de comandos de la CLI `fabrica` (pipeline, build, validate, ask, faq, summary, evaluate,
   faq-visor, simulador) con ejemplos.
9. **API**: tabla de endpoints `/api/v1/*` y enlace a OpenAPI.
10. **Servidor MCP**: herramientas expuestas (solo lectura) y configuración.
11. **Proveedores LLM**: `claude_code` (sin clave de API), alternativas, y variables de `.env.example` sin
    valores reales.
12. **Calidad**: pruebas (pytest, Vitest, Playwright), cobertura, Ruff, mypy, verificación de capas, CI y
    resultados de la evaluación v1–v3 (tabla de métricas).
13. **Datos y ética**: robots.txt, User-Agent identificable, no se eluden protecciones, sin datos personales,
    cifras demostrativas y supuestos didácticos marcados.
14. **Estructura del proyecto**: árbol resumido.
15. **Limitaciones conocidas** y **hoja de ruta técnica**.
16. Licencia: **no inventar una**. Si no existe un archivo LICENSE, preguntar al usuario cuál desea.

Estilo:
- Impersonal, sin primera ni tercera persona.
- Sin referencias a curso, rúbrica, docente, entregas ni calificación.
- Enlaces relativos verificados y ningún enlace roto (comprobarlo con un script).
- Encabezados navegables con tabla de contenidos.

## Paso 6 · Verificación y cierre

- Correr `.\scripts\verificar_calidad.ps1` completo (incluye Playwright).
- Revisar que el README se vea bien: generar una vista previa HTML local y mostrar una captura al usuario.
- Buscar de nuevo datos personales con `git grep` en todo el árbol versionado: el resultado debe estar vacío.
- Hacer un commit local: `docs: README técnico con arquitectura (Archify), flujos y capturas`.
- **Sin push.** Detenerse y mostrar al usuario el README renderizado y la lista final de archivos quitados de Git.
