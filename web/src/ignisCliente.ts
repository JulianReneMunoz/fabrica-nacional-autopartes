/**
 * Cliente de conversación de IGNIS.
 * 1) Intenta el SSE del agente (POST /api/v1/ignis/stream).
 * 2) Si ese endpoint no existe o falla antes de empezar, usa el Q&A del M1 (POST /api/v1/tareas/qa) y lo marca como respaldo.
 * El texto llega por eventos; nunca se interpretan etiquetas dentro del texto (R09).
 */

/**
 * Origen de un dato mostrado en el visor (AGENTS.md): `scraping`, `lectura_web` o `semilla` para el corpus de Fanalca;
 * `demostrativo` para recursos ilustrativos o cualquier dato que llegue sin origen.
 */
export type OrigenDato = "scraping" | "lectura_web" | "semilla" | "demostrativo";

export function normalizarOrigen(valor: unknown): OrigenDato {
  return valor === "scraping" || valor === "lectura_web" || valor === "semilla" ? valor : "demostrativo";
}

export interface CitaIgnis {
  id: string;
  titulo: string;
  url: string;
  origen: OrigenDato;
}

export interface AdjuntoIgnis {
  id: string;
  tipo: string;
  titulo: string;
  formato: string;
  url: string;
  origen: OrigenDato;
  tamano_kb?: number;
}

export interface MetadatosIgnis {
  ruta_router?: string;
  score_router?: number;
  blindaje_activado?: boolean;
  bloqueada?: boolean;
  citas?: CitaIgnis[];
  /** Compatibilidad: algunos backends envían los adjuntos dentro de los metadatos («archivos_adjuntos»). */
  adjuntos?: AdjuntoIgnis[];
}

export type EventoConversacion =
  | { tipo: "token"; texto: string }
  | { tipo: "oracion"; texto: string }
  | { tipo: "metadatos"; datos: MetadatosIgnis }
  | { tipo: "adjunto"; adjunto: AdjuntoIgnis }
  | { tipo: "error"; mensaje: string }
  | { tipo: "fin" };

export type OrigenRespuesta = "sse" | "respaldo";

const BASE = "/api/v1";

/** Solo se aceptan descargas servidas por la propia aplicación (lista blanca de prefijos). */
const PREFIJOS_PERMITIDOS = ["/api/v1/adjuntos/", "/app/assets/", "/app/models/"];

export function urlAdjuntoPermitida(url: string): boolean {
  if (!url.startsWith("/") || url.startsWith("//") || url.includes("..")) return false;
  return PREFIJOS_PERMITIDOS.some((p) => url.startsWith(p));
}

/**
 * Etiquetas v2 del router (documentos / datos / mixto / directo / bloqueado) para la interfaz.
 * El contrato del backend no cambia: `ruta_router` sigue llegando con los nombres de `agente_ignis_m2.py`.
 */
const ETIQUETA_RUTA: Record<string, string> = {
  rag_documental: "Documentos",
  herramienta_estructurada: "Datos",
  mixto: "Mixto",
  directo: "Directo",
  memoria_store: "Memoria",
  bloqueado_salvaguarda: "Bloqueado",
  bloqueada: "Bloqueado",
  respaldo_m1: "Documentos (respaldo M1)",
};

export function etiquetaRuta(ruta: string): string {
  return ETIQUETA_RUTA[ruta] ?? ruta;
}

/** Normaliza una cita que puede venir como {id|fragmento_id, titulo, url, origen}. */
export function normalizarCita(c: Record<string, unknown>): CitaIgnis | null {
  const id = String(c.id ?? c.fragmento_id ?? "").trim();
  if (!id) return null;
  const url = typeof c.url === "string" && /^https?:\/\//.test(c.url) ? c.url : "";
  return { id, titulo: String(c.titulo ?? c.title ?? id), url, origen: normalizarOrigen(c.origen) };
}

/** Adjunto validado contra la lista blanca; null si la URL no es de la propia aplicación. */
function crearAdjunto(d: Record<string, unknown>, tipoArchivo: unknown): AdjuntoIgnis | null {
  const url = String(d.url ?? (d.id ? `${BASE}/adjuntos/${encodeURIComponent(String(d.id))}` : ""));
  if (!urlAdjuntoPermitida(url)) return null;
  return {
    id: String(d.id ?? url),
    tipo: String(tipoArchivo ?? "archivo"),
    titulo: String(d.titulo ?? "Archivo"),
    formato: String(d.formato ?? ""),
    url,
    origen: normalizarOrigen(d.origen),
    tamano_kb: typeof d.tamano_kb === "number" ? d.tamano_kb : undefined,
  };
}

