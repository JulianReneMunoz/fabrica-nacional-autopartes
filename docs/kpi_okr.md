# KPI y OKR del agente

Indicadores definidos a posteriori (**retrospectivo**) sobre métricas que ya se midieron en las ejecuciones reales
del agente (bitácora [A-08, A-10 y A-11](prompts/bitacora_experimentos.md)). Los umbrales y los OKR son una
**propuesta** para la fase siguiente: no son compromisos aprobados ni se miden todavía en el CI. Ficha del modelo en
la [Model Card](model_card.md).

## KPI

Valor actual: la ejecución A-11 (banco v2, recuperador `hibrido`), informe
[`20261111T011717Z_agente_claude-haiku-5-5_banco-v2.json`](../evaluacion/resultados/20261111T011717Z_agente_claude-haiku-5-5_banco-v2.json).

| KPI | Definición | Valor actual | Fuente | Umbral propuesto |
|---|---|---|---|---|
| Exactitud global | Aciertos sobre las 24 preguntas del banco v2 (criterio estricto en las negativas) | **0,875** (21/24) | A-11, `metricas.exactitud_global` | ≥ 0,85 |
| Alucinaciones en ausentes | Respuestas a P20, P21 y P22 que contienen el dato ausente (horario, precio, correo personal) | **0** en A-10 y A-11 | Diagnóstico manual de A-10 y A-11 (las ausentes que fallaron no inventaron el dato; las demás dieron la frase fija) | 0 |
| URL inválidas | Preguntas con al menos una URL citada fuera de las fuentes devueltas | **0** | A-08, A-10 y A-11, `metricas.con_urls_invalidas` | 0 |
| Costo por pregunta | Costo total del banco dividido entre 24 | **≈ USD 0,00048** (cálculo sobre USD 0,0116 / 24) | A-11, `consumo.costo_usd` | ≤ USD 0,001 |
| Latencia mediana | Mediana de `latencia_ms` de las 24 preguntas | **2280 ms** | A-11 | ≤ 3000 ms |
| Tasa fundamentada | Respondibles con `puntaje_fundamentacion` ≥ 0,6 (fórmula de A-09, sin URL) | **0,789** | A-11, `metricas.tasa_fundamentada` | ≥ 0,75 |

Notas:
- El KPI de alucinaciones es hoy una **medición manual**. La métrica automática `ausentes_sin_dato_inventado` está
  propuesta en A-11 y pendiente en el [tablero](kanban.md).
- Cada valor sale de **una sola ejecución**; el modelo no admite temperatura 0 (ADR-028), así que una ejecución nueva
  puede variar. Un KPI se considera incumplido solo si falla en dos ejecuciones seguidas (propuesta).
- Los umbrales se fijaron un poco por debajo del valor actual, para detectar regresiones sin exigir una mejora que no
  esté medida.

Evolución registrada (mismas definiciones):

| KPI | A-08 (banco v1) | A-10 (banco v2) | A-11 (banco v2) |
|---|---|---|---|
| Exactitud global | 0,792 | 0,875 | 0,875 |
| URL inválidas | 0 | 0 | 0 |
| Costo por pregunta (cálculo) | ≈ USD 0,00057 | ≈ USD 0,00059 | ≈ USD 0,00048 |
| Latencia mediana (calculada del JSON en A-08 y A-10) | 2379 ms | 2322 ms | 2280 ms |
| Tasa fundamentada | 0,579 (fórmula anterior) | 0,737 | 0,789 |

## OKR (propuesta para la fase siguiente)

**O1. Respuestas confiables en todo el banco.**
- KR1: métrica `ausentes_sin_dato_inventado` implementada, con pruebas, y recalculada sobre los informes de A-10 y
  A-11.
- KR2: P08 acierta con el prompt v3 del agente, medido primero sin red con el agente simulado y luego en real.
- KR3: exactitud global ≥ 0,875 con el banco v2 en la ejecución real posterior al prompt v3.

**O2. Cumplimiento de datos personales y seguridad de herramientas.**
- KR1: log de diagnóstico del agente opcional y desactivado por defecto (Ley 1581 de 2012), con la limitación de
  `_cerrar_turno_interrumpido` anotada en ADR-030.
- KR2: escaneo con SkillSpector de Antigravity CLI documentado en la bitácora, con decisión registrada.

**O3. Entrega y sustentación.**
- KR1: informe LaTeX con las cifras de este documento y sus fuentes.
- KR2: presentación lista antes del hito de sustentación (fecha por confirmar, [cronograma](cronograma.md)).
