# Arquitectura del simulador 3D

```mermaid
flowchart LR
  cat["Catálogo de ensamblajes<br/>freno_disco y moto_honda<br/>simulador/catalogo_*.py"]
  puntos["Puntos duros<br/>puntos_duros_moto.py"]
  gen["Generación procedural<br/>trimesh<br/>simulador/generacion.py"]
  glb[("GLB y manifiesto<br/>web/public/modelos")]
  fisica["Física didáctica<br/>fisica_freno.py y fisica_moto.py"]
  fichas[("Fichas curadas<br/>data/catalogo/motos_honda.yaml")]
  api["API<br/>/api/v1/simulador y /api/v1/motos"]
  visor["Visor<br/>React Three Fiber"]
  ts["moto.ts y freno.ts"]
  ref[("referencia_moto.json<br/>paridad Python y TypeScript, 1e-6")]

  puntos --> cat
  cat --> gen
  gen --> glb
  cat --> api
  fisica --> api
  fichas --> api
  api -- "jerarquía, despiece, cinemática, cálculo" --> visor
  glb --> visor
  ts --> visor
  fisica -. "exporta casos" .-> ref
  ref -. "prueba Vitest" .-> ts
```

La geometría es procedural y esquemática; la animación no valida propiedades mecánicas. La posición armada se valida
con una prueba de conectividad (cada pieza toca la pieza a la que se monta, tolerancia de 2 mm).