/** Convierte un objeto JSON de un evento SSE en un evento tipado; ignora lo desconocido. */
export function interpretarEvento(nombre: string | null, datos: unknown): EventoConversacion | null {
  if (typeof datos !== "object" || datos === null) {
    return typeof datos === "string" && (nombre === "token" || nombre === null) ? { tipo: "token", texto: datos } : null;
  }
  const d = datos as Record<string, unknown>;
  const tipo = String(nombre ?? d.tipo ?? d.type ?? "");
  switch (tipo) {
    case "token":
      return { tipo: "token", texto: String(d.texto ?? d.text ?? "") };
    case "oracion":
      return { tipo: "oracion", texto: String(d.texto ?? "") };
    case "metadatos": {
      const citas = Array.isArray(d.citas)
        ? (d.citas as Record<string, unknown>[]).map(normalizarCita).filter((c): c is CitaIgnis => c !== null)
        : undefined;
      return {
        tipo: "metadatos",
        datos: {
          ruta_router: typeof d.ruta_router === "string" ? d.ruta_router : undefined,
          score_router: typeof d.score_router === "number" ? d.score_router : undefined,
          blindaje_activado: d.blindaje_activado === true,
          bloqueada: d.bloqueada === true || d.ruta_router === "bloqueada",
          citas,
          adjuntos: Array.isArray(d.archivos_adjuntos)
            ? (d.archivos_adjuntos as Record<string, unknown>[])
                .map((a) => crearAdjunto(a, a.tipo_archivo ?? a.tipo))
                .filter((a): a is AdjuntoIgnis => a !== null)
            : undefined,
        },
      };
    }
    case "adjunto": {
      const adjunto = crearAdjunto(d, nombre === "adjunto" ? d.tipo : d.tipo_archivo);
      return adjunto ? { tipo: "adjunto", adjunto } : null;
    }
    case "error":
      return { tipo: "error", mensaje: String(d.mensaje ?? d.detail ?? "Error del servidor") };
    case "fin":
    case "end":
    case "done":
      return { tipo: "fin" };
    default:
      return null;
  }
}

/**
 * Lector SSE incremental: acumula fragmentos hasta tener eventos completos (separados por línea en blanco),
 * admite «event:», varias líneas «data:» y finales de línea \r\n.
 */
export function crearLectorSSE(alEvento: (e: EventoConversacion) => void) {
  let bufer = "";
  const procesarBloque = (bloque: string) => {
    let nombre: string | null = null;
    const datos: string[] = [];
    for (const linea of bloque.split("\n")) {
      if (linea.startsWith(":")) continue;
      if (linea.startsWith("event:")) nombre = linea.slice(6).trim();
      else if (linea.startsWith("data:")) datos.push(linea.slice(5).replace(/^ /, ""));
    }
    if (datos.length === 0) return;
    const crudo = datos.join("\n");
    if (crudo === "[DONE]") {
      alEvento({ tipo: "fin" });
      return;
    }
    let valor: unknown = crudo;
    try {
      valor = JSON.parse(crudo);
    } catch {
      /* texto plano */
    }
    const evento = interpretarEvento(nombre, valor);
    if (evento) alEvento(evento);
  };
  return {
    alimentar(fragmento: string) {
      bufer += fragmento.replace(/\r\n/g, "\n");
      let corte = bufer.indexOf("\n\n");
      while (corte >= 0) {
        procesarBloque(bufer.slice(0, corte));
        bufer = bufer.slice(corte + 2);
        corte = bufer.indexOf("\n\n");
      }
    },
    cerrar() {
      if (bufer.trim()) procesarBloque(bufer);
      bufer = "";
    },
  };
}

class SinStream extends Error {}

/** Envía la consulta y emite eventos. Devuelve el origen usado (SSE o respaldo). */
export async function conversar(
  mensaje: string,
  threadId: string,
  alEvento: (e: EventoConversacion) => void,
  senal?: AbortSignal,
): Promise<OrigenRespuesta> {
  try {
    const r = await fetch(`${BASE}/ignis/stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
      body: JSON.stringify({ mensaje, thread_id: threadId }),
      signal: senal,
    });
    if (!r.ok || !r.body) throw new SinStream(`HTTP ${r.status}`);
    const lector = crearLectorSSE(alEvento);
    const reader = r.body.getReader();
    const decoder = new TextDecoder("utf-8");
    for (;;) {
      const { value, done } = await reader.read();
      if (done) break;
      lector.alimentar(decoder.decode(value, { stream: true }));
    }
    lector.alimentar(decoder.decode());
    lector.cerrar();
    alEvento({ tipo: "fin" });
    return "sse";
  } catch (e) {
    if (senal?.aborted) throw e;
    if (!(e instanceof SinStream) && !(e instanceof TypeError)) throw e;
  }

  // Respaldo: Q&A del M1 (sin streaming ni memoria por hilo).
  const r = await fetch(`${BASE}/tareas/qa`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ pregunta: mensaje }),
    signal: senal,
  });
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  const j = (await r.json()) as { respuesta?: string; fuentes?: Record<string, unknown>[]; fundamentada?: boolean };
  alEvento({
    tipo: "metadatos",
    datos: {
      ruta_router: "respaldo_m1",
      citas: (j.fuentes ?? []).map(normalizarCita).filter((c): c is CitaIgnis => c !== null),
    },
  });
  alEvento({ tipo: "token", texto: j.respuesta ?? "" });
  alEvento({ tipo: "fin" });
  return "respaldo";
}
