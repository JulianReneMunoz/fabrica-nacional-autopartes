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
