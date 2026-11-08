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
| `make instalar-semantica` | `uv sync --locked --extra semantica-cpu` (PyTorch CPU) | — |
| `make instalar-semantica-gpu` | `uv sync --locked --extra semantica-gpu` (PyTorch cu130) | — |
| `make indexar [DESCARGAR=--descargar]` | `fabrica indexar-vectores`: índice Chroma en `data/vectores/` con nomic | — |
| `make comparar-recuperadores [DISPOSITIVOS=cpu,cuda]` | Experimento de prefijos y BM25 frente a semántico en `evaluacion/resultados/` | — |

Todos los objetivos usan `uv run --no-sync` (salvo los de instalación). Los modelos locales quedan pospuestos y no
tienen objetivo ([ADR-022](docs/arquitectura/adr/ADR-022-ollama-pospuesto.md)). `make -n <objetivo>` muestra los
comandos sin ejecutarlos.

### Base semántica: CPU o GPU
La base semántica ([ADR-023](docs/arquitectura/adr/ADR-023-base-semantica-nomic-chroma.md)) es opcional: CI y
`make instalar` no instalan PyTorch, y BM25 sigue siendo el recuperador por defecto. Las dos variantes son excluyentes;
cambiar de una a otra reemplaza `torch`.

| Variante | Cuándo usarla | Descarga aproximada |
|---|---|---|
| `make instalar-semantica` (CPU) | Equipos sin GPU NVIDIA, Linux de servidor o cuando basta indexar de vez en cuando (167 fragmentos) | 0,3 GB |
| `make instalar-semantica-gpu` (CUDA 13.0) | GPU NVIDIA con controlador compatible con CUDA 13 (probada en una RTX 5070 Ti Laptop GPU, sm_120); acelera la indexación y los experimentos | 2,1 GB |

- `EMBEDDINGS_DEVICE=auto|cpu|cuda` (por defecto `auto`: `cuda` si PyTorch detecta una GPU) elige el dispositivo; el
  usado queda en el registro y en los resultados.
- La primera indexación descarga el modelo (unos 550 MB, a la caché de Hugging Face): `make indexar DESCARGAR=--descargar`.
- `make instalar` o un `uv run` sin `--no-sync` dejan el entorno sin el extra: volver a ejecutar el objetivo de
  instalación de la variante.

### Agente con memoria: activar el proveedor
El agente (`fabrica agente`, `POST /api/v1/agente`) usa Claude Haiku 5.5 vía API
([ADR-026](docs/arquitectura/adr/ADR-026-haiku-proveedor-principal-agente.md); precios y costo estimado en
[`docs/arquitectura/modelos.md`](docs/arquitectura/modelos.md)). Sin clave responde 503 con la instrucción.

**A. Activar el agente con Claude Haiku 5.5 (por defecto)**

1. Vincular los créditos del plan Max: en claude.ai, *Settings > Billing > API credits > Link organization*.
   Requisitos: 7 días en el plan y rol Owner, Admin o Billing en la organización de la Claude Console; solo se
   puede vincular una organización. No activar la recarga automática (*auto-reload*).
   Fuente: https://support.claude.com/en/articles/17154008-monthly-api-credits-for-max-and-team-plans
2. Crear la clave en la Claude Console (*API keys*), en la organización vinculada.
3. Guardarla en `.env` con `Read-Host -AsSecureString` en PowerShell: la clave no se muestra ni queda en el
   historial. Nunca pegarla en chats, capturas ni commits. Si `.env` ya tiene una línea `FNA_ANTHROPIC_API_KEY=`,
   borrarla antes con `notepad .env`.

   ```powershell
   $segura = Read-Host "Clave de la API (no se muestra)" -AsSecureString
   $bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($segura)
   $clave = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr)
   Add-Content -Path .env -Value "FNA_ANTHROPIC_API_KEY=$clave" -Encoding ascii
   [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr); Remove-Variable clave, segura, bstr
   git status --short .env          # no debe mostrar nada: .env está ignorado
   ```
4. Comprobar con `make verificar-agente`: debe decir «Disponible».

**B. Advertencia:** usar siempre `FNA_ANTHROPIC_API_KEY` y nunca `ANTHROPIC_API_KEY`, porque esta última haría que
Claude Code facture por API en lugar de usar el plan Max.
