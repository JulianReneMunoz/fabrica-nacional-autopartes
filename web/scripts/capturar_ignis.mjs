// Capturas de IGNIS v2 (criterio de aceptación 5): cada pestaña a 1600, 1366 y 900 px, y Atención en reposo,
// escribiendo y respondiendo (sin voz y con voz).
// Uso: npm run build && npx vite preview --port 4173   (en otra terminal)   y luego   node scripts/capturar_ignis.mjs
// Variables: IGNIS_URL (por omisión http://127.0.0.1:4173/app/), IGNIS_SALIDA (carpeta de salida),
//            IGNIS_POSTER=1 también guarda el póster estático del auto en public/assets/ignis_auto_poster.jpg.
// El backend se simula con rutas de Playwright (salud, SSE y TTS): las capturas no dependen de FastAPI ni de la red.
import { chromium } from "@playwright/test";
import { mkdirSync } from "node:fs";

const BASE = process.env.IGNIS_URL ?? "http://127.0.0.1:4173/app/";
const SALIDA = process.env.IGNIS_SALIDA ?? "capturas_ignis";
const POSTER = process.env.IGNIS_POSTER === "1";
mkdirSync(SALIDA, { recursive: true });

const PESTANAS = [
  "atencion", "faq", "qa", "proceso-datos", "corpus", "base", "agente", "herramientas", "router", "prompts",
  "configuracion", "rayos-x", "seguridad", "auditoria", "panel", "evaluacion", "mlflow", "kanban", "arquitectura",
  "sesion", "ajustes",
];

// Respuesta de ejemplo con el contrato vigente del SSE (ignis_routes.py): metadatos → oraciones → fin → [DONE].
const SSE = [
  { tipo: "metadatos", thread_id: "hilo-captura", ruta_router: "rag_documental", score_router: 0.86, blindaje_activado: false, bloqueada: false,
    citas: [{ id: "f12", titulo: "Unidad de autopartes", url: "https://autopartesfanalca.com.co/" }], archivos_adjuntos: [] },
  { tipo: "oracion", texto: "Respuesta de ejemplo para la captura de pantalla." },
  { tipo: "oracion", texto: "Los datos reales llegan del backend de FastAPI." },
  { tipo: "fin" },
]
  .map((d) => `data: ${JSON.stringify(d)}\n\n`)
  .join("") + "data: [DONE]\n\n";

/** WAV PCM de 16 bits con un tono de 2 s modulado, para que el analizador del TTS tenga señal. */
function wavDePrueba(segundos = 2, tasa = 22050) {
  const n = segundos * tasa;
  const b = Buffer.alloc(44 + n * 2);
  b.write("RIFF", 0); b.writeUInt32LE(36 + n * 2, 4); b.write("WAVE", 8); b.write("fmt ", 12);
  b.writeUInt32LE(16, 16); b.writeUInt16LE(1, 20); b.writeUInt16LE(1, 22); b.writeUInt32LE(tasa, 24);
  b.writeUInt32LE(tasa * 2, 28); b.writeUInt16LE(2, 32); b.writeUInt16LE(16, 34); b.write("data", 36); b.writeUInt32LE(n * 2, 40);
  for (let i = 0; i < n; i++) {
    const t = i / tasa;
    const v = Math.sin(2 * Math.PI * 220 * t) * (0.5 + 0.5 * Math.sin(2 * Math.PI * 3 * t)) * 0.8;
    b.writeInt16LE(Math.round(v * 32767), 44 + i * 2);
  }
  return b;
}
const WAV = wavDePrueba();

const navegador = await chromium.launch({
  executablePath: process.env.CHROME_PATH,
  args: ["--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--no-proxy-server", "--autoplay-policy=no-user-gesture-required"],
});

async function abrir(ancho, alto) {
  const pagina = await navegador.newPage({ viewport: { width: ancho, height: alto } });
  await pagina.route("**/salud", (r) => r.fulfill({ status: 200, contentType: "application/json", body: '{"estado":"ok"}' }));
  await pagina.route("**/api/v1/ignis/stream", (r) => r.fulfill({ status: 200, contentType: "text/event-stream", body: SSE }));
  await pagina.route("**/api/v1/tts", (r) => r.fulfill({ status: 200, contentType: "audio/wav", body: WAV }));
  return pagina;
}

async function esperarAuto(pagina) {
  await pagina.waitForSelector("[data-modelo='cargado'], .ignis-sin-webgl", { timeout: 30_000 });
  await pagina.waitForTimeout(2500);
}

/** Envía con el panel ya abierto (por debajo de 1024 px el chat es un cajón y queda visible en la captura). */
async function enviar(pagina, texto) {
  await pagina.getByLabel("Mensaje para IGNIS").fill(texto);
  await pagina.keyboard.press("Enter");
}

for (const [ancho, alto] of [[1600, 900], [1366, 768], [900, 800]]) {
  // Todas las pestañas.
  const pagina = await abrir(ancho, alto);
  for (const id of PESTANAS) {
    await pagina.goto(`${BASE}#/${id}`);
    if (id === "atencion") await esperarAuto(pagina);
    else await pagina.waitForSelector("main h1", { timeout: 15_000 });
    await pagina.screenshot({ path: `${SALIDA}/pestana_${id}_${ancho}.png` });
  }
  await pagina.close();

  // Atención en reposo, escribiendo y respondiendo.
  const atencion = await abrir(ancho, alto);
  await atencion.goto(`${BASE}#/atencion`);
  await esperarAuto(atencion);
  await atencion.screenshot({ path: `${SALIDA}/atencion_reposo_${ancho}.png` });
  if (POSTER && ancho === 1600) {
    const lienzo = atencion.locator("canvas").first();
    if (await lienzo.count()) await lienzo.screenshot({ path: "public/assets/ignis_auto_poster.jpg", type: "jpeg", quality: 82 });
  }

  if (ancho < 1024) await atencion.getByRole("button", { name: "Abrir chat" }).click();
  await atencion.getByLabel("Mensaje para IGNIS").pressSequentially("¿Qué dice el corpus", { delay: 60 });
  if (ancho < 1024) await atencion.getByRole("button", { name: "Cerrar panel" }).click();
  await atencion.screenshot({ path: `${SALIDA}/atencion_escribiendo_${ancho}.png` });
  await atencion.waitForTimeout(1800);

  // Sin voz: el escáner sigue los tokens del SSE.
  if (ancho < 1024) await atencion.getByRole("button", { name: "Abrir chat" }).click();
  await atencion.getByRole("switch", { name: "Silenciar voz" }).check();
  await enviar(atencion, "¿Qué dice el corpus sobre la unidad de autopartes?");
  await atencion.waitForSelector(".ignis-app[data-estado='respondiendo']", { timeout: 5000 }).catch(() => undefined);
  await atencion.screenshot({ path: `${SALIDA}/atencion_respondiendo_sin_voz_${ancho}.png` });
  await atencion.waitForTimeout(2500);

  // Con voz: el escáner sigue el analizador del TTS.
  await atencion.getByRole("switch", { name: "Silenciar voz" }).uncheck();
  await enviar(atencion, "¿Qué dice el corpus sobre sostenibilidad?");
  await atencion.waitForSelector(".ignis-app[data-estado='hablando']", { timeout: 8000 }).catch(() => undefined);
  await atencion.waitForTimeout(600);
  await atencion.screenshot({ path: `${SALIDA}/atencion_respondiendo_con_voz_${ancho}.png` });
  await atencion.close();
}
await navegador.close();
console.log(`Capturas en ${SALIDA}/`);
