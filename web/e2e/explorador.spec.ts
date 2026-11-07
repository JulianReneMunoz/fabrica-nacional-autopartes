import { expect, test, type Page } from "@playwright/test";
import { mkdirSync } from "node:fs";
import { resolve } from "node:path";

/**
 * Fase 14 — «Explorador de la motocicleta» (#/maquina/moto_honda/explorador, alias #/explorador).
 * Capturas a 1920×1080: por omisión en test-results/ (no versionado); con FNA_CAPTURAS=1 en docs/capturas/explorador.
 */
const CAPTURAS = process.env.FNA_CAPTURAS === "1" ? resolve("../docs/capturas/explorador") : resolve("test-results/capturas/explorador");
mkdirSync(CAPTURAS, { recursive: true });

type Gancho = { piezas: () => number; contorno: (id: string) => boolean; fueraDeCuadro: () => string[] };
const gancho = (page: Page) => page.evaluate(() => Boolean((window as unknown as { __moto3d?: Gancho }).__moto3d));
const piezas = (page: Page) => page.evaluate(() => (window as unknown as { __moto3d?: Gancho }).__moto3d?.piezas() ?? 0);
const contorno = (page: Page, id: string) => page.evaluate((i) => (window as unknown as { __moto3d: Gancho }).__moto3d.contorno(i), id);
const fuera = (page: Page) => page.evaluate(() => (window as unknown as { __moto3d: Gancho }).__moto3d.fueraDeCuadro());
const raiz = (page: Page) => page.getByTestId("explorador-moto");
const PROHIBIDOS = /precio|disponibilidad|disponible|stock|carrito|referencia de repuesto|n\.º de parte|número de parte|\$\s?\d/i;

function vigilarConsola(page: Page) {
  const errores: string[] = [];
  page.on("pageerror", (e) => errores.push(e.message));
  page.on("console", (m) => m.type() === "error" && errores.push(m.text()));
  return errores;
}

async function abrir(page: Page, ruta = "/app/#/explorador") {
  await page.goto(ruta);
  await expect(page.getByTestId("escenario-explorador").locator("canvas")).toBeVisible();
  await expect.poll(() => gancho(page)).toBe(true);
  await expect.poll(() => piezas(page)).toBe(79);
  await expect(page.locator(".franja-sistemas button[data-sistema]")).toHaveCount(10);
  await page.waitForTimeout(1500); // encuadre inicial
}

/** Centro en pantalla del punto de la etiqueta (cae sobre la pieza ancla). */
async function puntoEtiqueta(page: Page, clave: string) {
  const escenario = await page.getByTestId("escenario-explorador").boundingBox();
  const punto = page.locator(".guias-etiquetas g").filter({ has: page.locator(`line[data-guia="${clave}"]`) }).locator("circle");
  const cx = Number(await punto.getAttribute("cx"));
  const cy = Number(await punto.getAttribute("cy"));
  return { x: escenario!.x + cx, y: escenario!.y + cy };
}

async function medirFps(page: Page, ms = 3000) {
  return page.evaluate(
    (dur) =>
      new Promise<number>((ok) => {
        let n = 0;
        const t0 = performance.now();
        const f = () => {
          n++;
          if (performance.now() - t0 < dur) requestAnimationFrame(f);
          else ok((n * 1000) / (performance.now() - t0));
        };
        requestAnimationFrame(f);
      }),
    ms,
  );
}

test("explorador: «Explorar piezas» en la tarjeta de la moto, navegación y ruta completa", async ({ page }) => {
  const errores = vigilarConsola(page);
  await page.goto("/app/#/");
  await expect(page.locator("article.tarjeta")).toHaveCount(4); // sin tarjeta propia
  const explorar = page.locator('article[data-maquina="moto_honda"]').getByRole("link", { name: "Explorar piezas" });
  await expect(explorar).toHaveAttribute("href", "#/explorador");
  await explorar.click();
  await expect(raiz(page)).toBeVisible();
  await expect(page.locator('header nav a[aria-current="page"]')).toHaveText("Explorador");
  await abrir(page, "/app/#/maquina/moto_honda/explorador");
  await expect(raiz(page)).toBeVisible();
  expect(errores).toEqual([]);
});

test("explorador: hover con contorno; clic en 3D selecciona el sistema, lo encuadra y muestra el panel", async ({ page }) => {
  const errores = vigilarConsola(page);
  await abrir(page);
  // Las once etiquetas de sistema existen; las visibles llevan su punto sobre la pieza.
  await expect(page.locator(".etiqueta-sistema")).toHaveCount(11);
  const visibles = await page.locator(".etiqueta-sistema").evaluateAll((els) => els.filter((e) => (e as HTMLElement).style.visibility === "visible").length);
  expect(visibles).toBeGreaterThanOrEqual(8);

  // Hover: contorno tenue de la pieza bajo el cursor (punto de la etiqueta «Asiento», sobre el sillín).
  const pSillin = await puntoEtiqueta(page, "asiento");
  await page.mouse.move(pSillin.x, pSillin.y, { steps: 3 });
  await expect(page.locator(".leyenda-escena")).toContainText("Bajo el cursor: Sillín");
  await expect.poll(() => contorno(page, "sillin")).toBe(true);

  // Clic en 3D sobre el motor (punto de la etiqueta «Motor», sobre el cilindro).
  const pMotor = await puntoEtiqueta(page, "motor");
  await page.mouse.click(pMotor.x, pMotor.y);
  await expect.poll(() => contorno(page, "sillin")).toBe(false); // el hover cede al contorno del sistema
  await expect(raiz(page)).toHaveAttribute("data-sistema", /.+/);
  const sistema = await raiz(page).getAttribute("data-sistema");
  await expect(page.getByTestId("panel-sistema")).toHaveAttribute("data-sistema", sistema!);
  await page.waitForTimeout(1500); // transición de cámara
  // Ninguna pieza del sistema queda fuera de cuadro tras el encuadre.
  const ids = await page.locator(".piezas-sistema button[data-pieza]").evaluateAll((b) => b.map((x) => x.getAttribute("data-pieza")!));
  const salen = await fuera(page);
  expect(ids.filter((i) => salen.includes(i))).toEqual([]);
  expect(await contorno(page, ids[0])).toBe(true);
  expect(errores).toEqual([]);
});

