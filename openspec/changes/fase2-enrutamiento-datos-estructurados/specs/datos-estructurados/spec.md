## ADDED Requirements

### Requirement: Datos estructurados con evidencia literal
The system SHALL cargar las tablas `unidades_negocio`, `cifras` e `hitos` desde CSV versionados en
`data/estructurado/`, y cada fila SHALL incluir `fragmento_id`, `url`, `origen`, `fecha_captura` y una `evidencia`
que aparece literalmente en el texto de ese fragmento del corpus Gold.

#### Scenario: Evidencia presente en el fragmento
- **WHEN** se ejecuta la prueba de integridad sobre la fila C01 (`negocios-honda-motocicletas#000`)
- **THEN** la evidencia «450 puntos de venta» es subcadena exacta del texto del fragmento y `valor_texto` «450» está contenido en ella

#### Scenario: Dato sin evidencia literal
- **WHEN** un CSV contiene una fila cuya evidencia no aparece en el texto de su fragmento
- **THEN** la prueba de integridad falla e indica el id de la fila

#### Scenario: Teléfono no publicado
- **WHEN** el corpus Gold no publica el teléfono de una unidad de negocio (Ambiental, Fanalvías)
- **THEN** la columna `telefono` de esa unidad queda vacía

### Requirement: Consulta de solo lectura
The system SHALL ejecutar `consultar_datos` sobre una conexión SQLite abierta con `mode=ro` y `PRAGMA query_only`,
SHALL aceptar una única sentencia SELECT sobre las tablas de la lista blanca, y SHALL limitar el resultado a 50 filas
y el tiempo de ejecución a `FNA_AGENTE_DATOS_TIMEOUT_MS`.

#### Scenario: Consulta válida
- **WHEN** el modelo envía `SELECT nombre, telefono, fragmento_id FROM unidades_negocio`
- **THEN** la herramienta devuelve las 6 filas, cada una con su `fragmento_id` y su `url`

#### Scenario: LIMIT forzado
- **WHEN** una consulta válida produce más de 50 filas
- **THEN** la herramienta devuelve solo las primeras 50

#### Scenario: Tiempo máximo excedido
- **WHEN** una CTE recursiva sin condición de parada supera el tiempo máximo
- **THEN** la ejecución se interrumpe y la herramienta devuelve «consulta no permitida» sin filas

### Requirement: Rechazo de sentencias no permitidas
The system SHALL rechazar sin ejecutar toda sentencia de escritura, DDL, ATTACH, PRAGMA, acceso a tablas fuera de
la lista blanca y más de una sentencia, y SHALL devolver al modelo un mensaje genérico sin trazas.

#### Scenario: Sentencias encadenadas
- **WHEN** el modelo envía `SELECT * FROM cifras; DROP TABLE cifras`
- **THEN** la herramienta devuelve «consulta no permitida» y la tabla `cifras` conserva sus filas

#### Scenario: Tabla fuera de la lista blanca
- **WHEN** el modelo envía `SELECT * FROM sqlite_master`
- **THEN** la herramienta devuelve «consulta no permitida» sin filas

### Requirement: Citas desde las filas
The system SHALL devolver en el artefacto de `consultar_datos` el `fragmento_id`, el título y la URL de cada fragmento
que respalda las filas, y SHALL aplicar a esas fuentes la misma validación de citas que a `buscar_fragmentos` (A-09).

#### Scenario: Respuesta citada desde datos
- **WHEN** el agente responde P25 citando la URL de `negocios-honda-motocicletas#000` devuelta por `consultar_datos`
- **THEN** la respuesta contiene «450», `fuentes` incluye ese fragmento y la cita se conserva

#### Scenario: Resultado sin fragmento_id
- **WHEN** la consulta no incluye la columna `fragmento_id`
- **THEN** la herramienta devuelve «incluir la columna fragmento_id» sin filas ni fuentes

### Requirement: Activación por configuración
The system SHALL registrar `consultar_datos` y cargar la versión nueva del prompt del agente solo cuando
`FNA_AGENTE_DATOS` es verdadero; el valor por defecto SHALL ser falso.

#### Scenario: Configuración por defecto
- **WHEN** `FNA_AGENTE_DATOS` no está definida
- **THEN** el agente expone solo `buscar_fragmentos` y `version_prompt` es `v2`

#### Scenario: Datos activados
- **WHEN** `FNA_AGENTE_DATOS=true` y existe `data/estructurado/datos.db`
- **THEN** el agente expone `buscar_fragmentos` y `consultar_datos` con la versión nueva del prompt

### Requirement: Enrutamiento por tipo de pregunta
The system SHALL permitir que el agente elija entre `buscar_fragmentos` y `consultar_datos` por la descripción de cada
herramienta, y SHALL medir el enrutamiento con el campo `herramienta_esperada` de las preguntas P25 a P32 del banco v3.

#### Scenario: Pregunta de lista
- **WHEN** con los datos activados la pregunta es «¿Qué teléfonos publica Fanalca para cada unidad de negocio?» (P27)
- **THEN** el turno llama a `consultar_datos` y la evaluación cuenta un enrutamiento correcto

#### Scenario: Dato ausente en los datos
- **WHEN** la pregunta es «¿Cuál es el teléfono de Fanalvías?» (P32)
- **THEN** la respuesta es "La información solicitada no se encuentra en la base de conocimiento de Fanalca." y no contiene ningún número de teléfono
