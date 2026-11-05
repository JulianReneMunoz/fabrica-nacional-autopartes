// Capturas de la fase 7d (Streamlit). Uso: node scripts/capturar_7d.mjs <antes|despues>
// Variables: FNA_URL_STREAMLIT (por omisión http://127.0.0.1:8611). Streamlit debe correr con
// FNA_PROVEEDOR_LLM=extractivo para que no se llame a ningún modelo ni a la red.
import { chromium } from "@playwright/test";
import { mkdirSync } from "node:fs";
import { resolve } from "node:path";

const fase = process.argv[2] ?? "antes";
const BASE = process.env.FNA_URL_STREAMLIT ?? "http://127.0.0.1:8611";
const SALIDA = resolve("../docs/capturas/7d");
mkdirSync(SALIDA, { recursive: true });
const tamanos = [
  [1280, 800],
  [1920, 1080],
];
const pestanas = { panel: "Panel", qa: "Q&A", proceso: "Proceso de datos", simulador: "Simulador 3D" };
const navegador = await chromium.launch({ channel: "chrome", args: ["--no-proxy-server"] });
for (const [w, h] of tamanos) {
  const ctx = await navegador.newContext({ viewport: { width: w, height: h } });
  const page = await ctx.newPage();
  await page.goto(BASE);
  await page.getByRole("tab").first().waitFor({ timeout: 30000 });
  for (const [nombre, texto] of Object.entries(pestanas)) {
    await page.getByRole("tab", { name: texto }).first().click();
    if (nombre === "qa") {
      await page.getByRole("button", { name: /cilindrajes/ }).click();
      await page.waitForTimeout(2500);
    }
    await page.waitForTimeout(4500);
    await page.screenshot({ path: `${SALIDA}/${fase}_${nombre}_${w}x${h}.png` });
  }
  await ctx.close();
}
await navegador.close();
console.log("listo");
