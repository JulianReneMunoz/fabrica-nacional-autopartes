## Qué cambia y por qué
<!-- Resumen del cambio y motivo (requisito, hallazgo, ADR o entrada de la bitácora relacionada). -->

## Tipo de cambio (Conventional Commits)
- [ ] `feat`: funcionalidad nueva
- [ ] `fix`: corrección de un error
- [ ] `docs`: solo documentación
- [ ] `test`: pruebas nuevas o corregidas
- [ ] `refactor`: cambio interno sin efecto funcional
- [ ] `chore`: mantenimiento, configuración o CI

## Lista de verificación
- [ ] `uv run --no-sync ruff check .` y `uv run --no-sync ruff format --check .` sin errores
- [ ] `uv run --no-sync mypy` sin errores
- [ ] `uv run --no-sync pytest -q` en verde
- [ ] `cd web; npm test` (Vitest) en verde, si cambia el visor
- [ ] `uv run --no-sync python scripts/verificar_enlaces.py` sin enlaces rotos
- [ ] Sin secretos, claves ni datos personales (Ley 1581 de 2012) en el código, los datos ni los commits
- [ ] Bitácora (`docs/prompts/bitacora_experimentos.md`) o ADR (`docs/arquitectura/adr/`) actualizada, si aplica

## Capturas
<!-- Obligatorias cuando cambia la interfaz (Streamlit o visor 3D); en otro caso, «No aplica». -->
