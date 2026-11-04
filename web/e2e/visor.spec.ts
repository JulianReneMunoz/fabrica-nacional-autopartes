import { expect, test, type Page } from "@playwright/test";

const CAPTURAS = "../docs/capturas/v2";

function vigilarConsola(page: Page) {
  const errores: string[] = [];
  page.on("pageerror", (e) => errores.push(e.message));
  page.on("console", (m) => m.type() === "error" && errores.push(m.text()));
  return errores;
}

test("biblioteca: tarjetas de máquinas alimentadas por la base de conocimiento", async ({ page }) => {
  const errores = vigilarConsola(page);
  await page.goto("/app/#/");
  const tarjetas = page.locator("article.tarjeta");
  await expect(tarjetas).toHaveCount(3);
  for (const id of ["freno", "prensa", "linea"]) {
    const t = page.locator(`article[data-maquina="${id}"]`);
    await expect(t.locator("h2")).toContainText("¿");
    await expect(t.locator("a.boton").first()).toHaveAttribute("href", `#/maquina/${id}`);
    await expect(t.locator(".datos a").first()).toHaveAttribute("href", /autopartesfanalca\.com\.co|fanalca\.com/);
  }
  await page.screenshot({ path: `${CAPTURAS}/01_biblioteca.png`, fullPage: true });
  expect(errores).toEqual([]);
});

test("freno 3D: carga, selección, ficha, pregunta, despiece, sección y frenado", async ({ page }) => {
  const errores = vigilarConsola(page);
  await page.goto("/app/#/maquina/freno");
  const escenario = page.getByTestId("escenario-freno");
  await expect(escenario.locator("canvas")).toBeVisible();
  await expect(page.locator(".arbol button[data-pieza]")).toHaveCount(15);
  await page.waitForTimeout(1500);
  await page.screenshot({ path: `${CAPTURAS}/02_freno_ensamblado.png` });

  // selección desde el árbol → ficha + lectura de posición
  await page.locator('.arbol button[data-pieza="piston"]').click();
  await expect(page.getByTestId("ficha-nombre")).toHaveText("Pistón de pinza");
  await expect(page.getByTestId("lectura-posicion")).toContainText("mm");
  await page.getByRole("button", { name: "Verificar en API" }).click();
  await expect(page.locator(".ficha")).toContainText("θ");

  // pregunta RAG
  await page.getByRole("button", { name: "¿Qué función cumple?" }).click();
  await expect(page.getByTestId("respuesta-pieza")).toBeVisible();
  await expect(page.getByTestId("respuesta-pieza")).toContainText(/demostraci/i);

  // despiece completo
  await page.getByRole("button", { name: "Despiece", exact: true }).click();
  await page.locator("select[aria-label='Velocidad de simulación']").selectOption("1");
  await expect(page.getByRole("button", { name: "▶ Correr" })).toBeVisible({ timeout: 10_000 });
  await page.screenshot({ path: `${CAPTURAS}/03_freno_despiece.png` });

  // sección + transparencia
  await page.getByRole("button", { name: "◧ Sección" }).click();
  await page.waitForTimeout(400);
  await page.screenshot({ path: `${CAPTURAS}/04_freno_seccion.png` });
  await page.getByRole("button", { name: "◧ Sección" }).click();

  // frenado: lecturas junto a las piezas
  await page.getByRole("button", { name: "Frenar" }).click();
  await expect(page.locator('[data-etiqueta="piston"]')).toContainText("kN");
  await expect(page.locator(".pasos li.actual")).toBeVisible();
  await page.waitForTimeout(2500);
  await page.screenshot({ path: `${CAPTURAS}/05_freno_frenado.png` });

  // experimento: 50 bar → bloqueo
  await page.locator(".experimento .opciones button").first().click();
  await page.getByRole("button", { name: "Ejecutar y comparar" }).click();
  await expect(page.locator(".experimento [role=status]")).toContainText("Predicción correcta");
  await expect(page.locator(".lecturas")).toContainText("rueda bloqueada");

  // reensamblaje y cámara
  await page.getByRole("button", { name: "Reensamblar" }).click();
  await page.getByRole("button", { name: "⌖ Cámara" }).click();

  // exportar captura PNG
  const descarga = page.waitForEvent("download");
  await page.getByRole("button", { name: "⤓ PNG" }).click();
  expect((await descarga).suggestedFilename()).toMatch(/^freno_disco_.*\.png$/);

  expect(errores).toEqual([]);
});

test("rendimiento: fotogramas por segundo del visor 3D", async ({ page }) => {
  await page.goto("/app/#/maquina/freno");
  await expect(page.locator(".arbol button[data-pieza]")).toHaveCount(15);
  await page.getByRole("button", { name: "Frenar" }).click();
  await page.waitForTimeout(1000);
  const fps = await page.evaluate(
    () =>
      new Promise<number>((ok) => {
        let n = 0;
        const t0 = performance.now();
        const f = () => {
          n++;
          if (performance.now() - t0 < 3000) requestAnimationFrame(f);
          else ok((n * 1000) / (performance.now() - t0));
        };
        requestAnimationFrame(f);
      }),
  );
  test.info().annotations.push({ type: "fps", description: fps.toFixed(1) });
  console.log(`FPS medidos (render por software SwiftShader): ${fps.toFixed(1)}`);
  // Umbral conservador: el entorno de pruebas renderiza por CPU; con GPU se esperan ≥ 50 FPS.
  expect(fps).toBeGreaterThan(5);
});

test("prensa y línea: máquinas 2D con controles, lecturas y experimento", async ({ page }) => {
  const errores = vigilarConsola(page);
  await page.goto("/app/#/maquina/prensa");
  await expect(page.getByTestId("escenario-prensa")).toBeVisible();
  await page.getByRole("button", { name: "▶ Correr" }).click();
  await page.waitForTimeout(1200);
  await page.screenshot({ path: `${CAPTURAS}/06_prensa.png` });
  await page.locator(".experimento .opciones button").nth(1).click();
  await page.locator(".experimento").getByRole("button", { name: "Siguiente" }).click();
  await page.locator(".experimento .opciones button").nth(1).click();
  await page.getByRole("button", { name: "Ejecutar y comparar" }).click();
  await expect(page.getByTestId("escenario-prensa")).toContainText("Sobrecarga", { timeout: 5000 });

  await page.goto("/app/#/maquina/linea");
  await expect(page.getByTestId("escenario-linea")).toContainText("takt =");
  await expect(page.locator(".control").first()).toContainText("24.000");
  await page.getByRole("button", { name: "▶ Correr" }).click();
  await page.waitForTimeout(1500);
  await page.screenshot({ path: `${CAPTURAS}/07_linea.png` });
  expect(errores).toEqual([]);
});
