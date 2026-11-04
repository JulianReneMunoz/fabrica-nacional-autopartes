# ADR-011 · Geometría procedural con trimesh + manifold3d (versión 2.0)

- **Estado:** aceptada
- **Contexto:** el simulador 3D requiere un modelo del freno de disco generado por código, ejecutable
  desde la CLI, reproducible y exportable a glTF binario (GLB) para el visor web. El prompt maestro v2
  exige justificar Blender CLI y descarta Anaconda/Conda.
- **Alternativas:**
  - Blender por CLI (`blender -b -P script.py`): render de alta calidad, pero no se instala con `uv`,
    agrega cientos de MB y una dependencia externa al entorno Python.
  - CadQuery / FreeCAD (B-Rep paramétrico): modelado CAD real, pero depende de OCP con binarios
    nativos pesados cuya vía de instalación habitual es Conda.
  - trimesh + manifold3d: ruedas binarias para Windows y Linux instalables con `uv`, booleanas
    robustas, exportación GLB directa y verificación de mallas cerradas (volumen, estanqueidad).
- **Decisión:** trimesh + manifold3d en `src/fabrica_autopartes/simulador/generacion.py`, invocado con
  `uv run fabrica simulador generar`. Cada pieza es un nodo GLB con su identificador y un material PBR.
- **Consecuencias:** geometría simplificada (primitivas y booleanas), adecuada para fines
  demostrativos y no para fabricación; salida reproducible verificada por hash en el manifiesto.
  Si en el futuro se requiere CAD paramétrico, la interfaz `construir_escena` permite sustituir el
  generador sin cambiar el visor ni la API.
