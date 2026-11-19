# Licencias de Modelos 3D — IGNIS

- `../assets/blueprint_2d.png`: Recurso propio generado por `scripts/generar_assets_ignis.py --solo-recursos` (matplotlib). Plano ilustrativo. Licencia MIT.
- `../assets/ignis_auto_poster.jpg`: captura del propio `ignis_auto.glb` en el estudio de la aplicación, generada con `scripts/capturar_ignis.mjs` (`IGNIS_POSTER=1`). Se muestra cuando no hay WebGL o el modelo no carga. Misma licencia que el modelo.

## ignis_auto.glb (avatar de IGNIS)

- **Origen:** modelo original creado por el Grupo 11 con apoyo de Claude (Anthropic), modelado por código en Blender 5.3 (bpy). No deriva de modelos comerciales ni de escaneos de vehículos reales.
- **Marcas:** sin logotipos, emblemas ni nombres de fabricantes.
- **Texturas:** fibra de carbono, atlas de ruedas y atlas de luces generadas por código (sin recursos de terceros).
- **Escáner frontal:** efecto genérico de barrido de luz; no reproduce ningún vehículo de series o películas.
- **Licencia:** uso académico del proyecto TAAML 2026-2S (Fanalca).
- **Optimización:** gltf-transform 4.1.1 (meshopt + WebP, nombres de nodos conservados).
