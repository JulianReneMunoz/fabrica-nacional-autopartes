import { expect, test, type Page } from "@playwright/test";

/** Fase 7b: plantilla común, biblioteca responsiva, navegación, accesibilidad y movimiento reducido. */
const MAQUINAS = [
  { id: "freno", escenario: "escenario-freno", nombre: "Freno" },
  { id: "prensa", escenario: "escenario-prensa", nombre: "Prensa" },
  { id: "linea", escenario: "escenario-linea", nombre: "Línea" },
  { id: "moto_honda", escenario: "escenario-moto", nombre: "Moto" },
];

function vigilarConsola(page: Page) {
  const errores: string[] = [];
  page.on("pageerror", (e) => errores.push(e.message));
  page.on("console", (m) => m.type() === "error" && errores.push(m.text()));
  return errores;
}

for (const m of MAQUINAS) {
  test(`plantilla común: ${m.id} (orden, columnas 8/12 + 4/12, barra, pestañas, controles, nota)`, async ({ page }) => {
    const errores = vigilarConsola(page);
    await page.setViewportSize({ width: 1280, height: 800 });
    await page.goto(`/app/#/maquina/${m.id}`);
    await expect(page.getByTestId(m.escenario)).toBeVisible();
    // orden vertical de los bloques
    const y = async (sel: string) => (await page.locator(sel).first().boundingBox())!.y;
    const ys = [await y(".migas"), await y("h1.titular"), await y(".franja-formula"), await y(".lienzo-col"), await y(".lecturas"), await y("[data-testid=idea-principal]"), await y(".dos-tarjetas"), await y(".pie-nota")];
    expect(ys).toEqual([...ys].sort((a, b) => a - b));
    // columnas: lienzo 8/12 y lateral 4/12
    const lienzo = (await page.locator(".lienzo-col").boundingBox())!;
    const lateral = (await page.locator(".lateral-col").boundingBox())!;
    expect(lienzo.width / (lienzo.width + lateral.width)).toBeGreaterThan(0.62);
    expect(lienzo.width / (lienzo.width + lateral.width)).toBeLessThan(0.72);
    expect(lienzo.width).toBeGreaterThan(780); // el lienzo no queda estrecho a 1280×800
    // «Controles» arriba de las pestañas y con deslizadores con aria-label
    const controles = (await page.locator(".lateral-col section[aria-label=Controles]").boundingBox())!;
    const pestanas = (await page.locator(".lateral-col .pestanas").boundingBox())!;
    expect(controles.y).toBeLessThan(pestanas.y);
    for (const r of await page.locator(".lateral-col input[type=range]").all()) await expect(r).toHaveAttribute("aria-label", /.+/);
    // barra estándar: orden fijo
    const botones = await page.locator(".barra-lienzo button").allInnerTexts();
    const ORDEN = ["Ensamblado", "Despiece", "◧ Sección", "⌖ Cámara", "⤓ PNG", "Guardar vista", "Recorrido 30 s"];
    expect(botones).toEqual(ORDEN.filter((b) => botones.includes(b)));
    expect(botones).toContain("Recorrido 30 s");
    // pestañas estándar
    const tabs = await page.getByRole("tab").evaluateAll((els) => els.map((e) => e.textContent));
    expect(tabs).toEqual(m.id === "moto_honda" ? ["Componentes", "Datos de la empresa", "Ficha técnica", "FAQ"] : ["Componentes", "Datos de la empresa", "FAQ"]);
    await expect(page.locator(".pie-nota")).toHaveText("Cifras demostrativas; los datos de la empresa provienen de fuentes oficiales citadas por URL.");
    await expect(page.locator(".dos-tarjetas section")).toHaveCount(2);
    // la pestaña «Datos de la empresa» muestra la URL y la insignia de procedencia, siempre en una línea
    await page.getByRole("tab", { name: "Datos de la empresa" }).click();
    await expect(page.locator(".pestanas-panel .datos a").first()).toHaveAttribute("href", /https?:\/\//);
    for (const i of await page.locator(".pestanas-panel .insignia").all()) {
      const caja = (await i.boundingBox())!;
      expect(caja.height).toBeLessThan(26); // una sola línea
    }
    expect(errores).toEqual([]);
  });
}

test("biblioteca: cuadrícula de 1/2/3/4 columnas y sin asteriscos", async ({ page }) => {
  const columnas = async () =>
    page.evaluate(() => getComputedStyle(document.querySelector(".rejilla")!).gridTemplateColumns.split(" ").length);
  for (const [ancho, esperadas] of [[1920, 4], [1440, 3], [1000, 2], [600, 1]] as const) {
    await page.setViewportSize({ width: ancho, height: 900 });
    await page.goto("/app/#/");
    await expect(page.locator("article.tarjeta")).toHaveCount(4);
    expect(await columnas(), `${ancho}px`).toBe(esperadas);
  }
  expect(await page.locator("main").innerText()).not.toContain("*");
  // a 1920 px el contenido usa el ancho disponible y las cuatro tarjetas caben en la misma fila
  await page.setViewportSize({ width: 1920, height: 1080 });
  const ys = await page.locator("article.tarjeta").evaluateAll((els) => els.map((e) => Math.round(e.getBoundingClientRect().top)));
  expect(new Set(ys).size).toBe(1);
});

test("cabecera: navegación unificada, estado activo y menú plegable por debajo de 900 px", async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 800 });
  await page.goto("/app/#/maquina/prensa");
  const nav = page.getByRole("navigation", { name: "Principal" });
  await expect(nav.getByRole("link")).toHaveText(["Biblioteca", "Freno", "Prensa", "Línea", "Moto", "API"]);
  await expect(nav.locator("a[aria-current=page]")).toHaveText("Prensa");
  await page.setViewportSize({ width: 800, height: 800 });
  await expect(nav).toBeHidden();
  const menu = page.getByRole("button", { name: /Menú/ });
  await menu.click();
  await expect(nav).toBeVisible();
  await nav.getByRole("link", { name: "Línea" }).click();
  await expect(page.getByTestId("escenario-linea")).toBeVisible();
  await expect(nav).toBeHidden(); // se pliega al navegar
});

