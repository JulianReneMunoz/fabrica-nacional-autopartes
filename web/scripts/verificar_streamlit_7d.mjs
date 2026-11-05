// Verificación en navegador de la interfaz Streamlit (fase 7d). Arranca SU PROPIA instancia de Streamlit con el
// proveedor extractivo (sin Claude ni red) y una base de auditoría temporal; al terminar detiene solo el proceso
// que arrancó. Uso (desde web/): node scripts/verificar_streamlit_7d.mjs [puerto]
// Comprueba: carga sin errores de consola, 10 pestañas, barra superior negra, pestaña activa visible, foco visible
// y que una consulta del Q&A produce una tarjeta con insignias de fuente y enlace.
import { chromium } from "@playwright/test";
import { spawn, spawnSync } from "node:child_process";
import { mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";

const puerto = process.argv[2] ?? "8612";
const BASE = `http://127.0.0.1:${puerto}`;
const raiz = resolve("..");
const tmp = mkdtempSync(join(tmpdir(), "fna7d-"));
const env = {
  ...process.env,
  FNA_PROVEEDOR_LLM: "extractivo",
  FNA_URL_BASE_DATOS: `sqlite:///${join(tmp, "auditoria.db").replaceAll("\\", "/")}`,
  UV_NO_SYNC: "1",
};
const servidor = spawn(
  "uv",
  ["run", "--no-sync", "streamlit", "run", "frontend/app.py", "--server.port", puerto, "--server.headless", "true"],
  { cwd: raiz, env, stdio: "ignore" },
);
const detener = () => {
  if (process.platform === "win32") spawnSync("taskkill", ["/PID", String(servidor.pid), "/T", "/F"], { stdio: "ignore" });
  else servidor.kill("SIGTERM");
  try {
    rmSync(tmp, { recursive: true, force: true, maxRetries: 5, retryDelay: 500 });
  } catch {
    /* la base temporal puede seguir bloqueada un instante: es un directorio temporal */
  }
};

const fallos = [];
const comprobar = (condicion, mensaje) => {
  console.log(`${condicion ? "OK   " : "FALLO"} ${mensaje}`);
  if (!condicion) fallos.push(mensaje);
};

try {
  let listo = false;
  for (let i = 0; i < 60 && !listo; i++) {
    try {
      listo = (await fetch(`${BASE}/_stcore/health`)).ok;
    } catch {
      /* aún no arranca */
    }
    if (!listo) await new Promise((r) => setTimeout(r, 1000));
  }
  comprobar(listo, "Streamlit arranca");
  if (!listo) throw new Error("Streamlit no arrancó en 60 s");

  const navegador = await chromium.launch({ channel: "chrome", args: ["--no-proxy-server"] });
  const page = await (await navegador.newContext({ viewport: { width: 1280, height: 800 } })).newPage();
  const errores = [];
  page.on("console", (m) => m.type() === "error" && errores.push(m.text()));
  page.on("pageerror", (e) => errores.push(String(e)));
  await page.goto(BASE);
  await page.getByRole("tab").first().waitFor({ timeout: 30000 });

  const pestanas = await page.getByRole("tab").allInnerTexts();
  comprobar(pestanas.length === 10, `10 pestañas (${pestanas.length})`);
  for (const nombre of ["Panel", "Proceso de datos", "Q&A", "Resumen", "FAQ", "Simulador 3D", "Auditoría"]) {
    comprobar(pestanas.some((t) => t.toLowerCase().includes(nombre.toLowerCase())), `pestaña «${nombre}»`);
  }
  const estilos = await page.evaluate(() => {
    const barra = document.querySelector(".fna-cabecera");
    const activa = document.querySelector('[data-testid="stTab"][aria-selected="true"]');
    return {
      barra: barra ? getComputedStyle(barra).backgroundColor : null,
      activa: activa ? getComputedStyle(activa).backgroundColor : null,
      enlace: [...document.querySelectorAll(".fna-cabecera a")].map((a) => a.getAttribute("href")),
      fuente: getComputedStyle(document.querySelector('[data-testid="stApp"]')).fontFamily,
    };
  });
  comprobar(estilos.barra === "rgb(11, 11, 11)", `barra superior negra (${estilos.barra})`);
  comprobar(estilos.activa === "rgb(11, 11, 11)", `pestaña activa invertida (${estilos.activa})`);
  comprobar(estilos.enlace.some((h) => h?.endsWith("#/")), "enlace a la biblioteca del visor");
  comprobar(/Inter|Segoe|system-ui/.test(estilos.fuente), `tipografía del visor (${estilos.fuente.slice(0, 40)})`);

  await page.getByRole("tab", { name: "Q&A" }).click();
  await page.getByRole("button", { name: /cilindrajes/ }).click();
  await page.locator("article.fna-tarjeta").waitFor({ timeout: 30000 });
  const tarjeta = page.locator("article.fna-tarjeta").first();
  comprobar((await tarjeta.locator(".fna-insignia").count()) >= 1, "la tarjeta tiene insignias de fuente");
  comprobar((await tarjeta.locator(".fna-citas a[href^='https://']").count()) >= 1, "las citas enlazan a su URL");
  comprobar((await tarjeta.locator(".fna-chip").count()) >= 4, "la tarjeta tiene chips de fundamentación, modelo y latencia");
  comprobar(/scraping|lectura web|semilla|base de conocimiento/i.test(await tarjeta.innerText()), "procedencia en texto, no solo color");

  await page.keyboard.press("Tab");
  await page.getByRole("tab", { name: "Panel" }).focus();
  const foco = await page.evaluate(() => {
    const e = document.activeElement;
    const s = e ? getComputedStyle(e) : null;
    return s ? `${e.getAttribute("role") ?? e.tagName} ${s.outlineStyle} ${s.outlineWidth}` : "";
  });
  comprobar(/ (solid|auto) /.test(foco) && !/ 0px/.test(foco), `foco visible (${foco})`);

  await page.waitForTimeout(500);
  comprobar(errores.length === 0, `sin errores de consola (${errores.length}${errores.length ? ": " + errores[0].slice(0, 120) : ""})`);
  await navegador.close();
} catch (e) {
  console.error(e);
  fallos.push(String(e));
} finally {
  detener();
}
console.log(fallos.length ? `FALLÓ: ${fallos.length}` : "TODO OK");
process.exit(fallos.length ? 1 : 0);
