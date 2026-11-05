# Especificación: interfaz de prueba

## Purpose
Ofrecer una interfaz Streamlit donde el usuario ingrese una pregunta y vea la respuesta, y
que muestre claramente las tres funcionalidades.

## Requirements

### Requirement: Tres funcionalidades visibles
The system SHALL presentar pestañas de Q&A, Resumen y FAQ operativas.

#### Scenario: Pregunta de ejemplo
- **WHEN** se pulsa el botón "¿Dónde queda la sede principal de Fanalca?"
- **THEN** se muestra una respuesta con etiquetas de fundamentación, confianza y fuentes

### Requirement: Transparencia
The system SHALL mostrar procedencia de cada respuesta y advertir cuando la base proviene del corpus semilla.

#### Scenario: Base construida desde la semilla
- **WHEN** los fragmentos Gold tienen `origen: semilla`
- **THEN** la interfaz muestra una advertencia con los comandos para regenerar la base desde el scraping
