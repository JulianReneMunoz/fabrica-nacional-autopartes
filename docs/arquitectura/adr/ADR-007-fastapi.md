# ADR-007 · API REST con FastAPI (extensión)

- **Estado:** aceptada como extensión
- **Contexto:** la API no es exigida en el Módulo 1 (la Clase 1 la ubica en la Fase 3), pero el enunciado del proyecto la solicita.
- **Decisión:** FastAPI con contratos Pydantic, errores centralizados `{codigo, mensaje}`, paginación, filtros, auditoría y una operación administrativa protegida por `X-API-Key`.
- **Consecuencias:** contrato OpenAPI exportable (`fabrica openapi`) y colección Postman. La lógica permanece en `services`, compartida con Streamlit, CLI y MCP.
