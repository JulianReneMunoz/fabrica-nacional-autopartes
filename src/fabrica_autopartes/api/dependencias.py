"""Dependencias inyectables de FastAPI (permiten sustituir el servicio en pruebas)."""

from __future__ import annotations

import secrets

from fastapi import Depends, Header, HTTPException, status

from fabrica_autopartes.services.asistente import ServicioAsistente, servicio_por_defecto


def obtener_servicio() -> ServicioAsistente:
    return servicio_por_defecto()


def exigir_admin(
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    servicio: ServicioAsistente = Depends(obtener_servicio),
) -> None:
    """Protege operaciones administrativas. Si no hay clave configurada, se deniegan."""
    clave = servicio.config.api_clave_admin
    if clave is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Operación deshabilitada: falta FNA_API_CLAVE_ADMIN")
    if x_api_key is None or not secrets.compare_digest(x_api_key, clave.get_secret_value()):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Clave de administración inválida")
