import { expect, test, type Page } from "@playwright/test";

/**
 * Recorrido de IGNIS v2 (criterio de aceptación 3): todas las pestañas de la barra lateral abren sin errores en la
 * consola y las rutas retiradas del M1 redirigen a Atención. Corre contra FastAPI (webServer de playwright.config)
 * o contra `vite preview` con FNA_URL; el SSE y el TTS se simulan para no depender de un proveedor LLM.
 */
const PESTANAS = [
  ["atencion", "Atención — IGNIS"],
  ["faq", "Preguntas frecuentes"],
  ["qa", "Consulta puntual Q&A"],
  ["proceso-datos", "Proceso de datos"],
  ["corpus", "Corpus"],
  ["base", "Base de conocimiento — Qdrant"],
  ["agente", "Agente y memoria"],
  ["herramientas", "Herramientas LangChain"],
  ["router", "Router"],
  ["prompts", "Prompts"],
  ["configuracion", "Configuración de agentes"],
  ["rayos-x", "Rayos-X y validación"],
  ["seguridad", "Seguridad RAG"],
  ["auditoria", "Auditoría"],
  ["panel", "Panel"],
  ["evaluacion", "Evaluación"],
  ["mlflow", "Experimentos MLflow"],
  ["kanban", "Tablero Kanban"],
  ["arquitectura", "Arquitectura y API"],
  ["sesion", "Mi sesión"],
  ["ajustes", "Ajustes"],
] as const;

const RUTAS_VIEJAS = ["#/", "#/biblioteca", "#/prensa", "#/linea", "#/moto", "#/explorador", "#/maquina/freno", "#/maquina/moto_honda", "#/robot", "#/simulador"];

/** WAV PCM de 16 bits en silencio (0,3 s) para simular /tts sin errores de red en la consola. */
function wavSilencio(segundos = 0.3, tasa = 8000): Buffer {
  const n = Math.round(segundos * tasa);
  const b = Buffer.alloc(44 + n * 2);
  b.write("RIFF", 0); b.writeUInt32LE(36 + n * 2, 4); b.write("WAVE", 8); b.write("fmt ", 12);
  b.writeUInt32LE(16, 16); b.writeUInt16LE(1, 20); b.writeUInt16LE(1, 22); b.writeUInt32LE(tasa, 24);
  b.writeUInt32LE(tasa * 2, 28); b.writeUInt16LE(2, 32); b.writeUInt16LE(16, 34); b.write("data", 36); b.writeUInt32LE(n * 2, 40);
  return b;
}

/** Errores de consola y excepciones de la página; se ignoran los avisos de WebGL del renderizador por software. */
function vigilarConsola(page: Page): string[] {
  const errores: string[] = [];
  page.on("console", (m) => {
    if (m.type() === "error" && !/GPU stall|WebGL|swiftshader|favicon/i.test(m.text())) errores.push(m.text());
  });
  page.on("pageerror", (e) => errores.push(e.message));
  return errores;
}

/** Pestañas con implementación propia (sin estado vacío). */
const IMPLEMENTADAS = new Set(["atencion", "sesion", "router"]);

test.beforeEach(async ({ page }) => {
  // Sesión real (ADR-033): page.request comparte las cookies con el contexto del navegador.
  const entrada = await page.request.post("/api/v1/sesiones", { data: { alias: "e2e-01" } });
  expect(entrada.status()).toBe(201);
  await page.route("**/api/v1/ignis/stream", (r) =>
    r.fulfill({ status: 200, contentType: "text/event-stream", body: 'data: {"tipo":"metadatos","ruta_router":"directo","citas":[]}\n\ndata: {"tipo":"oracion","texto":"Hola."}\n\ndata: {"tipo":"fin"}\n\ndata: [DONE]\n\n' }),
  );
  await page.route("**/api/v1/tts", (r) => r.fulfill({ status: 200, contentType: "audio/wav", body: wavSilencio() }));
});

