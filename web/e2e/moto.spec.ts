import { expect, test, type Page } from "@playwright/test";
import { mkdirSync } from "node:fs";
import { resolve } from "node:path";

/** Capturas del visor de la moto para el manual (docs/latex/figuras). */
const FIGURAS = resolve("../docs/latex/figuras");
mkdirSync(FIGURAS, { recursive: true });

function vigilarConsola(page: Page) {
  const errores: string[] = [];
  page.on("pageerror", (e) => errores.push(e.message));
  page.on("console", (m) => m.type() === "error" && errores.push(m.text()));
  return errores;
}

const FAQ_FALSA = {
  generado: "2026-11-05T00:00:00+00:00",
  proveedor: "simulado",
  modelo: "prueba",
  version_prompt: "v3",
  advertencia: "Respuestas de prueba (proveedor simulado).",
  total: 2,
  items: [
    {
      id: "q1",
      categoria: "sede",
      pregunta: "¿Dónde queda la sede principal de Fanalca?",
      respuesta: "La sede principal está en Cali [f1].",
      rechazo: false,
      fundamentada: true,
      confianza: "alta",
      fuentes: [{ fragmento_id: "f1", url: "https://fanalca.com/" }],
    },
    {
      id: "q2",
      categoria: "fuera",
      pregunta: "¿Cuál es el clima de Marte?",
      respuesta: "La información solicitada no se encuentra en la base de conocimiento de Fanalca.",
      rechazo: true,
      fundamentada: false,
      confianza: "ninguna",
      fuentes: [],
    },
  ],
};

async function abrir(page: Page, ruta = "/app/#/maquina/moto_honda", faqSimulada = true) {
  if (faqSimulada) await page.route("**/api/v1/faq-visor", (r) => r.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(FAQ_FALSA) }));
  await page.goto(ruta);
  await expect(page.getByTestId("escenario-moto").locator("canvas")).toBeVisible();
  await expect(page.locator(".ficha-tecnica")).toBeVisible();
  await expect(page.locator(".lista-piezas, .pestanas-panel").first()).toBeVisible();
  await page.waitForTimeout(1800);
}

test("moto: carga sin errores de consola, cabecera, escala de cámara lenta y alias #/moto", async ({ page }) => {
  const errores = vigilarConsola(page);
  await abrir(page, "/app/#/moto");
  await expect(page.getByTestId("cab-nombre")).toContainText("referencia genérica");
  await expect(page.getByTestId("estado")).toHaveText("EN MARCHA");
  await expect(page.getByTestId("escala-lenta")).toContainText("animación a 1/200 de la velocidad real");
  await expect(page.getByTestId("idea-principal")).toContainText("el freno invierte el camino");
  await expect(page.getByTestId("lista-supuestos")).toContainText("supuesto didáctico");
  await page.screenshot({ path: `${FIGURAS}/moto_01_general.png` });
  expect(errores).toEqual([]);
});

test("moto: controles de acelerador y marcha actualizan velocidad, relación y etiquetas 3D", async ({ page }) => {
  const errores = vigilarConsola(page);
  await abrir(page);
  await page.getByRole("radio", { name: "3", exact: true }).click();
  await page.getByLabel("Acelerador").fill("6000");
  await expect(page.getByTestId("cab-marcha")).toHaveText("3.ª");
  await expect(page.getByTestId("cab-rpm")).toHaveText("6.000");
  const v = await page.getByTestId("cab-velocidad").innerText();
  expect(parseFloat(v.replace(",", "."))).toBeGreaterThan(40);
  await expect(page.locator('[data-etiqueta="rueda"]')).toContainText("km/h");
  await expect(page.locator('[data-etiqueta="transmision"]')).toContainText("m/s");
  // La cadena avanza a la misma velocidad lineal vista desde el piñón y desde la corona.
  const cp = await page.getByTestId("v-cadena-pinon").innerText();
  const cc = await page.getByTestId("v-cadena-corona").innerText();
  expect(cp).toBe(cc);
  await expect(page.getByTestId("verificacion-api")).toContainText("API verificada");
  await page.screenshot({ path: `${FIGURAS}/moto_02_corte_motor.png` });
  expect(errores).toEqual([]);
});

