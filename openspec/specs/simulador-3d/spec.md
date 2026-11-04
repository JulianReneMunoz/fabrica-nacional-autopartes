# Especificación: simulador 3D de ensamblajes (versión 2.0)

## Purpose
Ofrecer un simulador 3D demostrativo del freno de disco con modelo de componentes, articulaciones,
despiece reversible, cálculo simplificado e integración con la base de conocimiento, sin presentar
la geometría como diseño certificado ni generar procedimientos de reparación o seguridad.

## Requirements

### Requirement: Modelo de componentes validado
The system SHALL validar que cada pieza tenga identificador único, dirección de despiece no nula, articulaciones con eje unitario y límites, y dependencias de desmontaje sin ciclos.

#### Scenario: Dependencia circular
- **WHEN** dos piezas se declaran mutuamente en `retirar_antes`
- **THEN** la validación del ensamblaje falla con un error que nombra el ciclo

### Requirement: Despiece reversible
The system SHALL calcular la posición de despiece como posición ensamblada más dirección unitaria por distancia por factor, con factor en [0, 1].

#### Scenario: Ida y vuelta
- **WHEN** se aplica el factor 1 y luego el factor 0
- **THEN** cada pieza vuelve exactamente a su posición ensamblada

### Requirement: Validación de valores del cliente
The system SHALL rechazar con HTTP 422 articulaciones inexistentes, valores no finitos o fuera de límites enviados a la API.

#### Scenario: Pistón fuera de carrera
- **WHEN** se envía `j_piston = 0.01` a `/api/v1/simulador/ensamblajes/freno_disco/cinematica`
- **THEN** la respuesta es 422 y no se calcula ninguna transformación

### Requirement: Separación entre documentación y demostración
The system SHALL responder preguntas sobre una pieza separando fragmentos documentados con URL de los datos del modelo de demostración y rechazar preguntas de reparación o seguridad.

#### Scenario: Pregunta de seguridad
- **WHEN** se pregunta cómo reparar los frenos
- **THEN** la respuesta indica que no se generan procedimientos de reparación ni de seguridad

### Requirement: Modelo procedural reproducible
The system SHALL generar el GLB desde la CLI con mallas cerradas y un manifiesto con hash reproducible.

#### Scenario: Generación repetida
- **WHEN** se ejecuta dos veces `uv run fabrica simulador generar` con los mismos parámetros
- **THEN** el hash sha256 del GLB es idéntico
