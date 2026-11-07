/**
 * Fase 14 — «Explorador de la motocicleta»: selección por clic en 3D, franja inferior y buscador; el panel solo
 * muestra datos con fuente o con marca de estado; ningún texto de referencia de repuesto, precio ni disponibilidad.
 */
import { act } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { FichaMotoApi } from "../api";
import type { CampoFichaApi } from "../modelos/moto";
import type { EstadoMoto } from "../paginas/EscenaMoto";

// La escena real necesita WebGL: la falsa expone un botón por pieza que llama a `alSeleccionar` como el raycaster.
const escenaVista: { estado: { current: EstadoMoto } | null } = { estado: null };
vi.mock("../paginas/EscenaMoto", async (original) => ({
  ...(await original<typeof import("../paginas/EscenaMoto")>()),
  default: (p: { estado: { current: EstadoMoto }; alSeleccionar: (id: string | null) => void; alPasar?: (id: string | null) => void }) => {
    escenaVista.estado = p.estado;
    return (
      <div data-testid="escena-falsa">
        {["cilindro", "cadena", "disco_delantero"].map((id) => (
          <button key={id} data-pieza-3d={id} onClick={() => p.alSeleccionar(id)} onMouseEnter={() => p.alPasar?.(id)} />
        ))}
      </div>
    );
  },
}));

import { idDeRuta } from "../App";
import { buscarPiezas, camposRelacionados, campoMostrable } from "../componentes/explorador";
import { FRASE_RECHAZO } from "../componentes/panelesMoto";
import { TERMINOS_PROHIBIDOS } from "../maquinas/explorador_moto";
import ExploradorMoto from "../paginas/ExploradorMoto";

