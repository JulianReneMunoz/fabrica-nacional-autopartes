## ADDED Requirements

### Requirement: Recuperación vectorial
The system SHALL indexar cada fragmento Gold con un modelo de embeddings local y recuperar los k más similares.

#### Scenario: Consulta semántica
- **WHEN** la pregunta es "¿dónde fabrican las motos?"
- **THEN** entre los 5 primeros resultados aparece un fragmento de `negocios/honda-motocicletas`