test("moto: «Ver con ficha de…» cambia la llanta a 140/70-17 y el radio", async ({ page }) => {
  const errores = vigilarConsola(page);
  await abrir(page);
  await expect(page.getByTestId("nota-ficha")).toContainText("130/70-17");
  await page.getByRole("radio", { name: "3", exact: true }).click();
  await page.getByLabel("Acelerador").fill("6000");
  const vGenerica = parseFloat((await page.getByTestId("cab-velocidad").innerText()).replace(",", "."));
  await page.getByLabel("Ver con ficha de…").selectOption("dlx");
  await expect(page.getByTestId("nota-ficha")).toContainText("140/70-17");
  await expect(page.locator(".lecturas")).toContainText("0,3139");
  const vFicha = parseFloat((await page.getByTestId("cab-velocidad").innerText()).replace(",", "."));
  expect(vFicha).toBeGreaterThan(vGenerica);
  await expect(page.getByTestId("cab-version")).toHaveText("DLX");
  expect(errores).toEqual([]);
});

test("moto: ficha técnica con «No publicado», resaltado de pieza y FAQ de modelos", async ({ page }) => {
  const errores = vigilarConsola(page);
  await abrir(page);
  const ficha = page.locator(".ficha-tecnica");
  await expect(ficha).toContainText("No publicado");
  await expect(ficha).toContainText("lamina-cb160-std-dlx");
  await expect(ficha).toContainText("consulta 2026-11-04");
  await ficha.locator('button[data-campo="llantas.trasera"]').click();
  await expect(ficha.locator('button[data-campo="llantas.trasera"]')).toHaveAttribute("aria-pressed", "true");
  await page.getByRole("tab", { name: "FAQ modelos" }).click();
  const pregunta = page.locator('[data-faq-modelo="potencia"] summary');
  await pregunta.click();
  await expect(page.locator('[data-faq-modelo="potencia"]')).toContainText("No publicado");
  await page.getByRole("tab", { name: "Ficha técnica" }).click();
  await page.screenshot({ path: `${FIGURAS}/moto_04_ficha_faq.png` });
  expect(errores).toEqual([]);
});

test("moto: FAQ Fanalca precalculada (simulada), 404 con mensaje y pregunta en vivo simulada", async ({ page }) => {
  await page.route("**/api/v1/tareas/qa", (r) =>
    r.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ pregunta: "x", respuesta: "Respuesta simulada [f9].", fuentes: [{ fragmento_id: "f9", titulo: "t", url: "https://fanalca.com/x" }], fundamentada: true, confianza: "media", proveedor: "simulado", modelo: "m" }),
    }),
  );
  await abrir(page);
  await page.getByRole("tab", { name: "FAQ Fanalca" }).click();
  await page.locator('[data-faq-fanalca="q1"] summary').click();
  await expect(page.locator('[data-faq-fanalca="q1"]')).toContainText("https://fanalca.com/");
  await page.locator('[data-faq-fanalca="q2"] summary').click();
  await expect(page.locator('[data-faq-fanalca="q2"]')).toContainText("no se encuentra en la base de conocimiento");
  await page.getByLabel("Pregunta sobre Fanalca").fill("¿Dónde queda la planta?");
  await page.getByRole("button", { name: "Preguntar en vivo" }).click();
  await expect(page.getByTestId("respuesta-en-vivo")).toContainText("Respuesta simulada");
});

test("moto: FAQ Fanalca sin archivo (404) muestra el comando y no rompe", async ({ page }) => {
  const errores: string[] = [];
  page.on("pageerror", (e) => errores.push(e.message));
  await page.route("**/api/v1/faq-visor", (r) => r.fulfill({ status: 404, contentType: "application/json", body: JSON.stringify({ detail: "Aún no se generó faq_visor.json" }) }));
  await page.goto("/app/#/maquina/moto_honda");
  await expect(page.getByTestId("escenario-moto").locator("canvas")).toBeVisible();
  await page.getByRole("tab", { name: "FAQ Fanalca" }).click();
  await expect(page.getByTestId("faq-sin-archivo")).toContainText("uv run fabrica faq-visor");
  expect(errores).toEqual([]);
});

test("moto: despiece, corte del motor y ensamblajes", async ({ page }) => {
  const errores = vigilarConsola(page);
  await abrir(page);
  await page.getByRole("tab", { name: "Vista" }).click();
  await page.getByLabel("Despiece por ensamblaje").check();
  await expect(page.getByTestId("estado")).toHaveText("DESPIECE", { timeout: 10_000 });
  await page.waitForTimeout(5500);
  await page.screenshot({ path: `${FIGURAS}/moto_03_despiece.png` });
  await page.getByLabel("Despiece por ensamblaje").uncheck();
  await page.waitForTimeout(5500);
  await page.getByLabel("Corte del motor").check();
  await page.waitForTimeout(3000);
  await page.screenshot({ path: `${FIGURAS}/moto_02_corte_motor.png` });
  await page.getByLabel("Corte del motor").uncheck();
  await page.getByRole("tab", { name: "Ensamblajes" }).click();
  await page.locator('button[data-ensamblaje="motor"]').click();
  await page.locator('button[data-pieza="piston"]').click();
  await expect(page.getByTestId("ficha-nombre")).toContainText(/pist/i);
  expect(errores).toEqual([]);
});

