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
