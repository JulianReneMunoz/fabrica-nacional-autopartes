import { act } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import App from "../App";
import { BarraLienzo } from "../componentes/plantilla/BarraLienzo";
import { ChipDato } from "../componentes/plantilla/ChipDato";
import { Deslizador } from "../componentes/plantilla/controles";
import { InsigniaFuente, TEXTO_FUENTE } from "../componentes/plantilla/InsigniaFuente";
import { PanelLateral } from "../componentes/plantilla/PanelLateral";
import { PlantillaMaquina } from "../componentes/plantilla/PlantillaMaquina";
import { TarjetaMaquina } from "../componentes/plantilla/TarjetaMaquina";
import { TextoEnLinea } from "../componentes/plantilla/TextoEnLinea";
import { MAQUINAS, PRENSA } from "../maquinas";
import MaquinaPrensa from "../paginas/MaquinaPrensa";

const fuentes = import.meta.glob(["../componentes/plantilla/*.tsx", "../paginas/MaquinaPrensa.tsx", "../paginas/MaquinaLinea.tsx", "../paginas/Biblioteca.tsx"], { query: "?raw", import: "default", eager: true }) as Record<string, string>;
const CSS = (Object.values(import.meta.glob("../estilos.css", { query: "?inline", import: "default", eager: true }))[0] as string) ?? "";

(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

let contenedor: HTMLDivElement;
beforeEach(() => {
  contenedor = document.createElement("div");
  document.body.appendChild(contenedor);
  vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify({}), { status: 404, headers: { "Content-Type": "application/json" } })));
});
afterEach(() => {
  contenedor.remove();
  vi.unstubAllGlobals();
  window.location.hash = "";
});

async function montar(el: React.ReactElement) {
  const raiz = createRoot(contenedor);
  await act(async () => raiz.render(el));
  await act(async () => new Promise((r) => setTimeout(r, 20)));
  return raiz;
}
const tour = () => (window as { __tour?: { estado: string } }).__tour;
const movimientoReducido = (reducido: boolean) =>
  vi.stubGlobal("matchMedia", (q: string) => ({ matches: reducido && q.includes("reduce"), media: q, addEventListener: () => undefined, removeEventListener: () => undefined }));

describe("InsigniaFuente", () => {
  it("cubre las fuentes pedidas, siempre con texto y en una sola línea", () => {
    for (const f of ["scraping", "lectura_web", "base_conocimiento", "ficha", "supuesto", "no_publicado"] as const) expect(TEXTO_FUENTE[f]).toBeTruthy();
    expect(CSS).toMatch(/\.insignia\s*\{[^}]*white-space:\s*nowrap/);
  });
  it("traduce los alias del backend y muestra el texto de la fuente", async () => {
    const raiz = await montar(
      <>
        <InsigniaFuente fuente="demostrativo" />
        <InsigniaFuente fuente="lectura_web" />
        <InsigniaFuente fuente="base_conocimiento" />
      </>,
    );
    const t = Array.from(contenedor.querySelectorAll(".insignia")).map((e) => e.textContent);
    expect(t).toEqual(["supuesto didáctico", "lectura web", "base de conocimiento"]);
    expect(contenedor.querySelector(".fuente-supuesto")).toBeTruthy();
    act(() => raiz.unmount());
  });
});

describe("ChipDato", () => {
  it("tiene cuatro variantes; el estado lleva ícono y texto, el supuesto lleva insignia", async () => {
    const raiz = await montar(
      <>
        <ChipDato etiqueta="a" valor="1" />
        <ChipDato etiqueta="b" valor="2" variante="dato" />
        <ChipDato etiqueta="c" valor="3" variante="supuesto" />
        <ChipDato etiqueta="d" valor="ok" variante="estado" ok />
        <ChipDato etiqueta="e" valor="mal" variante="estado" ok={false} />
      </>,
    );
    const v = Array.from(contenedor.querySelectorAll(".chip")).map((e) => e.getAttribute("data-variante"));
    expect(v).toEqual(["neutro", "dato", "supuesto", "estado", "estado"]);
    expect(contenedor.querySelectorAll(".chip-ok .chip-icono")[0].textContent).toBe("✓");
    expect(contenedor.querySelectorAll(".chip-alerta .chip-icono")[0].textContent).toBe("✕");
    expect(contenedor.querySelector(".chip-supuesto .insignia")).toBeTruthy();
    act(() => raiz.unmount());
  });
});

