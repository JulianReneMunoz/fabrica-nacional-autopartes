# ADR-016 · Proveedor `claude_code`: Claude mediante la CLI de Claude Code, sin clave de API

- **Estado:** aceptada
- **Contexto:** el equipo trabaja con una suscripción de Claude (Claude Code) y no con créditos de API. El
  proveedor `anthropic` exige `FNA_ANTHROPIC_API_KEY`, que la suscripción no incluye.
- **Decisión:** nuevo proveedor `claude_code` (`src/fabrica_autopartes/llm/claude_code.py`), un `BaseChatModel` de
  LangChain que ejecuta `claude -p --output-format json --model <alias> --max-turns 1` con la sesión iniciada en
  Claude Code. El proceso se ejecuta en una carpeta temporal vacía (no lee el repositorio ni su CLAUDE.md) y recibe
  por la entrada estándar las instrucciones del sistema y el mensaje que construye la cadena, de modo que las
  salvaguardas (contexto delimitado, citas, rechazo) son las mismas que con los demás proveedores.
- **Alternativas:** clave de API (`anthropic`), recomendada para usuarios finales; Ollama local, sin costo pero con
  menor calidad.
- **Consecuencias:** cada llamada inicia un proceso (mayor latencia que la API) y consume la cuota de la suscripción.
  Uso previsto: desarrollo y evaluación local por la persona titular de la cuenta. Los errores (CLI ausente, sesión
  no iniciada, límite alcanzado) se informan como `proveedor_llm_no_disponible`.
