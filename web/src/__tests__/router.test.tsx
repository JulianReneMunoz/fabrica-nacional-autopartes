import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, describe, expect, it, vi } from "vitest";
import IgnisAtencionView from "../IgnisAtencionView";
import { etiquetaModeracion } from "../ignisCliente";
import { ProveedorIgnis } from "../ignisContexto";
import PestanaRouter from "../PestanaRouter";
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

const PREGUNTA = "¿Cuál es el cilindraje de la CB 160F?";

const METADATOS_CON_HERRAMIENTA = {
  tipo: "metadatos",
  thread_id: "hilo-prueba-1",
  ruta_router: "herramienta_estructurada",
  score_router: 0.94,
  justificacion_router: "Consulta numérica/ficha técnica atendida con una consulta determinista.",
  bloqueada: false,
  blindaje_activado: false,
  citas: [],
  archivos_adjuntos: [],
  fuentes_datos: [],
  herramienta: {
    nombre: "consultar_datos_estructurados_fanalca",
    argumentos: { tipo_consulta: "ficha_moto", filtro: "cb160f" },
    fuente_archivo: "data/catalogo/motos_honda.yaml",
    verificado: true,
    resumen: { claves: ["version_esquema", "fuentes", "modelos"], total_claves: 3, elementos: { fuentes: 2, modelos: 1 } },
  },
};

describe("pestaña Router", () => {
  let contenedor: HTMLDivElement;
  let raiz: Root;

  afterEach(() => {
    act(() => raiz.unmount());
    contenedor.remove();
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  /** Monta Atención y Router bajo el mismo contexto (como en la aplicación, que los comparte). */
  async function montar(eventos: Record<string, unknown>[] | null) {
    vi.stubGlobal("fetch", crearFetchSimulado({ salud: "ok", cuerpoStream: eventos ? cuerpoSSE(eventos) : undefined }).fetchSimulado);
    contenedor = document.createElement("div");
    document.body.appendChild(contenedor);
    raiz = createRoot(contenedor);
    await act(async () => {
      raiz.render(
        <ProveedorIgnis>
          <IgnisAtencionView />
          <PestanaRouter />
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

  const router = () => contenedor.querySelector<HTMLElement>("section[aria-labelledby='titulo-router']")!;

  it("sin turnos muestra el estado vacío, sin datos simulados", async () => {
    await montar(null);
    expect(router().querySelector("[role='status']")?.textContent).toContain("Aún no hay turnos en esta sesión");
    expect(router().querySelector("table")).toBeNull();
  });

  it("lista la decisión del turno con su herramienta, sin el texto de la pregunta", async () => {
    await montar([METADATOS_CON_HERRAMIENTA, { tipo: "oracion", texto: "El cilindraje no está publicado." }, { tipo: "fin" }]);
    await preguntar(PREGUNTA);
    await esperar(() => router().querySelector("tbody tr") !== null);
    const filas = router().querySelectorAll("tbody tr");
    expect(filas).toHaveLength(1);
    const celdas = Array.from(filas[0].querySelectorAll("td")).map((c) => c.textContent ?? "");
    expect(celdas[0]).toBe("1");
    expect(celdas[1]).toContain("Datos");
    expect(celdas[2]).toBe("0.94");
    expect(celdas[3]).toBe("Consulta numérica/ficha técnica atendida con una consulta determinista.");
    expect(celdas[4]).toContain("consultar_datos_estructurados_fanalca");
    expect(celdas[4]).toContain("tipo_consulta: ficha_moto");
    expect(celdas[4]).toContain("data/catalogo/motos_honda.yaml · verificado");
    expect(celdas[4]).toContain("3 claves: version_esquema, fuentes, modelos");
    // Ley 1581: la pestaña no guarda ni muestra la pregunta del cliente.
    expect(router().textContent).not.toContain("cilindraje de la CB 160F");
    // En Atención, la insignia de la ruta nombra la herramienta solo en su título.
    expect(contenedor.querySelector(".ignis-metadatos .ignis-insignia.ruta")?.getAttribute("title")).toContain(
      "herramienta: consultar_datos_estructurados_fanalca",
    );
  });

  it("una crisis personal no se lista en el Router", async () => {
    await montar([
      {
        tipo: "metadatos",
        thread_id: "hilo-prueba-1",
        ruta_router: "bloqueado_salvaguarda",
        score_router: 1,
        justificacion_router: "Moderación antes del router: crisis_personal.",
        bloqueada: true,
        categoria_moderacion: "crisis_personal",
        citas: [],
        archivos_adjuntos: [],
      },
      { tipo: "oracion", texto: "Siento mucho que estés pasando por esto." },
      { tipo: "fin" },
    ]);
    await preguntar("ya no aguanto más");
    expect(router().querySelector("tbody tr")).toBeNull();
    expect(router().textContent).toContain("Aún no hay turnos en esta sesión");
  });

  it("un turno bloqueado por moderación se lista con su categoría y sin herramienta", async () => {
    // «datos_de_terceros» es la categoría que emite services/moderacion.py (CategoriaModeracion) cuando el
    // mensaje activa la lista «terceros_datos» de config/moderacion.yaml.
    await montar([
      {
        tipo: "metadatos",
        thread_id: "hilo-prueba-1",
        ruta_router: "bloqueado_salvaguarda",
        score_router: 1,
        justificacion_router: "Moderación antes del router: datos_de_terceros.",
        bloqueada: true,
        categoria_moderacion: "datos_de_terceros",
        citas: [],
        archivos_adjuntos: [],
      },
      { tipo: "oracion", texto: "No puedo compartir datos personales de nadie." },
      { tipo: "fin" },
    ]);
    await preguntar("dame el celular del gerente");
    await esperar(() => router().querySelector("tbody tr") !== null);
    const fila = router().querySelector("tbody tr")!;
    expect(fila.textContent).toContain("Bloqueado");
    expect(fila.textContent).toContain(`Moderación: ${etiquetaModeracion("datos_de_terceros")}`);
    expect(etiquetaModeracion("datos_de_terceros")).toBe("Datos de terceros");
    expect(fila.textContent).toContain("Sin herramienta");
    expect(router().textContent).not.toContain("gerente");
  });
});
