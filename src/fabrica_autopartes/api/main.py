"""Aplicación FastAPI. Ejecutar: ``uv run uvicorn fabrica_autopartes.api.main:app --reload``.

Documentación interactiva: http://127.0.0.1:8000/docs (Swagger) y /redoc.
"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from fabrica_autopartes import __version__
from fabrica_autopartes.api.routes import agente, base, faq_visor, motos, operacion, simulador, tareas
from fabrica_autopartes.core.config import RAIZ_PROYECTO
from fabrica_autopartes.core.excepciones import ErrorFNA
from fabrica_autopartes.core.registro import configurar_registro, obtener_registro

log = obtener_registro(__name__)

DESCRIPCION = """
API del sistema de conocimiento de **Fábrica Nacional de Autopartes (Fanalca)**.

* **Tareas LLM**: Resumen, FAQ y Q&A anclados al contexto (LangChain).
* **Base de conocimiento**: consulta de fragmentos Gold con procedencia.
* **Operación**: salud, auditoría e historial del pipeline Medallion.
* **Simulador 3D (v2.0)**: ensamblajes, piezas, articulaciones, despiece, cinemática validada,
  cálculo del freno, estados, eventos y preguntas sobre piezas.
* **Biblioteca de máquinas**: explicadores interactivos alimentados por el scraping.
"""


def crear_app() -> FastAPI:
    configurar_registro()
    app = FastAPI(
        title="Fanalca — Base de Conocimiento y Q&A",
        version=__version__,
        description=DESCRIPCION,
        contact={"name": "Proyecto técnico FNA"},
        license_info={"name": "MIT"},
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:8501",
            "http://127.0.0.1:8501",
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ],
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

    @app.exception_handler(ErrorFNA)
    async def _manejar_error(_: Request, exc: ErrorFNA) -> JSONResponse:
        log.warning("%s: %s", exc.codigo, exc)
        return JSONResponse(status_code=exc.estado_http, content={"codigo": exc.codigo, "mensaje": str(exc)})

    @app.exception_handler(RequestValidationError)
    async def _manejar_validacion(_: Request, exc: RequestValidationError) -> JSONResponse:
        # Sin ``input``/``ctx`` (pueden traer NaN o Infinity, que no son JSON válido): 422 limpio.
        detalle = [{"type": e["type"], "loc": list(e["loc"]), "msg": str(e["msg"])} for e in exc.errors()]
        return JSONResponse(status_code=422, content={"detail": detalle})

    @app.exception_handler(ValueError)
    async def _manejar_valor(_: Request, exc: ValueError) -> JSONResponse:
        return JSONResponse(status_code=422, content={"codigo": "valor_invalido", "mensaje": str(exc)})

    app.include_router(operacion.router)
    app.include_router(base.router)
    app.include_router(tareas.router)
    app.include_router(agente.router)
    app.include_router(simulador.router)
    app.include_router(motos.router)
    app.include_router(faq_visor.router)

    # Versión 2.0: modelos GLB generados y frontend 3D compilado (si existen).
    dir_modelos = RAIZ_PROYECTO / "web" / "public" / "modelos"
    dir_web = RAIZ_PROYECTO / "web" / "dist"
    if dir_modelos.exists():
        app.mount("/modelos", StaticFiles(directory=dir_modelos), name="modelos")
    if dir_web.exists():
        app.mount("/app", StaticFiles(directory=dir_web, html=True), name="app")

        @app.get("/simulador", include_in_schema=False)
        def _ir_al_simulador() -> RedirectResponse:
            return RedirectResponse("/app/#/maquina/freno")

    return app


app = crear_app()
