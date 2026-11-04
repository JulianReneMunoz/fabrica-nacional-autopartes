import { defineConfig } from "@playwright/test";

/**
 * Pruebas de extremo a extremo del visor (biblioteca, freno 3D, prensa, línea) y grabación del
 * recorrido automático. Usa el Chrome instalado en el sistema (channel "chrome" en Windows 11);
 * CHROME_PATH permite indicar otro ejecutable. El backend se inicia con uvicorn si no está activo.
 */
const ejecutable = process.env.CHROME_PATH;
const BASE = process.env.FNA_URL ?? "http://127.0.0.1:8000";

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
  projects: [
    { name: "funcional", testIgnore: /recorrido/ },
    {
      name: "recorrido",
      testMatch: /recorrido/,
      use: { viewport: { width: 1280, height: 800 } },
    },
  ],
  webServer: {
    command: "uv run uvicorn fabrica_autopartes.api.main:app --host 127.0.0.1 --port 8000",
    cwd: "..",
    url: `${BASE}/salud`,
    reuseExistingServer: true,
    timeout: 120_000,
  },
});
