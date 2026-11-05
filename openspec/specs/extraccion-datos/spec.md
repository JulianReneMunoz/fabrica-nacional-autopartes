# Especificación: extracción de datos (scraping)

## Purpose
Capturar el contenido textual público del sitio oficial de Fanalca de forma responsable y
trazable (extracción de datos).

## Requirements

### Requirement: Cumplimiento de robots.txt
The system SHALL leer robots.txt antes de solicitar cualquier página de un host y SHALL NOT
solicitar rutas prohibidas por `Disallow` para su User-Agent.

#### Scenario: Ruta prohibida
- **WHEN** el sitemap contiene `/privado/intranet/` y robots.txt declara `Disallow: /privado/`
- **THEN** la URL se registra como omitida y no se emite ninguna petición HTTP hacia ella

#### Scenario: robots.txt no disponible por error del servidor
- **WHEN** robots.txt responde HTTP 5xx
- **THEN** el host completo se trata como prohibido

### Requirement: Identificación y control de frecuencia
The system SHALL enviar un User-Agent identificable y SHALL esperar al menos
`FNA_PAUSA_ENTRE_PETICIONES_S` (2 s por defecto) o el `Crawl-delay` declarado entre peticiones al mismo host.

#### Scenario: Cabecera User-Agent
- **WHEN** se captura cualquier página
- **THEN** la cabecera User-Agent inicia con `FNA-KnowledgeBot`

### Requirement: Capa Bronze inmutable con procedencia
The system SHALL guardar el HTML original y una línea JSONL con URL, URL final, fecha,
estado HTTP y hash SHA-256 por captura.

#### Scenario: Reanudación tras fallo
- **WHEN** el rastreo se ejecuta de nuevo sobre el mismo almacén Bronze
- **THEN** las URL ya capturadas no se solicitan otra vez
