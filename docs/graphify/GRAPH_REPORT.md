<!--
Informe generado con Graphify (graphifyy 0.9.102, versión fijada; excepción S-08 y ADR-020) el 2026-11-07.
Comando: GRAPHIFY_BACKEND=none graphify extract <copia> --code-only y graphify cluster-only --no-label
(análisis AST local, sin LLM ni red; comunidades con Louvain de networkx, porque graspologic/Leiden no está instalado).
Alcance: copia de los archivos .py de src/fabrica_autopartes (incluye simulador/ y pipelines/) y .ts/.tsx de web/src,
sin pruebas, datos, documentos, .env, .claude, node_modules, .venv ni dist. Las rutas son relativas a esa copia.
Vista por módulos: docs/imagenes/mapa_codigo.svg (derivada de graph.json, que no se versiona).
-->

# Graph Report - graphify-fanalca  (2026-11-07)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 1252 nodes · 3492 edges · 52 communities (40 shown, 12 thin omitted)
- Extraction: 93% EXTRACTED · 7% INFERRED · 0% AMBIGUOUS · INFERRED: 243 edges (avg confidence: 0.93)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- Community 0
- Community 1
- Community 2
- Community 3
- Community 4
- Community 5
- Community 6
- Community 7
- Community 8
- Community 9
- Community 10
- Community 11
- Community 12
- Community 13
- Community 14
- Community 15
- Community 16
- Community 17
- Community 18
- Community 19
- Community 20
- Community 21
- Community 22
- Community 23
- Community 24
- Community 25
- Community 26
- Community 27
- Community 28
- Community 29
- Community 30
- Community 31
- Community 32
- Community 33
- Community 34
- Community 35
- Community 36
- Community 37
- Community 38
- Community 40
- Community 41
- Community 42
- Community 43

## God Nodes (most connected - your core abstractions)
1. `ServicioAsistente` - 61 edges
2. `MaquinaMoto()` - 40 edges
3. `BaseConocimiento` - 34 edges
4. `Ensamblaje` - 33 edges
5. `construir_moto()` - 32 edges
6. `RepositorioAuditoria` - 27 edges
7. `Configuracion` - 27 edges
8. `Fragmento` - 27 edges
9. `AlmacenBronze` - 26 edges
10. `construir_base()` - 26 edges

## Surprising Connections (you probably didn't know these)
- `calculo_freno()` --uses--> `EntradaFreno`  [INFERRED]
  fabrica_autopartes/api/routes/simulador.py → fabrica_autopartes/simulador/fisica_freno.py
- `calculo_freno()` --uses--> `ResultadoFreno`  [INFERRED]
  fabrica_autopartes/api/routes/simulador.py → fabrica_autopartes/simulador/fisica_freno.py
- `calcular()` --uses--> `EntradaMoto`  [INFERRED]
  fabrica_autopartes/services/motos.py → fabrica_autopartes/simulador/fisica_moto.py
- `CalculoMoto` --uses--> `ResultadoMoto`  [INFERRED]
  fabrica_autopartes/services/motos.py → fabrica_autopartes/simulador/fisica_moto.py
- `FichaMoto` --uses--> `SupuestoDidactico`  [INFERRED]
  fabrica_autopartes/services/motos.py → fabrica_autopartes/simulador/fisica_moto.py

## Import Cycles
- None detected.

## Communities (52 total, 12 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.05
Nodes (28): crear_app(), construir_parser(), main(), _main(), _op(), _opciones_llm(), configurar_registro(), obtener_registro() (+20 more)

### Community 1 - "Community 1"
Cohesion: 0.06
Nodes (38): calcular(), EntradaFreno, ResultadoFreno, angulo_biela_rad(), calcular_moto(), calcular_moto_desde_estado(), cilindrada_cm3(), _componer() (+30 more)

### Community 2 - "Community 2"
Cohesion: 0.12
Nodes (43): Animacion, api, NodoJerarquia, fmt(), hashRecorrido(), PasoTour, prefiereMovimientoReducido(), useMaquina() (+35 more)

### Community 3 - "Community 3"
Cohesion: 0.07
Nodes (42): ADR-0019, apiMoto, ArticulacionApi, CalculoMotoApi, crearApi(), DatoEmpresa, ENSAMBLAJE, ENSAMBLAJE_MOTO (+34 more)

### Community 4 - "Community 4"
Cohesion: 0.10
Nodes (41): acotar(), ajusteDesdeFicha(), AjusteFicha, calcularMoto(), calcularMotoDesdeEstado(), cilindradaCm3(), componer(), diametroLlantaMm() (+33 more)

### Community 5 - "Community 5"
Cohesion: 0.07
Nodes (42): chispaPermitida(), EJE_CORONA, EJE_PINON, EstadoMotor, FaseCiclo, faseCiclo(), FASES_INFO, GEOMETRIA_MOTOR (+34 more)

### Community 6 - "Community 6"
Cohesion: 0.10
Nodes (25): calculo(), faq(), ficha(), listar(), aplicar_ficha(), calcular(), CalculoMoto, _campo() (+17 more)

