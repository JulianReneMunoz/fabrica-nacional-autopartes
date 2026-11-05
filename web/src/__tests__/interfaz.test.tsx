import { act } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { leerRuta } from "../App";
import Biblioteca from "../paginas/Biblioteca";
import MaquinaLinea from "../paginas/MaquinaLinea";

(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

const MAQUINAS = [
  {
    id: "freno",
    pregunta: "¿Cómo convierte un freno de disco la presión hidráulica en fuerza de frenado?",
    una_linea: "Despiece 3D",
    relacion: "T = 2 · μ · p · A · r",
    ruta: "#/maquina/freno",
    idea_principal: "idea",
    datos_empresa: [{ texto: "Fabricación de partes metálicas", url: "https://autopartesfanalca.com.co/", fragmento_id: "f1", origen: "scraping" }],
    parametros: [],
  },
  {
    id: "linea",
    pregunta: "¿Cada cuánto debe salir un chasis de la línea de ensamble?",
    una_linea: "takt",
    relacion: "takt = tiempo disponible / demanda",
    ruta: "#/maquina/linea",
    idea_principal: "La demanda fija el ritmo",
    datos_empresa: [],
    parametros: [{ nombre: "capacidad_anual", valor: 24000, unidad: "chasises/año", procedencia: "base_conocimiento", fuente: "https://autopartesfanalca.com.co/nosotros/" }],
  },
];

let contenedor: HTMLDivElement;
beforeEach(() => {
  contenedor = document.createElement("div");
  document.body.appendChild(contenedor);
  vi.stubGlobal("fetch", vi.fn(async (url: string) => {
    const cuerpo = url.endsWith("/maquinas") ? MAQUINAS : MAQUINAS.find((m) => url.endsWith(`/maquinas/${m.id}`));
    return new Response(JSON.stringify(cuerpo), { status: 200, headers: { "Content-Type": "application/json" } });
  }));
});
afterEach(() => {
  contenedor.remove();
  vi.unstubAllGlobals();
});

async function montar(elemento: React.ReactElement) {
  const raiz = createRoot(contenedor);
  await act(async () => raiz.render(elemento));
  await act(async () => new Promise((r) => setTimeout(r, 10)));
  return raiz;
}

describe("enrutador por hash", () => {
  it("separa ruta y parámetros", () => {
    const r = leerRuta("#/maquina/freno?tour=1");
    expect(r.ruta).toBe("/maquina/freno");
    expect(r.parametros.get("tour")).toBe("1");
    expect(leerRuta("").ruta).toBe("/");
  });
});

describe("biblioteca de máquinas", () => {
  it("muestra una tarjeta por máquina con pregunta, relación, dato con URL y botón", async () => {
    const raiz = await montar(<Biblioteca />);
    const tarjetas = contenedor.querySelectorAll("article.tarjeta");
    expect(tarjetas).toHaveLength(4); // la biblioteca sale de maquinas/*.ts; la API aporta los datos de la empresa
    expect(tarjetas[0].querySelector("h2")?.textContent).toContain("freno de disco");
    expect(tarjetas[0].querySelector(".relacion")?.textContent).toBe("T = 2 · μ · p · A · r");
    expect(tarjetas[0].querySelector(".datos a")?.getAttribute("href")).toBe("https://autopartesfanalca.com.co/");
    expect(tarjetas[0].querySelector(".insignia")?.textContent).toBe("scraping"); // visible en mayúsculas por CSS
    expect(tarjetas[0].querySelector("a.boton")?.getAttribute("href")).toBe("#/maquina/freno");
    act(() => raiz.unmount());
  });
});

describe("máquina línea", () => {
  it("toma la demanda de la base de conocimiento y muestra el takt", async () => {
    const raiz = await montar(<MaquinaLinea tour={false} />);
    expect(contenedor.textContent).toContain("24.000");
    expect(contenedor.textContent).toContain("takt = 11,52 min/chasis");
    expect(contenedor.querySelectorAll("input[type=range]").length).toBe(4);
    expect(contenedor.textContent).toContain("base de conocimiento");
    act(() => raiz.unmount());
  });
});
