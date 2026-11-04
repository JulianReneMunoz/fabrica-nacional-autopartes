# Especificación: biblioteca de máquinas interactivas (versión 2.0, método Anatomy)

## Purpose
Presentar un menú de máquinas interactivas que expliquen procesos de una planta de autopartes con
datos de la empresa obtenidos por web scraping, cada una con una pregunta y una relación medible.

## Requirements

### Requirement: Tarjetas alimentadas por la base de conocimiento
The system SHALL mostrar por máquina una tarjeta con pregunta, una línea, relación, datos de la empresa con URL y origen, y un botón para abrirla.

#### Scenario: Biblioteca cargada
- **WHEN** se abre `/app/#/`
- **THEN** se muestran las tarjetas freno, prensa y línea con al menos un dato con URL de autopartesfanalca.com.co o fanalca.com

### Requirement: Legibilidad Anatomy
The system SHALL ofrecer en cada máquina entre 2 y 4 controles del mecanismo, correr, pausar, reiniciar, cámara lenta, cifras junto a las piezas y una idea principal en una frase.

#### Scenario: Línea de ensamble
- **WHEN** se abre la máquina línea
- **THEN** la demanda inicial proviene de la base de conocimiento y el takt se muestra junto a la línea

### Requirement: Recorrido automático y modo experimento
The system SHALL ejecutar un recorrido automático de menos de 30 s con `?tour=1` y un modo experimento que compare una predicción con el resultado.

#### Scenario: Recorrido grabado
- **WHEN** se ejecuta `npx playwright test --project=recorrido`
- **THEN** se generan videos MP4 de menos de 30 s en `docs/videos/`
