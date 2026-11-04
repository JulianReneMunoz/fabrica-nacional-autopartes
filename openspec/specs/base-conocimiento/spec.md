# Especificación: base de conocimiento semántico

## Purpose
Transformar las capturas en un corpus limpio, segmentado y consolidado en un archivo de
texto (Taller 1, sección 2 "Preprocesamiento y Segmentación"; rúbrica "consolidación del
conocimiento en un archivo de texto limpio").

## Requirements

### Requirement: Limpieza Silver
The system SHALL eliminar HTML, scripts, menús, pies de página y avisos de cookies, normalizar
espacios y deduplicar documentos exactos y casi duplicados (Jaccard ≥ 0,9).

#### Scenario: Pie de página repetido
- **WHEN** una línea aparece en al menos el 60 % de los documentos
- **THEN** la línea se elimina de todos los documentos

### Requirement: Protección de datos personales
The system SHALL reemplazar por `[correo omitido]` todo correo electrónico no corporativo.

#### Scenario: Correo personal en una página
- **WHEN** el texto contiene `persona.privada@gmail.com`
- **THEN** el corpus Gold no contiene esa dirección

### Requirement: Fragmentación semántica y consolidación
The system SHALL fragmentar por encabezados Markdown y tamaño máximo configurable, asignar un
identificador citable `documento#NNN` y generar `data/gold/base_conocimiento.txt`.

#### Scenario: Archivo consolidado
- **WHEN** se ejecuta `uv run fabrica build`
- **THEN** existe `base_conocimiento.txt` con cada fragmento precedido por `[id] (sección | url)`
