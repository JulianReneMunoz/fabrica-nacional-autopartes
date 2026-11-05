import { expect, test, type Page } from "@playwright/test";
import { mkdirSync } from "node:fs";
import { resolve } from "node:path";

/**
 * Capturas del visor de la moto. Por omisión se escriben en test-results/ (no versionado);
 * con FNA_CAPTURAS=1 se escriben en docs/latex/figuras para el manual.
 */
const FIGURAS = process.env.FNA_CAPTURAS === "1" ? resolve("../docs/latex/figuras") : resolve("test-results/capturas");
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
  await page.waitForTimeout(1800);
}

const numero = (t: string) => parseFloat(t.replace(/\./g, "").replace(",", ".").replace(/[^0-9.\-]/g, ""));
const velocidad = async (page: Page) => numero(await page.getByTestId("cab-velocidad").innerText());
const rpm = async (page: Page) => numero(await page.getByTestId("cab-rpm").innerText());
const marcha = (page: Page, m: number) => page.locator(`[data-marcha="${m}"]`).click();
const acelerador = (page: Page, pct: number) => page.getByLabel("Acelerador").fill(String(pct));

/** Arranca en 1.ª con el acelerador a fondo hasta superar `kmh` (el limitador de 1.ª llega a unos 39 km/h). */
async function acelerarHasta(page: Page, kmh: number) {
  await marcha(page, 1);
  await acelerador(page, 100);
  await expect.poll(() => velocidad(page), { timeout: 20_000 }).toBeGreaterThan(kmh);
}

test("moto: carga sin errores de consola, cabecera, escala de cámara lenta y alias #/moto", async ({ page }) => {
  const errores = vigilarConsola(page);
  await abrir(page, "/app/#/moto");
  await expect(page.getByTestId("cab-nombre")).toContainText("referencia genérica");
  await expect(page.getByTestId("estado")).toHaveText("EN MARCHA");
  await expect(page.getByTestId("escala-lenta")).toContainText("animación a 1/200 de la velocidad real");
  await expect(page.getByTestId("escenario-moto")).toContainText("dinámica del frenado en tiempo real");
  await expect(page.getByTestId("idea-principal")).toContainText("el freno invierte el camino");
  await expect(page.getByTestId("lista-supuestos")).toContainText("supuesto didáctico");
  await expect(page.locator('[data-etiqueta="cilindrada"]')).toContainText("150 cm³ nominal — supuesto didáctico");
  expect(await page.locator("body").innerText()).not.toContain("15,04");
  await page.screenshot({ path: `${FIGURAS}/moto_01_general.png` });
  expect(errores).toEqual([]);
});

test("moto: A2 cambiar de marcha salta las rpm, no la velocidad; la cadena sigue a ω·r", async ({ page }) => {
  const errores = vigilarConsola(page);
  await abrir(page);
  await acelerarHasta(page, 15);
  const v1 = await velocidad(page);
  const rpm1 = await rpm(page);
  await marcha(page, 3);
  const rpm3 = await rpm(page);
  const v3 = await velocidad(page);
  expect(Math.abs(v3 - v1)).toBeLessThan(2.5); // solo avanza lo que dura el clic: la velocidad no salta
  expect(rpm3).toBeLessThan(rpm1 * 0.65); // 3.ª es una relación más larga: las rpm bajan de golpe
  // rpm = v·i_total·60/(2π·R) con R = 0,3069 m (130/70-17 genérica) e i_total(3.ª) = 3,35·1,40·3,00
  const esperada = ((v3 / 3.6 / 0.3069) * 3.35 * 1.4 * 3 * 60) / (2 * Math.PI);
  expect(Math.abs(rpm3 - esperada) / esperada).toBeLessThan(0.04);
  await expect(page.locator('[data-etiqueta="rueda"]')).toContainText("km/h");
  // v_cadena = ω_corona·r_corona con ω_corona = v/R
  const cadena = numero(await page.getByTestId("v-cadena-corona").innerText());
  expect(Math.abs(cadena - (v3 / 3.6 / 0.3069) * 0.09)).toBeLessThan(0.12);
  await expect(page.getByTestId("verificacion-api")).toContainText("API verificada");
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({ path: `${FIGURAS}/moto_06_cambio_marcha.png` });
  expect(errores).toEqual([]);
});

