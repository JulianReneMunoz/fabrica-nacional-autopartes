# Propuesta (pendiente, Módulo 2): RAG con embeddings y base vectorial

## Why
El informe del Módulo 1 debe explicar el modelo de embeddings, el LLM y la base vectorial
que se usarán en el Módulo 2 (Taller 1, sección 5, "Modelado").

## What Changes
- Embeddings locales con Ollama: `nomic-embed-text-v2-moe` (alternativas indicadas en la Clase 1:
  `qwen3-embedding`, `embeddinggemma`).
- Base vectorial: Chroma persistente en `data/vectores/` (alternativa: Qdrant).
- Recuperación híbrida: BM25 (existente) + similitud coseno, fusión por rango recíproco.

## Impact
Estado: **pendiente**. No implementado en el Módulo 1.
