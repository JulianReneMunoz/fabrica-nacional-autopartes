# Corpus semilla de demostración

Estos archivos **no** provienen del scraper del proyecto. Los archivos `autopartes-*.md` (origen `lectura_web`) resumen las páginas oficiales de autopartesfanalca.com.co leídas con una herramienta de lectura web (fuente de terceros); el resto (origen `semilla`) parafrasea páginas de fanalca.com. Son paráfrasis en español de datos públicos
del sitio oficial de Fanalca, consultados el 2026-11-04 mediante una herramienta de lectura
web, con la URL de origen en el *frontmatter* de cada archivo.

Finalidad: permitir que la aplicación, las pruebas y la demostración funcionen sin red.

Reemplazo obligatorio para la entrega: ejecutar en la raíz del repositorio

```powershell
uv run fabrica scrape
uv run fabrica build --fuente scraping
```

Con ello la capa Gold se reconstruye a partir de las capturas reales de la capa Bronze y la
semilla deja de usarse. El campo `origen` de cada fragmento (`semilla` o `scraping`) permite
auditar qué información respalda cada respuesta.
