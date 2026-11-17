import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import App from "../App";
import { conversar, ErrorSesionIgnis } from "../ignisCliente";
import { validarAlias } from "../ignisSesion";
import { crearFetchSimulado, type OpcionesSimulador } from "./simuladorApi";

(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

/** Cambia el valor de un campo controlado de React como lo haría el usuario. */
function escribir(campo: HTMLInputElement, valor: string) {
  Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value")!.set!.call(campo, valor);
  campo.dispatchEvent(new Event("input", { bubbles: true }));
}

describe("validación del alias en el cliente (misma regla que el backend)", () => {
  it.each(["compras-01", "Ñandú3", "abc12"])("acepta %s", (alias) => {
    expect(validarAlias(alias)).toBeNull();
  });
  it.each(["ana@gmail.com", "3001234567", "Ana Gómez", "ana-gomez", "ab", "user-123456", "12345"])(
    "rechaza %s",
    (alias) => {
      expect(validarAlias(alias)).toMatch(/Alias no válido/);
    },
  );
});

describe("stream con la sesión rechazada", () => {
  afterEach(() => vi.unstubAllGlobals());

  it.each([401, 403, 503] as const)("HTTP %i lanza ErrorSesionIgnis y no usa el respaldo Q&A", async (estado) => {
    const { fetchSimulado, llamadas } = crearFetchSimulado({ stream: estado });
    vi.stubGlobal("fetch", fetchSimulado);
    await expect(conversar("Hola", "hilo-1", () => undefined)).rejects.toBeInstanceOf(ErrorSesionIgnis);
    expect(llamadas.some((l) => l.url.includes("/tareas/qa"))).toBe(false);
  });
});

describe("sesión en la aplicación (jsdom)", () => {
  let contenedor: HTMLDivElement;
  let raiz: Root;

  beforeEach(() => {
    contenedor = document.createElement("div");
    document.body.appendChild(contenedor);
  });
  afterEach(() => {
    act(() => raiz?.unmount());
    contenedor.remove();
    vi.unstubAllGlobals();
    window.location.hash = "";
  });

  async function esperar() {
    for (let i = 0; i < 25; i++) {
      await act(async () => {
        await new Promise((r) => setTimeout(r, 20));
      });
      if (!contenedor.querySelector("[aria-busy='true']") && !contenedor.textContent?.includes("preparando…")) break;
    }
  }

  async function montar(hash: string, opciones: OpcionesSimulador) {
    const simulado = crearFetchSimulado({ salud: "ok", ...opciones });
    vi.stubGlobal("fetch", simulado.fetchSimulado);
    window.history.replaceState(null, "", `/${hash}`);
    raiz = createRoot(contenedor);
    await act(async () => {
      raiz.render(<App />);
    });
    await esperar();
    return simulado;
  }

  const boton = (texto: string) =>
    Array.from(contenedor.querySelectorAll("button")).find((b) => b.textContent?.trim().includes(texto));

  it("la entrada valida el alias en el cliente y, con uno válido, abre la aplicación", async () => {
    const { llamadas } = await montar("#/atencion", { sesion: "ninguna" });
    const campo = contenedor.querySelector<HTMLInputElement>("#ig-alias")!;

    await act(async () => escribir(campo, "ana-gomez"));
    await act(async () => boton("Entrar")!.click());
    expect(contenedor.querySelector("#ig-alias-error")?.textContent).toMatch(/Alias no válido/);
    expect(llamadas.some((l) => l.metodo === "POST" && l.url === "/api/v1/sesiones")).toBe(false);

    await act(async () => escribir(campo, "compras-01"));
    await act(async () => boton("Entrar")!.click());
    await esperar();
    const entrada = llamadas.find((l) => l.metodo === "POST" && l.url === "/api/v1/sesiones");
    expect(JSON.parse(entrada?.cuerpo ?? "{}")).toEqual({ alias: "compras-01" });
    expect(contenedor.querySelector("nav[aria-label='Principal']")).toBeTruthy();
    expect(contenedor.querySelector(".ig-usuario")?.textContent).toContain("compras-01");
  });

  it("«Mi sesión» lista los hilos y «Reabrir» lleva a Atención con el historial del hilo", async () => {
    await montar("#/sesion", {
      hilos: [
        {
          thread_id: "hilo-a",
          titulo: "¿Qué preferencias tengo guardadas?",
          turnos: 1,
          ultima_ruta: "memoria_store",
          creado: "2026-11-16T10:00:00+00:00",
          actualizado: "2026-11-16T10:05:00+00:00",
        },
      ],
      mensajes: {
        "hilo-a": [
          { rol: "user", contenido: "¿Qué preferencias tengo guardadas?", ruta: null, citas: [] },
          { rol: "assistant", contenido: "Preferencias guardadas: formato de respuesta: breve.", ruta: "memoria_store", citas: [] },
        ],
      },
    });
    expect(contenedor.querySelector("h1")?.textContent).toBe("Mi sesión");
    const fila = contenedor.querySelector("tbody tr");
    expect(fila?.textContent).toContain("¿Qué preferencias tengo guardadas?");
    expect(fila?.textContent).toContain("Memoria"); // etiqueta v2 de la ruta

    await act(async () => boton("Reabrir")!.click());
    await esperar();
    expect(window.location.hash).toBe("#/atencion");
    expect(contenedor.textContent).toContain("Hilo reabierto (hilo-a)");
    expect(contenedor.textContent).toContain("Preferencias guardadas: formato de respuesta: breve.");
  });

  it("al entrar sin hilos se crea uno en el servidor y «Mi sesión» lo lista sin mensajes", async () => {
    const { llamadas } = await montar("#/sesion", { hilos: [] });
    await esperar();
    expect(llamadas.filter((l) => l.metodo === "POST" && l.url === "/api/v1/sesiones/yo/hilos")).toHaveLength(1);
    expect(contenedor.querySelector("tbody tr")?.textContent).toContain("(sin mensajes)");
    expect(contenedor.querySelector("tbody tr")?.getAttribute("aria-current")).toBe("true");
  });

  it("«Cerrar sesión» borra la sesión en el servidor y vuelve a la pantalla de entrada", async () => {
    const { llamadas } = await montar("#/kanban", {});
    await act(async () => boton("Cerrar sesión")!.click());
    await esperar();
    expect(llamadas.some((l) => l.metodo === "POST" && l.url === "/api/v1/sesiones/cerrar")).toBe(true);
    expect(contenedor.querySelector("h1")?.textContent).toBe("Entrar a IGNIS");
  });

  it("la sesión no se guarda en el almacenamiento del navegador", async () => {
    await montar("#/atencion", {});
    const almacenes = ["local", "session"].map((n) => (window as unknown as Record<string, Storage>)[`${n}Storage`]);
    for (const almacen of almacenes) expect(almacen.length).toBe(0);
  });
});
