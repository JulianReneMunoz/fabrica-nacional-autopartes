import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, describe, expect, it, vi } from "vitest";
import PestanaCorpus from "../PestanaCorpus";

(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

const json = (datos: unknown, estado = 200) =>
  new Response(JSON.stringify(datos), { status: estado, headers: { "Content-Type": "application/json" } });

const fragmento = (n: number, extra: Record<string, unknown> = {}) => ({
  id: `doc#${String(n).padStart(3, "0")}`,
  documento_id: "doc",
  url: "https://fanalca.com/nosotros",
  titulo: `Título ${n}`,
  seccion: n % 2 ? "nosotros" : "contacto",
  encabezado: `Encabezado ${n}`,
  idioma: "es",
  texto: `Texto completo del fragmento ${n}.`,
  tokens_aprox: 10 + n,
  orden: n,
  origen: "scraping",
  ...extra,
});

const ESTADISTICAS = {
  documentos: 2,
  fragmentos: 25,
  tokens_aprox: 500,
  secciones: { nosotros: 13, contacto: 12 },
  origenes: { scraping: 25 },
  urls: ["https://fanalca.com/nosotros"],
  generado_en: null,
};

type Modo = "ok" | "caida" | "error";

describe("pestaña Corpus", () => {
  let contenedor: HTMLDivElement;
  let raiz: Root;
  let pedidos: URLSearchParams[];

  afterEach(() => {
    act(() => raiz.unmount());
    contenedor.remove();
    vi.unstubAllGlobals();
  });

  async function esperar(condicion: () => boolean) {
    for (let i = 0; i < 60 && !condicion(); i++) {
      await act(async () => {
        await new Promise((r) => setTimeout(r, 20));
      });
    }
  }

  async function montar(modo: Modo = "ok") {
    pedidos = [];
    vi.stubGlobal("fetch", (async (entrada: RequestInfo | URL) => {
      const url = new URL(String(entrada), "http://localhost");
      if (url.pathname.endsWith("/base/estadisticas")) return json(ESTADISTICAS);
      if (!url.pathname.endsWith("/base/fragmentos") || modo === "caida") throw new TypeError("Failed to fetch");
      if (modo === "error") return json({ detail: "Traceback: /api/v1/base/fragmentos falló" }, 500);
      pedidos.push(url.searchParams);
      const pagina = Number(url.searchParams.get("pagina") ?? 1);
      const q = url.searchParams.get("q");
      const todos = Array.from({ length: q ? 1 : 25 }, (_, i) => fragmento(i + 1, q ? { titulo: `Coincide ${q}` } : {}));
      const tamano = Number(url.searchParams.get("tamano") ?? 10);
      const elementos = todos.slice((pagina - 1) * tamano, pagina * tamano).map((f) => ({ fragmento: f, puntaje: null }));
      return json({ elementos, total: todos.length, pagina, tamano });
    }) as typeof fetch);
    contenedor = document.createElement("div");
    document.body.appendChild(contenedor);
    raiz = createRoot(contenedor);
    await act(async () => {
      raiz.render(<PestanaCorpus />);
    });
    await esperar(() => contenedor.querySelector("[aria-busy='true']") === null);
  }

  const filas = () => Array.from(contenedor.querySelectorAll("tbody tr"));

  it("lista la primera página con título, sección, origen, tokens y URL segura", async () => {
    await montar();
    expect(filas()).toHaveLength(20);
    expect(pedidos[0].get("tamano")).toBe("20");
    const primera = filas()[0];
    expect(primera.textContent).toContain("Título 1");
    expect(primera.textContent).toContain("scraping");
    const enlace = primera.querySelector("a")!;
    expect(enlace.getAttribute("href")).toBe("https://fanalca.com/nosotros");
    expect(enlace.getAttribute("rel")).toBe("noopener noreferrer");
    expect(contenedor.textContent).toContain("25 fragmentos · Página 1 de 2");
    const secciones = Array.from(contenedor.querySelectorAll("#ig-corpus-seccion option")).map((o) => o.textContent);
    expect(secciones).toEqual(["Todas", "contacto", "nosotros"]);
  });

  it("pagina con Siguiente y Anterior", async () => {
    await montar();
    const [anterior, siguiente] = Array.from(contenedor.querySelectorAll<HTMLButtonElement>(".ig-corpus-paginacion button"));
    expect(anterior.disabled).toBe(true);
    await act(async () => siguiente.click());
    await esperar(() => contenedor.textContent?.includes("Página 2 de 2") ?? false);
    expect(filas()).toHaveLength(5);
    expect(pedidos.at(-1)?.get("pagina")).toBe("2");
  });

  it("busca por texto tras una pausa al escribir", async () => {
    await montar();
    const campo = contenedor.querySelector<HTMLInputElement>("#ig-corpus-busqueda")!;
    const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value")!.set!;
    await act(async () => {
      setter.call(campo, "sede");
      campo.dispatchEvent(new Event("input", { bubbles: true }));
    });
    await esperar(() => pedidos.some((p) => p.get("q") === "sede") && filas().length === 1);
    expect(filas()[0].textContent).toContain("Coincide sede");
    expect(pedidos.at(-1)?.get("pagina")).toBe("1");
  });

  it("al elegir un fragmento muestra su texto, su URL y su origen", async () => {
    await montar();
    await act(async () => filas()[0].querySelector("button")!.click());
    const detalle = contenedor.querySelector(".ig-corpus-detalle")!;
    expect(detalle.textContent).toContain("Texto completo del fragmento 1.");
    expect(detalle.textContent).toContain("Origen: scraping");
    expect(detalle.querySelector("a")?.getAttribute("href")).toBe("https://fanalca.com/nosotros");
  });

  it("con el backend caído o con error muestra un mensaje claro, sin URL ni detalles técnicos", async () => {
    await montar("caida");
    expect(contenedor.querySelector("[role='alert']")?.textContent).toContain("No se pudo conectar con el backend");
    expect(filas()).toHaveLength(0);
    act(() => raiz.unmount());
    contenedor.remove();

    await montar("error");
    expect(contenedor.querySelector("[role='alert']")?.textContent).toContain("HTTP 500");
    expect(contenedor.textContent).not.toContain("Traceback");
    expect(contenedor.textContent).not.toContain("/api/v1");
  });
});
