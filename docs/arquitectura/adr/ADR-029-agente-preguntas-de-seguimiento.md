# ADR-029 · Preguntas de seguimiento en el agente (prompt v2 y log de diagnóstico)

- **Estado:** aceptada (2026-11-08, opciones (a) y (d) aprobadas por el usuario). Detalle en la entrada A-06 de
  `docs/prompts/bitacora_experimentos.md`.
- **Contexto (prueba real en Streamlit, Claude Haiku 5.5, mismo hilo):** el turno 1, «¿Dónde queda la sede
  principal?», hizo 1 llamada a `buscar_fragmentos` y respondió con 4 fuentes. El turno 2, «¿Y cuál es su
  teléfono?», hizo 0 llamadas, tardó unos 1,4 s y devolvió la frase de rechazo, dos veces igual.
- **Diagnóstico (lectura del código, sin red):**
  - La frase se impone en `services/agente.py` (`_resultado`): sin llamadas a la herramienta en el turno, o sin
    fragmentos devueltos en él, la respuesta se reemplaza por la frase de rechazo. Es la garantía de anclaje de la
    ADR-024: el modelo respondió sin buscar.
  - El recorte del historial (`FNA_AGENTE_LIMITE_HISTORIAL_TOKENS`, 3000) podría quitar el turno 1 si los bloques
    de razonamiento de Haiku 5.5 fueran grandes, porque el contador aproximado también cuenta su firma. Con
    fragmentos reales y firmas supuestas de 2000 caracteres, el turno 1 suma unos 1523 tokens y se conserva. Queda
    sin confirmar: el tamaño real de las firmas solo se ve en una llamada real.
  - La auditoría guarda la respuesta ya reemplazada (`salida=r.respuesta`), así que no permitía saber qué respondió
    el modelo.
- **Opciones evaluadas:** (a) prompt v2 con búsqueda obligatoria en cada turno y reformulación del seguimiento; (b)
  `tool_choice` forzado en la primera llamada del turno, descartado porque con el razonamiento activo la
  documentación de razonamiento extendido solo admite `auto` o `none` (no verificado para Haiku 5.5) y daría
  probablemente un 400; (c) aceptar citas de fragmentos de turnos anteriores del hilo, descartado porque relaja la
  regla de buscar en cada turno; (d) log de diagnóstico, como complemento.
- **Decisión:**
  1. `llm/prompts/agente.yaml` **v2**, por defecto (`VERSION_PROMPT_AGENTE`); la v1 se conserva sin cambios. La v2
     pide llamar a `buscar_fragmentos` en cada turno, reformular el seguimiento como una consulta autocontenida
     (por ejemplo, «teléfono de contacto de Fanalca»), no responder solo con la conversación previa y citar la URL en
     texto plano entre paréntesis, sin Markdown (en la prueba real, Haiku escribió un enlace Markdown con la URL
     como texto y la interfaz lo mostró duplicado).
  2. La garantía de anclaje no cambia: sin búsqueda o sin cita válida en el turno, la frase de rechazo.
  3. Log de diagnóstico solo local (`logging`, nivel INFO; no se guarda en la base ni en archivos versionados): en
     cada llamada al modelo, el `thread_id`, los mensajes enviados (y los del estado) y los tokens aproximados; en
     cada turno, las llamadas a la herramienta, si la respuesta se reemplazó y la respuesta original recortada a 500
     caracteres. Nunca la clave ni encabezados.
- **Consecuencias:**
  - Que Haiku 5.5 obedezca la v2 solo se comprueba en la prueba real; las pruebas simuladas verifican el prompt
    enviado, la garantía de anclaje y el log, no el comportamiento del modelo.
  - Buscar en cada turno agrega una llamada a la herramienta y otra al modelo por seguimiento (más latencia y
    tokens).
  - El log de la próxima prueba real dirá si el recorte de 3000 tokens quita el turno anterior; si es así, se
    ajusta en otro PR.
