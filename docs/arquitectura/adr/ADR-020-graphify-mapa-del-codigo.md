# ADR-020 · Graphify para el mapa del código (excepción documentada)

- **Estado:** aceptada, con excepción a la regla de `fna-seguridad` (puntuación ≥ 51 se rechaza); detalle en la
  entrada S-08 de `docs/prompts/bitacora_experimentos.md`.
- **Contexto:** se necesita un mapa de dependencias del código (módulos, comunidades y nodos más conectados) que los
  diagramas Mermaid del README no ofrecen. Graphify (`graphifyy` en PyPI) construye ese grafo por análisis AST, pero
  SkillSpector lo califica con 100/100 porque el paquete también incluye skills para agentes, instaladores de hooks y
  clientes de LLM.
- **Decisión:**
  1. Versión fijada `graphifyy==0.9.102`, instalada con `uv tool`. Toda actualización repite el escaneo y la revisión.
  2. Solo `graphify extract --code-only` con `GRAPHIFY_BACKEND=none`: análisis AST local, sin LLM y sin red.
  3. El análisis se hace sobre una copia temporal de los archivos `.py`, `.ts` y `.tsx` de `src/` y `web/src/` (sin
     pruebas, datos, documentos ni configuración), y la salida queda fuera del repositorio.
  4. No se ejecutan `graphify install`, `claude install`, `hook install` ni `/setup-graphify`: `.claude/`, `CLAUDE.md`,
     `AGENTS.md` y `.git/hooks` (hook de GGA) no cambian.
  5. Se versionan solo el SVG y el informe (`docs/imagenes/mapa_codigo.svg`, `docs/graphify/GRAPH_REPORT.md`),
     revisados para que no contengan rutas personales, correos ni secretos; `graphify-out/` queda ignorado.
- **Consecuencias:** el mapa es una vista de dependencias generada, no un diseño; se regenera a mano cuando cambia la
  estructura. Los diagramas Mermaid (arquitectura y flujos) se conservan.
- **Alternativas:** `pydeps` o `madge` (sin comunidades ni informe), diagramas a mano en Mermaid (no escalan a todo el
  código), no incluir mapa.
