import { act } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import MaquinaMoto from "../paginas/MaquinaMoto";
import Biblioteca from "../paginas/Biblioteca";

// El lienzo WebGL no existe en jsdom: la escena se sustituye por un marcador.
vi.mock("../paginas/EscenaMoto", () => ({ default: () => <div data-testid="escena-falsa" /> }));

(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

const campo = (valor: unknown, estado: string, extra: object = {}) => ({ valor, unidad: null, fuente: estado === "no_publicado" ? null : "lamina-cb160-std-dlx (aportada por el usuario)", fecha_consulta: estado === "no_publicado" ? null : "2026-11-04", estado, ...extra });
const FICHA = {
  id: "cb160f",
  nombre: "CB 160F",
  categoria: "Sport (naked)",
  versiones: ["STD", "DLX"],
  grupos: {
    motor: { tipo: campo("Honda 4T", "publicado"), cilindrada: campo(null, "no_publicado") },
    llantas: { trasera: campo("140/70-17", "publicado", { unidad: "ancho/perfil-rin" }) },
  },
  por_version: { STD: { cbs: campo(false, "publicado") }, DLX: { cbs: campo(true, "publicado") } },
  pendientes_de_confirmar: [],
  fuentes: [{ id: "lamina-cb160-std-dlx", descripcion: "Lámina", url: null, fecha_consulta: "2026-11-04", estado_acceso: null }],
  supuestos: [],
  ensamblaje_id: "moto_honda",
  titulo_biblioteca: "Motocicleta (referencia genérica) con fichas Honda",
};
const FAQ_MODELO = [
  { id: "potencia", pregunta: "¿Qué potencia tiene?", respuesta: "Potencia: No publicado.", campos: ["motor.potencia"], fuentes: [], estado: "no_publicado" },
];
const PIEZAS = [{ id: "piston", nombre: "Pistón", tipo: "p", descripcion: "", funcion: "Recibe la presión", material: null, subconjunto: "motor", dimensiones_m: {}, relacionadas: [], retirar_antes: [], metadatos: {}, referencia_documental: "demo" }];
const MAQUINA = { id: "moto_honda", pregunta: "¿Cómo convierte?", una_linea: "Motocicleta (referencia genérica) con fichas Honda", relacion: "v", ruta: "#/maquina/moto_honda", idea_principal: "idea", datos_empresa: [], parametros: [] };

let contenedor: HTMLDivElement;
let faqVisor: { status: number; cuerpo: unknown };
const llamadas: string[] = [];

beforeEach(() => {
  contenedor = document.createElement("div");
  document.body.appendChild(contenedor);
  faqVisor = { status: 404, cuerpo: { detail: "Aún no se generó faq_visor.json" } };
  llamadas.length = 0;
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string, init?: RequestInit) => {
      llamadas.push(`${init?.method ?? "GET"} ${url}`);
      const ok = (cuerpo: unknown, status = 200) => new Response(JSON.stringify(cuerpo), { status, headers: { "Content-Type": "application/json" } });
      if (url.endsWith("/motos/cb160f")) return ok(FICHA);
      if (url.endsWith("/motos/cb160f/faq")) return ok(FAQ_MODELO);
      if (url.endsWith("/faq-visor")) return ok(faqVisor.cuerpo, faqVisor.status);
      if (url.includes("/motos/cb160f/calculo")) return ok({ resultado: { velocidad_kmh: 0, estado_motor: "neutro", radio_llanta_m: 0.3069, relacion_total: null, rpm_efectivas: 1400 }, ficha_aplicada: null });
      if (url.endsWith("/tareas/qa")) return ok({ pregunta: "x", respuesta: "Respuesta en vivo [f1]", fuentes: [{ fragmento_id: "f1", titulo: "t", url: "https://fanalca.com/" }], fundamentada: true, confianza: "alta", proveedor: "p", modelo: "m" });
      if (url.endsWith("/piezas")) return ok(PIEZAS);
      if (url.endsWith("/jerarquia")) return ok({ id: "r", nombre: "r", tipo: "raiz", hijos: [{ id: "motor", nombre: "Motor en corte", tipo: "subconjunto", hijos: [] }] });
      if (url.endsWith("/animacion")) return ok({ duracion_por_pieza_s: 0.35, solape: 0.5, orden_desmontaje: ["piston"], orden_reensamblaje: ["piston"] });
      if (url.includes("/despiece")) return ok({ piston: [0, 0.47, 0] });
      if (url.endsWith("/maquinas/moto_honda")) return ok(MAQUINA);
      if (url.endsWith("/maquinas")) return ok([MAQUINA]);
      if (url.endsWith("/eventos")) return ok({});
      return ok({}, 404);
    }),
  );
});
afterEach(() => {
  contenedor.remove();
  vi.unstubAllGlobals();
});

