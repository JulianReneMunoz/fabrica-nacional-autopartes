import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import App from "../App";
import { GRUPOS, PESTANAS_PIE, resolverRuta, TODAS_LAS_PESTANAS } from "../ignisRutas";

(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

describe("rutas de la barra lateral", () => {
  it("tiene los seis grupos en el orden del plan, con Atención como inicio", () => {
    expect(GRUPOS.map((g) => g.titulo)).toEqual(["Conversación", "Datos y conocimiento", "Agente", "Calidad y seguridad", "Observabilidad", "Proyecto"]);
    expect(GRUPOS[0].pestanas[0].id).toBe("atencion");
    expect(GRUPOS.flatMap((g) => g.pestanas.map((p) => p.id))).toEqual([
      "atencion", "faq", "qa", "proceso-datos", "corpus", "base", "agente", "herramientas", "router", "prompts",
      "configuracion", "rayos-x", "seguridad", "auditoria", "panel", "evaluacion", "mlflow", "kanban", "arquitectura",
    ]);
    expect(PESTANAS_PIE.map((p) => p.id)).toEqual(["sesion", "ajustes"]);
  });

  it("resuelve cada pestaña sin redirigir", () => {
    for (const p of TODAS_LAS_PESTANAS) expect(resolverRuta(`#/${p.id}`)).toMatchObject({ id: p.id, redirigirA: null });
  });

  it("las rutas viejas del M1, del robot y del simulador redirigen a Atención", () => {
    for (const vieja of ["", "#", "#/", "#/biblioteca", "#/prensa", "#/linea", "#/moto", "#/explorador", "#/maquina/freno", "#/maquina/moto_honda/explorador", "#/robot", "#/simulador"]) {
      expect(resolverRuta(vieja), vieja).toMatchObject({ id: "atencion", redirigirA: "#/atencion" });
    }
  });

  it("conserva los parámetros al redirigir y los expone en la ruta válida", () => {
    expect(resolverRuta("#/maquina/freno?calidad=bajo").redirigirA).toBe("#/atencion?calidad=bajo");
    expect(resolverRuta("#/atencion?calidad=bajo").parametros.get("calidad")).toBe("bajo");
  });
});

describe("aplicación (jsdom)", () => {
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

  async function montar(hash: string, fetchSimulado: typeof fetch) {
    vi.stubGlobal("fetch", fetchSimulado);
    window.history.replaceState(null, "", `/${hash}`);
    raiz = createRoot(contenedor);
    await act(async () => {
      raiz.render(<App />);
    });
    // Espera a que resuelvan los imports diferidos (React.lazy) y la primera consulta de salud.
    for (let i = 0; i < 20 && contenedor.querySelector("[aria-busy='true']"); i++) {
      await act(async () => {
        await new Promise((r) => setTimeout(r, 20));
      });
    }
  }

  const apiCaida = (() => Promise.reject(new TypeError("Failed to fetch"))) as unknown as typeof fetch;

  it.each(TODAS_LAS_PESTANAS.filter((p) => p.id !== "atencion").map((p) => [p.id, p] as const))(
    "la pestaña %s muestra su estado vacío con el PR y no inventa datos",
    async (_id, p) => {
      await montar(`#/${p.id}`, apiCaida);
      expect(contenedor.querySelector("h1")?.textContent).toBe(p.etiqueta);
      expect(contenedor.textContent).toContain(`No disponible todavía (${p.pr})`);
      const activo = contenedor.querySelector('nav a[aria-current="page"]');
      expect(activo?.textContent).toBe(p.etiqueta);
    },
  );

  it("con el backend caído el encabezado lo dice y la app sigue navegable", async () => {
    await montar("#/corpus", apiCaida);
    const chips = Array.from(contenedor.querySelectorAll(".ig-chip-servicio")).map((c) => c.textContent);
    expect(chips).toEqual(["APIsin conexión", "SSEsin uso aún", "Qdrantno disponible todavía (#34)"]);
    expect(contenedor.querySelector(".ig-chip-servicio")?.getAttribute("role")).toBe("status");
  });

  it("con la API en línea el chip lo refleja y el hilo se muestra con «Nuevo hilo»", async () => {
    const enLinea = (async () => new Response(JSON.stringify({ estado: "ok" }), { status: 200 })) as typeof fetch;
    await montar("#/kanban", enLinea);
    expect(contenedor.querySelector(".ig-chip-servicio.en_linea")?.textContent).toContain("API");
    const hilo = contenedor.querySelector(".ig-hilo code")?.textContent ?? "";
    expect(hilo).toMatch(/^hilo-[a-z0-9]+$/);
    const boton = Array.from(contenedor.querySelectorAll("button")).find((b) => b.textContent?.includes("Nuevo hilo"));
    await act(async () => boton?.click());
    expect(contenedor.querySelector(".ig-hilo code")?.textContent).not.toBe(hilo);
  });

  it("una ruta vieja del M1 abre Atención y reescribe el hash", async () => {
    await montar("#/maquina/prensa", apiCaida);
    expect(window.location.hash).toBe("#/atencion");
    expect(contenedor.querySelector('nav a[aria-current="page"]')?.textContent).toBe("Atención — IGNIS");
    expect(contenedor.textContent).toContain("Atención al cliente — IGNIS");
  });

  it("la barra lateral se expande con etiquetas y se recorre con las flechas", async () => {
    await montar("#/faq", apiCaida);
    const alternar = contenedor.querySelector<HTMLButtonElement>(".ig-nav-alternar")!;
    expect(alternar.getAttribute("aria-expanded")).toBe("false");
    await act(async () => alternar.click());
    expect(contenedor.querySelector(".ig-lateral")?.classList.contains("expandida")).toBe(true);
    const items = Array.from(contenedor.querySelectorAll<HTMLAnchorElement>(".ig-nav-item"));
    items[0].focus();
    await act(async () => {
      items[0].dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowDown", bubbles: true }));
    });
    expect(document.activeElement).toBe(items[1]);
  });
});
