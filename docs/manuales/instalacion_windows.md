# Instalación desde cero en Windows 11

Generada desde `herramientas_windows.yaml`. Terminal: PowerShell, salvo indicación.

## 1. Windows Terminal y PowerShell 7

- **Función:** Terminal y lenguaje de scripts para todos los comandos del manual.
- **Página oficial:** https://learn.microsoft.com/powershell/scripting/install/installing-powershell-on-windows
- **Versión recomendada:** PowerShell 7.4 LTS o superior (la sintaxis de los scripts se verificó con 7.4.6). Los scripts evitan sintaxis exclusiva de la versión 7, pero no se probaron en Windows PowerShell 5.1.
- **Requisitos previos:** Windows 11 actualizado; Windows Terminal viene incluido.
- **Instalación gráfica:** Microsoft Store → "PowerShell" → Instalar.
- **Instalación por PowerShell:**

```powershell
winget install --id Microsoft.PowerShell --source winget
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

- **Configuración inicial:** En Windows Terminal → Configuración → Perfil predeterminado → PowerShell.
- **Variables de entorno:** Ninguna.
- **Verificación:** `$PSVersionTable.PSVersion`; `Get-ExecutionPolicy -List`
- **Errores frecuentes:** 'la ejecución de scripts está deshabilitada' → aplicar Set-ExecutionPolicy al usuario actual; archivos descargados → Unblock-File .\scripts\*.ps1.
- **Actualización:** `winget upgrade --id Microsoft.PowerShell`
- **Seguridad:** No usar -ExecutionPolicy Bypass de forma global; revisar scripts descargados antes de ejecutarlos.

## 2. Git y autenticación con GitHub

- **Función:** Control de versiones y entrega del repositorio (rúbrica).
- **Página oficial:** https://git-scm.com/download/win · https://cli.github.com/
- **Versión recomendada:** Última estable de Git for Windows y GitHub CLI.
- **Requisitos previos:** Cuenta de GitHub con verificación en dos pasos.
- **Instalación gráfica:** Instalador de git-scm.com con opciones por defecto (incluye Git Bash y Git Credential Manager).
- **Instalación por PowerShell:**

```powershell
winget install --id Git.Git -e --source winget
winget install --id GitHub.cli -e --source winget
git config --global user.name "Nombre Apellido"
git config --global user.email "correo@ejemplo.com"
git config --global init.defaultBranch main
gh auth login
gh auth setup-git
```

- **Configuración inicial:** El repositorio incluye .gitattributes (LF para código, CRLF para .ps1).
- **Variables de entorno:** Git agrega C:\\Program Files\\Git\\cmd al PATH.
- **Verificación:** `git --version`; `gh auth status`
- **Errores frecuentes:** 'Authentication failed' → gh auth login y gh auth setup-git; finales de línea mezclados → git add --renormalize .
- **Actualización:** `winget upgrade --id Git.Git ; winget upgrade --id GitHub.cli`
- **Seguridad:** Nunca incrustar tokens en la URL remota; tokens con alcance mínimo y caducidad; .env fuera de Git.

## 3. uv y Python

- **Función:** Gestor único de Python, entornos virtuales y dependencias (estándar del proyecto).
- **Página oficial:** https://docs.astral.sh/uv/
- **Versión recomendada:** uv 0.11 o superior (construcción con 0.11.32); Python 3.12 fijado en .python-version.
- **Requisitos previos:** Ninguno (uv descarga Python).
- **Instalación gráfica:** No aplica.
- **Instalación por PowerShell:**

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
uv python install 3.12
```

- **Configuración inicial:** Opcional UV_CACHE_DIR para mover la caché a otro disco.
- **Variables de entorno:** El instalador agrega %USERPROFILE%\\.local\\bin al PATH del usuario.
- **Verificación:** `uv --version`; `uv python list --only-installed`
- **Errores frecuentes:** 'uv' no se reconoce → cerrar y abrir la terminal; antivirus bloquea el instalador → usar winget install --id astral-sh.uv -e.
- **Actualización:** `uv self update`
- **Seguridad:** Descargar el script, revisarlo y luego ejecutarlo si la política institucional lo exige.

## 4. Visual Studio Code

