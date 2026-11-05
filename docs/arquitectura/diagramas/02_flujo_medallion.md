# Flujo de datos Medallion

Del sitio oficial a la base de conocimiento, con una gráfica por etapa (`docs/graficas/`).

```mermaid
flowchart LR
  sitio[("Sitios oficiales")]
  rastreo["Rastreo responsable<br/>robots.txt, sitemaps, pausa mínima de 2 s"]
  antibots{{"Protección anti-bots<br/>HTTP 403, 429 o desafío"}}
  lectura["Lectura web puntual<br/>del dominio protegido"]
  bronze[("Bronze<br/>HTML + manifiesto.jsonl<br/>URL, fecha, estado, hash")]
  silver[("Silver<br/>texto limpio, secciones,<br/>contacto del pie, sin duplicados")]
  gold[("Gold<br/>documentos .md, fragmentos.jsonl,<br/>base_conocimiento.txt")]
  graficas["Gráficas por etapa<br/>docs/graficas"]

  sitio --> rastreo
  rastreo --> antibots
  antibots -- "no" --> bronze
  antibots -- "sí: se marca y se omite, no se elude" --> lectura
  lectura --> bronze
  bronze --> silver
  silver --> gold
  rastreo -.-> graficas
  bronze -.-> graficas
  silver -.-> graficas
  gold -.-> graficas
```

Reglas: se respeta `robots.txt` y `Crawl-delay`, el User-Agent es identificable y los correos no corporativos se
anonimizan en Silver (Ley 1581 de 2012).