test("moto: A3 el neutro no detiene la moto en seco; las rpm son libres y se rotula «sin tracción»", async ({ page }) => {
  await abrir(page);
  await acelerarHasta(page, 15);
  await marcha(page, 0);
  const v0 = await velocidad(page);
  await page.waitForTimeout(1500);
  const v1 = await velocidad(page);
  expect(v1).toBeGreaterThan(v0 * 0.7); // decae por rozamiento, sin parar en seco
  expect(v1).toBeLessThan(v0 + 0.01);
  expect(v1).toBeGreaterThan(5);
  await expect(page.getByTestId("cab-marcha")).toHaveText("N");
  await expect(page.locator(".lecturas")).toContainText("sin tracción (neutro)");
  await expect(page.locator(".datos-vivo")).toContainText("sin tracción: neutro");
  await acelerador(page, 40);
  await expect.poll(() => rpm(page)).toBeGreaterThan(4000); // rpm libres siguen al acelerador
  await acelerador(page, 0);
  await expect.poll(() => rpm(page)).toBeLessThan(1700);
});

test("moto: A4 soltar el freno tras DETENIDA parte de la velocidad actual; el embrague se muestra en la cabecera", async ({ page }) => {
  const errores = vigilarConsola(page);
  await abrir(page);
  await acelerarHasta(page, 15);
  await acelerador(page, 0);
  await page.getByLabel("Ver con ficha de…").selectOption("dlx");
  await page.getByRole("radio", { name: "Palanca trasera" }).click();
  await page.getByLabel("Fuerza en la palanca").fill("300");
  await page.getByLabel("CBS (freno combinado)").check();
  await page.getByRole("button", { name: "Frenar", exact: true }).click();
  await expect(page.getByTestId("estado")).toHaveText("FRENANDO");
  await expect(page.getByTestId("cab-embrague")).toContainText("EMBRAGUE");
  await expect.poll(() => velocidad(page), { timeout: 30_000 }).toBeLessThan(0.05); // v monótona hasta 0
  await expect(page.getByTestId("estado")).toHaveText("DETENIDA");
  await page.getByRole("button", { name: "Soltar freno" }).click();
  expect(await velocidad(page)).toBeLessThan(0.5); // no recupera la velocidad anterior
  await expect(page.getByTestId("estado")).not.toHaveText("FRENANDO");
  await expect(page.getByTestId("cab-embrague")).not.toContainText("EMBRAGUE");
  // vuelve a arrancar desde cero con marcha engranada (el embrague patina)
  await acelerador(page, 100);
  await expect.poll(() => velocidad(page), { timeout: 20_000 }).toBeGreaterThan(5);
  expect(errores).toEqual([]);
});

