# Análisis verificable de los documentos

Documentos examinados (copias PDF de la plataforma UAO Virtual, impresas el 17/10/2026 y el 24/10/2026):

| Documento | Páginas útiles | Observación |
|---|---|---|
| 551462-B-1-(2026-2S) Taller 1 — Aplicación de Técnicas Avanzadas de IA en Modelos de Lenguaje | 1-3 | Dos copias (id 537363 y 537851) con el mismo contenido; la segunda indica "Tarea retrasada por 175 días" |
| Clase 1 — Introducción a los LLMs | 1-4 | Ecosistema, proyecto integrador en 3 fases |
| Clase 2 — Modelos Cerrados vs Abiertos y uv | 1-4 | uv, arquitectura Medallion, scraping ético (dos copias idénticas) |
| Clase 3 — Consolas Agénticas (OpenCode) | 1-5 | OpenCode, MCP, skills, SkillSpector, Engram, OpenSpec, GGA (dos copias idénticas) |

El texto de los PDF no es extraíble (fuentes con codificación propia); el análisis se hizo sobre las páginas rasterizadas.

## 1. Problema empresarial
"Necesidad de un canal de comunicación automatizado y preciso para la empresa X" (Taller 1, p. 2, §5).
Empresa del caso: **Fábrica Nacional de Autopartes (Fanalca)**, Yumbo, Valle del Cauca.

## 2. Objetivo general (literal, Taller 1, p. 1)
"Diseñar y construir el núcleo de conocimiento para un futuro asistente virtual (chatbot) de una empresa líder del Valle del Cauca."

## 3. Objetivos específicos derivados
1. Extraer información pública de la empresa (§2).
2. Procesarla: limpieza y segmentación en fragmentos (§2).
3. Crear un sistema Q&A con Prompt Engineering basado únicamente en el contexto (§3).
4. Construir una interfaz de prueba Streamlit/Gradio (§4).
5. Evaluar con ≥ 20 preguntas y documentar (§5).
6. Implementar Resumen, FAQ y Q&A con LangChain (rúbrica).

## 4. Actores y sistemas externos
- **Cliente o visitante**: formula preguntas de primer contacto.
- **Equipo de desarrollo (4 personas)**: construye y valida la capa de conocimiento.
- **Docente evaluador**: revisa repositorio, informe y demostración.
- **Sitio oficial fanalca.com** (fuente), **Ollama / API de LLM** (generación), **GitHub** (entrega).

## 5. Datos requeridos y fuentes
Secciones "Quiénes somos", productos/servicios (negocios), sostenibilidad, informes, noticias (Taller 1, p. 1, §1); horarios, sedes, productos, historia, contacto y procesos básicos (alcance).

## 6. Procesos que requieren scraping
Únicamente el sitio web oficial (§2 "web scraping del sitio web de su empresa"). Redes sociales y medios se consultan manualmente (ADR-010).

## 7. Entregables exigidos
Repositorio con códigos y base de conocimiento del scraping; aplicativo con prompt y framework LLM; interfaz Streamlit/Gradio; ≥ 20 preguntas de prueba; informe con cinco secciones; sustentación en vivo de 15 minutos sin PowerPoint.

## 8. Restricciones
- Académicas: grupos de 4; apertura 3 de abril de 2026, cierre 2 de mayo de 2026 (la copia del 24/10/2026 indica entrega vencida).
- Técnicas: LangChain recomendado; Ollama o API privada; uv obligatorio (Clase 2).
- Éticas y legales: robots.txt, datos públicos, Ley 1581 de 2012 (Clase 2, p. 3).

## 9. Información ausente, ambigua o contradictoria
| # | Hallazgo | Tratamiento |
|---|---|---|
| A1 | La sección 4 del taller queda cortada entre páginas; solo es legible "...muestre la respuesta generada por el sistema". | Se interpreta como interfaz que recibe la pregunta y muestra la respuesta (coherente con el título "Desarrollo de una Interfaz de Prueba"). |
| A2 | Dos esquemas de evaluación: "Rúbrica ajustada" (15/25/25/15/10/10 = 100 %) y tabla "Criterios de calificación" (10/20/20/20/10/10 visibles = 90 %, tabla truncada a la derecha). | Se cubren los criterios de ambas; la matriz referencia la rúbrica ajustada. |
| A3 | La rúbrica exige Resumen y FAQ, pero las instrucciones detalladas solo describen Q&A. | Se implementan las tres tareas. |
| A4 | El informe pide "modelo de embedding y base de datos vectorial a utilizar en el módulo 2", mientras el Módulo 1 consolida el texto en el prompt. | Módulo 1: contexto completo; Módulo 2: propuesta en `openspec/changes/rag-embeddings-modulo2`. |
| A5 | La Clase 2 nombra las capas `data/raw`, `data/processed`, `data/gold`; el enunciado del proyecto usa `bronze/silver/gold`. | Se usa bronze/silver/gold y se documenta la equivalencia (ADR-002). |
| A6 | Asignación: el taller habla del "Top 50" asignado; la Clase 1 de elegir "una de las 16 empresas del ranking". | Sin impacto técnico; empresa del caso: Fanalca. |
| A7 | Razón social: "Fábrica Nacional de Autopartes S.A.S." (solicitud) vs. "Fanalca S.A." (pie del sitio y registros judiciales). | Se usa "Fábrica Nacional de Autopartes (Fanalca)". |
| A8 | El alcance sugiere "horarios", pero el sitio no publica horarios de atención. | Pregunta P20 evalúa el rechazo correcto. |
| A9 | El ejemplo de modelos del taller menciona "GPT-5, Gemini 2.5 Pro" bajo "API de OpenAI". | Se interpreta como "API privada"; se soportan OpenAI y Anthropic. |
