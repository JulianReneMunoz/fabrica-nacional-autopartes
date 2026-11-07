/** Fase 9 (ADR-019): el botón «Buscar en la web con Claude» solo aparece tras la frase de rechazo. */
import { act } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { esRechazo, FRASE_RECHAZO } from "../componentes/panelesMoto";
import { FaqFanalcaAuto } from "../componentes/plantilla/PanelFaq";

(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

const ETIQUETA = "Respuesta complementaria desde la web — no proviene de la base verificada";
let contenedor: HTMLDivElement;
let respuestaQa: string;
const posts: string[] = [];

beforeEach(() => {
  contenedor = document.createElement("div");
  document.body.appendChild(contenedor);
  posts.length = 0;
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string, init?: RequestInit) => {
      const ok = (c: unknown, status = 200) => new Response(JSON.stringify(c), { status, headers: { "Content-Type": "application/json" } });
      if (init?.method === "POST") posts.push(url);
      if (url.endsWith("/faq-visor")) return ok({ detail: "no" }, 404);
      if (url.endsWith("/tareas/qa"))
        return ok({ pregunta: "¿Cuántos empleados?", respuesta: respuestaQa, fuentes: [], fundamentada: false, confianza: "ninguna", proveedor: "p", modelo: "m" });
      if (url.endsWith("/tareas/qa-web"))
        return ok({
          pregunta: "¿Cuántos empleados?", respuesta: "Dato encontrado.", encontrado: true, etiqueta: ETIQUETA, fecha_consulta: "2026-11-06", proveedor: "claude_code", modelo: "sonnet", latencia_ms: 10,
          hallazgos: [{ dato: "Dato encontrado", url: "https://fanalca.com/x", fecha_consulta: "2026-11-06" }],
        });
      return ok({}, 404);
    }),
  );
});
afterEach(() => {
  contenedor.remove();
  vi.unstubAllGlobals();
});

async function preguntar() {
  const raiz = createRoot(contenedor);
  await act(async () => raiz.render(<FaqFanalcaAuto />));
  const entrada = contenedor.querySelector<HTMLInputElement>("#pregunta-en-vivo")!;
  await act(async () => {
    Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value")!.set!.call(entrada, "¿Cuántos empleados?");
    entrada.dispatchEvent(new Event("input", { bubbles: true }));
  });
  await act(async () => contenedor.querySelector<HTMLFormElement>("form.en-vivo")!.requestSubmit());
  await act(async () => new Promise((r) => setTimeout(r, 10)));
  return raiz;
}

describe("búsqueda web complementaria en el visor", () => {
  it("con una respuesta de la base no ofrece la búsqueda web (nunca automática)", async () => {
    respuestaQa = "Fanalca tiene su sede en Yumbo [f1].";
    const raiz = await preguntar();
    expect(contenedor.querySelector('[data-testid="buscar-web"]')).toBeNull();
    expect(posts.some((u) => u.endsWith("/qa-web"))).toBe(false);
    act(() => raiz.unmount());
  });

  it("tras la frase de rechazo ofrece el botón y muestra la respuesta etiquetada con URL y fecha", async () => {
    respuestaQa = FRASE_RECHAZO;
    const raiz = await preguntar();
    expect(posts.some((u) => u.endsWith("/qa-web"))).toBe(false); // no se busca hasta que se pulse
    await act(async () => contenedor.querySelector<HTMLButtonElement>('[data-testid="buscar-web"]')!.click());
    await act(async () => new Promise((r) => setTimeout(r, 10)));
    const web = contenedor.querySelector('[data-testid="respuesta-web"]')!;
    expect(web.textContent).toContain(ETIQUETA);
    expect(web.textContent).toContain("2026-11-06");
    expect(web.querySelector("a")?.getAttribute("href")).toBe("https://fanalca.com/x");
    act(() => raiz.unmount());
  });
});

describe("esRechazo replica llm.salvaguardas.es_rechazo", () => {
  it("acepta la frase fija y su núcleo, y rechaza respuestas normales", () => {
    expect(esRechazo(FRASE_RECHAZO)).toBe(true);
    expect(esRechazo(`  ${FRASE_RECHAZO.toUpperCase()}  `)).toBe(true);
    expect(esRechazo("El dato no se encuentra en la base de conocimiento disponible.")).toBe(true);
    expect(esRechazo("La sede principal está en Yumbo [f1].")).toBe(false);
  });
});
