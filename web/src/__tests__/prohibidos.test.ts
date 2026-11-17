import { describe, expect, it } from "vitest";

/**
 * Criterio de aceptación 4: nada en web/ referencia Streamlit, Gradio (Anuncio 006), el robot retirado ni sus
 * estados de transformación. Se revisan las fuentes, las pruebas e2e, los scripts y el HTML de entrada.
 * Los términos se arman por partes para que este archivo no se detecte a sí mismo.
 */
const PROHIBIDOS = [["stream", "lit"], ["gra", "dio"], ["ignis", "_robot"], ["transfor", "mando"], ["robot", "_reposo"]].map((p) => p.join(""));

const archivos = {
  ...import.meta.glob(["../**/*.{ts,tsx,css}", "!./prohibidos.test.ts"], { query: "?raw", import: "default", eager: true }),
  ...import.meta.glob("/e2e/**/*.ts", { query: "?raw", import: "default", eager: true }),
  ...import.meta.glob("/scripts/**/*.mjs", { query: "?raw", import: "default", eager: true }),
  ...import.meta.glob("/index.html", { query: "?raw", import: "default", eager: true }),
} as Record<string, string>;

describe("referencias prohibidas en web/", () => {
  it("revisa fuentes, e2e, scripts e index.html", () => {
    const rutas = Object.keys(archivos);
    expect(rutas.some((r) => r.includes("/e2e/"))).toBe(true);
    expect(rutas.some((r) => r.includes("/scripts/"))).toBe(true);
    expect(rutas.some((r) => r.endsWith("index.html"))).toBe(true);
    expect(rutas.some((r) => r.endsWith("prohibidos.test.ts"))).toBe(false);
  });

  it.each(PROHIBIDOS)("ningún archivo menciona «%s»", (termino) => {
    const encontrados = Object.entries(archivos)
      .filter(([, texto]) => texto.toLowerCase().includes(termino))
      .map(([ruta]) => ruta);
    expect(encontrados).toEqual([]);
  });
});
