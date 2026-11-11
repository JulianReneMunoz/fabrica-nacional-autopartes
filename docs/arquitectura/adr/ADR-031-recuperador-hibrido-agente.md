# ADR-031 · Recuperador híbrido (RRF) fijo por configuración en `buscar_fragmentos`

- **Estado:** aceptada (2026-11-10, configuración aprobada por el usuario). Mediciones en la entrada A-11 de
  `docs/prompts/bitacora_experimentos.md`.
- **Contexto:** con el banco v2 el agente da 0,875 (A-10) y fallan P11 y P18 por recuperación.
  - `buscar_fragmentos` usaba `bm25` con `k=5` por defecto, y el modelo podía pedir `semantico` en cada llamada.
  - Con BM25 y la pregunta literal, `negocios-ambiental#000` (P11) queda en el puesto 9 y `nosotros#000` (P18) en
    el 38.
  - Los informes del banco no registraban los argumentos de cada búsqueda, así que no se sabía qué recuperador
    pedía el modelo.
  - Un valor explícito del modelo anula el valor por defecto: si el modelo escribe `bm25`, cambiar el valor por
    defecto no tiene ningún efecto.
- **Mediciones (sin red):** Gold versionado de 167 fragmentos y banco v2, con la pregunta literal de las 19
  respondibles. Se evalúan 18, porque P08 no tiene fragmento relevante según el criterio de E-06. Detalle por
  pregunta en A-11.

  | Opción | hit@1 | hit@3 | hit@5 | hit@8 | MRR@10 | P11 | P18 | Tokens por llamada con k=5 (media) |
  |---|---|---|---|---|---|---|---|---|
  | `bm25` (anterior) | 0,667 | 0,833 | **0,944** | 0,944 | 0,754 | 9 | 38 | 840 |
  | `semantico` | 0,778 | 0,833 | 0,889 | 0,889 | 0,810 | 2 | 35 | 943 |
  | `hibrido` (RRF) | 0,778 | 0,889 | **0,944** | 0,944 | 0,838 | 1 | fuera del top 20 | 873 |

- **Decisión:**
  1. **Recuperador por defecto: `hibrido`.** Es una fusión por rangos recíprocos (RRF) de BM25 y del semántico:
     el puntaje de cada fragmento es Σ 1/(60 + rango), con los 20 primeros de cada recuperador
     (`knowledge.recuperacion.RecuperadorHibrido`). Los empates se ordenan por id.
  2. **`k = 5`.** En ninguna opción hit@8 supera a hit@5, y k=8 añade unos 550 tokens por llamada (+65 %).
  3. **El recuperador queda fijo por configuración** (`FNA_AGENTE_RECUPERADOR`: `hibrido` por defecto, `bm25` o
     `semantico`) **y deja de ser un argumento de la herramienta**, que solo expone `consulta` y `k`. Si el
     modelo envía un `recuperador`, se ignora como cualquier campo desconocido.
  4. **Vuelta explícita a `bm25`** cuando el semántico no está disponible: falta el extra, el modelo o el índice.
     Pasa en el CI, en un clon nuevo y en la imagen Docker.
     - Se registra un aviso la primera vez en cada `BaseConocimiento` y se guarda el motivo, para no volver a
       comprobar la disponibilidad en cada consulta.
     - Cada fuente del artefacto de la herramienta lleva el recuperador usado (`recuperador`), y el informe del
       banco lo muestra en `busquedas[].recuperador_usado`. `Fuente` no lo incluye: la respuesta del agente no
       cambia.
     - Antes, pedir `semantico` sin el semántico devolvía un error y ningún fragmento.
  5. **Prompt v2 sin cambios.** No menciona el recuperador; solo cambia el esquema de la herramienta.
  6. **`k` sigue siendo un argumento del modelo** (de 1 a 10). Preguntas de lista como P08 pueden necesitar más
     fragmentos, y la trazabilidad (A-11) mostrará si el modelo lo usa.
