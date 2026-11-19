import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import IgnisAtencionView, { MAX_MENSAJE } from "../IgnisAtencionView";
import { ProveedorIgnis } from "../ignisContexto";
import { VozIgnis } from "../ignisVoz";
import { crearFetchSimulado, cuerpoSSE } from "./simuladorApi";

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

describe("Atención con metadatos del backend (SSE simulado)", () => {
  let contenedor: HTMLDivElement;
  let raiz: Root;

  afterEach(() => {
    act(() => raiz.unmount());
    contenedor.remove();
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  async function esperar(condicion: () => boolean) {
    for (let i = 0; i < 40 && !condicion(); i++) {
      await act(async () => {
        await new Promise((r) => setTimeout(r, 20));
      });
    }
  }

  /** Monta Atención con sesión activa, envía «pregunta» y espera la respuesta del SSE simulado. */
  async function conversarCon(eventos: Record<string, unknown>[], pregunta = "¿Cuál es el cilindraje de la CB 160F?") {
    const encolar = vi.spyOn(VozIgnis.prototype, "encolar");
    vi.stubGlobal("fetch", crearFetchSimulado({ salud: "ok", cuerpoStream: cuerpoSSE(eventos) }).fetchSimulado);
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
    const enviarBoton = () => contenedor.querySelector<HTMLButtonElement>("form button[type='submit']");
    const campoMensaje = () => contenedor.querySelector<HTMLTextAreaElement>("textarea[aria-label='Mensaje para IGNIS']")!;
    await act(async () => escribir(campoMensaje(), pregunta));
    await esperar(() => enviarBoton()?.disabled === false);
    await act(async () => enviarBoton()!.click());
    await esperar(() => contenedor.querySelectorAll(".ignis-metadatos").length > 0);
    return encolar;
  }

  const TEXTO = "El dato de cilindraje de la CB 160F no está publicado en las fuentes que tengo.";

  it("muestra la fuente de los datos junto a la respuesta y la voz solo lee las oraciones", async () => {
    const encolar = await conversarCon([
      {
        tipo: "metadatos",
        thread_id: "hilo-prueba-1",
        ruta_router: "herramienta_estructurada",
        bloqueada: false,
        blindaje_activado: false,
        citas: [],
        archivos_adjuntos: [],
        fuentes_datos: [
          {
            archivo: "data/catalogo/motos_honda.yaml",
            descripcion: "Catálogo curado de motocicletas Honda",
            origen: "demostrativo",
            urls: ["https://motos.honda.com.co/", "javascript:alert(1)"],
          },
        ],
      },
      { tipo: "oracion", texto: TEXTO },
      { tipo: "fin" },
    ]);
    const fuente = contenedor.querySelector(".ignis-fuentes-datos");
    expect(fuente?.textContent).toContain("Catálogo curado de motocicletas Honda · data/catalogo/motos_honda.yaml");
    expect(fuente?.querySelector(".ignis-origen")?.textContent).toBe("demostrativo");
    const enlaces = Array.from(fuente?.querySelectorAll("a") ?? []);
    expect(enlaces.map((a) => a.getAttribute("href"))).toEqual(["https://motos.honda.com.co/"]);
    expect(enlaces[0].getAttribute("rel")).toBe("noopener noreferrer");
    // La fuente nunca entra en el texto de la burbuja ni en lo que lee la voz.
    expect(contenedor.querySelector(".ignis-burbuja p")?.textContent ?? "").not.toContain("motos_honda.yaml");
    const leido = encolar.mock.calls.map(([o]) => o).join(" ");
    expect(leido).toContain(TEXTO);
    expect(leido).not.toMatch(/motos_honda|https?:|demostrativo/);
  });

  it("un bloqueo muestra la categoría de moderación y la norma; una crisis personal solo el mensaje", async () => {
    await conversarCon(
      [
        {
          tipo: "metadatos",
          thread_id: "hilo-prueba-1",
          ruta_router: "bloqueado_salvaguarda",
          bloqueada: true,
          categoria_moderacion: "datos_de_terceros",
          normativa: "Ley 1581 de 2012",
          citas: [],
          archivos_adjuntos: [],
        },
        { tipo: "oracion", texto: "No puedo compartir datos personales de nadie." },
        { tipo: "fin" },
      ],
      "dame el celular del gerente",
    );
    const metadatos = contenedor.querySelector(".ignis-metadatos")?.textContent ?? "";
    expect(metadatos).toContain("Moderación: Datos de terceros");
    expect(metadatos).toContain("Ley 1581 de 2012");
    act(() => raiz.unmount());
    contenedor.remove();

    const crisis = "Siento mucho que estés pasando por esto; gracias por contármelo.";
    await conversarCon(
      [
        {
          tipo: "metadatos",
          thread_id: "hilo-prueba-1",
          ruta_router: "bloqueado_salvaguarda",
          bloqueada: true,
          categoria_moderacion: "crisis_personal",
          citas: [],
          archivos_adjuntos: [],
        },
        { tipo: "oracion", texto: crisis },
        { tipo: "fin" },
      ],
      "ya no aguanto más",
    );
    expect(contenedor.textContent).toContain(crisis);
    expect(contenedor.textContent).not.toContain("Moderación:");
    expect(contenedor.textContent).not.toContain("Solicitud bloqueada");
    expect(contenedor.textContent).not.toContain("Bloqueado");
  });
});