- **Función:** Editor con integración de Python, Ruff, TypeScript, YAML y LaTeX.
- **Página oficial:** https://code.visualstudio.com/
- **Versión recomendada:** Última estable.
- **Requisitos previos:** Ninguno.
- **Instalación gráfica:** Instalador de usuario con la opción "Agregar a PATH".
- **Instalación por PowerShell:**

```powershell
winget install --id Microsoft.VisualStudioCode -e --source winget
code --install-extension ms-python.python
code --install-extension charliermarsh.ruff
code --install-extension redhat.vscode-yaml
code --install-extension James-Yu.latex-workshop
```

- **Configuración inicial:** El repositorio incluye .vscode/settings.json (intérprete .venv, Ruff como formateador) y .vscode/extensions.json.
- **Variables de entorno:** Ninguna.
- **Verificación:** `code --version`; `code --list-extensions`
- **Errores frecuentes:** Intérprete incorrecto → Ctrl+Shift+P → 'Python: Select Interpreter' → .venv\Scripts\python.exe.
- **Actualización:** `Automática o winget upgrade --id Microsoft.VisualStudioCode`
- **Seguridad:** Mantener la confianza del espacio de trabajo (Workspace Trust); instalar extensiones de editores verificados.

## 5. Node.js LTS

- **Función:** Requisito de OpenCode (npm), de OpenSpec (Node 20.19 o superior) y del visor 3D web (Vite + React Three Fiber, carpeta web/).
- **Página oficial:** https://nodejs.org/
- **Versión recomendada:** LTS vigente (construcción con Node 22).
- **Requisitos previos:** Ninguno.
- **Instalación gráfica:** Instalador .msi LTS.
- **Instalación por PowerShell:**

```powershell
winget install --id OpenJS.NodeJS.LTS -e --source winget
```

- **Configuración inicial:** Ninguna.
- **Variables de entorno:** Los paquetes globales quedan en %APPDATA%\\npm (debe estar en PATH).
- **Verificación:** `node --version`; `npm --version`; `cd web; npm ci; npm run build; npm test`
- **Errores frecuentes:** Comando global no encontrado tras npm install -g → agregar %APPDATA%\npm al PATH del usuario.
- **Actualización:** `winget upgrade --id OpenJS.NodeJS.LTS`
- **Seguridad:** Verificar el nombre exacto de cada paquete (opencode-ai, @fission-ai/openspec) para evitar paquetes impostores.

## 6. Ollama

- **Función:** Servidor local de modelos abiertos (LLM de la aplicación y embeddings del Módulo 2).
- **Página oficial:** https://ollama.com/download · https://ollama.com/library
- **Versión recomendada:** Última estable.
- **Requisitos previos:** 8 GB de RAM para modelos 3B; 16 GB o más para 7B-8B; GPU opcional.
- **Instalación gráfica:** OllamaSetup.exe desde la página oficial.
- **Instalación por PowerShell:**

```powershell
winget install --id Ollama.Ollama -e --source winget
ollama pull llama3.2:3b
ollama pull nomic-embed-text-v2-moe
```

- **Configuración inicial:** La aplicación fija num_ctx con FNA_OLLAMA_NUM_CTX (16384 por defecto) porque el contexto completo se inyecta en el prompt.
- **Variables de entorno:** OLLAMA_HOST (por defecto 127.0.0.1:11434) y OLLAMA_MODELS (carpeta de modelos).
- **Verificación:** `ollama --version`; `ollama list`; `Invoke-RestMethod http://localhost:11434/api/tags`
- **Errores frecuentes:** Sin respuesta en 11434 → iniciar la aplicación Ollama u 'ollama serve'; memoria insuficiente → modelo más pequeño.
- **Actualización:** `winget upgrade --id Ollama.Ollama ; ollama pull <modelo> actualiza el modelo.`
- **Seguridad:** No exponer OLLAMA_HOST=0.0.0.0 en redes públicas; revisar la licencia de cada modelo en su ficha.

## 7. OpenCode

- **Función:** Consola agéntica de código abierto, multi-proveedor, con MCP, agentes y permisos.
- **Página oficial:** https://opencode.ai/docs · https://github.com/anomalyco/opencode
- **Versión recomendada:** Última estable del paquete npm opencode-ai.
- **Requisitos previos:** Node.js LTS; un proveedor LLM (Ollama, clave de API o servicio compatible). La documentación de OpenCode recomienda WSL para la mejor experiencia de terminal; la instalación nativa funciona.
- **Instalación gráfica:** Aplicación de escritorio opcional desde https://opencode.ai/download.
- **Instalación por PowerShell:**