describe("TextoEnLinea y tarjeta de la biblioteca", () => {
  it("renderiza negrita sin asteriscos y no interpreta HTML", async () => {
    const raiz = await montar(<p><TextoEnLinea texto={"Plantas en **Yumbo** y **Bogotá** <img src=x onerror=alert(1)>"} /></p>);
    expect(contenedor.querySelectorAll("strong")).toHaveLength(2);
    expect(contenedor.textContent).not.toContain("*");
    expect(contenedor.querySelector("img")).toBeNull();
    expect(contenedor.textContent).toContain("<img");
    act(() => raiz.unmount());
  });
  it("la tarjeta limpia el Markdown de los datos de la empresa", async () => {
    const datos = { id: "freno", pregunta: "p", una_linea: "Planta en **Yumbo**", relacion: "r", ruta: "#/maquina/freno", idea_principal: "i", parametros: [], datos_empresa: [{ texto: "**Yumbo** y **Bogotá**", url: "https://fanalca.com/", fragmento_id: "f", origen: "scraping" }] };
    const raiz = await montar(<TarjetaMaquina def={MAQUINAS[0]} datos={datos} />);
    expect(contenedor.textContent).not.toContain("*");
    expect(contenedor.querySelectorAll("strong").length).toBeGreaterThanOrEqual(2);
    act(() => raiz.unmount());
  });
});

