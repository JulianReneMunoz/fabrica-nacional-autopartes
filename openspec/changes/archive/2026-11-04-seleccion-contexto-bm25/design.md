# Diseño

- BM25 Okapi (k1 = 1,5; b = 0,75) sobre título + encabezado + texto.
- Tokenización: minúsculas, sin tildes, sin palabras vacías ES/EN, raíz simple de plurales.
- Presupuesto en tokens aproximados (4 caracteres por token).
- Alternativa descartada: `rank-bm25` (dependencia adicional sin beneficio a esta escala).