```powershell
npm install -g opencode-ai
opencode auth login
opencode auth list
```

- **Configuración inicial:** configuración local de OpenCode (agentes, permisos, MCP, proveedor Ollama; no versionada). Configuración global en %USERPROFILE%\\.config\\opencode\\opencode.json.
- **Variables de entorno:** Claves de proveedor en el almacén de OpenCode (opencode auth login), nunca en archivos del repositorio.
- **Verificación:** `opencode --version`; `En la interfaz: /models`
- **Errores frecuentes:** 'opencode' no se reconoce → %APPDATA%\npm en PATH; el paquete se llama opencode-ai (no opencode).
- **Actualización:** `npm install -g opencode-ai@latest`
- **Seguridad:** bash en 'ask', git push en 'deny'; no usar credenciales de suscripción Claude Pro/Max (los términos de Anthropic las limitan a Claude Code y claude.ai).

## 8. Claude Code

- **Función:** Consola agéntica de Anthropic con subagentes, skills, hooks y MCP.
- **Página oficial:** https://docs.claude.com/en/docs/claude-code/overview
- **Versión recomendada:** Instalador nativo con actualización automática.
- **Requisitos previos:** Windows 10 1809+ u 11 (64 bits); suscripción Claude (Pro/Max/Team/Enterprise) o cuenta de la Consola con facturación por API. Git for Windows recomendado (Git Bash).
- **Instalación gráfica:** No aplica.
- **Instalación por PowerShell:**

```powershell
irm https://claude.ai/install.ps1 | iex
winget install Anthropic.ClaudeCode
claude
```

- **Configuración inicial:** configuración local de Claude Code (no versionada) y .mcp.json del repositorio.
- **Variables de entorno:** El binario queda en %USERPROFILE%\\.local\\bin; si Git Bash no se detecta, definir CLAUDE_CODE_GIT_BASH_PATH en settings.json.
- **Verificación:** `claude --version`; `claude doctor`; `claude mcp list`
- **Errores frecuentes:** 'claude' no se reconoce → reabrir la terminal o agregar %USERPROFILE%\.local\bin al PATH; en CMD usar curl -fsSL https://claude.ai/install.cmd -o install.cmd && install.cmd && del install.cmd.
- **Actualización:** `Automática; manual con claude update.`
- **Seguridad:** Permisos allow/ask/deny por proyecto; lectura de .env denegada; revisar cada cambio antes de aceptarlo.

## 9. Docker Desktop (opcional)

- **Función:** Contenedores para Ollama, API e interfaz (docker-compose.yml).
- **Página oficial:** https://www.docker.com/products/docker-desktop/
- **Versión recomendada:** Última estable con backend WSL2.
- **Requisitos previos:** Virtualización habilitada en BIOS; WSL2. Uso académico permitido; las organizaciones grandes requieren suscripción de pago según la licencia de Docker Desktop.
- **Instalación gráfica:** Instalador oficial con "Use WSL 2 instead of Hyper-V".
- **Instalación por PowerShell:**

```powershell
winget install --id Docker.DockerDesktop -e --source winget
docker compose up --build
```

- **Configuración inicial:** Asignar memoria suficiente a WSL2 para Ollama.
- **Variables de entorno:** Ninguna.
- **Verificación:** `docker --version`; `docker run --rm hello-world`
- **Errores frecuentes:** 'WSL 2 installation is incomplete' → wsl --update y reiniciar.
- **Actualización:** `Desde la aplicación o winget upgrade --id Docker.DockerDesktop`
- **Seguridad:** No montar el disco completo en contenedores; usar el archivo .env local sin versionarlo.

## 10. WSL2 (solo si es necesario)

- **Función:** Requisito del backend de Docker Desktop; opcional para OpenCode.
- **Página oficial:** https://learn.microsoft.com/windows/wsl/install
- **Versión recomendada:** Kernel WSL actualizado.
- **Requisitos previos:** PowerShell como administrador.
- **Instalación gráfica:** No aplica.
- **Instalación por PowerShell:**

```powershell
wsl --install
wsl --update
```

