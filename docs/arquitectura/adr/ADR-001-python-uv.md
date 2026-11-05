# ADR-001 · Python 3.12 gestionado con uv

- **Estado:** aceptada · **Fecha:** 2026-11-04
- **Contexto:** `uv` es el gestor único de Python, entornos y dependencias del proyecto (sin pip ni requirements.txt). El entorno principal es Windows 11.
- **Decisión:** Python 3.12 fijado en `.python-version`; dependencias en `pyproject.toml`, bloqueo en `uv.lock`; grupo `dev` (sin notebooks ni Anaconda/Conda: el proyecto se ejecuta solo con módulos Python, CLI y pruebas); extras `anthropic` y `dinamico`.
- **Consecuencias:** instalación reproducible con `uv sync --locked` en Windows y Linux (CI con matriz `ubuntu-latest` y `windows-latest`). Python 3.13 queda admitido (`<3.14`) pero no es la versión de referencia.
