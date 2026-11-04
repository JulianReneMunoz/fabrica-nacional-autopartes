# Imagen única para API (con el visor 3D en /app) y Streamlit. Construir desde la raíz:
#   docker build -f infra/docker/Dockerfile -t fna-conocimiento .

# --- Etapa 1: compilar el visor web (Vite + React Three Fiber)
FROM node:22-bookworm-slim AS visor
WORKDIR /web
COPY web/package.json web/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY web/ ./
RUN npm run build

# --- Etapa 2: aplicación Python
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_NO_DEV=1

COPY pyproject.toml uv.lock README.md ./
RUN uv sync --locked --no-install-project

COPY src ./src
COPY frontend ./frontend
COPY alembic ./alembic
COPY alembic.ini ./
COPY data/seed ./data/seed
COPY evaluacion/preguntas.yaml ./evaluacion/preguntas.yaml
COPY docs/graficas ./docs/graficas
COPY web/public/modelos ./web/public/modelos
COPY --from=visor /web/dist ./web/dist
RUN uv sync --locked && uv run fabrica build --fuente semilla

RUN useradd --create-home fna && chown -R fna /app
USER fna
EXPOSE 8000 8501
CMD ["uv", "run", "uvicorn", "fabrica_autopartes.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
