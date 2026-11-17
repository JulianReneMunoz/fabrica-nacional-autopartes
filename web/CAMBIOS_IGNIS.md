# IGNIS v2 — PR 1 (#38 del plan): barra lateral agrupada, solo auto y Atención corregida

Rama `feat/ignis-frontend`. Plan: `claude/frontend_ignis_v2_plan.md` y `claude/prompt_ignis_v2_claude_code.md` (secciones 1 y 2).
El identificador #38 es del plan; el número real del PR lo asigna GitHub al abrirlo.

## Decisiones aplicadas
- **Solo el auto.** Se retiran el robot, la transformación y sus estados. Lo único que se anima al conversar es el escáner
  rojo del frente (`seg_00 … seg_11` de `ignis_auto.glb`).
- **Se retiran del frontend** Biblioteca, Prensa, Línea, Moto, Explorador y el Simulador 3D del M1. Se conservan en el backend
  los endpoints del simulador, las máquinas y las motos, y `web/public/modelos/*`, sin enlace desde la interfaz.
- **Contrato del router sin cambios.** `ruta_router` sigue llegando con los nombres del backend; la interfaz muestra las
  etiquetas v2 (Documentos, Datos, Mixto, Directo, Memoria, Bloqueado).
- **Honestidad de datos.** Las pestañas sin endpoint muestran «No disponible todavía (#PR)» y no presentan cifras.

## Qué cambia
| Archivo | Cambio |
|---|---|
| `src/App.tsx`, `src/main.tsx` | Shell nuevo: barra lateral de 72 px (240 px expandida) con seis grupos, encabezado global, pestañas con `React.lazy` y esqueleto de carga, redirección de rutas viejas a `#/atencion`. Sin BOM en `main.tsx` |
| `src/ignisRutas.ts` | Registro de pestañas, grupos, PR del plan y `resolverRuta` (redirecciones) |
| `src/ignisContexto.tsx` | Hilo activo (`thread_id`) y estado de API (`GET /salud` cada 30 s) y SSE compartidos con el encabezado |
| `src/PestanaPendiente.tsx` | Estado vacío con el PR que habilita cada pestaña |
| `src/IgnisCanvas3D.tsx` | Reescrito: carga `/app/models/ignis_auto.glb` con `useGLTF` (meshopt), encuadre automático por esfera envolvente, giro lento solo en reposo y sin giro con `prefers-reduced-motion`, escáner con `useEscanerIgnis` |
| `src/ignisEncuadre.ts` | Nuevo: distancia de encuadre, posición de cámara y límites del zoom (módulo puro con pruebas) |
| `src/IgnisEstudio.tsx`, `src/ignisCalidad.ts` | Sin brasas del robot; Bloom con `luminanceThreshold` 0,9; sombras `PCFShadowMap` (three r187) |
| `src/ignisStateMachine.ts` | Estados `auto`, `escribiendo`, `escuchando`, `pensando`, `respondiendo`, `hablando`, `mostrando_archivo`; pausa del teclado y espera a reposo de 1,5 s |
| `src/escanerIgnis.ts` | Una sola función de escáner (`pasoEscaner`). Nuevos: `leerAmplitud` (sin Three.js), amplitud compartida, `pulsarAmplitud` y `avanzarAmplitud` |
| `src/useEscanerIgnis.ts` | Buffer `Uint8Array<ArrayBuffer>`; base casi negra en `seg_XX`; `leerAmplitud` se reexporta del módulo puro |
| `src/ignisVoz.ts` | La amplitud del TTS sale del `AnalyserNode`; el respaldo `speechSynthesis` suma un pulso por `onboundary` (antes era una senoide simulada); `MicrofonoIgnis` mide el micrófono; velocidad de lectura |
| `src/IgnisAtencionView.tsx` | Sin barra lateral propia, sin botón de transformar ni descargas flotantes; sin `GET /api/v1/maquinas`; recurso `ignis_auto.glb`; `maxLength={2000}` con contador; «Usar transcripción»; metadatos compactos (ruta, puntaje, citas, blindaje); columna de recursos con desplazamiento propio y micrófono fijo; póster si no hay WebGL o el GLB falla |
| `src/ignisCliente.ts` | `etiquetaRuta` (etiquetas v2); el respaldo del M1 se marca `respaldo_m1`; citas y adjuntos conservan su `origen` (`scraping`, `lectura_web`, `semilla`; sin origen válido, `demostrativo`) y la vista lo muestra junto a cada cita, adjunto y recurso, y en el resumen exportado (regla de AGENTS.md) |
| `src/api.ts` | Solo corpus, auditoría, pipeline, tareas (Q&A, FAQ, resumen), agente, FAQ del visor y salud |
| `src/IgnisIconos.tsx` | Íconos de trazo para las pestañas nuevas; sin `robot` ni `transformar` |
| `src/ignis.css` | Tokens `--ig-*` globales, shell, barra lateral, encabezado y estados; cortes 1599, 1279, 1023 y 767. Por debajo de 1600 px los recursos de Atención pasan a una columna de filas compactas que se ajustan al ancho sin cortar texto |
| `public/models/LICENCIAS.md`, `public/assets/ignis_auto_poster.jpg` | Licencia de `ignis_auto.glb` y póster estático capturado del propio GLB |
| `package.json` | `@react-three/postprocessing` 3.2.2 y `postprocessing` 6.39.6 con versión fija (aprobadas) |
| `index.html`, `vite.config.ts`, `playwright.config.ts` | Título IGNIS, CSS de pruebas y un solo proyecto e2e |

## Borrado (58 archivos del M1)
`src/paginas/*`, `src/componentes/**`, `src/maquinas/*`, `src/modelos/*`, `src/tema/colores.ts`, `src/estilos.css`; pruebas Vitest
`busqueda_web`, `explorador`, `fidelidad`, `interfaz`, `modelos`, `moto`, `plantilla`; e2e `explorador`, `moto`, `plantilla`,
`visor` (y `recorrido`, reescrito); scripts `capturar_7b`, `capturar_7d`, `capturar_readme`, `validar_paleta`,
`verificar_streamlit_7d`. Se conservan `src/__tests__/referencia_*.json`, porque los lee `tests/unit/test_dinamica_moto.py`, y `src/tema/tokens.css`,
porque el Streamlit del M1 (`frontend/estilo.py`) toma de ahí sus colores; el frontend de IGNIS no lo importa.

## Pruebas
- Vitest (77): máquina de estados (ningún evento lleva a un estado de robot), amplitud del escáner, encuadre, rutas y
  redirecciones, estado vacío y de error de cada pestaña con el backend caído, Atención (contador, «Escribiendo», póster,
  sin `/maquinas`), referencias prohibidas en `web/` (Streamlit, Gradio, robot, transformación) y codificación sin BOM.
- Playwright (`e2e/recorrido.spec.ts`): todas las pestañas sin errores de consola, rutas viejas a Atención, carga del GLB
  y respuesta, menú por debajo de 1023 px.
- `scripts/capturar_ignis.mjs`: cada pestaña a 1600, 1366 y 900 px, y Atención en reposo, escribiendo y respondiendo
  con voz y sin voz (75 capturas).

## Capturas (`docs/capturas/ignis_v2/`)
| Archivo | Vista |
|---|---|
| `atencion_reposo_1600.png` | Atención en reposo (escáner con latido tenue) |
| `atencion_escribiendo_1600.png` | Atención mientras el usuario escribe |
| `atencion_respondiendo_con_voz_1600.png` | Atención respondiendo con voz (estado «Hablando», subtítulos y metadatos) |
| `barra_lateral_expandida_1366.png` | Barra lateral expandida con los grupos |
| `rayos_x_1366.png` | Pestaña Rayos-X y validación (estado vacío, #40) |
| `pestana_pendiente_corpus_1366.png` | Pestaña pendiente con su PR (Corpus, #38c) |

El juego completo (75 capturas) se regenera con `node scripts/capturar_ignis.mjs`.

## Estudio de presentación (vigente desde la Fase 6)
Todo el estudio es procedural: no se descargan HDRI ni texturas externas.
- `src/IgnisEstudio.tsx`: ciclorama con cúpula en degradado (horizonte gris grafito más claro detrás del auto para que la
  silueta oscura se lea), niebla del mismo color para fundir el piso con el fondo, piso de concreto pulido con
  `MeshReflectorMaterial` y rugosidad procedural, plataforma de exhibición con aro LED rojo, luz principal fría con
  sombra suave, entorno de franjas de luz (`Lightformer`) para reflejos largos en la laca y posprocesado (N8AO, Bloom,
  AgX, viñeta y SMAA).
- `src/ignisCalidad.ts`: niveles alto, medio y bajo (dpr, reflejos, oclusión, posprocesado y sombra). `PerformanceMonitor`
  baja o sube un nivel según los fps; con `?calidad=alto|medio|bajo` en la URL el nivel queda fijo. Pruebas en
  `src/__tests__/calidad.test.ts`.
- El tone mapping se hace una sola vez: en el efecto AgX cuando hay posprocesado y en el renderer cuando no lo hay.
- Los contraluces blancos salen de las franjas del entorno y no de luces puntuales, porque una luz puntual detrás del auto
  deja una mancha blanca en el capó y en el piso.

## Pendiente para los PR siguientes
- Sesiones de usuario (#44): alias en el encabezado, cookie httpOnly, hilos por usuario; el `thread_id` deja localStorage.
- Configuración por usuario (#38b): proveedor, modelo y modo de contexto en cada petición y en el encabezado.
- Qdrant (#34): chip de estado real.