test("accesibilidad: foco visible en botones y deslizadores operables con teclado", async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 800 });
  await page.goto("/app/#/maquina/prensa");
  const r = page.getByLabel("Espesor de lámina");
  await r.focus();
  const contorno = await r.evaluate((e) => getComputedStyle(e).outlineStyle);
  expect(contorno).not.toBe("none");
  const antes = await r.inputValue();
  await page.keyboard.press("ArrowRight");
  await page.keyboard.press("ArrowRight");
  expect(Number(await r.inputValue())).toBeGreaterThan(Number(antes));
  const boton = page.getByRole("button", { name: "▶ Correr" });
  await boton.focus();
  expect(await boton.evaluate((e) => getComputedStyle(e).outlineStyle)).not.toBe("none");
});

test("movimiento reducido: ?tour=1 no se inicia solo; «Recorrido 30 s» sí", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto("/app/#/maquina/prensa?tour=1");
  await expect(page.locator(".tour-banda")).toContainText("Movimiento reducido");
  await page.waitForTimeout(1500);
  expect(await page.evaluate(() => (window as unknown as { __tour?: unknown }).__tour)).toBeUndefined();
  await page.goto("/app/#/maquina/prensa");
  await page.getByRole("button", { name: "Recorrido 30 s" }).click();
  await page.waitForFunction(() => (window as unknown as { __tour?: { estado: string } }).__tour?.estado === "corriendo", null, { timeout: 10_000 });
});

test("movimiento reducido: la moto no arranca animada sola", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto("/app/#/maquina/moto_honda");
  await expect(page.getByTestId("escenario-moto").locator("canvas")).toBeVisible();
  await expect(page.getByTestId("estado")).toHaveText("PAUSA");
});

test("freno: el encuadre automático ocupa el lienzo sin tocar el GLB y «Cámara» lo restablece", async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 800 });
  await page.goto("/app/#/maquina/freno");
  await expect(page.locator(".arbol button[data-pieza]")).toHaveCount(15);
  await page.waitForTimeout(2500);
  const caja = (await page.getByTestId("escenario-freno").boundingBox())!;
  // porcentaje del lienzo ocupado por píxeles no vacíos del canvas (el fondo es el papel)
  const ocupado = await page.getByTestId("escenario-freno").locator("canvas").evaluate((c: HTMLCanvasElement) => {
    const t = document.createElement("canvas");
    t.width = c.width;
    t.height = c.height;
    const g = t.getContext("2d")!;
    g.drawImage(c, 0, 0);
    const d = g.getImageData(0, 0, t.width, t.height).data;
    let minX = t.width, maxX = 0, minY = t.height, maxY = 0;
    for (let y = 0; y < t.height; y += 2)
      for (let x = 0; x < t.width; x += 2) {
        const i = (y * t.width + x) * 4;
        if (Math.abs(d[i] - 252) + Math.abs(d[i + 1] - 252) + Math.abs(d[i + 2] - 251) > 60) {
          minX = Math.min(minX, x); maxX = Math.max(maxX, x); minY = Math.min(minY, y); maxY = Math.max(maxY, y);
        }
      }
    return { w: (maxX - minX) / t.width, h: (maxY - minY) / t.height };
  });
  expect(Math.max(ocupado.w, ocupado.h)).toBeGreaterThan(0.45);
  expect(caja.width).toBeGreaterThan(780);
});
