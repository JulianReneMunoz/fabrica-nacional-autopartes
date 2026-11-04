# ADR-005 · Contexto completo en el prompt de sistema con respaldo BM25

- **Estado:** aceptada
- **Contexto:** el Taller 1 pide consolidar todo el texto limpio en el prompt de sistema ("memoria" del asistente). Los modelos locales pequeños tienen ventana efectiva limitada por `num_ctx`.
- **Decisión:** modo `completo` (literal del taller), modo `seleccion` (k fragmentos BM25) y modo `auto` (completo si cabe en el presupuesto). BM25 implementado sin dependencias.
- **Consecuencias:** se cumple el requisito y se evita el truncamiento silencioso. Prepara el Módulo 2 (embeddings + base vectorial) con una interfaz de recuperación ya definida.
