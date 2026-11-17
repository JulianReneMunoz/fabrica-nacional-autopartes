import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import IgnisAtencionView, { MAX_MENSAJE } from "../IgnisAtencionView";
import { ProveedorIgnis } from "../ignisContexto";

(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

/** Cambia el valor de un campo controlado de React como lo haría el usuario. */
function escribir(campo: HTMLTextAreaElement, valor: string) {
  const setter = Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, "value")!.set!;
  setter.call(campo, valor);
  campo.dispatchEvent(new Event("input", { bubbles: true }));
}

describe("pestaña Atención", () => {
  let contenedor: HTMLDivElement;
  let raiz: Root;
  let pedidos: string[];

  beforeEach(async () => {
    vi.useFakeTimers({ toFake: ["setTimeout", "clearTimeout"] });
    pedidos = [];
    vi.stubGlobal("fetch", ((url: string) => {
      pedidos.push(String(url));
      return Promise.reject(new TypeError("Failed to fetch"));
    }) as unknown as typeof fetch);
    contenedor = document.createElement("div");
    document.body.appendChild(contenedor);
    raiz = createRoot(contenedor);
    await act(async () => {
      raiz.render(
        <ProveedorIgnis>
          <IgnisAtencionView />
        </ProveedorIgnis>,
      );
    });
  });
  afterEach(() => {
    act(() => raiz.unmount());
    contenedor.remove();
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  const campo = () => contenedor.querySelector<HTMLTextAreaElement>("textarea[aria-label='Mensaje para IGNIS']")!;
  const chip = () => contenedor.querySelector(".ignis-chip-estado")?.textContent;

  it("limita el mensaje a 2000 caracteres con contador visible", async () => {
    expect(campo().maxLength).toBe(MAX_MENSAJE);
    await act(async () => escribir(campo(), "Hola"));
    expect(contenedor.querySelector("#ignis-contador")?.textContent).toBe(`4 / ${MAX_MENSAJE}`);
    await act(async () => escribir(campo(), "x".repeat(MAX_MENSAJE + 50)));
    expect(campo().value).toHaveLength(MAX_MENSAJE);
    expect(contenedor.querySelector("#ignis-contador")?.classList.contains("lleno")).toBe(true);
  });

  it("al teclear pasa a «Escribiendo» y vuelve a reposo tras 1,5 s sin teclas", async () => {
    expect(chip()).toBe("En reposo");
    await act(async () => escribir(campo(), "H"));
    expect(chip()).toBe("Escribiendo");
    await act(async () => {
      vi.advanceTimersByTime(1400);
    });
    expect(chip()).toBe("Escribiendo");
    await act(async () => {
      vi.advanceTimersByTime(200);
    });
    expect(chip()).toBe("En reposo");
  });

  it("la transcripción se envía con «Usar transcripción» y no hay controles del robot", () => {
    const textos = Array.from(contenedor.querySelectorAll("button")).map((b) => b.textContent?.trim());
    expect(textos).toContain("Usar transcripción");
    expect(contenedor.innerHTML).not.toMatch(/robot|Transformar/i);
  });

  it("sin WebGL muestra el póster y mantiene el chat", () => {
    expect(contenedor.querySelector(".ignis-sin-webgl")).toBeTruthy();
    expect(contenedor.querySelector(".ignis-poster")?.getAttribute("src")).toContain("ignis_auto_poster.jpg");
    expect(campo()).toBeTruthy();
  });

  it("ofrece el GLB del auto como recurso y no consulta /api/v1/maquinas", () => {
    expect(pedidos.some((u) => u.includes("/maquinas"))).toBe(false);
    expect(pedidos.some((u) => u.endsWith("models/ignis_auto.glb"))).toBe(true);
    expect(contenedor.textContent).toContain("Modelo 3D del auto");
    // Los recursos ilustrativos se marcan demostrativo (AGENTS.md: todo dato mostrado cita su origen).
    const origenes = Array.from(contenedor.querySelectorAll(".ignis-recursos-lista .ignis-origen")).map((e) => e.textContent);
    expect(origenes).toEqual(["demostrativo", "demostrativo"]);
    expect(contenedor.innerHTML).not.toContain("/api/v1/maquinas");
  });
});
