# ADR-018 · Herramientas de desarrollo Engram (memoria) y GGA (revisión previa al commit)

- **Estado:** aceptada, con excepción documentada a la regla de `fna-seguridad` (puntuación ≥ 51 se rechaza).
- **Contexto:** el flujo de trabajo con agentes de código pierde contexto entre sesiones (Engram) y no tiene una
  revisión automática de las reglas de `AGENTS.md` antes de cada commit (GGA). Ambas herramientas son de terceros
  (Gentleman Programming) y obtienen puntuaciones de SkillSpector que superan el umbral de rechazo; el análisis
  manual de cada hallazgo figura en las entradas S-05 y S-06 de `docs/prompts/bitacora_experimentos.md`.
- **Decisión:**
  1. **Engram v3.6.2** (binario Go, memoria en SQLite local, servidor MCP). Se instala el binario del release oficial
     para Windows amd64 con verificación de SHA-256 en `%LOCALAPPDATA%\engram\bin`. El plugin de Claude Code y
     `engram setup opencode` los ejecuta el usuario; **no** se ejecuta `engram setup claude-code` ni se añaden
     permisos globales sin aprobación explícita.
  2. **GGA v2.10.1** (herramienta de shell). Se instala con `bash install.sh` desde el commit del tag
     `1124c3672f082c56b033c4e23a30e95d0e8cd593` en `%USERPROFILE%\bin`. Configuración versionada en `.gga`:
     proveedor `claude` (sesión local, sin claves), reglas en `AGENTS.md`, solo `*.py`, `*.ts` y `*.tsx`,
     excluyendo pruebas, datos, documentación y `web/dist`, `TIMEOUT=180`. El hook `pre-commit` vive en
     `.git/hooks` (no se versiona); `gga install` lo recrea.
  3. **Versiones fijadas.** La excepción vale solo para Engram v3.6.2 y GGA v2.10.1. Toda actualización exige repetir
     el escaneo y el análisis manual y registrar una entrada nueva en la bitácora.
- **Consecuencias:**
  - El diff en preparación (solo archivos que cumplen los patrones) se envía a `claude --print` en cada commit;
    la prueba de verificación tardó unos 19 s para un archivo pequeño. Un commit con muchos archivos puede acercarse
    al límite de 180 s; `git commit --no-verify` omite la revisión de forma explícita y deliberada.
  - GGA consulta `api.github.com` (2 s) para avisar de versiones nuevas; no instala nada por sí mismo.
  - Engram guarda memoria local en `%USERPROFILE%\.engram`; el contenido del plugin hace que los prompts del usuario
    se envíen al servidor local de Engram (127.0.0.1). No se guardan secretos (regla del protocolo de la skill).
  - La revisión de GGA es una ayuda, no un sustituto de `ruff`, `mypy`, `pytest` ni de `revisor-calidad`.
- **Alternativas:** no instalar (se pierde la revisión automática y la memoria entre sesiones); `pre-commit` con
  `ruff` y `mypy` (ya presente, no revisa reglas de negocio); memoria propia de Claude Code (`MEMORY.md`, ya en uso,
  sin búsqueda de texto completo).
