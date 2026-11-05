// Capturas del README técnico (fase 10, paso 4) a 1920x1080 en docs/capturas/readme/.
// Uso: node scripts/capturar_readme.mjs [prefijo ...]   (sin argumentos captura todo; p. ej. "05" "10")
// Variables: FNA_URL (API y visor, por omisión http://127.0.0.1:8071),
//            FNA_URL_STREAMLIT (por omisión http://127.0.0.1:8072).
// Streamlit debe correr con FNA_PROVEEDOR_LLM=extractivo: no se llama a ningún modelo ni a la red.
import { chromium } from "@playwright/test";
import { mkdirSync } from "node:fs";
import { resolve } from "node:path";

const API = process.env.FNA_URL ?? "http://127.0.0.1:8071";
const ST = process.env.FNA_URL_STREAMLIT ?? "http://127.0.0.1:8072";
const SALIDA = resolve("../docs/capturas/readme");
mkdirSync(SALIDA, { recursive: true });
const filtro = process.argv.slice(2);
const quiere = (n) => filtro.length === 0 || filtro.some((f) => n.startsWith(f));

const navegador = await chromium.launch({
  channel: "chrome",
  args: ["--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--no-proxy-server"],
});
const ctx = await navegador.newContext({ viewport: { width: 1920, height: 1080 } });
const page = await ctx.newPage();
const foto = (n, opts = {}) => page.screenshot({ path: `${SALIDA}/${n}.png`, ...opts });
const ir = async (hash, ms) => {
  await page.goto(`${API}/app/${hash}`);
  await page.reload(); // un cambio solo de hash no reinicia el estado de la escena anterior
  await page.waitForTimeout(ms);
};

if (quiere("01")) {
  await ir("#/", 2500);
  await foto("01_biblioteca");
}
for (const [n, h] of [["02_freno", "freno"], ["03_prensa", "prensa"], ["04_linea", "linea"]]) {
  if (!quiere(n)) continue;
  await ir(`#/maquina/${h}`, 6000);
  await foto(n);
}

const arribaPestana = async (tab) => {
  // coloca la lista de pestañas justo bajo la barra superior
  await tab.evaluate((el) => window.scrollBy(0, el.getBoundingClientRect().top - 70));
  await page.waitForTimeout(1200);
};
const moto = async () => {
  await ir("#/maquina/moto_honda", 7000);
};
if (quiere("05")) {
  await moto();
  await foto("05_moto_ensamblada");
}
if (quiere("06")) {
  await moto();
  await page.getByRole("toolbar").getByRole("button", { name: "Despiece", exact: true }).click();
  await page.waitForTimeout(10000);
  await foto("06_moto_despiece");
}
if (quiere("07")) {
  await moto();
  await page.getByRole("group", { name: "Cámara" }).getByRole("button", { name: "Motor", exact: true }).click();
  await page.waitForTimeout(3000);
  await page.getByRole("button", { name: "◧ Sección" }).click();
  await page.waitForTimeout(5000);
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.waitForTimeout(500);
  await foto("07_moto_corte_motor");
}
if (quiere("08")) {
  await moto();
  const t8 = page.getByRole("tab", { name: "Ficha técnica", exact: true });
  await t8.click();
  await arribaPestana(t8);
  await foto("08_moto_ficha_tecnica");
}
if (quiere("09")) {
  await moto();
  const t9 = page.getByRole("tab", { name: "FAQ", exact: true });
  await t9.click();
  await arribaPestana(t9);
  const q = page.locator("[data-faq-fanalca]").first();
  await q.locator("summary").click();
  await page.waitForTimeout(800);
  await foto("09_moto_faq");
}

// ---------------------------------------------------------------- Streamlit
const stAbrir = async () => {
  await page.goto(ST);
  await page.getByRole("tab").first().waitFor({ timeout: 30000 });
  await page.waitForTimeout(2500);
};
const stTab = async (texto) => {
  await page.getByRole("tab", { name: texto }).first().click();
  await page.waitForTimeout(1500);
};
if (quiere("10")) {
  await stAbrir();
  await stTab("Q&A");
  const caja = page.getByPlaceholder(/Escribir una pregunta/);
  await caja.fill("¿Cuántos puntos de venta tiene la red de Honda Motocicletas?");
  await caja.press("Enter");
  await page.waitForTimeout(6000);
  await foto("10_streamlit_qa");
}
if (quiere("11")) {
  await stAbrir();
  await stTab("Resumen");
  await page.getByRole("button", { name: "Generar resumen" }).click();
  await page.waitForTimeout(6000);
  await foto("11_streamlit_resumen");
}
if (quiere("12")) {
  await stAbrir();
  await stTab("FAQ");
  await page.getByRole("button", { name: "Generar FAQ" }).click();
  await page.waitForTimeout(6000);
  await foto("12_streamlit_faq");
}
if (quiere("13")) {
  await stAbrir();
  await stTab("Proceso de datos");
  await page.waitForTimeout(5000);
  await foto("13_streamlit_proceso");
}
if (quiere("14")) {
  await stAbrir();
  await stTab("Laboratorio");
  await page.getByRole("button", { name: "Comparar" }).click();
  await page.waitForTimeout(6000);
  await foto("14_streamlit_laboratorio");
}

if (quiere("15")) {
  await page.goto(`${API}/docs`);
  await page.waitForSelector(".opblock-tag", { timeout: 30000 });
  await page.waitForTimeout(2000);
  await foto("15_swagger");
}
await navegador.close();
console.log("listo");
