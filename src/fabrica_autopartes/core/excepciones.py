"""Jerarquía de excepciones del dominio, traducidas a respuestas HTTP en la API."""


class ErrorFNA(Exception):
    """Error base del proyecto."""

    codigo: str = "error_interno"
    estado_http: int = 500


class ErrorConfiguracion(ErrorFNA):
    codigo = "configuracion_invalida"
    estado_http = 500


class ErrorBaseConocimientoVacia(ErrorFNA):
    codigo = "base_conocimiento_vacia"
    estado_http = 409


class ErrorRecursoNoEncontrado(ErrorFNA):
    codigo = "no_encontrado"
    estado_http = 404


class ErrorProveedorLLM(ErrorFNA):
    codigo = "proveedor_llm_no_disponible"
    estado_http = 503


class ErrorScrapingBloqueado(ErrorFNA):
    """La URL está prohibida por robots.txt o fuera de los dominios permitidos."""

    codigo = "scraping_no_permitido"
    estado_http = 403


class ErrorPreguntaBloqueada(ErrorFNA):
    """La pregunta contiene instrucciones que intentan cambiar el comportamiento: no se busca en la web."""

    codigo = "pregunta_bloqueada"
    estado_http = 422


class ErrorLimiteBusquedaWeb(ErrorFNA):
    """Se superó el número de búsquedas web permitidas en la ventana de tiempo."""

    codigo = "limite_busqueda_web"
    estado_http = 429
