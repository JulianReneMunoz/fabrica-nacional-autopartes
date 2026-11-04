# ADR-002 · Arquitectura Medallion sobre archivos (JSONL y Markdown)

- **Estado:** aceptada
- **Contexto:** la Clase 2 propone Bronze (HTML + JSONL de captura), Silver (texto limpio) y Gold (Markdown + metadatos). El corpus de una empresa es pequeño (decenas a cientos de páginas).
- **Decisión:** almacenar las capas en `data/bronze`, `data/silver` y `data/gold` como archivos versionables. La clase usa los nombres `data/raw`, `data/processed` y `data/gold`; se adoptan los nombres Bronze/Silver/Gold del enunciado del proyecto y se documenta la equivalencia.
- **Consecuencias:** reprocesamiento sin red (`fabrica build`), revisión humana directa, sin servidor de base de datos. Para volúmenes mayores se evaluaría Parquet/DuckDB.