- **Configuración inicial:** Distribución Ubuntu por defecto.
- **Variables de entorno:** Ninguna.
- **Verificación:** `wsl --status`; `wsl --list --verbose`
- **Errores frecuentes:** Error de virtualización → habilitar VT-x/AMD-V en BIOS.
- **Actualización:** `wsl --update`
- **Seguridad:** No compartir credenciales entre Windows y WSL sin necesidad.

## 11. Servidores MCP

- **Función:** Servidor propio fna-conocimiento y memoria persistente Engram (opcional).
- **Página oficial:** https://github.com/Gentleman-Programming/engram · https://modelcontextprotocol.io
- **Versión recomendada:** SDK mcp 2.x en el proyecto; Engram última versión de GitHub Releases.
- **Requisitos previos:** Base Gold construida (uv run fabrica build).
- **Instalación gráfica:** No aplica.
- **Instalación por PowerShell:**

```powershell
uv run fabrica-mcp
claude mcp list
engram setup opencode
claude plugin marketplace add Gentleman-Programming/engram
claude plugin install engram
```

- **Configuración inicial:** .mcp.json (Claude Code) y la sección mcp de la configuración local de OpenCode. Engram en Windows: descargar engram_<versión>_windows_amd64.zip de GitHub Releases, copiar engram.exe en %USERPROFILE%\bin y agregar esa carpeta al PATH.
- **Variables de entorno:** FNA_MCP_PERMITIR_LLM=false por defecto.
- **Verificación:** `uv run pytest tests/integration/test_mcp.py -q`; `engram version`
- **Errores frecuentes:** Servidor 'failed' en claude mcp list → ejecutar uv run fabrica-mcp manualmente y leer stderr.
- **Actualización:** `uv sync (servidor propio); nueva versión del binario (Engram).`
- **Seguridad:** Solo herramientas de lectura; revisar cualquier servidor de terceros antes de registrarlo.

## 12. Motor de base de datos (SQLite y PostgreSQL)

- **Función:** Auditoría de interacciones, pipeline, evaluaciones, estados guardados y eventos del simulador 3D.
- **Página oficial:** https://www.postgresql.org/download/windows/ · https://alembic.sqlalchemy.org/
- **Versión recomendada:** SQLite embebido para desarrollo; PostgreSQL 17 para el despliegue (servicio postgres de docker-compose.yml o instalador nativo).
- **Requisitos previos:** Ninguno para SQLite; Docker Desktop o el instalador de PostgreSQL para el motor de despliegue.
- **Instalación gráfica:** Instalador de EDB con pgAdmin (opcional) o docker compose up postgres.
- **Instalación por PowerShell:**

```powershell
docker compose up -d postgres
winget install --id PostgreSQL.PostgreSQL.17 -e --source winget
uv run alembic upgrade head
```

- **Configuración inicial:** FNA_URL_BASE_DATOS=postgresql+psycopg://fna:fna@localhost:5432/fna (por defecto sqlite:///data/app.db).
- **Variables de entorno:** FNA_URL_BASE_DATOS.
- **Verificación:** `uv run alembic current`; `uv run pytest tests/integration/test_postgresql.py -q`
- **Errores frecuentes:** 'connection refused' → verificar que el servicio postgres esté activo (docker compose ps) y el puerto 5432 libre.
- **Actualización:** `Nuevas migraciones con uv run alembic revision --autogenerate -m \"descripcion\".`
- **Seguridad:** Credenciales solo en .env (no versionado); usuario sin privilegios de superusuario; copia de seguridad con pg_dump.

## 13. FFmpeg (videos del recorrido)

- **Función:** Codifica en MP4 los recorridos automáticos de menos de 30 s grabados por Playwright.
- **Página oficial:** https://ffmpeg.org/download.html
- **Versión recomendada:** Última estable.
- **Requisitos previos:** Ninguno.
- **Instalación gráfica:** No aplica.
- **Instalación por PowerShell:**

```powershell
winget install --id Gyan.FFmpeg -e --source winget
cd web; npx playwright test --project=recorrido
```

- **Configuración inicial:** Ninguna.
- **Variables de entorno:** ffmpeg debe estar en el PATH.
- **Verificación:** `ffmpeg -version`
- **Errores frecuentes:** 'ffmpeg' no se reconoce → cerrar y abrir la terminal tras la instalación.
- **Actualización:** `winget upgrade --id Gyan.FFmpeg`
- **Seguridad:** Descargar solo desde la fuente indicada por ffmpeg.org.

