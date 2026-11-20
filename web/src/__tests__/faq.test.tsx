import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, describe, expect, it, vi } from "vitest";
import PestanaFaq from "../PestanaFaq";
import { vaciarCacheOrigenes } from "../origenFuentes";

(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

const json = (datos: unknown, estado = 200) =>
  new Response(JSON.stringify(datos), { status: estado, headers: { "Content-Type": "application/json" } });

const FAQ = {
  generado: "2026-11-19T10:00:00Z",
  proveedor: "ollama",
  modelo: "qwen2.5:7b",
  version_prompt: "v3",
  advertencia: "Respuestas generadas automáticamente a partir del corpus de Fanalca.",
  total: 3,
  items: [
    {
      id: "faq-1",
      categoria: "Productos",
      pregunta: "¿Qué autopartes fabrica Fanalca?",
      respuesta: "Fabrica rines y piezas de suspensión.",
      rechazo: false,
      fundamentada: true,
      confianza: "alta",
      fuentes: [{ fragmento_id: "autopartes#001", url: "https://autopartesfanalca.com.co/productos" }],
    },
    {
      id: "faq-2",
      categoria: "Empresa",
      pregunta: "¿Dónde está la planta?",
      respuesta: "La planta está en Cali.",
      rechazo: false,
      fundamentada: true,
      confianza: "media",
      fuentes: [{ fragmento_id: "empresa#004", url: "https://fanalca.com/nosotros" }],
    },
    {
      id: "faq-3",
      categoria: "Productos",
      pregunta: "¿Cuál es el precio del rin?",
      respuesta: "La información solicitada no se encuentra en la base de conocimiento de Fanalca.",
      rechazo: true,
      fundamentada: false,
      confianza: "ninguna",
      fuentes: [],
    },
  ],
};

type Respuesta = Response | "caida";

let pedidosOrigen: string[] = [];

function fetchFaq(r: Respuesta, origenes: Record<string, string> = {}) {
  return (async (entrada: RequestInfo | URL) => {
    const url = String(entrada);
    const fragmento = url.match(/\/base\/fragmentos\/(.+)$/);
    if (fragmento) {
      const id = decodeURIComponent(fragmento[1]);
      pedidosOrigen.push(id);
      if (!(id in origenes)) throw new TypeError("Failed to fetch");
      return json({ id, url: "https://fanalca.com/", origen: origenes[id] });
    }
    if (r === "caida" || !url.endsWith("/faq-visor")) throw new TypeError("Failed to fetch");
    return r.clone();
  }) as typeof fetch;
}

async function esperar(condicion: () => boolean) {
  for (let i = 0; i < 40 && !condicion(); i++) {
    await act(async () => {
      await new Promise((r) => setTimeout(r, 20));
    });
  }
}

describe("pestaña Preguntas frecuentes", () => {
  let contenedor: HTMLDivElement;
  let raiz: Root;

  afterEach(() => {
    act(() => raiz.unmount());
    contenedor.remove();
    vi.unstubAllGlobals();
    vaciarCacheOrigenes();
    pedidosOrigen = [];
  });

  async function montar(r: Respuesta, origenes: Record<string, string> = {}) {
    vi.stubGlobal("fetch", fetchFaq(r, origenes));
    contenedor = document.createElement("div");
    document.body.appendChild(contenedor);
    raiz = createRoot(contenedor);
    await act(async () => {
      raiz.render(<PestanaFaq />);
    });
    await esperar(() => contenedor.querySelector("[aria-busy='true']") === null);
  }

  const preguntas = () => Array.from(contenedor.querySelectorAll(".ig-faq-item summary")).map((s) => s.textContent ?? "");

  async function buscar(texto: string) {
    const campo = contenedor.querySelector<HTMLInputElement>("#ig-faq-busqueda")!;
    const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value")!.set!;
    await act(async () => {
      setter.call(campo, texto);
      campo.dispatchEvent(new Event("input", { bubbles: true }));
    });
  }

  async function elegirCategoria(valor: string) {
    const select = contenedor.querySelector<HTMLSelectElement>("#ig-faq-categoria")!;
    const setter = Object.getOwnPropertyDescriptor(HTMLSelectElement.prototype, "value")!.set!;
    await act(async () => {
      setter.call(select, valor);
      select.dispatchEvent(new Event("change", { bubbles: true }));
    });
  }

  it("carga las preguntas con su respuesta, confianza, fuentes externas y el pie", async () => {
    await montar(json(FAQ));
    expect(preguntas()).toHaveLength(3);
    const primera = contenedor.querySelector<HTMLDetailsElement>(".ig-faq-item")!;
    expect(primera.textContent).toContain("Fabrica rines y piezas de suspensión.");
    expect(primera.textContent).toContain("Confianza alta");
    const enlace = primera.querySelector<HTMLAnchorElement>(".ig-faq-fuentes a")!;
    expect(enlace.getAttribute("href")).toBe("https://autopartesfanalca.com.co/productos");
    expect(enlace.getAttribute("target")).toBe("_blank");
    expect(enlace.getAttribute("rel")).toBe("noopener noreferrer");
    const pie = contenedor.querySelector(".ig-faq-pie")?.textContent ?? "";
    expect(pie).toContain("Respuestas generadas automáticamente");
    expect(pie).toContain("ollama / qwen2.5:7b");
    expect(pie).toContain("Prompt: v3");
    expect(pie).toContain("Generado: 2026-11-19T10:00:00Z");
    expect(contenedor.textContent).not.toContain("Preguntar a IGNIS");
  });

  it("filtra por texto sin acentos ni mayúsculas, en pregunta y respuesta", async () => {
    await montar(json(FAQ));
    await buscar("DONDE");
    expect(preguntas()).toEqual(["¿Dónde está la planta?"]);
    await buscar("suspension");
    expect(preguntas()).toEqual(["¿Qué autopartes fabrica Fanalca?"]);
    await buscar("xyz inexistente");
    expect(preguntas()).toHaveLength(0);
    expect(contenedor.textContent).toContain("Ninguna pregunta coincide con la búsqueda");
  });

  it("filtra por categoría y muestra el conteo de cada una", async () => {
    await montar(json(FAQ));
    const opciones = Array.from(contenedor.querySelectorAll("#ig-faq-categoria option")).map((o) => o.textContent);
    expect(opciones).toEqual(["Todas (3)", "Empresa (1)", "Productos (2)"]);
    await elegirCategoria("Empresa");
    expect(preguntas()).toEqual(["¿Dónde está la planta?"]);
    await elegirCategoria("Productos");
    expect(preguntas()).toHaveLength(2);
  });

  it("una pregunta con rechazo se marca «Sin respaldo en la base» y muestra la frase de rechazo fija", async () => {
    await montar(json(FAQ));
    const rechazada = contenedor.querySelectorAll<HTMLDetailsElement>(".ig-faq-item")[2];
    expect(rechazada.querySelector("summary")?.textContent).toContain("Sin respaldo en la base");
    expect(rechazada.querySelector("summary ~ p")?.textContent).toBe(
      "La información solicitada no se encuentra en la base de conocimiento de Fanalca.",
    );
    expect(rechazada.querySelector(".ig-faq-fuentes")).toBeNull();
  });

  it("con el backend caído o con error muestra un mensaje claro, sin URL ni detalles técnicos", async () => {
    await montar("caida");
    let alerta = contenedor.querySelector("[role='alert']")?.textContent ?? "";
    expect(alerta).toContain("No se pudo conectar con el backend");
    expect(contenedor.querySelector(".ig-faq-item")).toBeNull();
    act(() => raiz.unmount());
    contenedor.remove();

    await montar(json({ detail: "Traceback: /api/v1/faq-visor falló" }, 500));
    alerta = contenedor.querySelector("[role='alert']")?.textContent ?? "";
    expect(alerta).toContain("HTTP 500");
    expect(contenedor.textContent).not.toContain("Traceback");
    expect(contenedor.textContent).not.toContain("/api/v1");
    expect(contenedor.querySelector(".ig-faq-item")).toBeNull();
  });

  it("sin preguntas generadas muestra el estado vacío", async () => {
    await montar(json({ ...FAQ, total: 0, items: [] }));
    expect(contenedor.querySelector("[role='status']")?.textContent).toContain("Aún no hay preguntas frecuentes generadas");
  });
  it("pide el origen de las fuentes solo al desplegar la pregunta y lo muestra junto a la URL", async () => {
    await montar(json(FAQ), { "autopartes#001": "lectura_web" });
    expect(pedidosOrigen).toEqual([]);
    const primera = contenedor.querySelector<HTMLDetailsElement>(".ig-faq-item")!;
    await act(async () => {
      primera.open = true;
      primera.dispatchEvent(new Event("toggle"));
    });
    await esperar(() => primera.querySelector(".ig-fuente-origen")?.textContent === "(origen: lectura_web)");
    expect(primera.querySelector(".ig-fuente-origen")?.textContent).toBe("(origen: lectura_web)");
    expect(pedidosOrigen).toEqual(["autopartes#001"]);
  });

  it("si el backend no entrega el origen muestra «origen no disponible» sin deducirlo", async () => {
    await montar(json(FAQ));
    const segunda = contenedor.querySelectorAll<HTMLDetailsElement>(".ig-faq-item")[1];
    await act(async () => {
      segunda.open = true;
      segunda.dispatchEvent(new Event("toggle"));
    });
    await esperar(() => segunda.querySelector(".ig-fuente-origen")?.textContent === "(origen no disponible)");
    expect(segunda.querySelector(".ig-fuente-origen")?.textContent).toBe("(origen no disponible)");
  });
});
