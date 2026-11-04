# Servidores MCP del proyecto

| Servidor | Tipo | Propósito | Permisos | Registro |
|---|---|---|---|---|
| `fna-conocimiento` | **Propio** (`src/fabrica_autopartes/mcp_server/server.py`) | Consultar la base Gold (buscar, obtener, estadísticas, validar) | Solo lectura; sin red; `responder_pregunta` deshabilitada por defecto | `.mcp.json` y `opencode.json` |
| Engram | Existente (Gentleman-Programming/engram, MIT) | Memoria persistente de decisiones del agente (SQLite + FTS5) | Escribe en `~/.engram/engram.db` | `engram setup opencode`; en Claude Code: `claude plugin marketplace add Gentleman-Programming/engram` y `claude plugin install engram` |
| GitHub MCP | Existente (oficial de GitHub) | Issues, ramas y PR | Token con alcance mínimo, solo repositorio del proyecto | Según documentación oficial de GitHub; no incluido por defecto |

## Servidor propio: uso
```powershell
uv run fabrica build            # el servidor necesita la base Gold
uv run fabrica-mcp              # stdio (lo inician OpenCode/Claude Code)
uv run fabrica-mcp --http       # Streamable HTTP en http://127.0.0.1:8765/mcp (solo local)
claude mcp list                 # verificar registro en Claude Code
```

Prueba funcional: `uv run pytest tests/integration/test_mcp.py -q` (incluye una sesión JSON-RPC real por stdio).

## Controles de seguridad
- Tools anotadas con `read_only_hint=True`, `destructive_hint=False`, `open_world_hint=False`.
- Límites: consulta ≤ 300 caracteres, k ≤ 10.
- Auditoría de cada llamada en stderr (stdout reservado al protocolo).
- El texto devuelto se declara como DATOS en las instrucciones del servidor (mitigación de inyección indirecta).
- En Claude Code solo se habilita `fna-conocimiento` (`enabledMcpjsonServers`); en OpenCode Engram queda `enabled: false` hasta instalarlo.
