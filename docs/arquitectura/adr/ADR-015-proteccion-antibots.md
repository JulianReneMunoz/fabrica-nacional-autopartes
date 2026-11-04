# ADR-015 · Sitios con protección antibots: no se elude; complemento con lectura web documentada

- **Estado:** aceptada (4 de noviembre de 2026, tras la primera ejecución real del scraping)
- **Contexto:** en la ejecución real desde Windows 11, `https://autopartesfanalca.com.co/` respondió a
  todas las peticiones con `HTTP 202 Accepted` y el encabezado `SG-Captcha: challenge` (SiteGround
  Security): una página de verificación para navegadores, no el contenido. `fanalca.com` se rastreó con
  normalidad (60 páginas). AGENTS.md prohíbe eludir CAPTCHAs, autenticación o bloqueos.
- **Alternativas descartadas:** navegador automatizado o cambio de User-Agent para superar el desafío
  (vulnera la regla de scraping responsable); omitir la unidad de autopartes (deja sin datos la
  biblioteca de máquinas y las preguntas sobre plantas y clientes).
- **Decisión:**
  1. El rastreador detecta el desafío (encabezados `SG-Captcha`, `cf-mitigated`, `x-sucuri-block`,
     `x-amzn-waf-action` o marcas de CAPTCHA en respuestas 202/403/429/503), registra el host como
     protegido en `data/bronze/errores.jsonl` y en `resumen_rastreo.json`, y no vuelve a solicitarlo.
  2. `uv run fabrica pipeline` construye la base con la fuente `mixta`: todo lo capturado por scraping
     más la lectura web documentada (`data/seed/autopartes-*.md`, `origen: lectura_web`, con URL y fecha)
     **solo** de los dominios sin capturas. La semilla genérica nunca se mezcla.
  3. La gráfica de rastreo muestra las URL omitidas por protección y el host protegido.
- **Consecuencias:** la base distingue `scraping` y `lectura_web` en cada fragmento; si el sitio retira
  la protección o la empresa autoriza el acceso, la siguiente ejecución lo rastrea y el complemento deja
  de usarse automáticamente. `--sin-complemento` construye solo con scraping.
