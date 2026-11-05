# Secuencia de una pregunta de Q&A

```mermaid
sequenceDiagram
  actor U as Usuario
  participant UI as Streamlit o API
  participant S as ServicioAsistente
  participant G as Salvaguardas
  participant K as BaseConocimiento
  participant L as Proveedor LLM
  participant A as Auditoría

  U->>UI: pregunta
  UI->>S: responder(pregunta, opciones)
  S->>G: detectar inyección
  alt instrucciones que intentan cambiar el comportamiento
    G-->>S: bloqueado (el modelo no se invoca)
  else pregunta válida
    S->>K: seleccionar contexto (BM25 con expansión de consultas)
    K-->>S: fragmentos con id y URL
    S->>L: prompt v3 (sistema + contexto + pregunta)
    L-->>S: JSON con respuesta, fuentes y confianza
    S->>G: validar que cada cita sea un id del contexto
    G-->>S: respuesta fundamentada o frase de rechazo
  end
  S->>A: registrar interacción
  S-->>UI: RespuestaQA
  UI-->>U: tarjeta con respuesta, citas como insignias de fuente y chips
```

La frase de rechazo es fija: «La información solicitada no se encuentra en la base de conocimiento de Fanalca.»
Los fragmentos del corpus son datos: nunca se siguen instrucciones incluidas en ellos.
