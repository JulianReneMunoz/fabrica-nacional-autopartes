import { defineConfig } from "@playwright/test";

/**
 * Pruebas de extremo a extremo de IGNIS v2 (recorrido de todas las pestañas y redirecciones). Usa el Chrome
 * instalado en el sistema (channel "chrome" en Windows 11); CHROME_PATH permite indicar otro ejecutable.
 * El backend se inicia con uvicorn si no está activo; FNA_URL permite apuntar a otro servidor.
 */
const ejecutable = process.env.CHROME_PATH;
const BASE = process.env.FNA_URL ?? "http://127.0.0.1:8000";

/**
 * Secreto de sesiones SOLO para las pruebas e2e (ADR-033): se pasa al uvicorn que levanta Playwright. Nunca va en
 * .env.example ni como valor por defecto en el código. Si ya hay un servidor en el puerto (reuseExistingServer),
 * ese servidor debe tener su propio IGNIS_SECRETO_SESION.
 */
const SECRETO_SESION_E2E = "secreto-e2e-de-sesiones-ignis-solo-pruebas-0123456789";

export default defineConfig({
  testDir: "e2e",
  timeout: 90_000,
  workers: 1,
  reporter: [["list"], ["json", { outputFile: "test-results/e2e.json" }]],
  use: {
    baseURL: BASE,
    viewport: { width: 1440, height: 900 },
    launchOptions: {
      ...(ejecutable ? { executablePath: ejecutable } : { channel: "chrome" }),
      args: ["--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--no-proxy-server"],
    },
  },
  projects: [{ name: "recorrido" }],
  webServer: {
    command: "uv run uvicorn fabrica_autopartes.api.main:app --host 127.0.0.1 --port 8000",
    cwd: "..",
    url: `${BASE}/salud`,
    reuseExistingServer: true,
    timeout: 120_000,
    env: { ...(process.env as Record<string, string>), IGNIS_SECRETO_SESION: SECRETO_SESION_E2E },
  },
});
