# ADR-007 · API REST con FastAPI (extensión)

- **Estado:** aceptada como extensión
- **Contexto:** la API no es imprescindible para construir la base de conocimiento, pero el proyecto la ofrece como contrato para integradores.
- **Decisión:** FastAPI con contratos Pydantic, errores centralizados `{codigo, mensaje}`, paginación, filtros, auditoría y una operación administrativa protegida por `X-API-Key`.
- **Consecuencias:** contrato OpenAPI exportable (`fabrica openapi`) y colección Postman. La lógica permanece en `services`, compartida con Streamlit, CLI y MCP.
