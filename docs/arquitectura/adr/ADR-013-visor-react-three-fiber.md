# ADR-013 · Visor 3D con Vite + React + React Three Fiber, servido por FastAPI (versión 2.0)

- **Estado:** aceptada
- **Contexto:** Streamlit es la interfaz empresarial principal, pero no ofrece una escena WebGL con
  selección por rayos, planos de corte, animación por fotograma ni controles de órbita.
- **Alternativas:** componente Streamlit personalizado (acopla el ciclo de re-ejecución de Streamlit a
  la animación); three.js sin framework (más código imperativo); Babylon.js (motor completo, mayor peso).
- **Decisión:** aplicación Vite + React + TypeScript con `three`, `@react-three/fiber` y
  `@react-three/drei` en `web/`. Se compila a `web/dist` y FastAPI la sirve en `/app`, mismo origen que
  la API (sin CORS en producción). Streamlit enlaza e incrusta el visor.
- **Consecuencias:** se agrega Node.js LTS al entorno de desarrollo (ya requerido por OpenCode y
  OpenSpec). El cálculo del freno se replica en TypeScript para responder en cada fotograma y se
  verifica con Vitest contra valores exportados por Python.
