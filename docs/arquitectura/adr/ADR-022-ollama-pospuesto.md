# ADR-022 · Ollama pospuesto

- **Estado:** aceptada (2026-11-07); detalle en la entrada R-04 de `docs/prompts/bitacora_experimentos.md`.
- **Contexto:** Ollama figura como proveedor LLM (`llm/proveedores.py`, ADR-004), como dependencia
  (`langchain-ollama`), en los scripts de instalación y verificación de Windows y en la propuesta OpenSpec de embeddings
  del Módulo 2. Nunca se instaló en la máquina de desarrollo: la evaluación v1–v3 se ejecutó con `extractivo` (E-00) y
  con `claude_code` (E-01 a E-03, ADR-016). Mantenerlo como requisito obliga a descargar varios GB de modelos sin que
  ningún entregable vigente lo use.
- **Decisión:**
  1. Ollama no se instala, no se ejecuta y no se agrega como dependencia nueva ni como objetivo del `Makefile`.
  2. Los entregables que dependen de Ollama se marcan «⏸ pospuesto», no «✗».
  3. LLM: `claude_code` (desarrollo y evaluación local) y `extractivo` (línea base y pruebas). Para un agente con
     herramientas (`create_agent`), `ChatAnthropic` de `langchain-anthropic`, o `bind_tools` en `ChatClaudeCode`.
  4. Embeddings: `nomic-embed-text` mediante `sentence-transformers` con el modelo descargado de Hugging Face, que
     admite los mismos prefijos `search_query:` y `search_document:`.
  5. El proveedor `ollama` existente, `langchain-ollama` y las menciones en scripts y manuales se retiran o se marcan
     en un PR aparte; este cambio no los modifica.
- **Consecuencias:**
  - Sin modelos locales de varios GB ni servicio en `localhost:11434`; los LLM dependen de la sesión de Claude Code o
    de una clave de API, y los embeddings de `sentence-transformers` (dependencia nueva cuando se implementen).
  - Las pruebas siguen sin red: proveedor `extractivo` y modelos simulados.
  - Hasta el PR de retiro, el código conserva un proveedor que no se prueba de extremo a extremo.
- **Alternativa:** Ollama como servidor local de LLM y embeddings (`nomic-embed-text-v2-moe`, `llama3.2:3b`).
- **Condición para retomarlo:** que el curso exija modelos abiertos ejecutados en local, o que se requiera operar
  sin conexión, con hardware suficiente. Retomarlo exige versión fijada, el escaneo de `fna-seguridad`, una entrada
  nueva en la bitácora y una ADR que reemplace a esta.
