import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, describe, expect, it, vi } from "vitest";
import PestanaBase from "../PestanaBase";

(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

const json = (datos: unknown, estado = 200) =>
  new Response(JSON.stringify(datos), { status: estado, headers: { "Content-Type": "application/json" } });

const ESTADISTICAS = {
  documentos: 12,
  fragmentos: 340,
  tokens_aprox: 51234,
  secciones: { productos: 200, empresa: 140 },
  origenes: { scraping: 300, semilla: 40 },
  urls: ["https://autopartesfanalca.com.co/", "https://fanalca.com/"],
  generado_en: "2026-11-19T10:00:00Z",
};

const VECTORIAL = {
  disponible: true,
  motivo: "",
  modo: "local",
  coleccion: "ignis_fanalca",
  puntos: 340,
  dimension: 384,
  distancia: "Cosine",
  hnsw_m: 16,
  hnsw_ef_construct: 100,
  umbral_busqueda_exacta_kb: 10000,
  vectores_indexados: 0,
  tipo_busqueda: "exacta",
  explicacion: "Con pocos puntos Qdrant compara contra todos los vectores (búsqueda exacta).",
  campos_payload: ["id", "url", "origen"],
  modelo: "multilingual-e5-small",
  revision: "",
  generado_en: null,
  recuperador_ignis: "hibrido",
};

type Respuesta = Response | "caida";

function fetchBase(estadisticas: Respuesta, vectorial: Respuesta) {
  return (async (entrada: RequestInfo | URL) => {
    const url = String(entrada);
    const r = url.endsWith("/base/estadisticas") ? estadisticas : url.endsWith("/base/vectorial") ? vectorial : "caida";
    if (r === "caida") throw new TypeError("Failed to fetch");
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

describe("pestaña Base de conocimiento", () => {
  let contenedor: HTMLDivElement;
  let raiz: Root;

  afterEach(() => {
    act(() => raiz.unmount());
    contenedor.remove();
    vi.unstubAllGlobals();
  });

  async function montar(estadisticas: Respuesta, vectorial: Respuesta) {
    vi.stubGlobal("fetch", fetchBase(estadisticas, vectorial));
    contenedor = document.createElement("div");
    document.body.appendChild(contenedor);
    raiz = createRoot(contenedor);
    await act(async () => {
      raiz.render(<PestanaBase />);
    });
    await esperar(() => contenedor.querySelector("[aria-busy='true']") === null);
  }

  it("con datos muestra las cifras del corpus y el estado de la base vectorial", async () => {
    await montar(json(ESTADISTICAS), json(VECTORIAL));
    const texto = contenedor.textContent ?? "";
    expect(texto).toContain("Documentos12");
    expect(texto).toContain("Fragmentos340");
    expect(texto).toContain("URL distintas2");
    expect(contenedor.querySelectorAll("tbody tr")).toHaveLength(4);
    expect(texto).toContain("DisponibleSí");
    expect(texto).toContain("Local (archivo en disco)");
    expect(texto).toContain("ignis_fanalca");
    expect(texto).toContain("Puntos340");
    expect(texto).toContain("Tipo de búsquedaExacta");
    expect(texto).toContain("búsqueda exacta");
    expect(texto).toContain("Recuperador de IGNIShibrido");
    expect(Array.from(contenedor.querySelectorAll(".ig-base-vectorial ~ p code")).map((c) => c.textContent?.trim())).toEqual([
      "id",
      "url",
      "origen",
    ]);
  });

  it("base vacía y Qdrant no disponible: estado vacío y motivo, sin puntos", async () => {
    const vacia = { ...ESTADISTICAS, documentos: 0, fragmentos: 0, tokens_aprox: 0, secciones: {}, origenes: {}, urls: [] };
    await montar(json(vacia), json({ ...VECTORIAL, disponible: false, puntos: 0, motivo: "qdrant-client no está instalado." }));
    expect(contenedor.querySelector("[role='status']")?.textContent).toContain("aún no tiene documentos");
    expect(contenedor.querySelector("table")).toBeNull();
    const texto = contenedor.textContent ?? "";
    expect(texto).toContain("DisponibleNo");
    expect(texto).toContain("Motivo: qdrant-client no está instalado.");
    expect(texto).not.toContain("Puntos");
  });

  it("con el backend caído muestra el error claro, sin trazas ni cifras", async () => {
    await montar("caida", json({ detail: "Traceback (most recent call last): ..." }, 500));
    const alertas = Array.from(contenedor.querySelectorAll("[role='alert']")).map((a) => a.textContent ?? "");
    expect(alertas).toHaveLength(2);
    expect(alertas[0]).toContain("No se pudo conectar con el backend");
    expect(alertas[1]).toContain("HTTP 500");
    const texto = contenedor.textContent ?? "";
    expect(texto).not.toContain("Traceback");
    for (const cifra of ["Documentos", "Fragmentos", "Puntos", "340", "12"]) expect(texto).not.toContain(cifra);
  });
});
