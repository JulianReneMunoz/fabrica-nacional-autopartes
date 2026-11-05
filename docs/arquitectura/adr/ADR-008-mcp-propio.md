# ADR-008 · Servidor MCP propio de solo lectura (SDK oficial 2.x)

- **Estado:** aceptada
- **Contexto:** MCP es el protocolo que conecta agentes con herramientas ("USB-C de los agentes"). Durante la construcción se instaló `mcp` 2.3.0, donde `FastMCP` fue renombrado a `MCPServer`.
- **Decisión:** servidor `fna-conocimiento` (stdio por defecto, Streamable HTTP opcional en 127.0.0.1) con tools anotadas `read_only_hint=True`; la tool que invoca el LLM está deshabilitada salvo `FNA_MCP_PERMITIR_LLM=true`. Se fija `mcp>=2.0,<3`.
- **Consecuencias:** OpenCode y Claude Code consultan la base sin permisos de escritura ni de red. La auditoría de llamadas se escribe en stderr para no contaminar el canal JSON-RPC.
