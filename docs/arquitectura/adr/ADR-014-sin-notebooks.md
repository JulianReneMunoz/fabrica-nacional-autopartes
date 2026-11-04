# ADR-014 · Sin notebooks ni Anaconda; exploración mediante CLI, gráficas y Streamlit (versión 2.0)

- **Estado:** aceptada (reemplaza el grupo de dependencias `notebooks` de la versión inicial)
- **Contexto:** el prompt maestro v2 prohíbe notebooks y Anaconda. La exploración del corpus de la
  versión inicial se realizaba en `notebooks/01_exploracion_corpus.ipynb`.
- **Decisión:** eliminar la carpeta `notebooks/`, el grupo `notebooks` de `pyproject.toml` y JupyterLab
  del manual. La exploración se cubre con `uv run fabrica stats`, las gráficas por etapa
  (`uv run fabrica graficas`) y las pestañas de Streamlit «Proceso de datos» y «Base de conocimiento».
- **Consecuencias:** todo el análisis es reproducible desde módulos Python versionados y probados.
