---
name: fna-simulador-3d
description: Guía para modificar el simulador 3D v2.0 (modelo de componentes, articulaciones, despiece, generación procedural GLB, API del simulador y visor React Three Fiber). Usar al agregar piezas, ensamblajes, articulaciones o funciones del visor.
---

# Simulador 3D (versión 2.0)

## Responsabilidad
Mantener un simulador **demostrativo**: geometría procedural simplificada, parámetros marcados
como `demostrativo` y separación estricta entre animación visual y cálculo físico.

## Mapa del código
- Modelo y validación (Pydantic): `src/fabrica_autopartes/simulador/modelos.py`.
- Catálogo del freno de disco: `simulador/catalogo_freno.py` (`construir_freno`).
- Cinemática, despiece y secuencias: `simulador/cinematica.py`.
- Física simplificada del freno: `simulador/fisica_freno.py` (réplica TS en `web/src/modelos/freno.ts`).
- Generación GLB (trimesh + manifold3d, sin Blender): `simulador/generacion.py` →
  `uv run fabrica simulador generar`.
- API: `src/fabrica_autopartes/api/routes/simulador.py` (prefijo `/api/v1/simulador`).
- Visor: `web/src/paginas/EscenaFreno.tsx` y `MaquinaFreno.tsx`.

## Procedimiento para agregar una pieza
1. Declarar la `Pieza` en el catálogo con `id` en minúsculas, `funcion`, `dimensiones_m`,
   `direccion_despiece` (no nula), `distancia_despiece_m` en (0, 1] y `retirar_antes`.
2. Declarar su `Articulacion` (fija, rotacional, prismática, esférica o compuesta) con límites o
   `continua=True`; las compuestas requieren `maestra` y `relacion`.
3. Ejecutar `uv run pytest tests/unit/test_simulador.py tests/integration/test_generacion_3d.py -q`.
4. Regenerar el modelo: `uv run fabrica simulador generar` y la referencia del visor:
   `uv run python scripts/exportar_referencia_web.py`; luego `cd web; npm test; npm run build`.

## Restricciones
- No presentar la geometría como diseño industrial certificado ni afirmar que la animación valida
  propiedades mecánicas.
- No generar procedimientos de reparación ni de seguridad crítica; las preguntas de ese tipo se
  rechazan con `MENSAJE_SEGURIDAD`.
- El backend valida identificadores, límites y valores finitos enviados por el cliente.
- Todo modelo 3D externo documenta procedencia y licencia en el manifiesto.
