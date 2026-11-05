// Capturas de la fase 7b (fuera de los e2e). Uso: node scripts/capturar_7b.mjs <antes|despues>
// Variables: FNA_URL (por omisión http://127.0.0.1:8031).
import { chromium } from "@playwright/test";
import { mkdirSync } from "node:fs";
import { resolve } from "node:path";

const fase = process.argv[2] ?? "antes";
const BASE = process.env.FNA_URL ?? "http://127.0.0.1:8031";
const SALIDA = resolve("../docs/capturas/7b");
mkdirSync(SALIDA, { recursive: true });
const paginas = { biblioteca: "#/", freno: "#/maquina/freno", prensa: "#/maquina/prensa", linea: "#/maquina/linea", moto: "#/maquina/moto_honda" };
const tamanos = [[1280, 800], [1920, 1080]];
const navegador = await chromium.launch({
  channel: "chrome",
  args: ["--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--no-proxy-server"],
});
for (const [w, h] of tamanos) {
  const ctx = await navegador.newContext({ viewport: { width: w, height: h } });
  const page = await ctx.newPage();
  for (const [nombre, hash] of Object.entries(paginas)) {
    await page.goto(`${BASE}/app/${hash}`);
    await page.waitForTimeout(nombre === "biblioteca" ? 1500 : 4500);
    await page.screenshot({ path: `${SALIDA}/${fase}_${nombre}_${w}x${h}.png`, fullPage: nombre === "biblioteca" });
  }
  await ctx.close();
}
await navegador.close();
console.log("listo");