### Community 7 - "Community 7"
Cohesion: 0.11
Nodes (23): DocumentoLimpio, deduplicar(), desde_bronze(), desde_semilla(), _documentos_contacto_sitio(), eliminar_lineas_repetidas(), escribir_silver(), excluida() (+15 more)

### Community 8 - "Community 8"
Cohesion: 0.11
Nodes (15): catalogo(), clasificar(), _sin_tildes(), construir_freno(), _pieza(), sistemas_moto(), Articulacion, Geometria (+7 more)

### Community 9 - "Community 9"
Cohesion: 0.14
Nodes (30): articulaciones(), calculo_freno(), cinematica(), despiece(), ensamblaje(), EstadoGuardado, guardar_estado(), jerarquia() (+22 more)

### Community 10 - "Community 10"
Cohesion: 0.09
Nodes (14): _auditar(), base(), buscar_fragmentos(), estadisticas_base(), obtener_fragmento(), plantilla_qa(), recurso_consolidado(), recurso_fuentes() (+6 more)

### Community 11 - "Community 11"
Cohesion: 0.13
Nodes (7): RepositorioAuditoria, Base, EjecucionPipeline, EstadoSimulador, Evaluacion, EventoSimulador, Interaccion

### Community 12 - "Community 12"
Cohesion: 0.08
Nodes (7): AlmacenCapturas, normalizar_url(), ResultadoRastreo, dominio_de(), esta_en_dominios(), PoliticaRobots, url_excluida()

### Community 13 - "Community 13"
Cohesion: 0.12
Nodes (13): Configuracion, ejecutar_faq(), ejecutar_qa(), ejecutar_resumen(), _ms(), Opciones, _opciones(), catalogo() (+5 more)

### Community 14 - "Community 14"
Cohesion: 0.12
Nodes (17): _describir_movimiento(), ErrorEnsamblaje, euler_desde_matriz(), homogenea(), jerarquia(), lecturas(), matriz_rotacion_eje(), matriz_rotacion_euler() (+9 more)

### Community 15 - "Community 15"
Cohesion: 0.11
Nodes (31): FichaMotoApi, Pieza, RespuestaPieza, SistemaApi, BuscadorPiezas(), buscarPiezas(), campoMostrable(), CampoRelacionado (+23 more)

### Community 16 - "Community 16"
Cohesion: 0.09
Nodes (13): _Constructor, construir_moto(), cuna(), fork(), _despiece_radial(), _largo(), ParametrosMoto, _r() (+5 more)

### Community 17 - "Community 17"
Cohesion: 0.16
Nodes (23): Maquina, BandaTour(), BarraLienzo(), BotonBarra, DEFINICION, PropsBarraLienzo, PropsReproduccion, Reproduccion() (+15 more)

### Community 18 - "Community 18"
Cohesion: 0.15
Nodes (18): EjecucionDTO, ErrorDTO, InteraccionDTO, OpcionesLLM, SolicitudFAQ, SolicitudQA, SolicitudQAWeb, SolicitudReconstruccion (+10 more)

### Community 19 - "Community 19"
Cohesion: 0.07
Nodes (29): EstadoDinamico, FACTOR_LENTO_DEFECTO, FACTORES_LENTO, MandoMoto, PalancaMoto, SUPUESTOS, textoMarcha(), geometriaMovil() (+21 more)

### Community 20 - "Community 20"
Cohesion: 0.11
Nodes (8): ErrorFNA, ErrorProveedorLLM, ErrorScrapingBloqueado, BuscadorClaudeCode, _extraer_json(), interpretar_salida(), ResultadoBuscador, texto_prompt()

### Community 21 - "Community 21"
Cohesion: 0.12
Nodes (19): ETIQUETAS_SISTEMA, EtiquetaSistema, EXPLORADOR_MOTO, ICONOS_SISTEMA, IdSistema, LECCIONES, ORDEN_SISTEMAS, TERMINOS_PROHIBIDOS (+11 more)

### Community 22 - "Community 22"
Cohesion: 0.11
Nodes (5): ClienteHTTP, detectar_proteccion(), RespuestaHTTP, Rastreador, analizar_sitemap()

### Community 23 - "Community 23"
Cohesion: 0.16
Nodes (8): ErrorBaseConocimientoVacia, Fragmento, BaseConocimiento, ContextoArmado, formatear_fragmento(), expandir_consulta(), IndiceBM25, Resultado

### Community 24 - "Community 24"
Cohesion: 0.12
Nodes (8): obtener_configuracion(), ErrorLimiteBusquedaWeb, ErrorPreguntaBloqueada, HallazgoWeb, BuscadorWeb, fecha_hoy(), detectar_inyeccion(), ServicioBusquedaWeb

### Community 25 - "Community 25"
Cohesion: 0.19
Nodes (13): _area_con_signo(), _cerrar(), _chaikin(), _diferencia(), engranaje(), extrusion(), perfil_neumatico(), poligono_engranaje() (+5 more)