(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

const pieza = (id: string, nombre: string, subconjunto: string, funcion: string) => ({
  id, nombre, tipo: "t", descripcion: "", funcion, material: null, subconjunto, dimensiones_m: {}, relacionadas: [], retirar_antes: [], metadatos: {},
  referencia_documental: "Modelo de demostración del proyecto (sin documentación de fabricante)",
});
const PIEZAS = [
  pieza("cilindro", "Cilindro (en corte)", "motor", "Guía al pistón y contiene la cámara de combustión."),
  pieza("piston", "Pistón", "motor", "Transmite la presión de los gases a la biela."),
  pieza("pinon", "Piñón de salida (14 dientes)", "transmision", "Mueve la cadena de transmisión final."),
  pieza("cadena", "Cadena de transmisión", "transmision", "Transmite el giro del piñón a la corona."),
  pieza("corona", "Corona trasera (42 dientes)", "transmision", "Recibe la cadena."),
  pieza("disco_delantero", "Disco de freno delantero", "frenos", "Superficie de fricción de las pastillas."),
  pieza("caliper_delantero", "Cáliper delantero", "frenos", "Convierte la presión hidráulica en fuerza de sujeción."),
  pieza("bateria", "Batería", "electrico", "Alimenta el sistema eléctrico."),
];
const SISTEMAS = [
  { id: "motor", nombre: "Motor", funcion: "Convierte la energía del combustible en giro del cigüeñal.", piezas: ["cilindro", "piston"] },
  { id: "transmision", nombre: "Transmisión", funcion: "Adapta el régimen del motor a la velocidad de la rueda.", piezas: ["pinon", "cadena", "corona"] },
  { id: "frenos", nombre: "Frenos", funcion: "Convierten la fuerza de la manija en fricción.", piezas: ["disco_delantero", "caliper_delantero"] },
  { id: "electrico", nombre: "Sistema eléctrico", funcion: "Almacena y distribuye la energía eléctrica.", piezas: ["bateria"] },
];
const FUENTE = "lamina-cb160-std-dlx (aportada por el usuario)";
const campo = (valor: CampoFichaApi["valor"], estado: CampoFichaApi["estado"]): CampoFichaApi => ({ valor, unidad: null, fuente: estado === "no_publicado" ? null : FUENTE, fecha_consulta: estado === "no_publicado" ? null : "2026-11-04", estado });
const FICHA: FichaMotoApi = {
  id: "cb160f", nombre: "CB 160F", categoria: "Sport (naked)", versiones: ["STD", "DLX"],
  grupos: {
    motor: { tipo: campo("4T", "publicado"), cilindrada: campo(null, "no_publicado") },
    transmision: { transmision_final: campo(null, "no_publicado") },
  },
  por_version: { STD: { delantero: campo("Disco", "publicado") }, DLX: { delantero: campo("Disco", "publicado") } },
  pendientes_de_confirmar: [], fuentes: [], supuestos: [], ensamblaje_id: "moto_honda", titulo_biblioteca: "t",
};
const MAQUINA = { id: "moto_honda", pregunta: "p", una_linea: "l", relacion: "v", ruta: "#/maquina/moto_honda", idea_principal: "i", datos_empresa: [], parametros: [] };
const POSICIONES = Object.fromEntries(PIEZAS.map((p, i) => [p.id, [i * 0.1, 0.4, 0]]));

let contenedor: HTMLDivElement;
let documentado: unknown[];
const posts: { url: string; cuerpo: unknown }[] = [];
beforeEach(() => {
  contenedor = document.createElement("div");
  document.body.appendChild(contenedor);
  documentado = [];
  posts.length = 0;
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string, init?: RequestInit) => {
      const ok = (c: unknown, status = 200) => new Response(JSON.stringify(c), { status, headers: { "Content-Type": "application/json" } });
      if (init?.method === "POST") posts.push({ url, cuerpo: JSON.parse(String(init.body)) });
      if (url.endsWith("/moto_honda/preguntar"))
        return ok({ pieza_id: "cadena", pregunta: "¿Para qué sirve?", intencion: "funcion", respuesta_modelo: "Cadena de transmisión: transmite el giro.", documentado, advertencia: "a" });
      if (url.endsWith("/moto_honda/piezas")) return ok(PIEZAS);
      if (url.endsWith("/moto_honda/sistemas")) return ok(SISTEMAS);
      if (url.includes("/moto_honda/despiece")) return ok(POSICIONES);
      if (url.endsWith("/motos/cb160f")) return ok(FICHA);
      if (url.endsWith("/maquinas/moto_honda")) return ok(MAQUINA);
      if (url.endsWith("/faq-visor")) return ok({ detail: "no" }, 404);
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
const q = <T extends Element = HTMLElement>(sel: string) => contenedor.querySelector(sel) as T | null;
const pulsar = async (el: Element | null) => {
  expect(el).toBeTruthy();
  await act(async () => (el as HTMLElement).click());
};
const panel = () => q('[data-testid="panel-sistema"]');

describe("rutas del explorador", () => {
  it("#/maquina/moto_honda/explorador y el alias #/explorador abren la misma vista; #/moto sigue siendo la moto", () => {
    expect(idDeRuta("/maquina/moto_honda/explorador")).toBe("moto_explorador");
    expect(idDeRuta("/explorador")).toBe("moto_explorador");
    expect(idDeRuta("/moto")).toBe("moto_honda");
    expect(idDeRuta("/maquina/freno")).toBe("freno");
  });
});

describe("lógica pura", () => {
  it("el buscador ignora tildes y mayúsculas y exige todas las palabras", () => {
    expect(buscarPiezas(PIEZAS, "caliper").map((p) => p.id)).toEqual(["caliper_delantero"]);
    expect(buscarPiezas(PIEZAS, "PIÑON salida").map((p) => p.id)).toEqual(["pinon"]);
    expect(buscarPiezas(PIEZAS, "freno disco").map((p) => p.id)).toEqual(["disco_delantero"]);
    expect(buscarPiezas(PIEZAS, "   ")).toEqual([]);
  });
  it("los campos relacionados salen de la ficha por las piezas del sistema y siempre traen estado", () => {
    const motor = camposRelacionados(FICHA, ["cilindro", "piston"]).map((c) => c.ruta);
    expect(motor).toEqual(expect.arrayContaining(["motor.tipo", "motor.cilindrada"]));
    expect(camposRelacionados(FICHA, ["disco_delantero"]).map((c) => c.ruta)).toEqual(["frenos.STD.delantero", "frenos.DLX.delantero"]);
    expect(camposRelacionados(FICHA, ["bateria"])).toEqual([]);
    expect(camposRelacionados(null, ["cilindro"])).toEqual([]);
    // Un dato «publicado» sin fuente no se muestra.
    expect(campoMostrable({ valor: 1, unidad: null, fuente: null, fecha_consulta: null, estado: "publicado" })).toBe(false);
    expect(campoMostrable({ valor: null, unidad: null, fuente: null, fecha_consulta: null, estado: "no_publicado" })).toBe(true);
  });
});

describe("selección de sistemas", () => {
  it("el clic en una pieza 3D selecciona su sistema: contorno, resto atenuado y cámara que encuadra el sistema", async () => {
    const raiz = await montar(<ExploradorMoto />);
    expect(q('[data-testid="panel-sistema-vacio"]')).toBeTruthy();
    await pulsar(q('[data-pieza-3d="cilindro"]'));
    expect(panel()?.getAttribute("data-sistema")).toBe("motor");
    expect(panel()?.textContent).toContain("Convierte la energía del combustible");
    const e = escenaVista.estado!.current;
    expect(e.seleccion).toBe("cilindro");
    expect([...e.resaltadas].sort()).toEqual(["cilindro", "piston"]); // contorno en todo el sistema
    expect([...(e.enfoque ?? [])].sort()).toEqual(["cilindro", "piston"]); // el resto pasa a fantasma
    expect(e.camara?.encuadre?.centro[0]).toBeCloseTo(0.05, 5); // centro entre cilindro (0) y pistón (0,1)
    // El hover marca solo la pieza bajo el cursor.
    await act(async () => q('[data-pieza-3d="cadena"]')!.dispatchEvent(new MouseEvent("mouseover", { bubbles: true })));
    expect([...(escenaVista.estado!.current.pasando ?? [])]).toEqual(["cadena"]);
    act(() => raiz.unmount());
  });

  it("los 10 botones de la franja seleccionan el sistema igual que el clic en 3D, con icono y nombre", async () => {
    const raiz = await montar(<ExploradorMoto />);
    const botones = contenedor.querySelectorAll(".franja-sistemas button[data-sistema]");
    expect(botones).toHaveLength(SISTEMAS.length);
    expect(botones[0].querySelector("svg.icono-sistema")).toBeTruthy();
    await pulsar(q('.franja-sistemas button[data-sistema="frenos"]'));
    expect(panel()?.getAttribute("data-sistema")).toBe("frenos");
    expect(q('.franja-sistemas button[data-sistema="frenos"]')?.getAttribute("aria-pressed")).toBe("true");
    expect([...escenaVista.estado!.current.resaltadas].sort()).toEqual(["caliper_delantero", "disco_delantero"]);
    // Lección relacionada: frenos → freno de disco.
    expect(q('[data-testid="ver-leccion"]')?.getAttribute("href")).toBe("#/maquina/freno");
    // Pulsar de nuevo deselecciona.
    await pulsar(q('.franja-sistemas button[data-sistema="frenos"]'));
    expect(panel()).toBeNull();
    act(() => raiz.unmount());
  });

  it("las etiquetas de sistema alrededor de la moto son botones que seleccionan su sistema", async () => {
    const raiz = await montar(<ExploradorMoto />);
    const etiquetas = contenedor.querySelectorAll(".etiqueta-sistema .boton-etiqueta");
    expect(etiquetas).toHaveLength(11);
    await pulsar(q('[data-etiqueta="freno_delantero"] button'));
    expect(panel()?.getAttribute("data-sistema")).toBe("frenos");
    expect(escenaVista.estado!.current.seleccion).toBe("disco_delantero");
    act(() => raiz.unmount());
  });

  it("el buscador selecciona la pieza, activa su sistema y encuadra la pieza", async () => {
    const raiz = await montar(<ExploradorMoto />);
    const entrada = q<HTMLInputElement>("#buscador-piezas")!;
    await act(async () => {
      const set = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value")!.set!;
      set.call(entrada, "cadena");
      entrada.dispatchEvent(new Event("input", { bubbles: true }));
    });
    await pulsar(q('.buscador-resultados button[data-pieza="cadena"]'));
    expect(panel()?.getAttribute("data-sistema")).toBe("transmision");
    const e = escenaVista.estado!.current;
    expect(e.seleccion).toBe("cadena");
    expect(e.camara?.encuadre?.centro[0]).toBeCloseTo(0.3, 5); // posición de la cadena
    expect(q('.piezas-sistema li.activa button')?.getAttribute("data-pieza")).toBe("cadena");
    act(() => raiz.unmount());
  });
});

describe("panel de detalle", () => {
  it("solo muestra datos de ficha con estado y fuente; lo ausente se marca «No publicado»", async () => {
    const raiz = await montar(<ExploradorMoto />);
    await pulsar(q('.franja-sistemas button[data-sistema="motor"]'));
    const filas = Array.from(contenedor.querySelectorAll(".panel-sistema .ficha-tecnica tr"));
    expect(filas.length).toBe(2);
    for (const f of filas) {
      const insignia = f.querySelector(".insignia")!;
      expect(insignia).toBeTruthy(); // cada dato lleva su estado (publicado / no publicado / supuesto didáctico)
      if (insignia.classList.contains("fuente-ficha")) expect(f.textContent).toContain(FUENTE);
      else expect(f.textContent).toContain("No publicado");
    }
    // Un sistema sin datos en la ficha lo dice explícitamente.
    await pulsar(q('.franja-sistemas button[data-sistema="electrico"]'));
    expect(q('[data-testid="ficha-no-publicada"]')?.textContent).toContain("No publicado");
    act(() => raiz.unmount());
  });

  it("«Preguntar sobre esta pieza» usa POST …/moto_honda/preguntar y muestra la frase de rechazo o las citas", async () => {
    const raiz = await montar(<ExploradorMoto />);
    await pulsar(q('[data-pieza-3d="cadena"]'));
    await pulsar(q('[data-testid="preguntar-pieza"]'));
    await act(async () => new Promise((r) => setTimeout(r, 10)));
    expect(posts.at(-1)?.url).toBe("/api/v1/simulador/ensamblajes/moto_honda/preguntar");
    expect(posts.at(-1)?.cuerpo).toEqual({ pieza_id: "cadena", pregunta: "¿Para qué sirve?" });
    expect(q('[data-testid="rechazo"]')?.textContent).toBe(FRASE_RECHAZO);
    documentado = [{ fragmento_id: "frag-7", texto: "Fanalca fabrica partes metálicas.", url: "https://autopartesfanalca.com.co/", origen: "scraping" }];
    await pulsar(q('[data-testid="preguntar-pieza"]'));
    await act(async () => new Promise((r) => setTimeout(r, 10)));
    const r = q('[data-testid="respuesta-pieza"]')!;
    expect(r.textContent).toContain("frag-7");
    expect(r.querySelector("a")?.getAttribute("href")).toBe("https://autopartesfanalca.com.co/");
    expect(q('[data-testid="rechazo"]')).toBeNull();
    act(() => raiz.unmount());
  });

  it("ningún texto de referencia de repuesto, precio, disponibilidad ni carrito en ninguna vista ni sistema", async () => {
    const raiz = await montar(<ExploradorMoto />);
    const revisar = () => expect((contenedor.textContent ?? "").match(TERMINOS_PROHIBIDOS)?.[0] ?? null).toBeNull();
    revisar();
    for (const s of SISTEMAS) {
      await pulsar(q(`.franja-sistemas button[data-sistema="${s.id}"]`));
      revisar();
    }
    await pulsar(q('.selector-vista [data-vista="partes"]'));
    expect(q('[data-testid="lista-partes"]')?.textContent).toContain("Cadena de transmisión");
    revisar();
    expect(contenedor.textContent).not.toContain("Modelo de demostración del proyecto (sin documentación"); // referencia_documental no se muestra
    act(() => raiz.unmount());
  });
});

describe("vistas", () => {
  it("Explosión aplica el despiece radial existente a todas las piezas y Partes muestra la lista", async () => {
    const mm = window.matchMedia;
    window.matchMedia = ((m: string) => ({ matches: m.includes("reduce"), media: m, addEventListener() {}, removeEventListener() {} })) as unknown as typeof window.matchMedia;
    const raiz = await montar(<ExploradorMoto />);
    await pulsar(q('.selector-vista [data-vista="explosion"]'));
    expect(q('[data-testid="explorador-moto"]')?.getAttribute("data-vista")).toBe("explosion");
    expect(Object.values(escenaVista.estado!.current.despiece).every((f) => f === 1)).toBe(true);
    await pulsar(q('.selector-vista [data-vista="interactiva"]'));
    expect(Object.values(escenaVista.estado!.current.despiece).every((f) => f === 0)).toBe(true);
    await pulsar(q('.selector-vista [data-vista="partes"]'));
    // Elegir una parte de la lista vuelve a la vista interactiva con la pieza encuadrada.
    await pulsar(q('[data-testid="lista-partes"] button[data-pieza="bateria"]'));
    expect(q('[data-testid="explorador-moto"]')?.getAttribute("data-vista")).toBe("interactiva");
    expect(panel()?.getAttribute("data-sistema")).toBe("electrico");
    window.matchMedia = mm;
    act(() => raiz.unmount());
  });
});
