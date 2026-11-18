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
- Configuración por usuario (#38b): proveedor, modelo y modo de contexto en cada petición y en el encabezado.
- Qdrant (#34): chip de estado real.

---

# IGNIS v2 — PR de sesiones por usuario seudónimo (#44 del plan, ADR-033)

## Qué cambia en el frontend
| Archivo | Cambio |
|---|---|
| `src/ignisSesion.ts` (nuevo) | Cliente de `/api/v1/sesiones` (entrar, sesión actual, hilos, mensajes, cerrar) y `validarAlias` con la misma regla del backend |
| `src/PantallaEntrada.tsx` (nuevo) | Entrada con alias, aviso de la Ley 1581 y el mensaje claro del servidor si falta `IGNIS_SECRETO_SESION` |
| `src/PestanaSesion.tsx` (nuevo) | «Mi sesión»: alias, usuario seudónimo recortado, hilos con «Reabrir», «Nuevo hilo» y «Cerrar sesión»; estados de carga, error y vacío |
| `src/ignisContexto.tsx` | Sesión y hilo desde el servidor (el más reciente o uno nuevo al entrar); sin almacenamiento en el navegador |
| `src/App.tsx` | Sin sesión, la pantalla de entrada; encabezado con alias y usuario seudónimo; «Cerrar sesión» como botón; `aria-label` en los ítems de la barra lateral (en la barra contraída la etiqueta es un tooltip oculto y no daba nombre accesible) |
| `src/IgnisAtencionView.tsx` | Al abrir o reabrir un hilo se carga su historial con ruta y citas; el envío espera a que el hilo esté listo y la carga del historial no pisa una conversación ya empezada |
| `src/ignisCliente.ts` | 401, 403 y 503 del stream lanzan `ErrorSesionIgnis` y no caen al respaldo Q&A |
| `src/ignisCasos.ts` | Casos 2A y 2B con los textos del OpenSpec `casos-validacion-ignis` (#27) |
| `src/ignis.css` | Entrada, «Mi sesión», tabla de hilos y `.ig-nav-boton` |
| `playwright.config.ts`, `e2e/recorrido.spec.ts` | Secreto de sesiones solo para e2e en `webServer.env`; inicio de sesión al empezar; pruebas de entrada, reabrir hilo y cerrar sesión |
| `scripts/capturar_ignis.mjs` | Simula los endpoints de sesión; captura también la pantalla de entrada |

## Pruebas
- Vitest (98): navegación con sesión simulada, pantalla de entrada (validación y 503), «Mi sesión» (lista, reabrir, cerrar), 401/403/503 sin respaldo, nada en el almacenamiento del navegador y la prueba de términos prohibidos ampliada.
- Playwright (6) contra FastAPI con sesión real.
- Capturas: `docs/capturas/ignis_v2/entrada_1366.png` y `mi_sesion_1366.png`.

## Limitaciones conocidas
- Demo sin contraseña: el mismo alias entra a la misma cuenta (mismo usuario seudónimo, mismos hilos y preferencias).
- La cookie no se puede revocar antes de que caduque (8 h): cerrar sesión la borra del navegador, pero una copia
  robada sigue siendo válida hasta su vencimiento.
- Los hilos «demo» antiguos sin dueño no se reasignan: responden 403.

Detalle en [ADR-033](../docs/arquitectura/adr/ADR-033-sesiones-y-memoria-persistente.md).

---

# IGNIS v2 — PR de voz neuronal con Piper (fix/voz-ignis)

## Decisiones aplicadas
- Piper corre dentro del proceso de la API, sin red; el repositorio no lo redistribuye (`LICENCIAS_TERCEROS.md`).
- `/tts` exige sesión (401 sin cookie); en el visor, un 401 pasa al respaldo del navegador sin romper el turno.
- `playbackRate` fijo en 1.0: la velocidad la da el servidor con `FNA_VOZ_LENGTH_SCALE`, sin alterar el tono.
- Una síntesis a la vez (semáforo de 1). Sin control de ritmo en la interfaz, la petición no lleva campo `ritmo`.

## Qué cambia
| Archivo | Cambio |
|---|---|
| `src/ignisVoz.ts` | Sin cadena de robotización (paso banda, oscilador de 40 Hz, WaveShaper y eco): fuente → analizador → ganancia → salida, con `playbackRate` 1.0 |
| `src/ignisVoz.ts` | Respaldo `speechSynthesis` ante 401, 503 o fallo de red, con `elegirVoz` (Microsoft Sabina, Microsoft Dalia, Paulina, Google español de Estados Unidos; después otra local es-MX, es-US, es-419 o es-CO; es-ES solo como último recurso, con aviso único), `pitch` 1.0 y `rate` 0,95 |
| `src/ignisVoz.ts` | LED del escáner: un pulso por `onboundary`; si no llega ninguno en 400 ms, pulsos a 4 Hz mientras habla |
| `src/ignisVoz.ts` | `textoParaVoz` (`cortarJson` + `limpiarParaVoz`): lo que se lee no lleva [ids], URL, JSON, nombres de archivo, markdown, «1)» ni «\|»; el texto visible del chat no cambia |
| `src/IgnisAtencionView.tsx` | El aviso de la voz de respaldo en español de España se muestra en la zona de avisos |
| Backend | `services/voz.py` (Piper con carga perezosa única y semáforo), `/tts` con `sesion_requerida` y 503 sin modelo, `scripts/descargar_voz.py` con verificación de tamaño y MD5, `FNA_VOZ_*` en la configuración |

## Pruebas
- Vitest: `voz.test.ts` (cadena directa y `playbackRate` 1.0, respaldo con 503 y 401, `elegirVoz`, aviso único, pulsos de 4 Hz) y `textoParaVoz.test.ts` (respuestas reales de las rutas herramienta estructurada, mixto y rag_documental; texto visible intacto).
- pytest: `tests/integration/test_tts.py` (WAV válido, 401, 600 caracteres, 503, 500 genérico, carga única, semáforo, `FNA_VOZ_DIR` vacío y modelo real si está descargado).
- e2e y `scripts/capturar_ignis.mjs` siguen simulando `/tts` con un WAV válido.

## Limitaciones conocidas
- La primera síntesis tarda unos segundos (carga del modelo); las siguientes, cerca de 0,2 s por oración en CPU.
- `textoParaVoz` es un parche hasta el PR de respuestas naturales: al quitar archivos o URL una frase puede quedar incompleta, y el fin de un JSON truncado se detecta por heurística.

---

# IGNIS v2 — PR de respuestas naturales y contenido de Fanalca (fix/ignis-respuestas-naturales)

## Decisiones aplicadas
- El texto de la respuesta es para el cliente; la evidencia técnica (citas, `fuentes_datos`, ruta, puntaje, blindaje y moderación) viaja en `metadatos`. AGENTS.md y el OpenSpec `casos-validacion-ignis` (casos 1, 3 y 6) se ajustaron antes del código.
- Sin precios, cotizaciones ni catálogo de repuestos: se retiró el PDF de cotización (`web/public/assets/resumen_cotizacion.pdf`) y su generación.
- Exclusiones de documentos y preferencia por el español solo en IGNIS: el buscador común del M1 no cambia.

## Qué cambia en el backend
| Archivo | Cambio |
|---|---|
| `services/moderacion.py` + `config/moderacion.yaml` | Moderación antes del router con 11 categorías: insulto, groserías, frustración, datos de terceros, insulto con datos de terceros, amenaza, odio o discriminación, acoso, manipulación, crisis personal y la pausa tras tres bloqueos seguidos; en una crisis personal da la Línea 192, opción 4, de salud mental, y el 123; en el historial y la auditoría se guarda la categoría, no el texto, y el hilo se titula «[mensaje moderado: …]» |
| `services/ficha_fanalca.py` + `data/catalogo/ficha_fanalca.json` | Ficha corporativa (propósito, pilares, valores, historia, 6 negocios, plantas y contacto) con fragmento, URL y evidencia literal por dato, verificada contra el corpus y sin nombres de personas; nuevo `tipo_consulta="ficha_empresa"` |
| `services/redactor_ignis.py` | Redactor extractivo: oraciones completas y pertinentes, ficha de la moto con valores exactos (lo no publicado se dice), estadísticas y procedencia en `fuentes_datos` |
| `services/cortesia.py` | Saludos que devuelven el del cliente, cortesía, fuera de tema y textos de memoria fijos y deterministas |
| `pipelines/sinonimos.py` + `config/ignis_exclusiones.yaml` | Sinónimos de búsqueda (misión y visión → propósito superior, pilares y valores) y documentos excluidos, solo en IGNIS |
| `pipelines/texto.py` | `pulir_respuesta` (filtro de salida sin `[id]`, URL, JSON, archivos, markdown ni jerga) y `limpiar_texto_scrapeado` (sin menús, cookies ni metadatos del blog) |
| `services/agente_ignis_m2.py`, `services/asistente.py`, `api/ignis_routes.py` | Moderación antes del router, ficha y textos fijos en el router, `pulir_respuesta` sobre el cuerpo y textos fijos después, sin cotización; título del hilo moderado; `fuentes_datos`, `categoria_moderacion` y `normativa` en los metadatos del SSE |

## Qué cambia en el frontend
| Archivo | Cambio |
|---|---|
| `src/ignisCliente.ts` | `fuentes_datos` (URL validadas con `new URL`, solo `http(s)`; elementos que no son objetos se descartan), `categoria_moderacion` y `normativa` en los metadatos; `etiquetaModeracion` |
| `src/IgnisAtencionView.tsx` | Ficha «Fuente de los datos» junto a la respuesta (nunca en el texto ni en la voz); insignia de moderación y norma de datos; en una crisis personal solo se muestra el mensaje, sin insignias ni ruta; `rel="noopener noreferrer"` en los enlaces; el resumen exportado incluye las fuentes de datos |
| `src/ignis.css` | `.ignis-fuentes-datos` y `.ignis-fuente-datos` |

## Pruebas
- Vitest: lectura de los campos nuevos (URL inválidas y elementos que no son objetos se descartan) y Atención con un SSE simulado: fuente visible, voz sin archivo ni URL, moderación y crisis.
- pytest: batería de las 20 preguntas de la fase 0 (`tests/integration/test_bateria_ignis.py`, con `tests/fixtures/ignis_bateria.json` y las respuestas antes y después).
- `textoParaVoz` y sus pruebas no cambian (segunda defensa de la voz).
- Resultado: pytest 846 pasan (1 omitida, la del modelo real); Vitest 128 pasan en 9 archivos; Playwright 6 de 6; batería de la fase 0, 20 de 20.

## Limitaciones conocidas
- Sin LLM, la respuesta documental es extractiva: puede elegir una oración que comparte el tema con la pregunta pero no la responde, o un rótulo largo del sitio (por ejemplo, «Explora las principales estrategias de sostenibilidad.» en la comparación mixta).
- La guía de estilo para el LLM (`llm/estilo_ignis.py`, constante `ESTILO_RESPUESTA_IGNIS`) queda para el PR de herramientas LangChain y LLM, que la inyectará con `dynamic_prompt`; este PR solo cubre el motor de reglas.