async function montar(el: React.ReactElement) {
  const raiz = createRoot(contenedor);
  await act(async () => raiz.render(el));
  await act(async () => new Promise((r) => setTimeout(r, 30)));
  return raiz;
}
const porId = (id: string) => contenedor.querySelector(`[data-testid="${id}"]`) as HTMLElement;
const cambiarRango = async (etiqueta: string, valor: string) => {
  const input = Array.from(contenedor.querySelectorAll<HTMLInputElement>("input[type=range]")).find((i) => contenedor.querySelector(`label[for="${i.id}"]`)?.textContent === etiqueta)!;
  const fijar = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value")!.set!;
  await act(async () => {
    fijar.call(input, valor);
    input.dispatchEvent(new Event("input", { bubbles: true }));
  });
};
const leerNumero = (texto: string) => parseFloat(texto.replace(/\./g, "").replace(",", ".").replace(/[^0-9.\-]/g, ""));
const clic = async (el: Element | null | undefined) => {
  expect(el).toBeTruthy();
  await act(async () => (el as HTMLElement).dispatchEvent(new MouseEvent("click", { bubbles: true })));
};

describe("máquina moto: interfaz", () => {
  it("muestra cabecera, escala de cámara lenta, insignia de supuesto y la frase final", async () => {
    const raiz = await montar(<MaquinaMoto tour={false} />);
    expect(porId("cab-rpm").textContent).toBe("1.400");
    expect(porId("cab-marcha").textContent).toBe("N");
    expect(porId("escala-lenta").textContent).toContain("1/200");
    expect(contenedor.querySelector(".insignia.supuesto")).toBeTruthy();
    expect(porId("idea-principal").textContent).toContain("el freno invierte el camino");
    act(() => raiz.unmount());
  });

  it("al cambiar de marcha saltan las rpm, nunca la velocidad; sin acelerar en marcha alta el motor se ahoga", async () => {
    const raiz = await montar(<MaquinaMoto tour={false} />);
    await clic(contenedor.querySelector('[data-marcha="3"]'));
    expect(porId("cab-marcha").textContent).toBe("3.ª");
    expect(porId("estado").textContent).toBe("MOTOR AHOGADO"); // 3.ª desde parado y sin acelerar
    await cambiarRango("Acelerador", "50");
    expect(porId("estado").textContent).toBe("EN MARCHA"); // el embrague patina en el arranque
    expect(porId("cab-embrague").textContent).toBe("patinando");
    // Experimento 1: 72 km/h en 3.ª con el acelerador a fondo
    await clic(contenedor.querySelectorAll(".experimento .opciones button")[1]);
    await clic(Array.from(contenedor.querySelectorAll("button")).find((b) => b.textContent === "Ejecutar y comparar"));
    const v3 = leerNumero(porId("cab-velocidad").textContent!);
    const rpm3 = leerNumero(porId("cab-rpm").textContent!);
    expect(v3).toBeGreaterThan(71.9);
    // rpm = v·i_total·60/(2π·R), con R = 0,3069 m (130/70-17) e i_total = 3,35·1,40·3,00
    const esperada3 = ((v3 / 3.6 / 0.3069) * 3.35 * 1.4 * 3 * 60) / (2 * Math.PI);
    expect(Math.abs(rpm3 - esperada3) / esperada3).toBeLessThan(0.01);
    await clic(contenedor.querySelector('[data-marcha="5"]'));
    const v5 = leerNumero(porId("cab-velocidad").textContent!);
    const rpm5 = leerNumero(porId("cab-rpm").textContent!);
    expect(Math.abs(v5 - v3)).toBeLessThan(0.6); // la velocidad no salta (solo avanza unos ms de simulación)
    expect(rpm5).toBeLessThan(rpm3 * 0.8); // las rpm sí saltan: 5.ª es una relación más larga
    act(() => raiz.unmount());
  });

  it("el neutro no detiene la moto en seco: la velocidad decae pero las rpm son libres", async () => {
    const raiz = await montar(<MaquinaMoto tour={false} />);
    await clic(contenedor.querySelectorAll(".experimento .opciones button")[1]);
    await clic(Array.from(contenedor.querySelectorAll("button")).find((b) => b.textContent === "Ejecutar y comparar"));
    await clic(contenedor.querySelector('[data-marcha="0"]'));
    expect(leerNumero(porId("cab-velocidad").textContent!)).toBeGreaterThan(70);
    expect(porId("cab-marcha").textContent).toBe("N");
    expect(contenedor.textContent).toContain("sin tracción (neutro)");
    act(() => raiz.unmount());
  });

  it("A5: con la palanca cargada y sin frenar no se muestra BLOQUEADA; al frenar sí", async () => {
    const raiz = await montar(<MaquinaMoto tour={false} />);
    await cambiarRango("Fuerza en la palanca", "400");
    const etiqueta = () => (contenedor.querySelector('[data-etiqueta="disco_del"]') as HTMLElement).textContent!;
    expect(etiqueta()).toContain("previsto");
    expect(etiqueta()).not.toContain("BLOQUEADA");
    // Experimento 3 (palanca delantera 400 N a 41 km/h): el freno se activa y la rueda se bloquea
    const sig = Array.from(contenedor.querySelectorAll("button")).find((b) => b.textContent === "Siguiente")!;
    await clic(sig);
    await clic(sig);
    await clic(contenedor.querySelectorAll(".experimento .opciones button")[0]);
    await clic(Array.from(contenedor.querySelectorAll("button")).find((b) => b.textContent === "Ejecutar y comparar"));
    await act(async () => new Promise((r) => setTimeout(r, 30)));
    expect(porId("estado").textContent).toBe("FRENANDO");
    expect(porId("cab-embrague").textContent).toContain("EMBRAGUE");
    expect(etiqueta()).toContain("BLOQUEADA");
    act(() => raiz.unmount());
  });

  it("A14: con la STD (CBS no publicado) el CBS no se habilita y no se reactiva solo al volver a la DLX", async () => {
    const raiz = await montar(<MaquinaMoto tour={false} />);
    const selector = contenedor.querySelector<HTMLSelectElement>('select[aria-label="Ver con ficha de…"]')!;
    const fijar = Object.getOwnPropertyDescriptor(HTMLSelectElement.prototype, "value")!.set!;
    const elegir = async (v: string) =>
      act(async () => {
        fijar.call(selector, v);
        selector.dispatchEvent(new Event("change", { bubbles: true }));
      });
    const cbs = () => Array.from(contenedor.querySelectorAll<HTMLInputElement>("input[type=checkbox]")).find((i) => i.parentElement?.textContent?.includes("CBS"))!;
    await elegir("dlx");
    expect(cbs().disabled).toBe(false);
    await clic(cbs());
    expect(cbs().checked).toBe(true);
    await elegir("std");
    expect(cbs().disabled).toBe(true);
    expect(cbs().checked).toBe(false);
    expect(porId("nota-ficha").textContent).toContain("frenos.STD.trasero"); // A6: trasero no publicado → genérico
    await elegir("dlx");
    expect(cbs().checked).toBe(false); // no se reactiva solo
    act(() => raiz.unmount());
  });

  it("«Ver con ficha de…» aplica 140/70-17 y cambia el radio de la llanta", async () => {
    const raiz = await montar(<MaquinaMoto tour={false} />);
    expect(contenedor.querySelector(".lecturas")?.textContent).toContain("0,3069");
    const selector = contenedor.querySelector<HTMLSelectElement>('select[aria-label="Ver con ficha de…"]')!;
    const fijar = Object.getOwnPropertyDescriptor(HTMLSelectElement.prototype, "value")!.set!;
    await act(async () => {
      fijar.call(selector, "std");
      selector.dispatchEvent(new Event("change", { bubbles: true }));
    });
    expect(porId("nota-ficha").textContent).toContain("140/70-17");
    expect(contenedor.querySelector(".lecturas")?.textContent).toContain("0,3139");
    expect(porId("cab-version").textContent).toBe("STD");
    act(() => raiz.unmount());
  });

  it("A1: la cifra de potencia sin unidad no aparece en el DOM", async () => {
    const raiz = await montar(<MaquinaMoto tour={false} />);
    expect(contenedor.textContent).not.toContain("15,04");
    act(() => raiz.unmount());
  });

  it("la ficha técnica muestra «No publicado» y fuente con fecha; pulsar un dato lo marca", async () => {
    const raiz = await montar(<MaquinaMoto tour={false} />);
    const ficha = contenedor.querySelector(".ficha-tecnica")!;
    expect(ficha.textContent).toContain("No publicado");
    expect(ficha.textContent).toContain("lamina-cb160-std-dlx");
    expect(ficha.textContent).toContain("consulta 2026-11-04");
    const boton = ficha.querySelector<HTMLButtonElement>('button[data-campo="llantas.trasera"]')!;
    await clic(boton);
    expect(boton.getAttribute("aria-pressed")).toBe("true");
    act(() => raiz.unmount());
  });

  it("las FAQ de modelos se despliegan con un clic real y resaltan las piezas del campo", async () => {
    const raiz = await montar(<MaquinaMoto tour={false} />);
    await clic(Array.from(contenedor.querySelectorAll('[role="tab"]')).find((t) => t.textContent === "FAQ modelos"));
    const det = contenedor.querySelector<HTMLDetailsElement>('[data-faq-modelo="potencia"]')!;
    const resumen = det.querySelector("summary")!;
    expect(det.open).toBe(false);
    expect(porId("moto-lab").getAttribute("data-resaltadas")).toBe("");
    await clic(resumen); // clic real sobre el <summary>: el navegador (jsdom) alterna `open`
    await act(async () => new Promise((r) => setTimeout(r, 10)));
    expect(det.open).toBe(true);
    expect(det.textContent).toContain("No publicado");
    expect(det.textContent).toContain("motor.potencia");
    expect(porId("moto-lab").getAttribute("data-resaltadas")).toContain("ciguenal");
    await clic(resumen);
    await act(async () => new Promise((r) => setTimeout(r, 10)));
    expect(det.open).toBe(false);
    expect(porId("moto-lab").getAttribute("data-resaltadas")).toBe("");
    act(() => raiz.unmount());
  });

  it("FAQ Fanalca: sin archivo indica el comando; con archivo despliega respuesta y cita", async () => {
    let raiz = await montar(<MaquinaMoto tour={false} />);
    await clic(Array.from(contenedor.querySelectorAll('[role="tab"]')).find((t) => t.textContent === "FAQ Fanalca"));
    expect(porId("faq-sin-archivo").textContent).toContain("uv run fabrica faq-visor");
    act(() => raiz.unmount());
    faqVisor = {
      status: 200,
      cuerpo: {
        generado: "2026-11-05", proveedor: "simulado", modelo: "m", version_prompt: "v3", advertencia: "Respuestas de prueba.", total: 1,
        items: [{ id: "q1", categoria: "sede", pregunta: "¿Dónde está la sede?", respuesta: "En Cali [f1].", rechazo: false, fundamentada: true, confianza: "alta", fuentes: [{ fragmento_id: "f1", url: "https://fanalca.com/" }] }],
      },
    };
    raiz = await montar(<MaquinaMoto tour={false} />);
    await clic(Array.from(contenedor.querySelectorAll('[role="tab"]')).find((t) => t.textContent === "FAQ Fanalca"));
    const det = contenedor.querySelector('[data-faq-fanalca="q1"]')!;
    expect(det.textContent).toContain("En Cali");
    expect(det.querySelector("a")?.getAttribute("href")).toBe("https://fanalca.com/");
    // pregunta en vivo (POST /tareas/qa)
    const input = contenedor.querySelector<HTMLInputElement>("#pregunta-en-vivo")!;
    const fijar = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value")!.set!;
    await act(async () => {
      fijar.call(input, "¿Dónde queda la planta?");
      input.dispatchEvent(new Event("input", { bubbles: true }));
    });
    await clic(Array.from(contenedor.querySelectorAll("button")).find((b) => b.textContent === "Preguntar en vivo"));
    await act(async () => new Promise((r) => setTimeout(r, 20)));
    expect(porId("respuesta-en-vivo").textContent).toContain("Respuesta en vivo");
    expect(llamadas.some((l) => l.startsWith("POST") && l.endsWith("/tareas/qa"))).toBe(true);
    act(() => raiz.unmount());
  });

  it("los chips de ensamblajes aíslan un conjunto y la lista permite elegir una pieza", async () => {
    const raiz = await montar(<MaquinaMoto tour={false} />);
    await clic(Array.from(contenedor.querySelectorAll('[role="tab"]')).find((t) => t.textContent === "Ensamblajes"));
    await clic(contenedor.querySelector('button[data-ensamblaje="motor"]'));
    await clic(contenedor.querySelector('button[data-pieza="piston"]'));
    expect(porId("ficha-nombre").textContent).toBe("Pistón");
    act(() => raiz.unmount());
  });

  it("la biblioteca muestra la tarjeta de la moto", async () => {
    const raiz = await montar(<Biblioteca />);
    const t = contenedor.querySelector('article[data-maquina="moto_honda"]')!;
    expect(t.textContent).toContain("Motocicleta (referencia genérica) con fichas Honda");
    expect(t.querySelector("a.boton")?.getAttribute("href")).toBe("#/maquina/moto_honda");
    act(() => raiz.unmount());
  });
});
