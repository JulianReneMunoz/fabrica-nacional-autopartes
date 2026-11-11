# Modelos Claude del proyecto: precios, uso y créditos

Decisión de proveedores en la [ADR-026](adr/ADR-026-haiku-proveedor-principal-agente.md). Precios **consultados en
noviembre de 2026** en la [página oficial de precios](https://platform.claude.com/docs/en/about-claude/pricing);
pueden cambiar: consultar la fuente antes de decidir.

## Modelos Claude

| Modelo | Identificador | Entrada / salida (USD por millón de tokens) | Uso en el proyecto |
|---|---|---|---|
| Claude Haiku 5.5 | `claude-haiku-5-5` | 0,10 / 0,50 con prompts de hasta 100 000 tokens; 0,50 / 2,50 por encima | **Agente, por defecto** (`FNA_MODELO_ANTHROPIC`) |
| Claude Sonnet 5.5 | `claude-sonnet-5-5` | 2 / 10 | Alternativa para el agente (`FNA_MODELO_ANTHROPIC=claude-sonnet-5-5`) |
| Claude Opus 5.5 | `claude-opus-5-5` | 4 / 20 | No necesario para esta carga |

En Haiku 5.5, una solicitud de más de 100 000 tokens de prompt paga la tarifa alta completa. El agente envía mucho
menos: el recorte del historial (`FNA_AGENTE_LIMITE_HISTORIAL_TOKENS`, 3000) y los fragmentos de la herramienta (hasta
10) lo mantienen lejos de ese umbral.

## Costo estimado por turno del agente

**Estimación**, no medición: unos 3000 tokens de entrada y 300 de salida por llamada, y 2 llamadas por turno (una para
decidir la búsqueda y otra para responder con los fragmentos).

| Modelo | Cálculo | Costo por turno |
|---|---|---|
| Haiku 5.5 | 2 × (3000 × 0,10 + 300 × 0,50) / 1 000 000 | ≈ USD 0,001 |
| Sonnet 5.5 | 2 × (3000 × 2 + 300 × 10) / 1 000 000 | ≈ USD 0,02 |

Con los créditos de Max (USD 100 al mes), la estimación equivale a unos 100 000 turnos con Haiku o unos 5000 con Sonnet.
Las cifras reales se registran en la bitácora cuando se ejecute la demostración con el modelo real.

## Costo medido del agente (A-08, A-10 y A-11)

La medición usa `usage_metadata` de cada respuesta del modelo, incluidas las que solo piden la herramienta. En Haiku
5.5 la salida incluye los tokens de razonamiento. El cálculo (`services/evaluacion_agente.py`) aplica 0,10 / 0,50 por
llamada y 0,50 / 2,50 si esa llamada supera los 100 000 tokens de entrada. Detalle y procedimiento en la entrada A-08
de `docs/prompts/bitacora_experimentos.md`.

| Ejecución | Llamadas al modelo | Tokens de entrada | Tokens de salida | Costo (USD) |
|---|---|---|---|---|
| Prueba de 3 turnos (mismo `thread_id`) | 6 | 17 852 | 605 | 0,00209 |
| Banco de 24 preguntas, v1 (A-08) | 49 | 101 774 | 7057 | 0,0137 |
| Banco de 24 preguntas, v2, recuperador `bm25` (A-10) | 50 | 104 721 | 7333 | 0,0141 |
| Banco de 24 preguntas, v2, recuperador `hibrido` (A-11, [ADR-031](adr/ADR-031-recuperador-hibrido-agente.md)) | 46 | 87 339 | 5756 | 0,0116 |
| **Total** | **151** | **311 686** | **20 751** | **≈ 0,041** |

Medido el 2026-11-10 con `claude-haiku-5-5`, sin ninguna llamada con tarifa alta. El costo medio fue de unos USD 0,0006
por pregunta del banco, por debajo de los USD 0,001 por turno estimados arriba. Hubo menos entrada por llamada de la
supuesta (unos 2000 tokens frente a 3000). El historial de un hilo largo sí la hace crecer: en la prueba de 3 turnos
pasó de 1155 a 4809 tokens por llamada. Con los créditos de Max (USD 100 al mes), el costo medido equivale a unas
160 000 preguntas.

Calidad del mismo banco: exactitud global oficial 0,792 (ajustada como análisis: 0,875), frente a 0,625 del Q&A
`extractivo` y 0,792–0,833 de `claude_code`. Diagnóstico de los fallos en A-08.

> **Nota (A-09):** el 0,625 del extractivo se midió sobre la semilla (`data/seed`), no sobre el Gold. Con el mismo
> corpus que el agente y `claude_code` (Gold), el extractivo da **0,375**, frente a **0,792** del agente. La cifra
> anterior se conserva como se registró.

Calidad por banco, todo sobre el Gold:

| Sistema | Banco | Exactitud respondibles | Rechazo correcto | Fundamentadas | Exactitud global | Fuente |
|---|---|---|---|---|---|---|
| Agente `anthropic` / `claude-haiku-5-5` | v1 | 0,789 | 0,8 | 0,579 (0,737 con la fórmula de A-09) | 0,792 | A-08 |
| Agente `anthropic` / `claude-haiku-5-5`, recuperador `bm25` | v2 | 0,895 | 0,8 | 0,737 | **0,875** | A-10 |
| Agente `anthropic` / `claude-haiku-5-5`, recuperador `hibrido` | v2 | 0,895 | 0,8 | 0,789 | **0,875** | A-11 |
| Q&A `extractivo` (selección BM25) | v1 | 0,368 | 0,4 | 0,789 | 0,375 | A-09 y A-10 |
| Q&A `extractivo` (selección BM25) | v2 | 0,474 | 0,4 | 0,789 | 0,458 | A-10 |

- Cifra oficial del agente con el banco v2 (A-10): **0,875**, sin errores, sin URL inválidas y sin ninguna llamada con
  tarifa alta.
- Con el recuperador `hibrido` (A-11, por defecto desde ADR-031), la exactitud es la misma (0,875). El costo baja un
  18 % (USD 0,0141 → 0,0116), la latencia media un 11 % (3265 → 2895 ms) y P11 queda resuelto. Fallan P08, P18 y
  P20.
- Los bancos v1 y v2 no se comparan directamente: cambian los hechos de P02, P07, P12, P15 y P16.
- `claude_code` (0,792–0,833) solo se midió con v1.

## Particularidades de Claude Haiku 5.5 en la API

Según la guía de migración oficial ([ADR-028](adr/ADR-028-compatibilidad-claude-haiku-5-5.md)):

- **Sin parámetros de muestreo:** se omiten `temperature`, `top_p` y `top_k`; cualquier valor no predeterminado
  da un 400. Con Haiku 5.5 no se fija T=0: el determinismo se guía con el prompt y con el anclaje del código.
- **Razonamiento adaptativo activo por defecto:** sus tokens cuentan dentro de `max_tokens` y se cobran como salida
  (indicación del usuario; pendiente de medir). Por eso `FNA_AGENTE_MAX_TOKENS` vale 16000, el valor del ejemplo
  oficial; es un tope, no un gasto. La estimación por turno de arriba no incluye el razonamiento: el costo real se
  registrará en la bitácora tras la prueba real.
- **`stop_reason`:** `refusal` (filtros de seguridad) y `max_tokens` (respuesta cortada) tienen mensajes propios en
  el agente.
- **Sin prefill:** el último mensaje enviado nunca es del asistente.

Fuente: [Claude Haiku 5.5 migration guide](https://platform.claude.com/docs/en/models/haiku-5-5/migration-guide).

## Cada modelo en su lugar

| Uso | Herramienta y modelo | Se paga con |
|---|---|---|
| Desarrollo del proyecto | Claude Code (sesión interactiva) | Cupo del plan Max |
| Q&A por defecto | Proveedor `extractivo` (sin LLM; [ADR-027](adr/ADR-027-proveedor-qa-por-defecto.md)) | Sin costo |
| Q&A, evaluación y FAQ del visor con un LLM | Proveedor `claude_code` (`FNA_PROVEEDOR_LLM=claude_code` o `--proveedor claude_code`; `claude -p`, Sonnet; [ADR-016](adr/ADR-016-proveedor-claude-code.md), [ADR-025](adr/ADR-025-endurecimiento-claude-p.md)) | Cupo del plan Max |
| Agente con memoria | Proveedor `anthropic` (API, Claude Haiku 5.5; [ADR-026](adr/ADR-026-haiku-proveedor-principal-agente.md)) | Créditos mensuales de API del plan Max: una bolsa aparte que no resta cupo a Claude Code |

La clave del agente se define como `FNA_ANTHROPIC_API_KEY` y **nunca** como `ANTHROPIC_API_KEY`: con esta última,
Claude Code facturaría por API en lugar de usar el plan.

## Créditos mensuales de API

- **Monto:** Max, USD 100 al mes; Ultra, USD 200 al mes. Claude Pro no incluye créditos de API.
- **Vinculación:** en claude.ai, *Settings > Billing* (Max o Ultra), sección *API credits*, opción *Link organization*.
  Requisitos: 7 días en el plan y rol Owner, Admin o Billing en la organización de la Claude Console. Solo se puede
  vincular una organización, y cambiarla requiere al soporte.
- **Alcance:** cubren la API de Claude (y la consola de pruebas de la Console); **no cubren Claude Code**.
- **Vencimiento:** vencen al final de cada ciclo de facturación; no se acumulan.
- **Al agotarse:** las solicitudes a la API se detienen hasta el siguiente ciclo, sin cobrar al plan.
- **Recomendación:** no activar la recarga automática (*auto-reload*) en la Console, para que el gasto no supere los
  créditos.

Fuentes: [API credits for subscribers (Claude Platform Docs)](https://platform.claude.com/docs/en/about-claude/api-credits-for-subscribers)
y [Monthly API credits for Max and Team plans (centro de ayuda)](https://support.claude.com/en/articles/17154008-monthly-api-credits-for-max-and-team-plans).
