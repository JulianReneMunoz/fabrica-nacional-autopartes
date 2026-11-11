# Model Card: agente de Fanalca con Claude Haiku 5.5

Tarjeta del modelo del agente conversacional (`services/agente.py`). Las cifras citan su entrada de la
[bitácora](prompts/bitacora_experimentos.md) (A-08, A-09, A-10 y A-11) o su informe JSON en
[`evaluacion/resultados/`](../evaluacion/resultados/). Documento redactado a posteriori sobre ejecuciones ya
registradas (**retrospectivo**); no se hizo ninguna llamada real para elaborarlo.

## Detalles del modelo

| Campo | Valor | Fuente |
|---|---|---|
| Proveedor | `anthropic` (API de Anthropic, `FNA_PROVEEDOR_AGENTE`) | [ADR-026](arquitectura/adr/ADR-026-haiku-proveedor-principal-agente.md) |
| Modelo | Claude Haiku 5.5 (`claude-haiku-5-5`, `FNA_MODELO_ANTHROPIC`) | ADR-026 |
| Prompt de sistema | `agente.yaml`, versión v2 (búsqueda en cada turno, también en los seguimientos) | [ADR-029](arquitectura/adr/ADR-029-agente-preguntas-de-seguimiento.md), [`agente.yaml`](../src/fabrica_autopartes/llm/prompts/agente.yaml) |
| Orquestación | `create_agent` (LangChain v1) con la herramienta tipada `buscar_fragmentos`, memoria `InMemorySaver` por `thread_id` y recorte del historial | [ADR-024](arquitectura/adr/ADR-024-agente-con-memoria.md) |
| Recuperador de la herramienta | `hibrido` (RRF de BM25 y semántico nomic + Chroma), k=5, fijado por `FNA_AGENTE_RECUPERADOR` y no elegible por el modelo | [ADR-031](arquitectura/adr/ADR-031-recuperador-hibrido-agente.md) |
| Muestreo | Sin `temperature`, `top_p` ni `top_k`: Haiku 5.5 no los admite | [ADR-028](arquitectura/adr/ADR-028-compatibilidad-claude-haiku-5-5.md) |
| `max_tokens` | 16000 (tope, no gasto); el razonamiento adaptativo cuenta dentro de ese tope | ADR-028 |
| Paradas especiales | `refusal` → `MENSAJE_RECHAZO_SEGURIDAD`; `max_tokens` → `MENSAJE_TRUNCADO` | ADR-028 |
| Tarifa usada en el cálculo de costo | USD 0,10 / 0,50 por millón de tokens de entrada / salida; 0,50 / 2,50 por llamada de más de 100 000 tokens de entrada | bitácora A-08, [modelos.md](arquitectura/modelos.md) |
| Clave | Solo `FNA_ANTHROPIC_API_KEY` (nunca `ANTHROPIC_API_KEY`); los informes JSON se versionan sin la clave | ADR-026, bitácora A-10 y A-11 |

El modelo es un servicio de terceros: no se entrena ni se ajusta en este proyecto. Lo que se evalúa es el sistema
completo (prompt, herramienta, recuperador, filtros de citas y modelo).

## Uso previsto

- Responder preguntas sobre Fanalca (unidades de negocio, contacto, historia, productos) **únicamente** con los
  fragmentos de la base de conocimiento, citando el id o la URL de cada fuente.
- Preguntas de seguimiento dentro de la misma conversación (`thread_id`).
- Demostración académica en Streamlit, la API y la CLI.

## Fuera de alcance

- Datos que la base no publica (horarios, precios, correos personales): se responde con la frase de rechazo fija
  «La información solicitada no se encuentra en la base de conocimiento de Fanalca.».
- Procedimientos de reparación o de seguridad crítica (`AGENTS.md`).
- Datos personales (Ley 1581 de 2012).
- Uso como fuente oficial de la empresa: el contenido proviene de páginas públicas extraídas por scraping y puede
  estar desactualizado.

## Datos