describe("BarraLienzo y PanelLateral", () => {
  it("la barra respeta el orden estándar y solo muestra los botones declarados", async () => {
    const f = () => undefined;
    const raiz = await montar(<BarraLienzo recorrido={{ alPulsar: f }} png={{ alPulsar: f }} despiece={{ alPulsar: f }} ensamblado={{ alPulsar: f }} />);
    expect(Array.from(contenedor.querySelectorAll("button")).map((b) => b.textContent)).toEqual(["Ensamblado", "Despiece", "⤓ PNG", "Recorrido 30 s"]);
    act(() => raiz.unmount());
  });
  it("las pestañas cambian con clic y con las flechas del teclado", async () => {
    const raiz = await montar(
      <PanelLateral pestanas={[{ id: "componentes", contenido: <p>uno</p> }, { id: "empresa", contenido: <p>dos</p> }, { id: "faq", contenido: <p>tres</p> }]} />,
    );
    const tabs = () => Array.from(contenedor.querySelectorAll<HTMLElement>('[role="tab"]'));
    expect(tabs().map((t) => t.textContent)).toEqual(["Componentes", "Datos de la empresa", "FAQ"]);
    expect(contenedor.querySelector('[role="tabpanel"]')?.textContent).toBe("uno");
    await act(async () => tabs()[0].dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowRight", bubbles: true })));
    expect(contenedor.querySelector('[role="tabpanel"]')?.textContent).toBe("dos");
    await act(async () => tabs()[1].click());
    expect(tabs()[1].getAttribute("aria-selected")).toBe("true");
    act(() => raiz.unmount());
  });
});

describe("accesibilidad de los controles", () => {
  it("los deslizadores tienen aria-label, aria-valuetext y son enfocables", async () => {
    const raiz = await montar(<Deslizador etiqueta="Presión hidráulica" valor={25} min={0} max={80} paso={1} unidad="bar" alCambiar={() => undefined} />);
    const r = contenedor.querySelector<HTMLInputElement>("input[type=range]")!;
    expect(r.getAttribute("aria-label")).toBe("Presión hidráulica");
    expect(r.getAttribute("aria-valuetext")).toBe("25 bar");
    expect(r.tabIndex).toBeGreaterThanOrEqual(0);
    act(() => raiz.unmount());
  });
  it("las hojas de estilo definen foco visible y movimiento reducido", () => {
    expect(CSS).toContain(":focus-visible");
    expect(CSS).toContain("prefers-reduced-motion: reduce");
  });
});

describe("tokens: ningún color fijo en componentes ni páginas", () => {
  it("sin literales #rrggbb fuera de tokens.css", () => {
    expect(Object.keys(fuentes).length).toBeGreaterThan(10);
    for (const [a, texto] of Object.entries(fuentes)) expect(texto, a).not.toMatch(/#[0-9a-fA-F]{6}\b|#[0-9a-fA-F]{3}\b(?![\w-])/);
  });
});

describe("plantilla común", () => {
  it("mantiene el orden: migas, título, fórmula, lienzo, controles, chips, idea, dos tarjetas y nota", async () => {
    const raiz = await montar(
      <PlantillaMaquina
        def={PRENSA}
        maquina={null}
        errorApi={null}
        barra={{ recorrido: { alPulsar: () => undefined } }}
        lienzo={<div data-testid="lienzo" />}
        leyenda="x"
        banda={{ texto: null, transcurrido: 0, duracion: 28 }}
        controles={<p>mandos</p>}
        contenidoPestanas={{}}
        chips={<ChipDato etiqueta="F" valor="1" />}
        pasoActual={-1}
        experimentos={[{ pregunta: "q", opciones: [{ texto: "a", correcta: true }], explicacion: "e", aplicar: () => undefined }]}
      />,
    );
    const orden = [".migas", "h1.titular", ".franja-formula", ".lienzo-col", ".lateral-col", ".lecturas", "[data-testid=idea-principal]", ".dos-tarjetas", ".pie-nota"];
    const posiciones = orden.map((s) => {
      const el = contenedor.querySelector(s);
      expect(el, s).toBeTruthy();
      return Array.from(contenedor.querySelectorAll("*")).indexOf(el!);
    });
    expect([...posiciones].sort((a, b) => a - b)).toEqual(posiciones);
    expect(contenedor.querySelector(".lateral-col section[aria-label=Controles]")).toBeTruthy();
    expect(contenedor.querySelector(".pie-nota")?.textContent).toBe("Cifras demostrativas; los datos de la empresa provienen de fuentes oficiales citadas por URL.");
    expect(contenedor.querySelectorAll(".dos-tarjetas > section")).toHaveLength(2);
    act(() => raiz.unmount());
  });
});

describe("navegación unificada", () => {
  it("muestra Biblioteca · Freno · Prensa · Línea · Moto · Explorador · API con la página activa marcada", async () => {
    window.location.hash = "#/maquina/prensa";
    const raiz = await montar(<App />);
    const enlaces = Array.from(contenedor.querySelectorAll("header nav a"));
    expect(enlaces.map((a) => a.textContent)).toEqual(["Biblioteca", "Freno", "Prensa", "Línea", "Moto", "Explorador", "API"]);
    expect(contenedor.querySelector('header nav a[aria-current="page"]')?.textContent).toBe("Prensa");
    expect(contenedor.querySelector(".boton-menu")).toBeTruthy();
    act(() => raiz.unmount());
  });
});

describe("prefers-reduced-motion", () => {
  it("con la preferencia activa el recorrido ?tour=1 no se inicia solo y se informa", async () => {
    movimientoReducido(true);
    delete window.__tour;
    const raiz = await montar(<MaquinaPrensa tour />);
    await act(async () => new Promise((r) => setTimeout(r, 700)));
    expect(tour()).toBeUndefined();
    expect(contenedor.querySelector(".tour-banda")?.textContent).toContain("Movimiento reducido");
    act(() => raiz.unmount());
  });
  it("sin la preferencia el recorrido sí arranca", async () => {
    movimientoReducido(false);
    delete window.__tour;
    const raiz = await montar(<MaquinaPrensa tour />);
    await act(async () => new Promise((r) => setTimeout(r, 900)));
    expect(tour()?.estado).toBe("corriendo");
    act(() => raiz.unmount());
    delete window.__tour;
  });
  it("con la preferencia activa, el botón «Recorrido 30 s» (orden explícita) sí lo inicia", async () => {
    movimientoReducido(true);
    delete window.__tour;
    window.location.hash = "#/maquina/prensa?tour=1&inicio=manual";
    const raiz = await montar(<MaquinaPrensa tour />);
    await act(async () => new Promise((r) => setTimeout(r, 900)));
    expect(tour()?.estado).toBe("corriendo");
    act(() => raiz.unmount());
    delete window.__tour;
  });
});
