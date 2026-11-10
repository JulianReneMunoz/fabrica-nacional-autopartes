# ADR-030 · `tool_use` sin `tool_result` en el historial del agente (reparación y log de diagnóstico)

- **Estado:** aceptada (2026-11-09, opciones (a) y (d) aprobadas por el usuario). Detalle en la entrada A-07 de
  `docs/prompts/bitacora_experimentos.md`.
- **Contexto (prueba real en Streamlit, Claude Haiku 5.5, mismo hilo):** un turno hizo 2 llamadas a
  `buscar_fragmentos` y respondió bien. En el turno siguiente la API devolvió un 400: «messages.6: tool_use ids
  were found without tool_result blocks immediately after: toolu_01SctqjrSKm1bpSnwu5AQEWM» (request_id
  `req_011Cgst3PyeLQyKaCDQiTRo7`). El aviso de la interfaz salió sin traza.
- **Regla de la API:** cada bloque `tool_use` de un mensaje del asistente debe tener su `tool_result` al comienzo
  del mensaje siguiente del usuario.
- **Diagnóstico (sin red, con `ModeloSimulado` y el formateo de `ChatAnthropic._get_request_payload`):**
  - Los flujos normales no reproducen el 400: llamadas paralelas y secuenciales, con y sin bloques de razonamiento
    firmados y con recortes del historial de 600, 900 y 1200 tokens dan siempre mensajes válidos.
  - El único mecanismo reproducido dentro del agente es un `AIMessage` con un bloque `tool_use` en `content` que no
    está ni en `tool_calls` ni en `invalid_tool_calls`. Ese `tool_use` se reenvía sin ningún `ToolMessage` y causa
    exactamente ese 400.
  - Una llamada en `invalid_tool_calls` no causa el 400 dentro del agente. LangChain 1.4.9 la responde antes del
    middleware, con un `ToolMessage` de error (`_patch_invalid_tool_calls` en `langchain.agents.factory`). En
    una versión anterior de este diagnóstico se incluyó ese caso. Era un error: se había comprobado solo formateando
    los mensajes, sin pasar por `create_agent`. La prueba del agente lo corrigió.
  - **La causa exacta del 400 real sigue sin confirmar.** La hipótesis es una respuesta de Haiku 5.5 con un
    `tool_use` que LangChain no pasó a `tool_calls` ni a `invalid_tool_calls`. Solo la confirmará el log (d) de
    la próxima prueba real.
- **Opciones evaluadas:**
  - (a) reparar solo la copia que se envía al modelo;
  - (b) reparar el estado al cerrar el turno, que queda para después;
  - (c) tratar las `invalid_tool_calls` como error del turno, que queda para después. Además perdió sentido,
    porque LangChain ya las responde;
  - (d) log de diagnóstico, como complemento.
- **Decisión:**
  1. (a) `reparar_resultados_de_herramientas` (`services/agente.py`), aplicada en `RecorteHistorial.wrap_model_call`
     después del recorte. Revisa cada llamada de un `AIMessage`: bloques `tool_use` de `content`, `tool_calls` e
     `invalid_tool_calls`. Si una llamada no tiene su `ToolMessage` inmediatamente después, inserta uno sintético
     con `status="error"` y el texto `RESULTADO_SINTETICO` («Sin resultado: esta llamada a la herramienta no se
     ejecutó. No usar como fuente.»). Así se evita el 400 sea cual sea la causa exacta.
  2. El `ToolMessage` sintético existe solo en la copia enviada. No se guarda en la memoria del hilo ni cuenta como
     llamada, fragmento devuelto ni fuente del turno. La garantía de anclaje de la ADR-024 no cambia.
  3. (d) Log solo local (`logging`; no se guarda en la base ni en archivos versionados):
     - un WARNING por cada reparación, con el `thread_id` y el id del `tool_use` reparado;
     - un INFO por cada respuesta del modelo, con `stop_reason`, los ids de los bloques `tool_use`, los de
       `tool_calls` y los de `invalid_tool_calls`.

     Nunca registra la clave ni los encabezados.
  4. Nuevo texto del 400 en `traducir_error_anthropic` (`llm/proveedores.py`): ya no remite a la ADR-028, que
     solo trata del modelo. Indica que el error es de la solicitud y no de la clave ni de la red, que el detalle
     indica la causa, y que, si persiste, se inicie una conversación nueva y se conserve el request_id.
- **Consecuencias:**
  - El modelo ve el resultado sintético. Por eso no puede citar nada de esa llamada, y si responde sin una búsqueda
    válida en el turno la garantía de anclaje sigue imponiendo la frase de rechazo.
  - Si la próxima prueba real no registra ninguna reparación ni ningún `tool_use` fuera de `tool_calls`, la
    hipótesis queda descartada y el diagnóstico se retoma con ese log.
  - Las pruebas (`tests/unit/test_agente_historial_herramientas.py`) son simuladas. Verifican la reparación, la
    memoria, el anclaje y el log, pero no el comportamiento real de Haiku 5.5.
