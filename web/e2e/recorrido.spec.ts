import { expect, test } from "@playwright/test";
import { execFileSync } from "node:child_process";
import { mkdirSync, mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";

/**
 * Graba el recorrido automático (< 30 s) de cada máquina como video MP4 para la presentación.
 * Se capturan los fotogramas con el screencast de Chrome (CDP) y se codifican con el ffmpeg del
 * sistema (H.264, preset veryfast). Requiere ffmpeg en el PATH (winget install Gyan.FFmpeg).
 */
const DESTINO = resolve("../docs/videos");

for (const id of ["freno", "prensa", "linea", "moto_honda"]) {
  test(`recorrido automático: ${id}`, async ({ page }, info) => {
    const cdp = await page.context().newCDPSession(page);
    const fotogramas: { datos: string; t: number }[] = [];
    cdp.on("Page.screencastFrame", async (f) => {
      fotogramas.push({ datos: f.data, t: f.metadata.timestamp ?? Date.now() / 1000 });
      await cdp.send("Page.screencastFrameAck", { sessionId: f.sessionId }).catch(() => undefined);
    });
    await page.goto(`/app/#/maquina/${id}?tour=1`);
    await cdp.send("Page.startScreencast", { format: "jpeg", quality: 85, maxWidth: 1280, maxHeight: 800, everyNthFrame: 1 });
    await page.waitForFunction(() => window.__tour?.estado === "corriendo", null, { timeout: 20_000 });
    const t0 = Date.now();
    await page.waitForFunction(() => window.__tour?.estado === "terminado", null, { timeout: 40_000 });
    const duracion = (Date.now() - t0) / 1000;
    await cdp.send("Page.stopScreencast");
    expect(duracion).toBeLessThan(30.5);
    // Se descartan los fotogramas de carga previos al tour: se conserva solo la ventana final de 29,4 s
    // medida con las marcas de tiempo del propio screencast (independiente del reloj del proceso).
    const tFinal = fotogramas[fotogramas.length - 1].t;
    const util = fotogramas.filter((f) => f.t >= tFinal - 29.4);
    fotogramas.splice(0, fotogramas.length, ...util);
    expect(fotogramas.length).toBeGreaterThan(20);

    // Lista concat de ffmpeg con la duración real de cada fotograma (respeta el ritmo del recorrido).
    const tmp = mkdtempSync(join(tmpdir(), "recorrido-"));
    const lineas: string[] = [];
    fotogramas.forEach((f, i) => {
      const nombre = join(tmp, `f${String(i).padStart(5, "0")}.jpg`);
      writeFileSync(nombre, Buffer.from(f.datos, "base64"));
      const dur = i + 1 < fotogramas.length ? Math.max(fotogramas[i + 1].t - f.t, 0.01) : 0.5;
      lineas.push(`file '${nombre.replace(/\\/g, "/")}'`, `duration ${dur.toFixed(3)}`);
    });
    lineas.push(`file '${join(tmp, `f${String(fotogramas.length - 1).padStart(5, "0")}.jpg`).replace(/\\/g, "/")}'`);
    writeFileSync(join(tmp, "lista.txt"), lineas.join("\n"));
    mkdirSync(DESTINO, { recursive: true });
    const salida = join(DESTINO, `recorrido_${id}.mp4`);
    execFileSync("ffmpeg", [
      "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", join(tmp, "lista.txt"),
      "-vf", "fps=30,scale=trunc(iw/2)*2:trunc(ih/2)*2", "-t", "29.95", "-c:v", "libx264", "-preset", "veryfast",
      "-crf", "23", "-pix_fmt", "yuv420p", "-movflags", "+faststart", salida,
    ]);
    rmSync(tmp, { recursive: true, force: true });
    info.annotations.push({ type: "video", description: `docs/videos/recorrido_${id}.mp4 (${duracion.toFixed(1)} s, ${fotogramas.length} fotogramas)` });
  });
}
