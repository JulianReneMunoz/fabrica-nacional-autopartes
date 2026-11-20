import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, describe, expect, it, vi } from "vitest";
import PestanaQa from "../PestanaQa";
import { vaciarCacheOrigenes } from "../origenFuentes";

(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

const json = (datos: unknown, estado = 200) =>
  new Response(JSON.stringify(datos), { status: estado, headers: { "Content-Type": "application/json" } });

const RESPUESTA = {
  pregunta: "¿Dónde queda la sede principal?",
  respuesta: "La sede principal está en Cali.",
  fuentes: [
    { fragmento_id: "empresa#004", titulo: "Nosotros", url: "https://fanalca.com/nosotros" },
    { fragmento_id: "semilla#001", titulo: "Semilla", url: "semilla://empresa" },
  ],
  fundamentada: true,
  confianza: "alta",
  version_prompt: "v3",
  proveedor: "extractivo",
  modelo: "bm25",
  modo_contexto: "auto",
  recuperador: "bm25",
  latencia_ms: 42,
};

type Respuesta = Response | "caida";

describe("pestaña Consulta puntual Q&A", () => {
  let contenedor: HTMLDivElement;
  let raiz: Root;
  let cuerpos: unknown[];

  afterEach(() => {
    act(() => raiz.unmount());
    contenedor.remove();
    vi.unstubAllGlobals();
  });

  async function montar(r: Respuesta, origenes: Record<string, string> = {}) {
    cuerpos = [];
    vaciarCacheOrigenes();
    vi.stubGlobal("fetch", (async (entrada: RequestInfo | URL, init?: RequestInit) => {
      const fragmento = String(entrada).match(/\/base\/fragmentos\/(.+)$/);
      if (fragmento) {
        const id = decodeURIComponent(fragmento[1]);
        if (!(id in origenes)) throw new TypeError("Failed to fetch");
        return json({ id, url: "https://fanalca.com/", origen: origenes[id] });
      }
      if (r === "caida" || !String(entrada).endsWith("/tareas/qa")) throw new TypeError("Failed to fetch");
      cuerpos.push(JSON.parse(String(init?.body)));
      return r.clone();
    }) as typeof fetch);
    contenedor = document.createElement("div");
    document.body.appendChild(contenedor);
    raiz = createRoot(contenedor);
    await act(async () => {
      raiz.render(<PestanaQa />);
    });
  }

  const boton = () => contenedor.querySelector<HTMLButtonElement>("button[type='submit']")!;

  async function escribir(texto: string) {
    const campo = contenedor.querySelector<HTMLTextAreaElement>("#ig-qa-pregunta")!;
    const setter = Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, "value")!.set!;
    await act(async () => {
      setter.call(campo, texto);
      campo.dispatchEvent(new Event("input", { bubbles: true }));
    });
  }

  async function elegirRecuperador(valor: string) {
    const select = contenedor.querySelector<HTMLSelectElement>("#ig-qa-recuperador")!;
    const setter = Object.getOwnPropertyDescriptor(HTMLSelectElement.prototype, "value")!.set!;
    await act(async () => {
      setter.call(select, valor);
      select.dispatchEvent(new Event("change", { bubbles: true }));
    });
  }

  async function enviar() {
    await act(async () => {
      boton().click();
    });
    for (let i = 0; i < 40 && contenedor.querySelector("[aria-busy='true']"); i++) {
      await act(async () => {
        await new Promise((r) => setTimeout(r, 20));
      });
    }
  }

  it("muestra el aviso, envía la pregunta y dibuja respuesta, fuentes y pie", async () => {
    await montar(json(RESPUESTA));
    expect(contenedor.textContent).toContain("Consulta sin memoria: cada pregunta es independiente. No escribas datos personales.");
    expect(contenedor.querySelector<HTMLTextAreaElement>("#ig-qa-pregunta")!.maxLength).toBe(500);
    await escribir("¿Dónde queda la sede principal?");
    await elegirRecuperador("semantico");
    await enviar();

    expect(cuerpos).toEqual([{ pregunta: "¿Dónde queda la sede principal?", recuperador: "semantico" }]);
    const resultado = contenedor.querySelector(".ig-qa-resultado")!;
    expect(resultado.textContent).toContain("La sede principal está en Cali.");
    expect(resultado.textContent).toContain("Confianzaalta");
    expect(resultado.textContent).toContain("FundamentadaSí");
    expect(resultado.textContent).not.toContain("Sin respaldo en la base");
    const enlaces = resultado.querySelectorAll<HTMLAnchorElement>(".ig-qa-fuentes a");
    expect(enlaces).toHaveLength(1);
    expect(enlaces[0].getAttribute("href")).toBe("https://fanalca.com/nosotros");
    expect(enlaces[0].getAttribute("target")).toBe("_blank");
    expect(enlaces[0].getAttribute("rel")).toBe("noopener noreferrer");
    expect(resultado.querySelector(".ig-qa-fuentes span")?.textContent).toBe("Semilla");
    const pie = resultado.querySelector(".ig-qa-pie")?.textContent ?? "";
    expect(pie).toContain("extractivo / bm25");
    expect(pie).toContain("Prompt: v3");
    expect(pie).toContain("Contexto: auto");
    expect(pie).toContain("Recuperador: bm25");
    expect(pie).toContain("Latencia: 42 ms");
  });

  it("sin recuperador elegido no envía el campo", async () => {
    await montar(json(RESPUESTA));
    await escribir("¿Qué fabrica Fanalca?");
    await enviar();
    expect(cuerpos).toEqual([{ pregunta: "¿Qué fabrica Fanalca?" }]);
  });

  it("el botón está deshabilitado con la pregunta vacía o solo con espacios", async () => {
    await montar(json(RESPUESTA));
    expect(boton().disabled).toBe(true);
    await escribir("   ");
    expect(boton().disabled).toBe(true);
    await escribir("Hola");
    expect(boton().disabled).toBe(false);
  });

  it("marca «Sin respaldo en la base» si no está fundamentada o la confianza es ninguna", async () => {
    await montar(json({ ...RESPUESTA, fundamentada: false, confianza: "ninguna", fuentes: [] }));
    await escribir("¿Cuál es el precio del rin?");
    await enviar();
    const resultado = contenedor.querySelector(".ig-qa-resultado")!;
    expect(resultado.textContent).toContain("Sin respaldo en la base");
    expect(resultado.textContent).toContain("FundamentadaNo");
    act(() => raiz.unmount());
    contenedor.remove();

    await montar(json({ ...RESPUESTA, fundamentada: true, confianza: "ninguna" }));
    await escribir("Otra pregunta");
    await enviar();
    expect(contenedor.querySelector(".ig-qa-resultado")!.textContent).toContain("Sin respaldo en la base");
  });

  it("con error muestra un mensaje claro, sin URL ni detalles técnicos", async () => {
    await montar("caida");
    await escribir("¿Dónde queda la sede?");
    await enviar();
    expect(contenedor.querySelector("[role='alert']")?.textContent).toContain("No se pudo conectar con el backend");
    expect(contenedor.querySelector(".ig-qa-resultado")).toBeNull();
    act(() => raiz.unmount());
    contenedor.remove();

    await montar(json({ detail: "Traceback: /api/v1/tareas/qa falló" }, 500));
    await escribir("¿Dónde queda la sede?");
    await enviar();
    expect(contenedor.querySelector("[role='alert']")?.textContent).toContain("HTTP 500");
    expect(contenedor.textContent).not.toContain("Traceback");
    expect(contenedor.textContent).not.toContain("/api/v1");
  });
  it("muestra el origen real de cada fuente y «origen no disponible» cuando el backend no lo entrega", async () => {
    await montar(json(RESPUESTA), { "empresa#004": "scraping" });
    await escribir("¿Dónde queda la sede principal?");
    await enviar();
    const origenes = () =>
      Array.from(contenedor.querySelectorAll(".ig-qa-fuentes .ig-fuente-origen")).map((o) => o.textContent ?? "");
    for (let i = 0; i < 40 && origenes().some((o) => o.includes("cargando")); i++) {
      await act(async () => {
        await new Promise((r) => setTimeout(r, 20));
      });
    }
    expect(origenes()).toEqual(["(origen: scraping)", "(origen no disponible)"]);
  });
});
