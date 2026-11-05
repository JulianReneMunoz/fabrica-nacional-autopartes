# Ciclo de vida de un dato de la ficha técnica

```mermaid
stateDiagram-v2
  [*] --> Campo: se agrega al YAML
  Campo --> Publicado: tiene valor, fuente y fecha de consulta
  Campo --> NoPublicado: no hay fuente verificable (valor nulo)
  Publicado --> Aplicado: «Ver con ficha de…» lo aplica al cálculo y a la escena
  NoPublicado --> Supuesto: el simulador conserva un valor típico marcado
  Supuesto --> Aplicado: se muestra como «supuesto didáctico»
  NoPublicado --> Publicado: se incorpora una ficha oficial posterior
  Aplicado --> [*]
```

Reglas: un valor sin fuente y fecha, o un `no_publicado` con valor, invalida el catálogo
(`services.motos.validar_catalogo`). Nada se estima en silencio; la interfaz muestra «No publicado» o
«supuesto didáctico» según corresponda.

## Flujo funcional del usuario

```mermaid
flowchart LR
  u(["Usuario"]) --> pest["Pestaña o máquina"]
  pest --> q["Streamlit: Q&A"]
  pest --> m["Visor: moto"]
  q --> aq["POST /api/v1/tareas/qa o servicio directo"]
  m --> am["GET /api/v1/motos/cb160f<br/>POST /api/v1/motos/cb160f/calculo"]
  aq --> r1["Tarjeta con respuesta y citas"]
  am --> r2["Números, ficha con fuente y estado"]
```
