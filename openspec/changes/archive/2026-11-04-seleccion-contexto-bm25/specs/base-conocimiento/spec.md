## ADDED Requirements

### Requirement: Modo de contexto configurable
The system SHALL permitir los modos `completo`, `seleccion` y `auto` para armar el contexto del Q&A.

#### Scenario: Presupuesto excedido
- **WHEN** el corpus supera `FNA_PRESUPUESTO_TOKENS_CONTEXTO` y el modo es `auto`
- **THEN** se usan los `FNA_FRAGMENTOS_SELECCION` fragmentos BM25 más pertinentes