test("moto: «Ver con ficha de…» cambia la llanta a 140/70-17 y el radio", async ({ page }) => {
  const errores = vigilarConsola(page);
  await abrir(page);
  await expect(page.getByTestId("nota-ficha")).toContainText("130/70-17");
  await expect(page.locator(".lecturas")).toContainText("0,3069");
  await acelerarHasta(page, 10);
  await page.getByLabel("Ver con ficha de…").selectOption("dlx");
  await expect(page.getByTestId("nota-ficha")).toContainText("140/70-17");
  await expect(page.locator(".lecturas")).toContainText("0,3139");
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
  expect(await ficha.innerText()).not.toContain("15,04");
  await ficha.locator('button[data-campo="llantas.trasera"]').click();
  await expect(ficha.locator('button[data-campo="llantas.trasera"]')).toHaveAttribute("aria-pressed", "true");
  await expect(page.getByTestId("moto-lab")).toHaveAttribute("data-resaltadas", /llanta_trasera/);
  await page.getByRole("tab", { name: "FAQ modelos" }).click();
  await page.locator('[data-faq-modelo="potencia"] summary').click();
  await expect(page.locator('[data-faq-modelo="potencia"]')).toContainText("No publicado");
  expect(await page.locator('[data-faq-modelo="potencia"]').innerText()).not.toContain("15,04");
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

test("moto: A5 con la palanca cargada y sin frenar no hay BLOQUEADA; al frenar se bloquea; frenado con CBS", async ({ page }) => {
  const errores = vigilarConsola(page);
  await abrir(page);
  await page.getByLabel("Fuerza en la palanca").fill("400");
  await expect(page.locator('[data-etiqueta="disco_del"]')).toContainText("previsto");
  await expect(page.locator('[data-etiqueta="disco_del"]')).not.toContainText("BLOQUEADA");
  await expect(page.locator(".lecturas")).not.toContainText("rueda bloqueada");
  await acelerarHasta(page, 20);
  await expect(page.locator(".lecturas")).toContainText("bloqueo previsto"); // aún sin frenar
  await expect(page.locator('[data-etiqueta="disco_del"]')).not.toContainText("BLOQUEADA");
  await page.getByRole("button", { name: "Frenar", exact: true }).click();
  await expect(page.locator('[data-etiqueta="disco_del"]')).toContainText("BLOQUEADA");
  await expect(page.locator(".lecturas")).toContainText("rueda bloqueada");
  await page.getByRole("button", { name: "Soltar freno" }).click();
  // frenado con CBS para la captura
  await page.getByLabel("Ver con ficha de…").selectOption("dlx");
  await acelerador(page, 100);
  await expect.poll(() => velocidad(page), { timeout: 20_000 }).toBeGreaterThan(25);
  await page.getByRole("radio", { name: "Palanca trasera" }).click();
  await page.getByLabel("Fuerza en la palanca").fill("180");
  await page.getByLabel("CBS (freno combinado)").check();
  await page.getByRole("button", { name: "Frenar", exact: true }).click();
  await expect(page.getByTestId("estado")).toHaveText("FRENANDO");
  await expect(page.locator('[data-etiqueta="disco_del"]')).toContainText("kN");
  await expect(page.locator('[data-etiqueta="disco_tras"]')).toContainText("kN");
  await page.waitForTimeout(800);
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({ path: `${FIGURAS}/moto_05_frenado_cbs.png` });
  expect(errores).toEqual([]);
});

test("moto: A6 con la STD el freno trasero se marca como disco genérico (supuesto didáctico)", async ({ page }) => {
  await abrir(page);
  await page.getByLabel("Ver con ficha de…").selectOption("std");
  await expect(page.getByTestId("nota-ficha")).toContainText("frenos.STD.trasero");
  await page.getByLabel("Fuerza en la palanca").fill("100");
  await page.getByRole("radio", { name: "Palanca trasera" }).click();
  await expect(page.locator('[data-etiqueta="disco_tras"]')).toContainText("disco genérico — supuesto didáctico");
  await expect(page.getByLabel("CBS (freno combinado)")).toBeDisabled();
});

test("moto: A8 el limitador suprime la chispa en ciclos alternos; sin limitador salta en todos", async ({ page }) => {
  await abrir(page);
  await page.getByLabel("Factor de cámara lenta").selectOption("50"); // ciclos más rápidos para la prueba
  const contadores = async () => {
    const lab = page.getByTestId("moto-lab");
    return { chispas: Number(await lab.getAttribute("data-chispas")), ciclos: Number(await lab.getAttribute("data-ciclos")) };
  };
  await acelerador(page, 40); // neutro, ~5.200 rpm: sin limitador
  await page.waitForTimeout(600);
  const a0 = await contadores();
  await page.waitForTimeout(6000);
  const a1 = await contadores();
  const ciclosNormal = a1.ciclos - a0.ciclos;
  expect(ciclosNormal).toBeGreaterThanOrEqual(4);
  expect(Math.abs(a1.chispas - a0.chispas - ciclosNormal)).toBeLessThanOrEqual(1); // una chispa por ciclo
  await acelerador(page, 100); // sobre el corte
  await expect(page.getByTestId("estado")).toHaveText("LIMITADOR");
  await page.waitForTimeout(600);
  const b0 = await contadores();
  await page.waitForTimeout(6000);
  const b1 = await contadores();
  const ciclosLim = b1.ciclos - b0.ciclos;
  expect(ciclosLim).toBeGreaterThanOrEqual(6);
  const chispasLim = b1.chispas - b0.chispas;
  expect(chispasLim).toBeGreaterThanOrEqual(ciclosLim / 2 - 1);
  expect(chispasLim).toBeLessThanOrEqual(ciclosLim / 2 + 1); // ciclos alternos: la mitad
});

test("moto: modo experimento (limitador, ahogo, bloqueo)", async ({ page }) => {
  const errores = vigilarConsola(page);
  await abrir(page);
  const exp = page.locator(".experimento");
  const ejecutar = async (opcion: number) => {
    await exp.locator(".opciones button").nth(opcion).click();
    await exp.getByRole("button", { name: "Ejecutar y comparar" }).click();
    await expect(exp.locator("[role=status]")).toContainText("Predicción correcta");
  };
  await ejecutar(1); // limitador: v estabilizada en el corte
  await expect(page.getByTestId("estado")).toHaveText("LIMITADOR", { timeout: 15_000 });
  await expect(page.locator(".lecturas")).toContainText("limitador");
  const vLimite = await velocidad(page);
  await page.waitForTimeout(1500);
  expect(Math.abs((await velocidad(page)) - vLimite)).toBeLessThan(1.5); // se estabiliza
  await exp.getByRole("button", { name: "Siguiente" }).click();
  await ejecutar(0); // ahogo en 5.ª a baja velocidad
  await expect(page.getByTestId("estado")).toHaveText("MOTOR AHOGADO");
  await expect(page.getByTestId("cab-rpm")).toHaveText("0");
  await exp.getByRole("button", { name: "Siguiente" }).click();
  await ejecutar(0); // bloqueo
  await expect(page.locator(".lecturas")).toContainText("rueda bloqueada");
  await expect(page.locator('[data-etiqueta="disco_del"]')).toContainText("BLOQUEADA");
  expect(errores).toEqual([]);
});

test("moto: A15 «Frenar» con 0 N avisa de la fuerza mínima aplicada", async ({ page }) => {
  await abrir(page);
  await acelerarHasta(page, 10);
  await page.getByRole("button", { name: "Frenar", exact: true }).click();
  await expect(page.getByTestId("aviso-freno")).toContainText("160 N");
  await expect(page.getByTestId("estado")).toHaveText("FRENANDO");
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

test("moto: rendimiento ≥ 50 fps con SwiftShader (79 piezas, PBR, sombras y entorno de estudio)", async ({ page }) => {
  await abrir(page);
  await expect.poll(() => page.evaluate(() => (window as unknown as { __moto3d?: { piezas: () => number } }).__moto3d?.piezas())).toBe(79);
  await marcha(page, 1);
  await acelerador(page, 60);
  await page.waitForTimeout(1500);
  const fps = await medirFps(page);
  test.info().annotations.push({ type: "fps", description: fps.toFixed(1) });
  console.log(`FPS moto (SwiftShader, 1440×900): ${fps.toFixed(1)}`);
  expect(fps).toBeGreaterThanOrEqual(50);
});

/* ---------- fase 7a: fidelidad 3D (79 piezas, eje inclinado, contorno, etiquetas con guía) ---------- */
type Gancho = {
  mundo: (id: string) => number[] | null;
  color: (id: string) => { hex: string; emisivo: number } | null;
  contorno: (id: string) => boolean;
  geom: () => { ejeCilindro: [number, number]; centroCiguenal: [number, number] };
  piezas: () => number;
};
/** Ejecuta `f(window.__moto3d)` en la página (gancho de pruebas que expone EscenaMoto). */
const gancho = <T,>(page: Page, f: (g: Gancho) => T): Promise<T> =>
  page.evaluate((cuerpo) => new Function("g", `return (${cuerpo})(g)`)((window as unknown as { __moto3d: Gancho }).__moto3d), f.toString()) as Promise<T>;

test("moto 7a: el GLB trae 79 piezas y los chips de ensamblajes incluyen dirección y carrocería", async ({ page }) => {
  await abrir(page);
  await expect.poll(() => gancho(page, (g) => g.piezas())).toBe(79);
  await page.getByRole("tab", { name: "Ensamblajes" }).click();
  await expect(page.locator(".chips-ensamblaje button")).toHaveCount(12); // Todo + 11 ensamblajes
  await page.locator('button[data-ensamblaje="direccion"]').click();
  await expect(page.locator('button[data-pieza="manubrio"]')).toBeVisible();
  await page.locator('button[data-ensamblaje="carroceria"]').click();
  await expect(page.locator('button[data-pieza="guardabarros_delantero"]')).toBeVisible();
});

test("moto 7a: el pistón se mueve sobre el EJE INCLINADO del cilindro (distancia al eje ≈ 0)", async ({ page }) => {
  await abrir(page);
  await page.getByLabel("Factor de cámara lenta").selectOption("50");
  await acelerador(page, 100); // rpm libres altas: el cigüeñal da varias vueltas durante el muestreo
  const g = await gancho(page, (m) => m.geom());
  const ang = (Math.atan2(g.ejeCilindro[0], g.ejeCilindro[1]) * 180) / Math.PI;
  expect(ang).toBeGreaterThan(14.9);
  expect(ang).toBeLessThan(15.1);
  const proy: number[] = [];
  for (let i = 0; i < 30; i++) {
    const p = (await gancho(page, (m) => m.mundo("piston")))!;
    const dx = p[0] - g.centroCiguenal[0];
    const dy = p[1] - g.centroCiguenal[1];
    const distancia = Math.abs(dx * g.ejeCilindro[1] - dy * g.ejeCilindro[0]); // |(p − C) × u|
    expect(distancia).toBeLessThan(0.002); // el pistón queda a < 2 mm del eje (tolerancia de conectividad)
    proy.push(dx * g.ejeCilindro[0] + dy * g.ejeCilindro[1]);
    await page.waitForTimeout(90);
  }
  expect(Math.max(...proy) - Math.min(...proy)).toBeGreaterThan(0.045); // recorre casi toda la carrera (58,7 mm)
  expect(Math.max(...proy) - Math.min(...proy)).toBeLessThan(0.0605);
});

test("moto 7a: la selección usa CONTORNO y no recolorea la pieza (llanta trasera, tanque, resaltado de la ficha)", async ({ page }) => {
  const errores = vigilarConsola(page);
  await abrir(page);
  const antes = await gancho(page, (g) => g.color("llanta_trasera"));
  expect(await gancho(page, (g) => g.contorno("llanta_trasera"))).toBe(false);
  await page.getByRole("tab", { name: "Ensamblajes" }).click();
  await page.locator('button[data-pieza="llanta_trasera"]').click();
  await expect.poll(() => gancho(page, (g) => g.contorno("llanta_trasera"))).toBe(true);
  expect(await gancho(page, (g) => g.color("llanta_trasera"))).toEqual(antes); // mismo color y sin emisivo naranja
  expect(antes!.emisivo).toBe(0);
  const tanque = await gancho(page, (g) => g.color("tanque"));
  await page.locator('button[data-pieza="tanque"]').click();
  await expect.poll(() => gancho(page, (g) => g.contorno("tanque"))).toBe(true);
  expect(await gancho(page, (g) => g.contorno("llanta_trasera"))).toBe(false);
  expect(await gancho(page, (g) => g.color("tanque"))).toEqual(tanque);
  // resaltado desde la ficha técnica: también por contorno
  await page.getByRole("tab", { name: "Ficha técnica" }).click();
  await page.locator('.ficha-tecnica button[data-campo="llantas.trasera"]').click();
  await expect.poll(() => gancho(page, (g) => g.contorno("llanta_trasera"))).toBe(true);
  expect(await gancho(page, (g) => g.color("llanta_trasera"))).toEqual(antes);
  expect(errores).toEqual([]); // sin errores de shader ni de WebGL
});

for (const [ancho, alto] of [
  [1440, 900],
  [1280, 800],
] as const) {
  test(`moto 7a: etiquetas con línea guía, sin solapes y sin recortes (${ancho}×${alto})`, async ({ page }) => {
    const errores = vigilarConsola(page);
    await page.setViewportSize({ width: ancho, height: alto });
    await abrir(page);
    const revisar = async () => {
      // Una sola lectura síncrona en la página (las etiquetas se reposicionan en cada fotograma).
      const lectura = await page.evaluate(() => {
        const esc = document.querySelector<HTMLElement>('[data-testid="escenario-moto"]')!.getBoundingClientRect();
        const zonas = Array.from(document.querySelectorAll<HTMLElement>(".superpuesto, .lento, .leyenda-escena")).map((z) => z.getBoundingClientRect());
        return ["motor", "cilindrada", "transmision", "rueda", "disco_del", "disco_tras"].flatMap((clave) => {
          const el = document.querySelector<HTMLElement>(`[data-etiqueta="${clave}"]`)!;
          if (getComputedStyle(el).visibility !== "visible") return [];
          const b = el.getBoundingClientRect();
          const l = document.querySelector<SVGLineElement>(`line[data-guia="${clave}"]`)!;
          return [{ clave, x: b.left - esc.left, y: b.top - esc.top, w: b.width, h: b.height, ew: esc.width, eh: esc.height, x2: Number(l.getAttribute("x2")), y2: Number(l.getAttribute("y2")), guia: getComputedStyle(l).visibility, sobreZona: zonas.some((z) => b.left < z.right && b.right > z.left && b.top < z.bottom && b.bottom > z.top) }];
        });
      });
      expect(lectura.length).toBeGreaterThanOrEqual(5);
      for (const c of lectura) {
        expect(c.x, `${c.clave} recortada a la izquierda`).toBeGreaterThanOrEqual(-0.5);
        expect(c.y, `${c.clave} recortada arriba`).toBeGreaterThanOrEqual(-0.5);
        expect(c.x + c.w, `${c.clave} recortada a la derecha`).toBeLessThanOrEqual(c.ew + 0.5);
        expect(c.y + c.h, `${c.clave} recortada abajo`).toBeLessThanOrEqual(c.eh + 0.5);
        expect(c.guia).toBe("visible");
        expect(c.sobreZona, `${c.clave} tapa la barra de herramientas, el cuadro de cámara lenta o la leyenda`).toBe(false);
        expect(c.x2).toBeGreaterThanOrEqual(c.x - 3);
        expect(c.x2).toBeLessThanOrEqual(c.x + c.w + 3);
        expect(c.y2).toBeGreaterThanOrEqual(c.y - 3);
        expect(c.y2).toBeLessThanOrEqual(c.y + c.h + 3);
      }
      for (let i = 0; i < lectura.length; i++)
        for (let j = i + 1; j < lectura.length; j++) {
          const a = lectura[i];
          const b = lectura[j];
          const solapa = a.x < b.x + b.w && a.x + a.w > b.x && a.y < b.y + b.h && a.y + a.h > b.y;
          expect(solapa, `${a.clave} se solapa con ${b.clave}`).toBe(false);
        }
    };
    await revisar();
    await page.getByRole("tab", { name: "Vista" }).click();
    for (const camara of ["3/4", "Lateral", "Frenos"]) {
      await page.getByRole("button", { name: camara, exact: true }).click();
      await page.waitForTimeout(2500);
      await revisar();
    }
    // textos exactos: ni «ficha 150» ni etiquetas lejos de su pieza
    const texto = await page.getByTestId("escenario-moto").innerText();
    expect(texto).toContain("150 cm³ nominal — supuesto didáctico");
    expect(texto).not.toMatch(/ficha\s*150/);
    await expect(page.locator('[data-etiqueta="disco_tras"]')).toContainText("Tras.: sin accionar");
    expect(errores).toEqual([]);
  });
}

test("moto 7a: calidad ligera por software y, forzando calidad alta, entorno de estudio local sin errores", async ({ page }) => {
  const errores = vigilarConsola(page);
  await abrir(page);
  await expect(page.getByTestId("escenario-moto")).toHaveAttribute("data-calidad", "ligera");
  await page.goto("/app/#/maquina/moto_honda?calidad=alta"); // IBL con Lightformers locales + SSAO
  await page.reload();
  await expect(page.getByTestId("escenario-moto").locator("canvas")).toBeVisible();
  await expect(page.getByTestId("escenario-moto")).toHaveAttribute("data-calidad", "alta");
  await expect.poll(() => gancho(page, (g) => g.piezas()), { timeout: 30_000 }).toBe(79);
  await page.waitForTimeout(2500);
  expect(errores.filter((e) => !/404/.test(e))).toEqual([]); // sin errores de shader/WebGL
});

test("moto 7a: capturas lateral, 3/4 y despiece (mismo encuadre y tamaño que la línea base «antes»)", async ({ page }) => {
  await abrir(page);
  await page.getByRole("tab", { name: "Vista" }).click();
  await page.getByRole("button", { name: "Lateral", exact: true }).click();
  await page.waitForTimeout(2500);
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({ path: `${FIGURAS}/moto_7a_despues_lateral.png` });
  await page.getByRole("button", { name: "3/4", exact: true }).click();
  await page.waitForTimeout(2500);
  await page.screenshot({ path: `${FIGURAS}/moto_7a_despues_3cuartos.png` });
  await page.getByLabel("Despiece por ensamblaje").check();
  await page.waitForTimeout(9000);
  await page.screenshot({ path: `${FIGURAS}/moto_7a_despues_despiece.png` });
});
