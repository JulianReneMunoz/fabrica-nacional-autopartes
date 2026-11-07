# ADR-019 · Búsqueda web complementaria con Claude (opcional, tras la frase de rechazo)

- **Estado:** aceptada
- **Contexto:** cuando la base de conocimiento no contiene un dato, el sistema responde con la frase de rechazo fija.
  Para algunas preguntas existe información pública reciente fuera del corpus. Incorporarla a la base sin revisión
  rompería la garantía de que cada respuesta verificada se apoya en fragmentos citables.
- **Decisión:**
  1. **Nunca automática.** Solo se ofrece el botón «Buscar en la web con Claude» (Streamlit, pestaña Q&A; visor,
     «Preguntar en vivo») cuando la respuesta es la frase de rechazo, y solo se ejecuta si la persona usuaria lo pulsa.
     En la CLI, `fabrica ask --web` busca únicamente si la base respondió con la frase de rechazo.
  2. **Contrato:** `POST /api/v1/tareas/qa-web` → `RespuestaWeb` (respuesta, hallazgos con dato, URL y fecha de
     consulta, `encontrado`, etiqueta fija «Respuesta complementaria desde la web — no proviene de la base
     verificada»). Sin fuentes con URL, se informa que no se encontró información.
  3. **Herramientas limitadas.** `claude -p` corre en una carpeta temporal vacía con `--tools WebSearch,WebFetch` y
     `--allowedTools WebSearch,WebFetch`, `--max-turns 8` y 120 s de límite (`llm/busqueda_web.py`). Dominios
     preferidos: fanalca.com, autopartesfanalca.com.co y motos.honda.com.co.
  4. **Seguridad.** La detección de inyección se aplica antes de buscar (P24 nunca dispara búsqueda; 422
     `pregunta_bloqueada`). El contenido web es un dato: las instrucciones piden no seguir instrucciones de las
     páginas, respetar `robots.txt` y no eludir bloqueos. Límite de 5 búsquedas cada 10 min (429).
  5. **Revisión humana.** Cada hallazgo se agrega a `data/revision/hallazgos_web.jsonl` con estado
     `pendiente_revision` (carpeta ignorada por Git). Nada entra a Bronze, Silver ni Gold.
  6. **Evaluación sin cambios.** El modo web queda fuera de las métricas v1–v3 y de `fabrica evaluate`.
- **Consecuencias:** la respuesta web se muestra separada y etiquetada, con URL y fecha por dato. Los dominios
  preferidos y el respeto de `robots.txt` durante la búsqueda son instrucciones al modelo: el código solo exige URL
  `http(s)` y no restringe el dominio de cada hallazgo, por eso todo hallazgo queda pendiente de revisión humana.
  Las preguntas, respuestas y hallazgos se anonimizan (correos no corporativos) antes de guardarse. Depende de la
  sesión de Claude Code (como ADR-016) y de la red; las pruebas usan un buscador simulado y no acceden a Internet.
- **Alternativas:** incorporar los hallazgos a la base de forma automática (rechazada: sin revisión no hay
  verificabilidad); búsqueda automática tras cada rechazo (rechazada: costo, privacidad y riesgo de inyección).