test("moto: frenado con CBS y modo experimento (limitador, ahogo, bloqueo)", async ({ page }) => {
  const errores = vigilarConsola(page);
  await abrir(page);
  await page.getByLabel("Ver con ficha de…").selectOption("dlx");
  await page.getByRole("radio", { name: "3", exact: true }).click();
  await page.getByLabel("Acelerador").fill("5000");
  await page.getByRole("radio", { name: "Palanca trasera" }).click();
  await page.getByLabel("Fuerza en la palanca").fill("180");
  await page.getByLabel("CBS (freno combinado)").check();
  await page.getByRole("button", { name: "Frenar", exact: true }).click();
  await expect(page.getByTestId("estado")).toHaveText("FRENANDO");
  await expect(page.locator('[data-etiqueta="disco_del"]')).toContainText("kN");
  await expect(page.locator('[data-etiqueta="disco_tras"]')).toContainText("kN");
  await page.waitForTimeout(1200);
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({ path: `${FIGURAS}/moto_05_frenado_cbs.png` });
  await page.getByRole("button", { name: "Soltar freno" }).click();

  const ejecutar = async (indice: number, opcion: number) => {
    const exp = page.locator(".experimento");
    for (let i = 0; i < indice; i++) await exp.getByRole("button", { name: "Siguiente" }).click();
    await exp.locator(".opciones button").nth(opcion).click();
    await exp.getByRole("button", { name: "Ejecutar y comparar" }).click();
    await expect(exp.locator("[role=status]")).toContainText("Predicción correcta");
  };
  await ejecutar(0, 1); // limitador
  await expect(page.getByTestId("estado")).toHaveText("LIMITADOR");
  await expect(page.locator(".lecturas")).toContainText("limitador");
  await page.locator(".experimento").getByRole("button", { name: "Siguiente" }).click();
  await page.locator(".experimento .opciones button").nth(1).click();
  await page.getByRole("button", { name: "Ejecutar y comparar" }).click();
  await expect(page.getByTestId("estado")).toHaveText("MOTOR AHOGADO");
  await expect(page.getByTestId("cab-velocidad")).toContainText("0,0");
  await page.locator(".experimento").getByRole("button", { name: "Siguiente" }).click();
  await page.locator(".experimento .opciones button").nth(0).click();
  await page.getByRole("button", { name: "Ejecutar y comparar" }).click();
  await expect(page.locator(".lecturas")).toContainText("rueda bloqueada");
  await expect(page.locator('[data-etiqueta="disco_del"]')).toContainText("BLOQUEADA");
  expect(errores).toEqual([]);
});

test("moto: secuencia, cajones en pantalla estrecha", async ({ page }) => {
  const errores = vigilarConsola(page);
  await abrir(page);
  await page.getByRole("button", { name: "▶ Reproducir secuencia" }).click();
  await expect(page.locator(".pasos-secuencia li.actual")).toBeVisible();
  await page.setViewportSize({ width: 820, height: 900 });
  await expect(page.getByRole("button", { name: /Ficha ☰/ })).toBeVisible();
  await page.getByRole("button", { name: /Ficha ☰/ }).click();
  await expect(page.locator(".moto-columna.der.cajon-abierto")).toBeVisible();
  expect(errores).toEqual([]);
});

test("moto: recorrido automático ?tour=1 termina en menos de 30 s sin errores (sin grabar video)", async ({ page }) => {
  const errores = vigilarConsola(page);
  await page.route("**/api/v1/faq-visor", (r) => r.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(FAQ_FALSA) }));
  await page.goto("/app/#/maquina/moto_honda?tour=1");
  await page.waitForFunction(() => window.__tour?.estado === "corriendo", null, { timeout: 20_000 });
  const t0 = Date.now();
  await expect(page.locator(".tour-banda")).toContainText("Motocicleta de referencia");
  await page.waitForFunction(() => window.__tour?.estado === "terminado", null, { timeout: 40_000 });
  expect((Date.now() - t0) / 1000).toBeLessThan(30.5);
  expect(errores).toEqual([]);
});