| Elemento | Detalle | Fuente |
|---|---|---|
| Corpus | Gold de **167 fragmentos** de 64 documentos (`data/gold/fragmentos.jsonl`), obtenido por scraping responsable y el pipeline Medallion | bitácora A-10 y A-11, [ADR-002](arquitectura/adr/ADR-002-medallion-archivos.md) |
| Banco v1 | [`preguntas.yaml`](../evaluacion/preguntas.yaml): 24 preguntas, 19 respondibles y 5 negativas (3 ausentes, 1 fuera de alcance, 1 inyección) | bitácora A-08 |
| Banco v2 | [`preguntas_v2.yaml`](../evaluacion/preguntas_v2.yaml): mismos ids y proporción 19/5; cambian P02, P07, P12, P15 y P16 para que todo hecho esperado esté en el Gold; las ausentes llevan `dato_ausente` | bitácora A-10 |

El CI reconstruye `data/gold` desde la semilla (48 fragmentos), no desde el Gold de 167; por eso la prueba del banco
lee el Gold versionado con `git show HEAD:` (bitácora A-10, corrección).

## Evaluación

Ejecuciones reales hechas por el usuario con su clave (24 preguntas, un `thread_id` por pregunta, base Gold).

| Métrica | A-08 (banco v1, `bm25`) | A-10 (banco v2, `bm25`) | A-11 (banco v2, `hibrido`) |
|---|---|---|---|
| Exactitud global | 0,792 (19/24) | 0,875 (21/24) | **0,875 (21/24)** |
| Exactitud de respondibles | 0,789 (15/19) | 0,895 (17/19) | 0,895 (17/19) |
| Rechazo correcto | 0,8 (4/5) | 0,8 (4/5) | 0,8 (4/5) |
| Tasa fundamentada | 0,579 (fórmula anterior); 0,737 recalculada con la de A-09 | 0,737 | 0,789 |
| URL inválidas / errores | 0 / 0 | 0 / 0 | 0 / 0 |
| Latencia media | 3298 ms | 3265 ms | 2895 ms |
| Latencia mediana | 2379 ms (calculada del JSON) | 2322 ms (calculada del JSON) | 2280 ms |
| Informe | [`20261110T133423Z_agente_claude-haiku-5-5.json`](../evaluacion/resultados/20261110T133423Z_agente_claude-haiku-5-5.json) | [`20261110T192320Z_…_banco-v2.json`](../evaluacion/resultados/20261110T192320Z_agente_claude-haiku-5-5_banco-v2.json) | [`20261111T011717Z_…_banco-v2.json`](../evaluacion/resultados/20261111T011717Z_agente_claude-haiku-5-5_banco-v2.json) |

Notas de lectura:
- **Cifra oficial vigente: 0,875** con el banco v2 (A-10 y A-11).
- Las cifras del banco v1 y del v2 **no se comparan directamente**: cambian los hechos esperados de cinco preguntas
  (A-10).
- La fórmula de fundamentación cambió en A-09 (excluye las URL); las métricas anteriores a A-09 usan la fórmula
  anterior.
- La latencia media de A-11 incluye la carga del semántico en P01 (15 751 ms); sin P01, la media es de 2336 ms (A-11).
- Las medianas de A-08 y A-10 no figuran en la bitácora: se calcularon del campo `latencia_ms` de cada JSON.
- Las fechas del JSON están en UTC: el informe de A-11 (`2026-11-11T01:18:26+00:00`) corresponde a la noche del
  2026-11-10 en hora de Colombia.
- Línea base con el mismo corpus (Gold, banco v1): Q&A `extractivo` 0,375 frente a agente 0,792 (A-09).

## Costos medidos

| Ejecución | Llamadas al modelo | Tokens entrada / salida | Costo (USD) | Fuente |
|---|---|---|---|---|
| Prueba de 3 turnos (A-08) | 6 | 17 852 / 605 | 0,00209 | [`20261110T133238Z_agente_3_turnos.json`](../evaluacion/resultados/20261110T133238Z_agente_3_turnos.json) |
| Banco v1, `bm25` (A-08) | 49 | 101 774 / 7057 | 0,0137 | JSON de A-08 |
| Banco v2, `bm25` (A-10) | 50 | 104 721 / 7333 | 0,0141 | JSON de A-10 |
| Banco v2, `hibrido` (A-11) | 46 | 87 339 / 5756 | 0,0116 | JSON de A-11 |

Ninguna llamada pagó la tarifa alta. Con A-11, el costo por pregunta es de unos USD 0,00048 (cálculo sobre
USD 0,0116 / 24).

## Limitaciones

- **P08 (lista de unidades de negocio):** en A-11 el modelo hizo una sola búsqueda y encontró 2 de los 3 hechos
  mínimos. Depende de cuántas búsquedas hace el modelo en una pregunta de lista (A-11).
