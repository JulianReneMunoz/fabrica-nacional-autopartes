# ADR-005 · Contexto completo en el prompt de sistema con respaldo BM25

- **Estado:** aceptada
- **Contexto:** el asistente consolida todo el texto limpio en el prompt de sistema ("memoria" del asistente). Los modelos locales pequeños tienen ventana efectiva limitada por `num_ctx`.
- **Decisión:** modo `completo` (todo el texto limpio), modo `seleccion` (k fragmentos BM25) y modo `auto` (completo si cabe en el presupuesto). BM25 implementado sin dependencias.
- **Consecuencias:** se cumple el requisito y se evita el truncamiento silencioso. Prepara una etapa posterior (embeddings + base vectorial) con una interfaz de recuperación ya definida.
