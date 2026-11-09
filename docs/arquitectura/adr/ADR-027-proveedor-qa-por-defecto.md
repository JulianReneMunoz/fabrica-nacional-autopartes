# ADR-027 · `extractivo` como proveedor por defecto del Q&A

- **Estado:** aceptada (2026-11-08, decisión del usuario). Detalle en la entrada R-05 de
  `docs/prompts/bitacora_experimentos.md`.
- **Contexto:** el valor por defecto de `FNA_PROVEEDOR_LLM` (Q&A, FAQ y resumen; `core/config.py`) era `ollama`,
  aunque Ollama no se usa ni está instalado ([ADR-026](ADR-026-haiku-proveedor-principal-agente.md)). Ese valor
  solo afecta a un **clon nuevo sin `.env`** (Streamlit, API, `fabrica ask`, `fabrica evaluate` y el MCP): el CI fija
  `FNA_PROVEEDOR_LLM: extractivo` en el paso de pytest y `tests/conftest.py` crea la configuración con `extractivo`;
  `docker-compose.yml` fija `${FNA_PROVEEDOR_LLM:-extractivo}`. En un clon nuevo, el Q&A fallaba por no haber
  servidor de Ollama.
- **Opciones** (análisis del código, sin ejecutar proveedores):

  | Valor | Clon nuevo sin `.env` | Requiere | Costo |
  |---|---|---|---|
  | `ollama` (anterior) | Falla: no hay servidor | Instalar Ollama y descargar `llama3.2:3b` | Gratis |
  | `extractivo` | Funciona, sin red ni modelo | Nada | Gratis; exactitud global 0,625 (evaluación v3, selección BM25) |
  | `claude_code` | Funciona solo con la CLI `claude` instalada y con sesión en un plan Pro o Max | CLI y sesión del plan | Consume cupo del plan; exactitud 0,792–0,833 |
  | `anthropic` | Falla sin clave; con clave, también falla por el modelo (ver pendiente) | Clave, red, créditos y `FNA_MODELO_LLM` | Créditos de API |

- **Decisión:** `proveedor_llm = "extractivo"` por defecto. Es la única opción que funciona en un clon nuevo sin
  instalar nada, sin red, sin clave y sin costo, y coincide con lo que ya usan el CI y Docker. Quien quiera un LLM lo
  elige con `FNA_PROVEEDOR_LLM` en `.env` (`claude_code`, `anthropic` u `ollama`). La línea explícita de
  `docker-compose.yml` se mantiene.
- **Consecuencias:**
  - El Q&A de un clon nuevo responde con el modelo extractivo (respuestas léxicas, sin redacción de un LLM). El selector
    de Streamlit parte de `extractivo` y puede cambiarse en la sesión.
  - No cambia el CI ni Docker; tampoco un `.env` que ya defina `FNA_PROVEEDOR_LLM`.
  - Las cifras de evaluación con `claude_code` (E-01 a E-07) siguen siendo válidas: se obtuvieron con
    `--proveedor claude_code` explícito.
- **Pendiente (otro PR):** `modelo_llm` vale `llama3.2:3b` por defecto (`core/config.py`), un modelo de Ollama. Con
  `claude_code`, `modelo_claude_code()` lo traduce a `sonnet`; con **`anthropic`**, en cambio, `crear_modelo` envía
  `llama3.2:3b` a la API y la solicitud fallaría. Hoy, usar `FNA_PROVEEDOR_LLM=anthropic` exige definir también
  `FNA_MODELO_LLM` con un modelo Claude (por ejemplo, `claude-haiku-5-5`). Revisar el valor por defecto de
  `modelo_llm` (o derivarlo del proveedor) en un PR aparte; aquí no se cambia.
- **Alternativas:** `claude_code` por defecto (falla en equipos sin la CLI y consume cupo sin elegirlo);
  `anthropic` por defecto (gasta créditos sin elegirlo y requiere cambiar `modelo_llm`); mantener `ollama`
  (contradice la ADR-026 y falla en un clon nuevo).
