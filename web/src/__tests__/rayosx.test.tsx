import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, describe, expect, it, vi } from "vitest";
import IgnisAtencionView from "../IgnisAtencionView";
import { ProveedorIgnis } from "../ignisContexto";
import PestanaRayosX from "../PestanaRayosX";
import { crearFetchSimulado, cuerpoSSE } from "./simuladorApi";

(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

function escribir(campo: HTMLTextAreaElement, valor: string) {
  const setter = Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, "value")!.set!;
  setter.call(campo, valor);
  campo.dispatchEvent(new Event("input", { bubbles: true }));
}

async function esperar(condicion: () => boolean) {
  for (let i = 0; i < 40 && !condicion(); i++) {
    await act(async () => {
      await new Promise((r) => setTimeout(r, 20));
    });
  }
}

const METADATOS = {
  tipo: "metadatos",
  thread_id: "hilo-prueba-1",
  ruta_router: "herramienta_estructurada",
  score_router: 0.94,
  justificacion_router: "Consulta numérica/ficha técnica atendida con una consulta determinista.",
  bloqueada: false,
  blindaje_activado: true,
  citas: [],
  archivos_adjuntos: [],
  fuentes_datos: [],
  herramienta: {
    nombre: "consultar_datos_estructurados_fanalca",
    argumentos: { tipo_consulta: "ficha_moto", filtro: "cb160f" },
    fuente_archivo: "data/catalogo/motos_honda.yaml",
    verificado: true,
    resumen: { claves: ["modelos"], total_claves: 1, elementos: { modelos: 1 } },
  },
};

describe("pestaña Rayos-X y validación", () => {
  let contenedor: HTMLDivElement;
  let raiz: Root;

  afterEach(() => {
    act(() => raiz.unmount());
    contenedor.remove();
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  async function montar(eventos: Record<string, unknown>[] | null) {
    vi.stubGlobal("fetch", crearFetchSimulado({ salud: "ok", cuerpoStream: eventos ? cuerpoSSE(eventos) : undefined }).fetchSimulado);
    contenedor = document.createElement("div");
    document.body.appendChild(contenedor);
    raiz = createRoot(contenedor);
    await act(async () => {
      raiz.render(
        <ProveedorIgnis>
          <IgnisAtencionView />
          <PestanaRayosX />
        </ProveedorIgnis>,
      );
    });
  }

  async function preguntar(pregunta: string) {
    const enviar = () => contenedor.querySelector<HTMLButtonElement>("form button[type='submit']");
    const campo = () => contenedor.querySelector<HTMLTextAreaElement>("textarea[aria-label='Mensaje para IGNIS']")!;
    await act(async () => escribir(campo(), pregunta));
    await esperar(() => enviar()?.disabled === false);
    await act(async () => enviar()!.click());
    await esperar(() => contenedor.querySelectorAll(".ignis-metadatos").length > 0);
  }

  const rayos = () => contenedor.querySelector<HTMLElement>("section[aria-labelledby='titulo-rayos-x']")!;

  it("sin turnos muestra el estado vacío, sin tabla ni datos simulados", async () => {
    await montar(null);
    expect(rayos().querySelector("[role='status']")?.textContent).toContain(
      "Envía una pregunta en Atención para ver aquí su recorrido",
    );
    expect(rayos().querySelector("table")).toBeNull();
    expect(rayos().querySelector(".ig-rayos-ultimo")).toBeNull();
  });

  it("con un turno muestra la tarjeta del último turno y la lista, sin el texto de la pregunta", async () => {
    await montar([METADATOS, { tipo: "oracion", texto: "El cilindraje no está publicado." }, { tipo: "fin" }]);
    await preguntar("¿Cuál es el cilindraje de la CB 160F?");
    await esperar(() => rayos().querySelector("tbody tr") !== null);

    const tarjeta = rayos().querySelector<HTMLElement>(".ig-rayos-ultimo")!;
    expect(tarjeta.textContent).toContain("Último turno (n.º 1)");
    expect(tarjeta.textContent).toContain("Datos");
    expect(tarjeta.textContent).toContain("0.94");
    expect(tarjeta.textContent).toContain("Blindaje activadoSí");
    expect(tarjeta.textContent).toContain("Sin bloqueo");
    expect(tarjeta.textContent).toContain("consultar_datos_estructurados_fanalca");
    expect(tarjeta.textContent).toContain("data/catalogo/motos_honda.yaml · verificado");

    const filas = rayos().querySelectorAll("tbody tr");
    expect(filas).toHaveLength(1);
    const celdas = Array.from(filas[0].querySelectorAll("td")).map((c) => c.textContent ?? "");
    expect(celdas[0]).toBe("1");
    expect(celdas[1]).toContain("Datos");
    expect(celdas[2]).toBe("0.94");
    expect(celdas[3]).toBe("consultar_datos_estructurados_fanalca");
    expect(celdas[4]).toBe("Sí");

    // Ley 1581: la pestaña no muestra la pregunta del cliente.
    expect(rayos().textContent).not.toContain("cilindraje de la CB 160F");
  });
});