test("todas las pestañas abren sin errores en la consola", async ({ page }) => {
  const errores = vigilarConsola(page);
  await page.goto("/app/#/atencion");
  const nav = page.getByRole("navigation", { name: "Principal" });
  for (const [id, etiqueta] of PESTANAS) {
    await page.goto(`/app/#/${id}`);
    await expect(page.locator("main h1")).toHaveText(id === "atencion" ? "Atención al cliente — IGNIS" : etiqueta);
    await expect(nav.locator('a[aria-current="page"]')).toHaveText(etiqueta);
    if (!IMPLEMENTADAS.has(id)) await expect(page.getByText(/No disponible todavía \(/)).toBeVisible();
  }
  expect(errores).toEqual([]);
});

test("las rutas retiradas del M1 redirigen a Atención", async ({ page }) => {
  for (const ruta of RUTAS_VIEJAS) {
    await page.goto(`/app/${ruta}`);
    await expect(page).toHaveURL(/#\/atencion$/);
    await expect(page.locator("main h1")).toHaveText("Atención al cliente — IGNIS");
  }
});

test("Atención carga el auto GLB y responde un mensaje", async ({ page }) => {
  const errores = vigilarConsola(page);
  await page.goto("/app/#/atencion");
  await expect(page.locator("[data-modelo='cargado']")).toBeVisible({ timeout: 30_000 });
  await page.getByLabel("Mensaje para IGNIS").fill("Hola");
  await page.keyboard.press("Enter");
  await expect(page.locator(".ignis-burbuja.ignis").last()).toContainText("Hola.");
  await expect(page.locator(".ignis-insignia.ruta").last()).toContainText("Directo");
  await expect(page.locator(".ignis-chip-estado")).toHaveText("En reposo", { timeout: 8000 });
  expect(errores).toEqual([]);
});

test("por debajo de 1023 px la barra lateral se vuelve un menú", async ({ page }) => {
  await page.setViewportSize({ width: 900, height: 800 });
  await page.goto("/app/#/corpus");
  const nav = page.getByRole("navigation", { name: "Principal" });
  await expect(nav).toBeHidden();
  await page.getByRole("button", { name: "Abrir menú" }).click();
  await expect(nav).toBeVisible();
  await nav.getByRole("link", { name: "Panel" }).click();
  await expect(page).toHaveURL(/#\/panel$/);
  await expect(nav).toBeHidden();
});

test("sin sesión se muestra la pantalla de entrada y entrar con un alias abre la aplicación", async ({ page }) => {
  await page.context().clearCookies();
  await page.goto("/app/#/atencion");
  await expect(page.getByRole("heading", { name: "Entrar a IGNIS" })).toBeVisible();
  await page.getByLabel("Alias").fill("ana-gomez");
  await page.getByRole("button", { name: "Entrar" }).click();
  await expect(page.getByRole("alert")).toContainText("Alias no válido");
  await page.getByLabel("Alias").fill("e2e-02");
  await page.getByRole("button", { name: "Entrar" }).click();
  await expect(page.locator("main h1")).toHaveText("Atención al cliente — IGNIS");
  await expect(page.locator(".ig-usuario")).toContainText("e2e-02");
});

test("«Mi sesión» lista el hilo y «Reabrir» carga su historial; «Cerrar sesión» vuelve a la entrada", async ({ page }) => {
  await page.unroute("**/api/v1/ignis/stream"); // respuesta real del backend para que el hilo tenga historial
  await page.goto("/app/#/atencion");
  await page.getByLabel("Mensaje para IGNIS").fill("Hola, buenas tardes.");
  await page.keyboard.press("Enter");
  await expect(page.locator(".ignis-insignia.ruta").last()).toContainText("Directo");

  await page.goto("/app/#/sesion");
  const fila = page.locator("tbody tr").first();
  await expect(fila).toContainText("Hola, buenas tardes.");
  await fila.getByRole("button", { name: /Reabrir/ }).click();
  await expect(page).toHaveURL(/#\/atencion$/);
  await expect(page.locator(".ignis-nota").first()).toContainText("Hilo reabierto");
  await expect(page.locator(".ignis-burbuja.usuario").first()).toContainText("Hola, buenas tardes.");

  await page.getByRole("button", { name: "Cerrar sesión" }).first().click();
  await expect(page.getByRole("heading", { name: "Entrar a IGNIS" })).toBeVisible();
});
