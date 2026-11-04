# ADR-012 · PostgreSQL para el despliegue; SQLite para desarrollo (versión 2.0)

- **Estado:** aceptada
- **Contexto:** la versión 2.0 agrega estados visuales guardados y eventos del simulador, con escritura
  concurrente desde la API y Streamlit. El prompt maestro exige conservar PostgreSQL.
- **Decisión:** el mismo repositorio SQLAlchemy y las mismas migraciones Alembic sirven a dos motores:
  SQLite por defecto (`sqlite:///data/app.db`, sin instalación) y PostgreSQL 17 en el despliegue
  (`postgresql+psycopg://…`, servicio `postgres` de `docker-compose.yml`). Las pruebas de integración
  ejecutan las migraciones sobre un PostgreSQL embebido (`pgserver`).
- **Alternativas:** solo PostgreSQL (obliga a instalar un servidor para cualquier prueba local);
  MongoDB (los datos del simulador son relacionales y pequeños).
- **Consecuencias:** cambiar de motor solo requiere `FNA_URL_BASE_DATOS` y `uv run alembic upgrade head`.
