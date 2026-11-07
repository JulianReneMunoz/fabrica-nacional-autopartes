# Contribución

Todo cambio entra a `main` por pull request con el CI en verde y squash merge
([ADR-021](docs/arquitectura/adr/ADR-021-flujo-pull-requests.md)). **Regla: no hacer commit directo en `main`.**
Las reglas para agentes de código están en [`AGENTS.md`](AGENTS.md).

## Nombres de rama
| Prefijo | Uso |
|---|---|
| `feat/` | Funcionalidad nueva |
| `fix/` | Corrección de errores |
| `docs/` | Solo documentación |
| `chore/` | Mantenimiento, configuración o CI |
| `test/` | Pruebas |

Formato: `prefijo/descripcion-corta-en-minusculas` (por ejemplo, `fix/anclas-readme`).

## Flujo
rama → commits → push de la rama → `gh pr create` → CI en verde → revisión → squash merge → borrar la rama.

Comandos de PowerShell, desde `C:\fabrica-nacional-autopartes`:

```powershell
# 1. Rama desde main actualizado
git switch main
git pull --ff-only
git switch -c feat/descripcion-corta

# 2. Commits (Conventional Commits) tras las verificaciones locales
uv run --no-sync ruff check .; uv run --no-sync ruff format --check .
uv run --no-sync mypy
uv run --no-sync pytest -q
cd web; npm test; cd ..
git add <archivos>
git commit -m "feat: descripción del cambio"

# 3. Push de la rama
git push -u origin feat/descripcion-corta

# 4. Pull request (rellena la plantilla .github/pull_request_template.md)
gh pr create --base main --fill

# 5. CI en verde
gh pr checks --watch

# 6. Revisión
gh pr view --web

# 7. Squash merge y borrado de la rama (remota y local)
gh pr merge --squash --delete-branch
git switch main
git pull --ff-only
```

## Checks obligatorios del CI
Trabajos de `.github/workflows/ci.yml` que deben pasar antes del merge:
- `calidad-y-pruebas (ubuntu-latest)`
- `calidad-y-pruebas (windows-latest)`
- `visor-web`

## Makefile
Atajos para los comandos frecuentes; funcionan con GNU make en Windows (PowerShell o cmd) y en Linux. Instalación en
Windows 11 (abrir una terminal nueva después):

```powershell
winget install ezwinports.make
make help
```

| Objetivo | Qué ejecuta | Equivale a |
|---|---|---|
| `make help` (por defecto) | Lista de objetivos | — |
| `make instalar` | `uv sync --locked` y `npm ci` en `web/` | `scripts/preparar_proyecto.ps1` (sin construir la base) |
| `make calidad` | `ruff check`, `ruff format --check`, `mypy`, `verificar_capas.py` y `pytest -q` | `scripts/verificar_calidad.ps1` (parte Python) |
| `make pruebas-web` | Vitest (`npm test` en `web/`) | `scripts/verificar_calidad.ps1` (parte web) |
| `make api [PUERTO=8000]` | API FastAPI en `127.0.0.1` con recarga | `scripts/ejecutar_api.ps1` |
| `make app` | Interfaz Streamlit | `scripts/ejecutar_app.ps1` |
| `make pipeline [MAX_PAGINAS=80]` | Scraping real, Bronze/Silver/Gold, validación y gráficas; **requiere red y aprobación** | `scripts/ejecutar_pipeline.ps1` |
| `make validar-moto` | `fabrica simulador validar --ensamblaje moto_honda` | — |
| `make enlaces` | `scripts/verificar_enlaces.py` (sin red) | — |
| `make graphify` | `scripts/graphify_codigo.py`: `--code-only` con `GRAPHIFY_BACKEND=none`, salida temporal fuera del repositorio | Procedimiento de la [ADR-020](docs/arquitectura/adr/ADR-020-graphify-mapa-del-codigo.md) |

Todos los objetivos usan `uv run --no-sync` (salvo `instalar`). Los modelos locales quedan pospuestos y no tienen
objetivo ([ADR-022](docs/arquitectura/adr/ADR-022-ollama-pospuesto.md)). `make -n <objetivo>` muestra los comandos sin
ejecutarlos.