test("explorador: teclado (Tab y Enter), buscador, pregunta con citas o rechazo y lección relacionada", async ({ page }) => {
  const errores = vigilarConsola(page);
  await abrir(page);
  // Franja: foco visible y Enter selecciona.
  const motor = page.locator('.franja-sistemas button[data-sistema="motor"]');
  await motor.focus();
  await page.keyboard.press("Enter");
  await expect(raiz(page)).toHaveAttribute("data-sistema", "motor");
  await expect(motor).toHaveAttribute("aria-pressed", "true");
  const contornoFoco = await motor.evaluate((b) => getComputedStyle(b).outlineStyle);
  expect(contornoFoco).not.toBe("none");
  // Etiqueta 3D: también es un botón operable con teclado, aun con otro sistema seleccionado.
  await page.locator('[data-etiqueta="escape"] button').focus();
  await page.keyboard.press("Enter");
  await expect(raiz(page)).toHaveAttribute("data-sistema", "escape");
  await page.keyboard.press("Escape");
  await expect(raiz(page)).toHaveAttribute("data-sistema", "");

  // Buscador: Enter elige el primer resultado, selecciona y encuadra la pieza.
  await page.locator("#buscador-piezas").fill("bujia");
  await page.keyboard.press("Enter");
  await expect(raiz(page)).toHaveAttribute("data-sistema", "motor");
  await expect(page.locator(".piezas-sistema li.activa button")).toHaveAttribute("data-pieza", "bujia");
  await expect.poll(() => contorno(page, "bujia")).toBe(true);

  // Pregunta sobre la pieza (backend real): respuesta del modelo + citas, o la frase de rechazo.
  await page.getByTestId("preguntar-pieza").click();
  const r = page.getByTestId("respuesta-pieza");
  await expect(r).toBeVisible();
  const citas = await r.locator("ul.datos li a").count();
  if (citas === 0) await expect(page.getByTestId("rechazo")).toHaveText("La información solicitada no se encuentra en la base de conocimiento de Fanalca.");
  else await expect(r.locator("ul.datos li a").first()).toHaveAttribute("href", /fanalca/);

  // Lección: motor → corte y ciclo 4T en la máquina de la moto.
  await page.getByTestId("ver-leccion").click();
  await expect(page).toHaveURL(/#\/maquina\/moto_honda\?vista=corte/);
  await expect(page.getByRole("button", { name: /Sección/ })).toHaveAttribute("aria-pressed", "true");
  expect(errores).toEqual([]);
});

test("explorador: sin datos comerciales; responsivo; ≥ 50 fps", async ({ page }) => {
  await abrir(page);
  for (const id of ["motor", "transmision", "frenos", "suspension", "iluminacion", "electrico", "carroceria", "ruedas", "escape", "direccion"]) {
    await page.locator(`.franja-sistemas button[data-sistema="${id}"]`).click();
    const texto = await page.locator("main").innerText();
    expect(texto.match(PROHIBIDOS)?.[0] ?? null).toBeNull();
  }
  await page.locator('.selector-vista [data-vista="interactiva"]').click();
  await page.keyboard.press("Escape");
  await page.waitForTimeout(800);
  const fps = await medirFps(page);
  test.info().annotations.push({ type: "fps", description: fps.toFixed(1) });
  console.log(`FPS explorador (SwiftShader, 1440×900): ${fps.toFixed(1)}`);
  expect(fps).toBeGreaterThanOrEqual(50);
  // Pantalla estrecha: el panel pasa debajo del lienzo.
  await page.setViewportSize({ width: 900, height: 900 });
  await page.waitForTimeout(400);
  const lienzo = await page.locator(".lienzo-col").boundingBox();
  const lateral = await page.locator(".lateral-col").boundingBox();
  expect(lateral!.y).toBeGreaterThan(lienzo!.y + lienzo!.height - 5);
});

test("explorador: capturas 1920×1080 (interactiva con el motor, explosión y lista de partes)", async ({ page }) => {
  await page.setViewportSize({ width: 1920, height: 1080 });
  await abrir(page);
  await page.locator('.franja-sistemas button[data-sistema="motor"]').click();
  await page.waitForTimeout(2200);
  await page.screenshot({ path: `${CAPTURAS}/01_interactiva_motor.png` });
  await page.keyboard.press("Escape");
  await page.locator('.selector-vista [data-vista="explosion"]').click();
  await expect(raiz(page)).toHaveAttribute("data-vista", "explosion");
  await page.waitForTimeout(2500);
  expect(await fuera(page)).toEqual([]);
  await page.screenshot({ path: `${CAPTURAS}/02_explosion.png` });
  await page.locator('.selector-vista [data-vista="partes"]').click();
  await expect(page.getByTestId("lista-partes")).toBeVisible();
  await expect(page.locator('[data-testid="lista-partes"] button[data-pieza]')).toHaveCount(79);
  await page.waitForTimeout(400);
  await page.screenshot({ path: `${CAPTURAS}/03_partes.png` });
});
