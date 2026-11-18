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


class ErrorRecuperadorNoDisponible(ErrorFNA):
    """El recuperador semántico no está listo: falta el extra, el modelo o el índice (ADR-023)."""

    codigo = "recuperador_no_disponible"
    estado_http = 503

    INSTRUCCION = "Ejecutar 'make instalar-semantica-gpu' (o 'make instalar-semantica') y 'make indexar'."

    def __init__(self, motivo: str) -> None:
        super().__init__(f"Recuperador semántico no disponible: {motivo}. {self.INSTRUCCION}")
        self.motivo = motivo


# --- Sesiones (ADR-033). Los mensajes son genéricos: nunca incluyen el alias ni el user_id. --------------
MENSAJE_SIN_SECRETO_SESION = "Las sesiones requieren IGNIS_SECRETO_SESION en .env (32 caracteres o más)."


class ErrorSesionesNoConfiguradas(ErrorFNA):
    """Falta ``IGNIS_SECRETO_SESION`` o es demasiado corto: no hay secreto por defecto en el código."""

    codigo = "sesiones_no_configuradas"
    estado_http = 503

    def __init__(self) -> None:
        super().__init__(MENSAJE_SIN_SECRETO_SESION)


class ErrorAliasInvalido(ErrorFNA):
    codigo = "alias_invalido"
    estado_http = 422

    def __init__(self) -> None:
        super().__init__(
            "Alias no válido: usa de 3 a 32 letras, números o guiones, "
            "sin nombre completo, correo ni teléfono."
        )


class ErrorSinSesion(ErrorFNA):
    codigo = "sin_sesion"
    estado_http = 401

    def __init__(self) -> None:
        super().__init__("Sesión no válida o vencida: vuelve a entrar con tu alias.")


class ErrorHiloAjeno(ErrorFNA):
    codigo = "hilo_ajeno"
    estado_http = 403

    def __init__(self) -> None:
        super().__init__("El hilo no pertenece a esta sesión.")


# --- Voz de IGNIS (Piper) ----------------------------------------------------------------------------
class ErrorVozNoDisponible(ErrorFNA):
    """Faltan los archivos de la voz de Piper: el frontend usa la voz del navegador como respaldo."""

    codigo = "voz_no_disponible"
    estado_http = 503

    def __init__(self) -> None:
        super().__init__("Falta la voz: ejecuta scripts/descargar_voz.py")
