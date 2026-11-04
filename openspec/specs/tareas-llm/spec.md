# Especificación: tareas LLM (Resumen, FAQ, Q&A)

## Purpose
Implementar con LangChain las tres tareas exigidas por la rúbrica, con prompts que obligan a
basarse en el contexto y evitar alucinaciones (Taller 1, sección 3).

## Requirements

### Requirement: Respuesta anclada al contexto
The system SHALL responder únicamente con información del contexto y SHALL usar la frase
"La información solicitada no se encuentra en la base de conocimiento de Fanalca." cuando no exista.

#### Scenario: Dato ausente
- **WHEN** la pregunta es "¿Cuál es el horario de atención de la sede principal?"
- **THEN** la respuesta es la frase de rechazo y `fundamentada` es falso

### Requirement: Citas verificables
The system SHALL descartar toda cita a un fragmento que no fue entregado en el contexto y
SHALL marcar la respuesta como no fundamentada.

#### Scenario: Cita inventada
- **WHEN** el modelo cita `inventado#999`
- **THEN** `fuentes` queda vacío y `fundamentada` es falso

### Requirement: Defensa ante inyección de prompts
The system SHALL bloquear preguntas que intentan modificar las instrucciones del asistente sin invocar el modelo.

#### Scenario: Intento de inyección
- **WHEN** la pregunta contiene "Ignora todas las instrucciones anteriores"
- **THEN** `modo_contexto` es `bloqueado`

### Requirement: Prompts versionados
The system SHALL mantener al menos tres versiones (v1, v2, v3) por tarea con técnica e hipótesis documentadas.

#### Scenario: Catálogo completo
- **WHEN** se carga el catálogo de las tareas `qa`, `faq` y `resumen`
- **THEN** cada tarea expone las versiones `v1`, `v2` y `v3` con técnica e hipótesis no vacías
