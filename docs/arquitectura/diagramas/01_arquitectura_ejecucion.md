# Arquitectura de ejecución

Componentes que existen en el código y cómo se comunican en ejecución. Las interfaces solo llaman a la capa de
servicios (`ServicioAsistente`, `ServicioSimulador`, `services.motos`); el acceso a SQL pasa por
`repositories/auditoria.py`.

```mermaid
flowchart LR
  usuario(["Usuario"])
  agente(["Agente de código<br/>Claude Code u OpenCode"])

  subgraph interfaces["Interfaces"]
    st["Streamlit<br/>frontend/app.py"]
    visor["Visor React + three.js<br/>web/ (servido en /app)"]
    api["FastAPI<br/>api/main.py"]
    cli["CLI fabrica"]
    mcp["Servidor MCP<br/>fna-conocimiento (solo lectura)"]
  end

  subgraph nucleo["Núcleo"]
    svc["Servicios<br/>services/"]
    kb[("Base de conocimiento<br/>data/gold")]
    db[("Auditoría y estados<br/>SQLite o PostgreSQL")]
    sim["Simulador 3D<br/>simulador/"]
  end

  llm["Proveedor LLM<br/>claude_code vía CLI, Ollama, OpenAI o Anthropic"]
  sitio[("Sitios oficiales<br/>fanalca.com y autopartesfanalca.com.co")]

  usuario --> st
  usuario --> visor
  usuario --> api
  agente -- "stdio" --> mcp
  st --> svc
  api --> svc
  cli --> svc
  visor -- "HTTP /api/v1" --> api
  mcp --> kb
  svc --> kb
  svc --> db
  svc --> sim
  svc -- "prompt con contexto" --> llm
  cli -- "scraping responsable" --> sitio
```

Regla de dependencias: `scraping → pipelines → knowledge → llm → services → interfaces`. El paquete `simulador`
solo depende de la biblioteca estándar, Pydantic, numpy y trimesh (se verifica con `scripts/verificar_capas.py`).
