---
name: fna-api
description: Construye o modifica endpoints FastAPI del proyecto Fanalca con contratos Pydantic, errores centralizados y pruebas. Usar al agregar o cambiar rutas en src/fabrica_autopartes/api.
---

# Construcción de API

## Responsabilidad
Exponer los servicios del asistente mediante contratos estables y documentados.

## Entradas
Caso de uso y contrato de entrada/salida.

## Procedimiento
1. Definir DTO en `api/esquemas.py` (validaciones con `Field`).
2. Crear la ruta en `api/routes/` usando `Depends(obtener_servicio)`.
3. Errores de dominio: subclases de `ErrorFNA` (se traducen a JSON `{codigo, mensaje}`).
4. Operaciones administrativas: `Depends(exigir_admin)` con cabecera `X-API-Key`.
5. Prueba en `tests/integration/test_api.py` con `TestClient` y `dependency_overrides`.
6. Regenerar contrato: `uv run fabrica openapi` y actualizar `postman/`.

## Salidas
Endpoint, prueba y `docs/api/openapi.json` actualizado.

## Restricciones
Sin lógica de negocio en las rutas; sin acceso directo a SQL.

## Validación
`uv run pytest tests/integration/test_api.py -q`.
