# ADR-002 · Arquitectura Medallion sobre archivos (JSONL y Markdown)

- **Estado:** aceptada
- **Contexto:** la arquitectura Medallion propone Bronze (HTML + JSONL de captura), Silver (texto limpio) y Gold (Markdown + metadatos). El corpus de una empresa es pequeño (decenas a cientos de páginas).
- **Decisión:** almacenar las capas en `data/bronze`, `data/silver` y `data/gold` como archivos versionables. Equivalencia con la nomenclatura alternativa `data/raw`, `data/processed` y `data/gold`: Bronze, Silver y Gold, respectivamente.
- **Consecuencias:** reprocesamiento sin red (`fabrica build`), revisión humana directa, sin servidor de base de datos. Para volúmenes mayores se evaluaría Parquet/DuckDB.
