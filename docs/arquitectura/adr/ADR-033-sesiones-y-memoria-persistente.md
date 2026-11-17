# ADR-033 · Memoria persistente (SqliteSaver y Store) y sesiones por usuario seudónimo

- **Estado:** aceptada (2026-11-16). La memoria persistente se implementa en el PR de memoria (#28 y #29 del
  plan); las sesiones, en el PR de sesiones (#44 del plan). Amplía la ADR-024 (agente con memoria).
- **Contexto:**
  - La rúbrica del Módulo 2 exige un checkpointer persistente con `thread_id` cuyo hilo sobreviva al reinicio
    (R03) y un Store de largo plazo con namespace y `search()` desde otro hilo (R05). Los casos 2A y 2B del
    OpenSpec `casos-validacion-ignis` lo verifican en vivo, incluido el reinicio del backend con otro PID.
  - Hasta ahora el agente con LLM (`ServicioAgente`) usaba `InMemorySaver` (ADR-024): el historial se perdía al
    reiniciar. IGNIS (`AgenteIgnisM2`, motor de reglas) guardaba su historial en tablas SQLite propias y no tenía
    Store de largo plazo por usuario.
  - El caso 2A original pedía recordar el nombre y la empresa del usuario, lo que choca con la Ley 1581 de 2012.
  - AGENTS.md limitaba el SQL a `repositories/auditoria.py`.
- **Decisión:**
  1. **Checkpointer `SqliteSaver`** (`langgraph-checkpoint-sqlite`) en `Configuracion.ruta_checkpoints`
     (`data/agente_checkpoints.sqlite`). Reemplaza a `InMemorySaver` en `ServicioAgente`. El tope
     `FNA_AGENTE_MAX_HILOS` sigue borrando los hilos más antiguos con `delete_thread`, pero cuenta solo los hilos
     usados desde el arranque del proceso.
  2. **Store `SqliteStore`** en `Configuracion.ruta_store` (`data/ignis_store.sqlite`), con namespace
     `("preferencias", user_id)`. Se lee con `search()` y, además, se exige que el namespace del ítem sea
     exactamente el del usuario, para que `u1` nunca reciba ítems de `u10`.
  3. **Solo preferencias de vocabularios cerrados** (`services/preferencias.py`): `area_laboral`,
     `formato_respuesta` y `linea_producto`, con valores canónicos. Nunca se guarda texto libre del usuario, así
     que ningún nombre, empresa ni dato de contacto puede llegar al Store.
  4. **La memoria se activa solo con una orden explícita** («recuérdalo», «recuerda que», «guárdalo», «guarda
     esto», «guarda que», «guarda mis») que traiga preferencias reconocidas o una autopresentación, o con la
     consulta «¿qué preferencias tengo?». «Prefiero» o «me interesa» por sí solos no desvían la pregunta. Las
     preguntas por datos personales del propio usuario («¿Cómo me llamo?») reciben un aviso fijo por la ruta
     `directo`, sin búsqueda.
  5. **Fábricas en `repositories/memoria_agente.py`** (`crear_checkpointer`, `crear_store` y sus cierres). La
     regla de AGENTS.md pasa a decir que el SQL vive exclusivamente en `repositories/`; ningún otro paquete importa
     `sqlite3`, `sqlalchemy`, `langgraph.checkpoint.sqlite` ni `langgraph.store.sqlite` (lo comprueba
     `tests/unit/test_memoria_agente.py`). La API cierra las conexiones en el lifespan al apagarse.
  6. **IGNIS adopta `SqliteSaver` en el bloque 3, al pasar a `create_agent`.** En este PR IGNIS sigue con el
     motor de reglas: su historial por hilo ya es persistente (tablas propias en SQLite) y usa el Store de
     preferencias. **Ese paso del bloque 3 no se puede recortar**, porque es el que cubre R03 en la demo: sin él,
     el checkpointer persistente solo lo usa el agente de `/api/v1/agente`.
  7. **Usuario provisional.** Hasta las sesiones, `/ignis/stream` usa `user_id = "demo"` (`USUARIO_DEMO`, con un
     TODO que apunta al PR de sesiones).
  8. **Sesiones (PR de sesiones):** el `user_id` es un HMAC-SHA256 del alias normalizado. De
     `IGNIS_SECRETO_SESION` se derivan con HKDF dos claves separadas, con etiquetas distintas: una para el HMAC del
     `user_id` y otra para Fernet. La cookie `ignis_sesion` va cifrada con Fernet (httpOnly, SameSite=Lax, Path=/,
     Secure configurable y desactivado en localhost, 8 h deslizantes). El alias solo viaja en esa cookie: no se
     guarda en la base, los logs, la auditoría ni el Store. Sin `IGNIS_SECRETO_SESION` las sesiones fallan con un
     mensaje claro; no hay secreto por defecto en el código.
- **Consecuencias:**
  - El historial del agente con LLM y las preferencias sobreviven al reinicio; los archivos `data/*.sqlite` están
    ignorados por git porque pueden contener mensajes de usuarios.
  - Se mantiene un solo worker en Docker Compose: el tope de hilos vive en el proceso.
  - En Windows hay que cerrar las conexiones antes de borrar los archivos (`cerrar()` del servicio y fixtures de
    las pruebas).
  - Hasta el PR de sesiones, todas las consultas de IGNIS comparten las preferencias del usuario `demo`.
- **Alternativas descartadas:**
  - **Envolver el motor de reglas de IGNIS en un grafo con `SqliteSaver` ya en este PR:** el bloque 3 lo
    reemplaza por `create_agent`; sería trabajo descartable.
  - **Guardar el texto libre del usuario en el Store tras anonimizarlo:** `omitir_autopresentaciones` borra
    «trabajo en …», lo que impediría el caso 2A, y la anonimización no reconoce todos los datos personales.
  - **Usar el mismo archivo para checkpointer y Store:** se separan para poder borrar o inspeccionar cada memoria
    por su cuenta.