- **Por qué el recuperador no es un argumento (sobre las 18 respondibles evaluadas, no solo P11 y P18):**
  - Con k=5, el híbrido deja dentro de los 5 primeros todas las preguntas que deja cualquiera de los recuperadores
    solos, y tiene el mejor MRR.
  - Si el modelo eligiera un recuperador solo, perdería posiciones: con `bm25`, P11 y P15 quedan en el puesto 5 y
    P19 en el 3 (el híbrido los pone en el 1); con `semantico`, P01 sale de los 10 primeros (con BM25 está en el
    puesto 1) y P03 baja al 4.
  - Dejar la elección al modelo no aporta ninguna mejora medida y añade un riesgo que no se puede observar en los
    informes anteriores.
- **Alcance esperado (explícito):**
  - **El hit@5 del híbrido es igual al de `bm25` (0,944).** La mejora está en el orden: hit@1 pasa de 0,667 a
    0,778, hit@3 de 0,833 a 0,889 y MRR@10 de 0,754 a 0,838.
  - **En el banco, la ganancia esperada es sobre todo P11**: `negocios-ambiental#000` pasa del puesto 9 al 1.
    Las demás respondibles que hoy aciertan ya tenían su fragmento dentro de los 5 primeros.
  - **P18 es un límite documentado.** Ninguna opción pone `nosotros#000` entre los 20 primeros con la pregunta
    literal, porque la pregunta y el fragmento casi no comparten vocabulario. No se agrega una expansión de
    consulta específica, que sería ajustar el banco a la medida.
- **Carga del semántico (unos 22,6 s en este equipo):**
  - Se carga **una sola vez por proceso**. La API (`servicio_por_defecto`, `lru_cache`) y Streamlit
    (`st.cache_resource`) comparten un único `ServicioAsistente`, y su `BaseConocimiento` guarda el recuperador
    cargado. Un lock evita cargas dobles si la precarga y una consulta llegan a la vez.
  - **Precarga al arrancar.** La API la lanza en el ciclo de vida de FastAPI y Streamlit la lanza una vez por
    proceso. Las dos usan un hilo en segundo plano, solo si el recuperador es `hibrido` o `semantico`, y nunca
    bloquean el arranque: si el semántico no está o falla al cargar, queda un aviso y las búsquedas vuelven a
    `bm25`.
  - La CLI (`fabrica agente`) y `scripts/evaluar_agente_real.py` no precargan: pagan la carga en la primera
    búsqueda del proceso.
- **Consecuencias:**
  - Con el semántico disponible, cada búsqueda tarda unos 24 ms más y añade unos 33 tokens por llamada (+4 %).
    El proceso ocupa además la memoria del modelo.
  - Sin el semántico, el comportamiento es el mismo que con `bm25` antes de este ADR.
  - **Docker:** `docker-compose.yml` define `FNA_AGENTE_RECUPERADOR` con `bm25` por defecto, porque la imagen no
    instala el extra semántico. Si se pone `hibrido`, el agente vuelve a `bm25` con aviso.
  - El Q&A (`FNA_RECUPERADOR`, ADR-023), el MCP y la evaluación de recuperación no cambian.
  - Las cifras del agente anteriores a este ADR (A-08 y A-10) se obtuvieron con `bm25` por defecto. Se reproducen
    con `FNA_AGENTE_RECUPERADOR=bm25`.
- **Alternativas descartadas:**
  - **`semantico` por defecto:** peor hit@5 (0,889); pierde P01.
  - **k=8:** sin ganancia en hit y con unos 550 tokens más por llamada.
  - **BM25 con más peso para título y encabezado** (×2 y ×3): solo sube P11 al puesto 4, y cambiaría también el
    índice del Q&A.
  - **Dejar el recuperador como argumento:** un valor explícito del modelo anula el valor por defecto, y no hay
    ninguna ganancia medida que lo justifique.
