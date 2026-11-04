# Propuesta: selección de contexto con BM25

## Why
El Módulo 1 exige consolidar todo el texto limpio en el prompt de sistema. Con
`llama3.2:3b` en Ollama la ventana efectiva depende de `num_ctx`; un corpus real del sitio
puede superar el presupuesto y provocar truncamiento silencioso.

## What Changes
- Modo `completo` (exigencia literal del taller) se mantiene por defecto cuando cabe.
- Nuevo modo `seleccion`: los k fragmentos más pertinentes por BM25 (extensión, sin dependencias).
- Modo `auto`: completo si cabe en `FNA_PRESUPUESTO_TOKENS_CONTEXTO`; si no, selección.

## Impact
- Código: `knowledge/recuperacion.py`, `knowledge/base.py`.
- Tipo: extensión propuesta (no exigida); prepara el Módulo 2 (RAG con embeddings).
