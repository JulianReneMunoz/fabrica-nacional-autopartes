# ADR-004 · LangChain (LCEL) con proveedores intercambiables; Ollama por defecto

- **Estado:** aceptada
- **Contexto:** el taller permite Ollama (open source) o API privada y recomienda LangChain. La Clase 2 compara costo, privacidad y control.
- **Decisión:** cadenas `plantilla | modelo | analizador`; fábrica `crear_modelo` con `ollama` (por defecto, `llama3.2:3b`, `num_ctx` configurable), `openai`, `anthropic` y `extractivo` (línea base sin LLM para pruebas).
- **Consecuencias:** cambio de modelo por variable de entorno; pruebas deterministas sin GPU. Una suscripción Claude Pro/Max no habilita el proveedor `anthropic`: este requiere clave de la Consola con facturación por uso.
