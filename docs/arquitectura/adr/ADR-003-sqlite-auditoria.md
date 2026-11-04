# ADR-003 · SQLite + SQLAlchemy 2 + Alembic para auditoría

- **Estado:** aceptada; ampliada por ADR-012 (PostgreSQL para despliegue en la versión 2.0)
- **Contexto:** se requiere registrar interacciones, ejecuciones del pipeline y evaluaciones. El enunciado pide justificar PostgreSQL, MongoDB o una arquitectura híbrida y evitar varias bases sin necesidad demostrada.
- **Decisión:** una sola base relacional SQLite (`data/app.db`) a través de un repositorio SQLAlchemy y migraciones Alembic. Ni PostgreSQL ni MongoDB se incorporan en el Módulo 1.
- **Alternativas:** PostgreSQL (requiere servidor; justificado en Fase 3 con concurrencia multiusuario); MongoDB (el corpus ya es documental en archivos; no aporta).
- **Consecuencias:** migrar a PostgreSQL solo exige cambiar `FNA_URL_BASE_DATOS` y ejecutar `alembic upgrade head`.
