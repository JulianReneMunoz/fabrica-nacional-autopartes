# ADR-024 · Agente con memoria por conversación

- **Estado:** aceptada (2026-11-07). **Conexión real PENDIENTE:** el agente está construido y probado con un modelo
  simulado; Ollama no está instalado y no hay clave de Anthropic configurada. Reemplaza parcialmente a la
  [ADR-022](ADR-022-ollama-pospuesto.md) (Ollama queda como proveedor del agente, sin activar). Detalle en la entrada
  A-01 de `docs/prompts/bitacora_experimentos.md`.
- **Contexto:** la Fase 2 exige un agente con `create_agent` (LangChain v1), una herramienta tipada sobre el corpus y
  memoria por conversación (`InMemorySaver` + `thread_id`) con recorte del historial (`trim_messages`). El proveedor
  `claude_code` (CLI `claude -p`) no admite llamadas a herramientas (`bind_tools`), así que el agente necesita un
  modelo con *tool calling*: uno local (Ollama) o la API de Anthropic.
- **Decisión:**
  1. **Dependencias:** `langchain==1.4.9` y `langgraph==1.2.20` (base, sin torch).
  2. **Herramienta `buscar_fragmentos`:** argumentos validados con Pydantic (`consulta` de 1 a 300 caracteres,
     `k` entre 1 y 10, `recuperador` `bm25` o `semantico`, por defecto `bm25`). Devuelve el texto de cada fragmento
     con su id, URL y título (`response_format="content_and_artifact"`); el artefacto estructurado permite validar
     las citas. Si el recuperador semántico no está disponible, lo informa al modelo sin fallar.
  3. **Agente** (`services/agente.py`): `create_agent` con la herramienta, el prompt de sistema versionado
     `llm/prompts/agente.yaml` (v1: buscar antes de responder, citar la URL, frase de rechazo fija sin evidencia,
     fragmentos como datos), temperatura 0, `max_tokens` acotado y tope de iteraciones (`recursion_limit`). Las
     preguntas con patrones de inyección se bloquean antes de llamar al modelo. El código exige el anclaje, sin
     depender de que el modelo siga el prompt: sin llamadas a la herramienta o sin ninguna cita válida, la respuesta
     es la frase de rechazo; las URL e ids que la herramienta no devolvió en el turno se retiran del texto; las
     fuentes son solo las citadas que la herramienta devolvió, y `fundamentada` compara la respuesta con su texto
     (`puntaje_fundamentacion`, como en el Q&A). El texto y los atributos de cada `<fragmento>` se escapan.
     Consecuencia deliberada: una pregunta sobre la conversación misma («¿cuál fue mi pregunta anterior?») no
     consulta la base y recibe la frase de rechazo. La memoria sirve para resolver seguimientos que sí exigen buscar
     («¿y cuál es su teléfono?» después de preguntar por Fanalca), no para responder desde el historial.
  4. **Memoria:** `InMemorySaver` con `thread_id` (1 a 64 caracteres `[A-Za-z0-9_-]`). Un middleware
     (`wrap_model_call`) aplica `trim_messages` (estrategia `last`, `start_on="human"`, límite
     `FNA_AGENTE_LIMITE_HISTORIAL_TOKENS`, 3000 por defecto) solo a lo que se envía al modelo; el estado guardado queda
     completo. Empezar en un mensaje humano evita resultados de herramienta huérfanos; si el turno actual supera el
     límite, se conserva completo.
  5. **Proveedores** (`llm/proveedores.py`, `FNA_PROVEEDOR_AGENTE`, por defecto `ollama`), sin respaldo automático:
     - `ollama`: `ChatOllama` en `OLLAMA_BASE_URL` (por defecto `http://localhost:11434`; solo hosts locales) con
       `FNA_MODELO_OLLAMA` (`qwen3:8b`) y `FNA_OLLAMA_RAZONAMIENTO` (por defecto `false`). El texto de razonamiento
       (bloques `reasoning`/`thinking` o etiquetas `<think>`) nunca se muestra en la respuesta.
     - `anthropic`: `ChatAnthropic` con `FNA_MODELO_ANTHROPIC` (`claude-haiku-5-5`) y `FNA_ANTHROPIC_API_KEY`, pasada
       siempre de forma explícita: nunca se lee `ANTHROPIC_API_KEY`, para que Claude Code siga usando el plan Max.
     - Sin configuración (clave ausente, host no local) → `ErrorProveedorLLM` (503) con la instrucción. Al invocar: un
       401/403 o saldo agotado de Anthropic → «clave FNA_ANTHROPIC_API_KEY inválida o sin créditos»; un error de red
       o de un servicio que no responde → «no respondió». El límite de iteraciones devuelve un mensaje propio
       («No fue posible completar la consulta dentro del límite de iteraciones…»), no la frase de rechazo, y cierra el
       turno en la memoria para que el hilo siga utilizable.
  6. **Interfaces:** `ServicioAsistente.preguntar_agente` (auditoría con `tarea="agente"`), `POST /api/v1/agente`
     (`{pregunta, thread_id}`; 422 y 503) y `fabrica agente` (una pregunta, modo interactivo y `--verificar`).
- **Límites de la memoria en proceso** (suficientes para la demostración, no para producción):
  - Se pierde al reiniciar la API o la CLI.
  - Solo funciona con **un worker** de uvicorn: con varios, cada proceso tiene su propia memoria y un mismo
    `thread_id` vería historiales distintos según el worker que atienda.
  - Crece con cada turno: el recorte afecta a lo enviado al modelo, no a lo guardado. El número de hilos está acotado
    por `FNA_AGENTE_MAX_HILOS` (500 por defecto; al superarlo se descarta el hilo menos usado), pero no hay
    expiración por tiempo ni límite de turnos por hilo.
  - Producción requiere un checkpointer persistente y compartido (`SqliteSaver` o `PostgresSaver` de LangGraph),
    con expiración de hilos.
- **Consecuencias:**
  - Las pruebas usan un modelo simulado con `bind_tools` y guion (`tests/simulados.py`): cubren herramienta, citas,
    memoria, recorte, inyección, razonamiento, límite de iteraciones, errores de credenciales y de red, 422 y 503,
    sin red ni clave. La prueba con modelo real (`tests/integration/test_agente_real.py`) es opcional
    (`FNA_PRUEBAS_AGENTE_REAL=1`) para no consumir la API en cada ejecución.
  - No hay evidencia de calidad con un modelo real hasta activar un proveedor y evaluar con el banco de preguntas.
- **Alternativas:** `claude_code` como modelo del agente (descartado: sin *tool calling*); un ciclo ReAct propio
  (descartado: `create_agent` ya resuelve herramientas, checkpointer y middleware); respaldo automático entre
  proveedores (descartado: ocultaría qué modelo respondió y podría generar costos no previstos).
