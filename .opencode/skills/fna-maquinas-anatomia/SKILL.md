---
name: fna-maquinas-anatomia
description: Aplica el método Anatomy a la biblioteca de máquinas interactivas del proyecto (una pregunta, una relación medible, 2–4 controles, cifras junto a las piezas, recorrido < 30 s y modo experimento) con datos de la empresa obtenidos por web scraping. Usar al crear o revisar una máquina.
---

# Biblioteca de máquinas (método Anatomy)

## Entradas
- Definición en `src/fabrica_autopartes/services/maquinas.py` (`DEFINICIONES`).
- Datos de empresa: fragmentos Gold con URL (`construir_biblioteca`), nunca texto inventado.
- Página del visor en `web/src/paginas/Maquina*.tsx` usando `web/src/componentes/anatomia.tsx`.

## Procedimiento
1. Investigar el mecanismo con fuentes técnicas y escribir UNA pregunta y UNA relación medible.
2. Implementar primero la lógica en `web/src/modelos/*.ts` con pruebas Vitest.
3. Construir la escena: 2–4 controles, correr/pausar/reiniciar, cámara lenta, pasos numerados,
   cifras junto a las piezas e idea principal en una frase.
4. Agregar el panel de datos de la empresa con insignia de origen (`scraping`, `lectura_web`,
   `semilla`, `base_conocimiento`, `demostrativo`) y la URL.
5. Revisión crítica: legibilidad, una sola idea, ningún dato sin procedencia.
6. Recorrido automático `?tour=1` de menos de 30 s y modo experimento (predecir → ejecutar → comparar).
7. Grabar: `cd web; npx playwright test --project=recorrido` (MP4 en `docs/videos/`).

## Skill externa de referencia
La skill pública Anatomy se instala de forma global con
`npx skills add wheresryan22/anatomy -g -a claude-code` y se invoca con `/anatomy`. Antes de usarla,
revisar su `SKILL.md` y los comandos que propone: una skill de terceros puede ejecutar código.
