# Objetivos de desarrollo de Fábrica Nacional de Autopartes.
# Funciona con GNU make en Windows (winget install ezwinports.make; PowerShell o cmd) y en Linux.
# Las recetas usan solo comandos válidos en sh y en cmd: `uv run --no-sync ...` y `cd web && ...`.
# Equivalencias con scripts/*.ps1 en CONTRIBUTING.md (sección «Makefile»).

UV := uv run --no-sync
PUERTO ?= 8000
MAX_PAGINAS ?= 80
DISPOSITIVOS ?= cpu,cuda
DESCARGAR ?=
THREAD ?= cli
PREGUNTA ?=

.DEFAULT_GOAL := help
.PHONY: help instalar instalar-semantica instalar-semantica-gpu calidad pruebas-web api app pipeline \n	validar-moto enlaces graphify indexar comparar-recuperadores agente verificar-agente

help: ## Lista los objetivos disponibles
	$(info Uso: make <objetivo> [PUERTO=8000] [MAX_PAGINAS=80] [DISPOSITIVOS=cpu,cuda] [DESCARGAR=--descargar])
	$(info              [THREAD=cli] [PREGUNTA="texto"])
	$(info )
	$(info   instalar      uv sync --locked y npm ci del visor)
	$(info   instalar-semantica      Base semántica con PyTorch CPU (extra semantica-cpu, ADR-023))
	$(info   instalar-semantica-gpu  Base semántica con PyTorch CUDA 13.0 (extra semantica-gpu))
	$(info   calidad       ruff check, ruff format --check, mypy, verificar capas y pytest -q)
	$(info   pruebas-web   Vitest del visor 3D (npm test en web/))
	$(info   api           API FastAPI en http://127.0.0.1:$(PUERTO) (Swagger en /docs))
	$(info   app           Interfaz Streamlit en http://localhost:8501)
	$(info   pipeline      Scraping real + Bronze/Silver/Gold + gráficas (requiere red y aprobación))
	$(info   validar-moto  Integridad del ensamblaje moto_honda)
	$(info   enlaces       Enlaces relativos y anclas de README.md y docs/)
	$(info   graphify      Grafo del código: --code-only, GRAPHIFY_BACKEND=none, salida fuera del repo (ADR-020))
	$(info   indexar       Índice Chroma en data/vectores/ con nomic (DESCARGAR=--descargar la primera vez))
	$(info   comparar-recuperadores  Prefijos C6 y BM25 frente a semántico; tiempos en $(DISPOSITIVOS))
	$(info   agente        Agente con memoria, Claude Haiku 5.5 por defecto (THREAD=$(THREAD)); sin PREGUNTA, interactivo)
	$(info   verificar-agente  Proveedor del agente configurado (FNA_PROVEEDOR_AGENTE) y si responde)
	$(info )
	$(info Ollama: opcional en el código, sin objetivos de instalación (ADR-022, ADR-026).)
	@exit 0

instalar: ## Entorno reproducible desde uv.lock y dependencias exactas del visor
	uv sync --locked
	cd web && npm ci --no-audit --no-fund

calidad: ## Lint, formato, tipos, capas y pruebas de Python
	$(UV) ruff check .
	$(UV) ruff format --check .
	$(UV) mypy
	$(UV) python scripts/verificar_capas.py
	$(UV) pytest -q

instalar-semantica: ## Extra semantica-cpu (índice PyTorch CPU); no lo instala CI
	uv sync --locked --extra semantica-cpu

instalar-semantica-gpu: ## Extra semantica-gpu (índice PyTorch cu130, GPU NVIDIA con controlador CUDA 13)
	uv sync --locked --extra semantica-gpu

pruebas-web: ## Pruebas Vitest del visor
	cd web && npm test

api: ## API FastAPI con recarga (equivale a scripts/ejecutar_api.ps1)
	$(UV) uvicorn fabrica_autopartes.api.main:app --reload --reload-dir src --host 127.0.0.1 --port $(PUERTO)

app: ## Interfaz Streamlit (equivale a scripts/ejecutar_app.ps1)
	$(UV) streamlit run frontend/app.py

pipeline: ## Proceso real con red (equivale a scripts/ejecutar_pipeline.ps1); requiere aprobación explícita
	$(UV) fabrica pipeline --max-paginas $(MAX_PAGINAS)
	$(UV) fabrica stats

validar-moto: ## Validación del ensamblaje de la motocicleta de referencia
	$(UV) fabrica simulador validar --ensamblaje moto_honda

enlaces: ## Verificación de enlaces de la documentación (sin red)
	$(UV) python scripts/verificar_enlaces.py

graphify: ## Mapa del código en el modo aprobado por la ADR-020
	$(UV) python scripts/graphify_codigo.py

indexar: ## Reconstruye data/vectores/ (Chroma + nomic); EMBEDDINGS_DEVICE=auto|cpu|cuda
	$(UV) fabrica indexar-vectores $(DESCARGAR)

comparar-recuperadores: ## Experimento de prefijos y comparación BM25 frente a semántico (evaluacion/resultados/)
	$(UV) fabrica comparar-recuperadores --dispositivos $(DISPOSITIVOS)

agente: ## Agente con memoria; Claude Haiku 5.5 con FNA_ANTHROPIC_API_KEY (ADR-026) u Ollama opcional
	$(UV) fabrica agente $(if $(PREGUNTA),"$(PREGUNTA)") --thread $(THREAD)

verificar-agente: ## Informa el proveedor del agente y si responde (sin respaldo a otro proveedor)
	$(UV) fabrica agente --verificar

# Pospuesto (ver ADR-022): no hay objetivos que instalen modelos locales. El agente usa Claude Haiku 5.5 con
# FNA_ANTHROPIC_API_KEY por defecto (ADR-026); Ollama solo si se instala y se elige FNA_PROVEEDOR_AGENTE=ollama.
