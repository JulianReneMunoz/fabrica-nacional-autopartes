# ADR-006 · Streamlit para la interfaz de prueba

- **Estado:** aceptada
- **Contexto:** el taller admite Streamlit o Gradio; la Clase 1 menciona "una primera interfaz en Streamlit".
- **Decisión:** Streamlit con pestañas (Panel, Q&A, Resumen, FAQ, Laboratorio de prompts, Evaluación, Base de conocimiento, Auditoría). La interfaz llama al servicio en proceso (sin pasar por la API) para una demostración fluida.
- **Consecuencias:** pruebas e2e con `streamlit.testing.v1.AppTest`. Gradio queda descartado por coherencia con el curso.