- **P18 (colaboradores iniciales):** límite de vocabulario. Ningún recuperador pone `nosotros#000` entre los 20
  primeros con la pregunta literal; no se agrega una expansión de consulta a la medida del banco (A-10, A-11).
- **Criterio estricto de las ausentes:** una respuesta que dice «no consta» y agrega un dato citado cuenta como fallo
  (regla de negocio de ADR-024). P20 y P21 alternan entre ejecuciones (A-10 y A-11), sin datos inventados.
- **Variación sin temperatura:** Haiku 5.5 no admite temperatura 0 (ADR-028); dos ejecuciones con la misma
  configuración pueden diferir. Cada cifra corresponde a una sola ejecución; no hay intervalos de confianza.
- **Métrica de fundamentación léxica:** mide solapamiento de términos con los fragmentos citados, no veracidad
  (A-08, A-09).
- **Corpus pequeño y estático:** 167 fragmentos de dos sitios públicos; un dato no publicado no se puede responder.

## Riesgos y mitigaciones

| Riesgo | Mitigación | Fuente |
|---|---|---|
| Alucinación o cita inventada | Anclaje por código: `urls_permitidas` y `_retirar_citas_inventadas` retiran toda URL que no sea el campo `url` o el texto de una fuente citada; frase de rechazo fija | bitácora A-09, ADR-024 |
| Citas que no corresponden al contexto | Toda cita debe ser un id o URL de un fragmento devuelto en el turno; el evaluador cuenta las URL inválidas (0 en A-08, A-10 y A-11) | `AGENTS.md`, JSON de evaluación |
| Inyección de prompts | Los fragmentos se tratan como datos; P24 (inyección) acierta en las tres ejecuciones; el recuperador no es un argumento del modelo | ADR-024, ADR-031, JSON de evaluación |
| Datos personales (Ley 1581 de 2012) | Silver anonimiza los correos no corporativos; P22 (correos personales) acierta en las tres ejecuciones. Pendiente: el log de diagnóstico guarda hasta 500 caracteres de la respuesta y debe ser opcional y desactivado por defecto ([tablero](kanban.md)) | `AGENTS.md`, [ADR-030](arquitectura/adr/ADR-030-agente-tool-use-sin-tool-result.md) |
| Costo descontrolado | Tope de costo por ejecución del banco (`--tope-usd`), parada ante el primer error y cálculo de la tarifa alta | bitácora A-08 |
| Exposición de la clave | Clave solo en `FNA_ANTHROPIC_API_KEY`; los JSON se revisan contra el prefijo de clave y las cadenas vetadas antes de versionarse | bitácora A-10, A-11 |

## Cómo reproducir

Las órdenes siguientes **no se ejecutaron en este documento**: hacen llamadas reales y gastan créditos. Las ejecuta el
usuario con su clave, como en A-10 y A-11.

Comando completo de A-11 (PowerShell):

```powershell
$env:FNA_PRUEBAS_AGENTE_REAL = "1"; $env:FNA_PROVEEDOR_AGENTE = "anthropic"; $env:FNA_MODELO_ANTHROPIC = "claude-haiku-5-5"; $env:FNA_AGENTE_RECUPERADOR = "hibrido"; $env:HF_HUB_OFFLINE = "1"
uv run --no-sync python scripts/evaluar_agente_real.py --banco v2 --tope-usd 0.10
Remove-Item Env:FNA_PRUEBAS_AGENTE_REAL, Env:FNA_PROVEEDOR_AGENTE, Env:FNA_MODELO_ANTHROPIC, Env:FNA_AGENTE_RECUPERADOR, Env:HF_HUB_OFFLINE
```

- `--no-sync` es obligatorio en el equipo de la ejecución: `uv run` sin esa opción sincroniza el entorno y retira el
  extra `semantica-gpu`, del que depende el recuperador `hibrido`.
- `HF_HUB_OFFLINE=1` carga el modelo de embeddings nomic desde la caché local, sin descargarlo.
- La última línea retira las variables de la sesión.

El script aborta sin llamar al modelo si la configuración no es `anthropic` / `claude-haiku-5-5` (A-08). La suite
normal (`uv run --no-sync pytest -q`) no hace llamadas reales: usa un modelo simulado.
