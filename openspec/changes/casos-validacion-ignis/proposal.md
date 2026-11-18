# Propuesta: casos de validación de IGNIS (Módulo 2)

## Why
El cambio responde a un **requisito documentado del curso**: el Anuncio 006 y la rúbrica del Módulo 2
(casos en vivo) piden validar en la sustentación RAG con citas (1), memoria de corto y largo plazo
(2A y 2B), datos estructurados (3), enrutamiento mixto y directo (4A y 4B) y blindaje (5). El caso 6
(moderación) es un **requisito propio del equipo** (P06).

Hasta ahora las preguntas exactas solo estaban en `web/src/ignisCasos.ts`, con un comentario que
remitía a «el OpenSpec del PR #27». Además, el caso 2A pedía registrar el nombre y la empresa del
usuario, lo que choca con la Ley 1581 de 2012 y con el diseño del Store de largo plazo, que guarda solo
preferencias no personales. Esta especificación fija los textos y el criterio de aceptación de cada caso.

## What Changes
- **Textos fijos de los casos 1, 2A, 2B, 3, 4A, 4B, 5 y 6**, con la ruta esperada del router (nombre del
  contrato del backend y etiqueta v2 de la interfaz), la evidencia esperada y lo que no debe ocurrir.
- **Caso 2A nuevo:** «Trabajo en compras de repuestos, prefiero respuestas breves y me interesan las
  motocicletas. Recuérdalo.» Se guardan tres preferencias no personales en el Store con namespace
  `("preferencias", user_id)`; no se guardan nombres, empresas ni datos de contacto.
- **Caso 2B nuevo:** «¿Qué preferencias tengo guardadas?», que recupera las preferencias del 2A en tres
  momentos: en el mismo hilo, en un hilo nuevo del mismo usuario y tras reiniciar el backend (PID distinto).
- **Aislamiento entre usuarios:** las preferencias y los hilos de un usuario seudónimo no son visibles
  para otro.
- **Revisión del PR de respuestas naturales:** el texto de la respuesta es para el cliente y la evidencia técnica
  viaja en `metadatos`. El caso 1 sin evidencia **empieza** por la frase de rechazo fija (admite una pregunta de
  seguimiento); el caso 3 entrega archivo y procedencia en `metadatos.fuentes_datos`; el caso 6 añade
  `metadatos.categoria_moderacion` y guarda la categoría, no el texto del mensaje.

## Out of Scope
- La implementación: el checkpointer SqliteSaver y el Store (PR de memoria persistente, #28 y #29 del
  plan), las sesiones por usuario (#44), las herramientas LangChain y el router (bloque 3) y las tarjetas
  de Rayos-X (#40).
- Cambios de la interfaz: el texto de `web/src/ignisCasos.ts` se actualiza en el PR de sesiones, que es el
  que toca `web/`.
- Evaluación cuantitativa del retrieval (#36), que tiene su propio banco de consultas.

## Impact
- **Solo documentación:** crea `openspec/changes/casos-validacion-ignis/` (este archivo, `tasks.md` y
  `specs/casos-validacion/spec.md`). No toca `src/`, `web/`, `tests/` ni `data/`.
- Las pruebas de aceptación de cada caso se escriben en los PR que implementan cada capacidad (ver
  `tasks.md`).
- Tipo: requisito del curso (casos 1–5) y extensión del equipo (caso 6, P06).
