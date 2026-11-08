# ADR-026 · Claude Haiku 5.5 como proveedor principal del agente

- **Estado:** aceptada (2026-11-08, decisión del usuario). Reemplaza parcialmente a la
  [ADR-024](ADR-024-agente-con-memoria.md) en la elección del proveedor por defecto. Demostración con el modelo real
  **pendiente** (requiere la clave configurada). Detalle en la entrada A-02 de `docs/prompts/bitacora_experimentos.md`.
- **Contexto:** el agente (ADR-024) necesita un modelo con llamadas a herramientas (`bind_tools`). Ollama era el
  proveedor por defecto, pero no está instalado. El proveedor `claude_code` (CLI `claude -p`) no devuelve
  `tool_calls`. El plan Max del usuario incluye créditos mensuales de API (USD 100), una bolsa separada del cupo de
  Claude Code ([modelos.md](../modelos.md)).
- **Decisión:**
  1. `FNA_PROVEEDOR_AGENTE=anthropic` por defecto, con `FNA_MODELO_ANTHROPIC=claude-haiku-5-5` (Claude Haiku 5.5),
     temperatura 0, `max_tokens` acotado (`FNA_AGENTE_MAX_TOKENS`, 1024) y la clave en `FNA_ANTHROPIC_API_KEY`
     (nunca `ANTHROPIC_API_KEY`, para que Claude Code siga usando el plan).
  2. Sin clave, el agente responde 503 con la instrucción para obtenerla (créditos de Max, vinculación de la
     organización de la Console, `make verificar-agente`). No hay respaldo automático a otro proveedor.
  3. Ollama se conserva en el código como proveedor **opcional** (`FNA_PROVEEDOR_AGENTE=ollama`, `qwen3:8b`), sin
     instrucciones de activación en `CONTRIBUTING.md` (que documenta solo Haiku 5.5) y sin objetivos de
     instalación; su configuración está en la [ADR-024](ADR-024-agente-con-memoria.md).
  4. `claude_code` no se usa en el agente; sigue siendo el proveedor del Q&A (ADR-016, ADR-025).
- **Costo** (estimación, precios de noviembre de 2026): unos 3000 tokens de entrada y 300 de salida por llamada, con
  2 llamadas por turno, dan ≈ USD 0,001 por turno con Haiku 5.5 y ≈ USD 0,02 con Sonnet 5.5. Los créditos de Max
  alcanzan para unos 100 000 turnos estimados con Haiku. Si se agotan, la API se detiene sin cobrar al plan; no se
  activa la recarga automática. Cálculo y fuentes en [modelos.md](../modelos.md).
- **Consecuencias:**
  - El agente depende de la red y de la API de Anthropic; los fragmentos del corpus (datos públicos de Fanalca) y las
    preguntas salen del equipo.
  - Con los créditos de Max, el uso del agente no consume cupo de Claude Code.
  - Las pruebas siguen sin red ni clave (modelo simulado); la prueba real es opcional (`FNA_PRUEBAS_AGENTE_REAL=1`).
- **Alternativas:**
  - **Ollama local** (`qwen3:8b`): sin costo por token y sin enviar datos fuera del equipo. Según el usuario, se
    probó e instaló, y luego se desinstaló sin llegar a usarse con el agente. Queda como opción en el código.
  - **`claude_code` con un adaptador** que tradujera JSON a `tool_calls`: usaría el cupo del plan sin clave, pero se
    descartó por la fragilidad del formato y por necesitar 2 o más llamadas a `claude -p` por turno.
  - **Sonnet 5.5:** mayor capacidad, unas 20 veces más costoso por turno; queda como alternativa configurable
    (`FNA_MODELO_ANTHROPIC=claude-sonnet-5-5`).
