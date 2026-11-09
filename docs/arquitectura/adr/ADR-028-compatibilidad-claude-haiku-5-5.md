# ADR-028 · Compatibilidad con Claude Haiku 5.5 (parámetros, errores, razonamiento y max_tokens)

- **Estado:** aceptada (2026-11-08). Detalle en la entrada A-05 de `docs/prompts/bitacora_experimentos.md`.
- **Contexto (hallazgo de la prueba real):** la primera pregunta real al agente en Streamlit falló con un 400 de
  Anthropic, «temperature: Extra inputs are not permitted» (request_id `req_011CgrZ1YPt63B8jXatHpBYJ`), y el
  error se mostró como traza. Causa, comprobada sin red: con `temperature=0`, `langchain-anthropic` 1.7.9 mueve la
  temperatura a `extra_body` y la envía; esa versión solo la retira para `claude-fable-5` y `claude-sonnet-5-5`, no
  para `claude-haiku-5-5`. Además, el traductor de errores del agente solo distinguía credenciales y red.
- **Fuente oficial:** guía de migración y página del modelo Haiku 5.5. Hay que omitir `temperature`, `top_p` y
  `top_k`. El razonamiento adaptativo está activo por defecto y sus tokens cuentan dentro de `max_tokens`. Existe
  `stop_reason: "refusal"`, que debe manejarse en el cliente, sin respaldo del servidor. El prefill del asistente se
  rechaza con 400. El ejemplo oficial usa `max_tokens: 16000`. La restricción de muestreo está verificada para
  Haiku 5.5 (y documentada también para Sonnet 5.5 y Opus 5.5); se aplica a toda la familia Claude 5.x por
  precaución.
- **Decisión:**
  1. `modelo_sin_parametros_de_muestreo()` (`llm/proveedores.py`) reconoce los modelos Claude 5.x; a ellos no se
     envía temperatura en el agente (`crear_modelo_agente`) ni en el Q&A con `anthropic` (`crear_modelo`).
     `aplica_temperatura()` informa `False` para esos modelos. `FNA_TEMPERATURA` no cambia para los demás
     proveedores ni para los modelos anteriores (por ejemplo, `claude-haiku-4-5`).
  2. `traducir_error_anthropic()` convierte los errores de estado de Anthropic en `ErrorProveedorLLM` (503): 401/403
     o saldo agotado → mensaje de credenciales; otros 400 (`BadRequestError`, `AnthropicInvalidRequestError`) →
     «La API de Anthropic rechazó la solicitud (400): …», con el `request_id`; el resto (red, 429, 5xx) sigue como
     «no respondió». Se usa en el agente y en `_proveedor_disponible` (Q&A, FAQ y resumen), así que Streamlit, la API
     y la CLI muestran un aviso y no una traza.
  3. Agente: `stop_reason: "refusal"` → mensaje propio (`MENSAJE_RECHAZO_SEGURIDAD`), sin fuentes y
     `rechazada_por_seguridad=True`; `stop_reason: "max_tokens"` → `MENSAJE_TRUNCADO` y `respuesta_truncada=True`, en
     lugar de la frase de rechazo, que sería engañosa. Ambos se evalúan solo en el turno actual. Streamlit los
     dibuja como rechazo (estilo `no_publicado`, sin fuentes) y la API devuelve los dos campos.
  4. `agente_max_tokens` pasa de 1024 a **16000** (ejemplo de la guía oficial) y su límite superior de 4096 a 32000.
     Es un tope, no un gasto.
  5. Prefill: no se usa. Todas las plantillas terminan en un turno `human` (`catalogo_prompts.py`) y el agente
     siempre envía una pregunta o un resultado de herramienta como último mensaje.
- **Consecuencias:**
  - **T=0:** con Haiku 5.5 no se fija la temperatura; la API usa sus valores por defecto. El determinismo se controla
    con el prompt (reglas de anclaje, frase de rechazo fija, citas) y con el anclaje exigido por el código (ADR-024),
    no con un parámetro de muestreo.
  - **Costo:** el razonamiento adaptativo está activo por defecto y se cobra como salida (indicación del usuario; las
    páginas consultadas confirman que cuenta dentro de `max_tokens`). El costo real por turno se medirá en la prueba
    real con Haiku y se registrará en la bitácora; la estimación de `modelos.md` (≈ USD 0,001) no lo incluye.
  - Los bloques de razonamiento de turnos anteriores quedan en el contexto y cuentan como entrada (guía de
    migración); el recorte del historial (ADR-024) los limita junto con el resto.
- **Pendientes (PR de `modelo_llm`):** detectar `stop_reason: "refusal"` en el Q&A (`llm/cadenas.py`), que hoy no se
  modifica para no arriesgar el Q&A con `claude_code`; y el `max_tokens=1024` fijo de `crear_modelo` con
  `anthropic`, junto con el `modelo_llm` por defecto (`llama3.2:3b`, ADR-027).
- **Alternativas:** fijar `temperature=1` (el valor por defecto) en lugar de omitirla (la documentación pide
  omitirla); actualizar `langchain-anthropic` y confiar en su filtro (no está garantizado para Haiku 5.5); 4096 de
  `max_tokens` con `effort: "low"` (menos razonamiento, sin cifras oficiales de cuánto ahorra).
- **Fuentes** (consultadas el 2026-11-08):
  - [Claude Haiku 5.5 migration guide](https://platform.claude.com/docs/en/models/haiku-5-5/migration-guide)
  - [Claude Haiku 5.5 overview](https://platform.claude.com/docs/en/models/haiku-5-5/overview)
  - [Thinking](https://platform.claude.com/docs/en/build-with-claude/thinking)
  - [Claude Sonnet 5.5 overview](https://platform.claude.com/docs/en/models/sonnet-5-5/overview)