### Community 26 - "Community 26"
Cohesion: 0.16
Nodes (12): validar_ensamblaje(), _cadena(), contorno(), construir_escena(), construir_malla(), _diferencia(), distancia_minima_mallas(), mallas_en_posicion_armada() (+4 more)

### Community 27 - "Community 27"
Cohesion: 0.12
Nodes (18): CajaEtiqueta, colocarEtiquetas(), hayCajasSolapadas(), puntoBorde(), Rect, rectDe(), solapa(), ANCLAS (+10 more)

### Community 28 - "Community 28"
Cohesion: 0.14
Nodes (5): ErrorConfiguracion, complemento_lectura_web(), construir_base(), _host(), ResultadoConstruccion

### Community 29 - "Community 29"
Cohesion: 0.15
Nodes (3): RegistroCaptura, AlmacenBronze, _metricas_bronze()

### Community 30 - "Community 30"
Cohesion: 0.19
Nodes (12): _sin_tildes(), tokenizar(), analizar_json(), extraer_citas_texto(), puntaje_fundamentacion(), quitar_citas(), _capacidad_chasises(), construir_biblioteca() (+4 more)

### Community 31 - "Community 31"
Cohesion: 0.19
Nodes (11): App(), ExploradorMoto, idDeRuta(), leerRuta(), MaquinaFreno, MaquinaMoto, Lamina(), TarjetaMaquina() (+3 more)

### Community 32 - "Community 32"
Cohesion: 0.19
Nodes (8): Fuente, ItemFAQ, RespuestaQA, RespuestaWeb, ResultadoFAQ, ResultadoResumen, SolicitudScraping, _proveedor_disponible()

### Community 33 - "Community 33"
Cohesion: 0.19
Nodes (7): ahora_utc(), EstadisticasBase, fragmentar_documento(), consolidar(), construir_gold(), documento_a_markdown(), tokens_aprox()

### Community 35 - "Community 35"
Cohesion: 0.21
Nodes (4): exigir_admin(), obtener_servicio(), faq_visor(), servicio_por_defecto()

### Community 36 - "Community 36"
Cohesion: 0.24
Nodes (8): preguntar(), _sim(), SolicitudPregunta, consultar_pieza(), FuenteDocumentada, responder_pieza(), RespuestaPieza, ServicioSimulador

### Community 37 - "Community 37"
Cohesion: 0.24
Nodes (9): BAR_A_PA, calcularFreno(), ENTRADA_FRENO_DEFECTO, EntradaFreno, G, redondear(), ResultadoFreno, FrenoRueda (+1 more)

### Community 38 - "Community 38"
Cohesion: 0.36
Nodes (5): extraer_contenido(), extraer_enlaces(), _idioma(), PaginaExtraida, _texto_bs4()

### Community 40 - "Community 40"
Cohesion: 0.39
Nodes (5): FragmentoBuscado, Pagina, estadisticas(), listar(), obtener()

### Community 42 - "Community 42"
Cohesion: 0.47
Nodes (5): Mecanismo, mecanismoMotor(), PuntoXY, anguloBielaRad(), posicionPistonM()

## Knowledge Gaps
- **3 isolated node(s):** `ADR-0017`, `ADR-0019`, `ADR-0017`
  These have ≤1 connection - possible missing edges. (Counts symbols only; 372 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **12 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `ServicioAsistente` connect `Community 18` to `Community 0`, `Community 32`, `Community 35`, `Community 36`, `Community 40`, `Community 9`, `Community 10`, `Community 11`, `Community 12`, `Community 13`, `Community 22`, `Community 23`, `Community 24`, `Community 28`, `Community 29`?**
  _High betweenness centrality (0.064) - this node is a cross-community bridge._
- **Are the 41 inferred relationships involving `ServicioAsistente` (e.g. with `exigir_admin()` and `obtener_servicio()`) actually correct?**
  _`ServicioAsistente` has 41 INFERRED edges - model-reasoned connections that need verification._
- **What connects `ADR-0017`, `ADR-0019`, `ADR-0017` to the rest of the system?**
  _3 weakly-connected nodes found - possible missing edges._
- **Should `Community 0` be split into smaller, more focused modules?**
  _Cohesion score 0.053313587560162905 - nodes in this community are weakly interconnected._
- **Why does `construir_moto()` connect `Community 16` to `Community 0`, `Community 1`, `Community 6`, `Community 8`, `Community 14`, `Community 25`, `Community 26`?**
  _High betweenness centrality (0.027) - this node is a cross-community bridge._
- **Are the 14 inferred relationships involving `BaseConocimiento` (e.g. with `ErrorBaseConocimientoVacia` and `ErrorRecursoNoEncontrado`) actually correct?**
  _`BaseConocimiento` has 14 INFERRED edges - model-reasoned connections that need verification._
- **Should `Community 1` be split into smaller, more focused modules?**
  _Cohesion score 0.05627545353572751 - nodes in this community are weakly interconnected._