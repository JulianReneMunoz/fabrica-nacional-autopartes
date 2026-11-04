---
name: fna-arquitectura
description: Revisa que un cambio respete la arquitectura documentada (capas, ADR, dependencias) del proyecto Fanalca. Usar antes de aprobar cambios estructurales o al crear un ADR.
---

# Revisión de arquitectura

## Responsabilidad
Detectar violaciones de capas y decisiones no documentadas.

## Entradas
Diff (`git diff --staged`) y `docs/arquitectura/adr/`.

## Procedimiento
1. Verificar dirección de dependencias: las interfaces importan `services`; `services` importa
   `llm`, `knowledge`, `pipelines`, `repositories`; ninguna capa inferior importa una superior.
   Comprobación rápida: `uv run python scripts/verificar_capas.py`.
2. Toda tecnología nueva requiere un ADR (`ADR-0NN-titulo.md`: contexto, decisión, consecuencias).
3. Revisar que el diagrama C4 (`docs/diagramas/`) siga vigente.

## Salidas
Lista de hallazgos con severidad (bloqueante / recomendación) y ADR propuesto si aplica.

## Restricciones
Solo lectura; no modifica código.

## Validación
`scripts/verificar_capas.py` termina con código 0.
