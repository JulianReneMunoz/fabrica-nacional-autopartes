# ADR-021 · Flujo con pull requests y protección de main

- **Estado:** aceptada (2026-11-07); detalle en la entrada R-03 de `docs/prompts/bitacora_experimentos.md`.
- **Contexto:** hasta esta decisión, los 42 commits del historial se subieron con push directo a `main`; el
  repositorio no tiene ningún pull request. El CI (`.github/workflows/ci.yml`) se ejecutaba después de que el cambio
  ya estaba en `main`, de modo que un fallo (por ejemplo, la prueba de `series_etapas` que dependía de `data/gold`)
  solo se detectaba cuando ya afectaba a la rama principal.
- **Decisión:**
  1. **PR obligatorio:** todo cambio se trabaja en una rama (`feat/`, `fix/`, `docs/`, `chore/`, `test/`) y entra a
     `main` por pull request con la plantilla `.github/pull_request_template.md`. Ningún commit se hace en `main`,
     tampoco por agentes de código (regla en `AGENTS.md`).
  2. **CI obligatorio:** el flujo `CI` se dispara con `push` a `main` y con `pull_request`; los checks
     `calidad-y-pruebas (ubuntu-latest)`, `calidad-y-pruebas (windows-latest)` y `visor-web` deben pasar antes del merge.
  3. **Squash merge:** cada PR queda como un único commit en `main` con mensaje de Conventional Commits; la rama se
     borra después del merge.
  4. La protección de `main` (PR requerido, checks requeridos, historial lineal) se configura en GitHub; la configura el
     usuario, no los agentes.
  5. Los commits anteriores se conservan tal como están: no se crean PR retroactivos.
- **Consecuencias:**
  - Los fallos del CI se detectan antes de llegar a `main`; el historial de `main` queda lineal y con un commit por
    cambio.
  - Cada cambio exige más pasos (rama, push, PR, espera del CI); los detalles están en `CONTRIBUTING.md`.
  - Los commits intermedios de una rama se pierden en `main` tras el squash; quedan en el PR.
  - Si se renombra un trabajo del CI, hay que actualizar los checks obligatorios de la protección de `main`.
- **Alternativas:** seguir con push directo (sin revisión previa ni CI antes de integrar); merge commit (historial no
  lineal); rebase merge (conserva commits intermedios sin agrupar).
