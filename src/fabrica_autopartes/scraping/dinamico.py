"""Navegación dinámica con Playwright para páginas que requieren JavaScript.

Dependencia opcional: ``uv sync --extra dinamico`` y luego ``uv run playwright install chromium``.
Solo se usa cuando el HTML estático no contiene el texto (por ejemplo, contenido
renderizado por *widgets* de Elementor). No elude CAPTCHAs ni controles de acceso.
"""

from __future__ import annotations


def renderizar(url: str, agente_usuario: str, tiempo_espera_ms: int = 20000) -> str:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "Playwright no está instalado. Ejecutar: uv sync --extra dinamico && "
            "uv run playwright install chromium"
        ) from exc

    with sync_playwright() as p:  # pragma: no cover - requiere navegador
        navegador = p.chromium.launch(headless=True)
        contexto = navegador.new_context(user_agent=agente_usuario)
        pagina = contexto.new_page()
        pagina.goto(url, wait_until="networkidle", timeout=tiempo_espera_ms)
        html = pagina.content()
        navegador.close()
        return html
