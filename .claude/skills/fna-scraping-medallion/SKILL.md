---
name: fna-scraping-medallion
description: Implementa o ajusta el scraping responsable del sitio de Fanalca y el pipeline Medallion Bronze-Silver-Gold. Usar al agregar fuentes, cambiar extracción, limpieza o fragmentación.
---

# Scraping responsable y arquitectura Medallion

## Responsabilidad
Capturar contenido público del sitio oficial y transformarlo en conocimiento citable.

## Entradas
URLs semilla (`FNA_URLS_SEMILLA`), dominios permitidos y reglas de exclusión.

## Procedimiento
1. Leer `robots.txt` y sitemaps; nunca solicitar rutas en `Disallow`.
2. Capturar con `uv run fabrica scrape` (pausa ≥ 2 s, User-Agent identificable, reintentos con
   backoff). El HTML queda en `data/bronze/html/` y el manifiesto en `data/bronze/manifiesto.jsonl`.
3. Construir Silver/Gold sin red: `uv run fabrica build --fuente scraping`.
4. Revisar `data/gold/base_conocimiento.txt` y `uv run fabrica validate`.
5. Para páginas que exigen JavaScript: `uv sync --extra dinamico` y `scraping/dinamico.py`.

## Salidas
Bronze (HTML + JSONL con URL, fecha, estado, hash), Silver (`documentos.jsonl`), Gold
(Markdown con frontmatter, `fragmentos.jsonl`, `base_conocimiento.txt`, `estadisticas.json`).

## Restricciones
- Prohibido eludir CAPTCHAs, autenticación, límites de tasa o condiciones de uso.
- Prohibido capturar datos personales; los correos no corporativos se anonimizan.
- Las pruebas usan `tests/fixtures/sitio/` con `responses`, nunca el sitio real.

## Validación
`uv run pytest tests/integration/test_rastreo.py -q` y `uv run fabrica validate` sin errores.
