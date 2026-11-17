/**
 * Backend simulado para las pruebas del frontend (jsdom): salud, sesiones (ADR-033), hilos y mensajes.
 * Enruta por URL y método y registra las llamadas. No usa red.
 */
import type { HiloDTO, MensajeHiloDTO } from "../ignisSesion";

export interface OpcionesSimulador {
  /** `/salud` responde (en línea) o falla como red caída. */
  salud?: "ok" | "caida";
  /** Sesión inicial: activa (cookie vigente), ninguna (401) o sin configurar en el servidor (503). */
  sesion?: "activa" | "ninguna" | "sin_secreto";
  hilos?: HiloDTO[];
  mensajes?: Record<string, MensajeHiloDTO[]>;
  /** Respuesta de `/ignis/stream` (por defecto, 200 sin cuerpo útil). */
  stream?: number;
}

export interface Llamada {
  metodo: string;
  url: string;
  cuerpo?: string;
}

const json = (datos: unknown, estado = 200) =>
  new Response(JSON.stringify(datos), { status: estado, headers: { "Content-Type": "application/json" } });

export const SESION_PRUEBA = { alias: "compras-01", user_id_corto: "a1b2c3d4" };
export const MENSAJE_SIN_SECRETO = "Las sesiones requieren IGNIS_SECRETO_SESION en .env (32 caracteres o más).";

export function crearFetchSimulado(opciones: OpcionesSimulador = {}) {
  let sesion = opciones.sesion ?? "activa";
  let siguiente = 1;
  const hilos = [...(opciones.hilos ?? [])];
  const llamadas: Llamada[] = [];

  const fetchSimulado = (async (entrada: RequestInfo | URL, init?: RequestInit) => {
    const url = String(entrada);
    const metodo = (init?.method ?? "GET").toUpperCase();
    llamadas.push({ metodo, url, cuerpo: typeof init?.body === "string" ? init.body : undefined });

    if (url.endsWith("/salud")) {
      if (opciones.salud === "caida") throw new TypeError("Failed to fetch");
      return json({ estado: "ok" });
    }
    if (url.startsWith("/api/v1/sesiones")) {
      if (sesion === "sin_secreto") return json({ codigo: "sesiones_no_configuradas", mensaje: MENSAJE_SIN_SECRETO }, 503);
      if (url === "/api/v1/sesiones" && metodo === "POST") {
        sesion = "activa";
        return json(SESION_PRUEBA, 201);
      }
      if (url === "/api/v1/sesiones/cerrar") {
        sesion = "ninguna";
        return new Response(null, { status: 204 });
      }
      if (sesion !== "activa") return json({ codigo: "sin_sesion", mensaje: "Sesión no válida o vencida." }, 401);
      if (url === "/api/v1/sesiones/yo") return json(SESION_PRUEBA);
      if (url === "/api/v1/sesiones/yo/hilos" && metodo === "POST") {
        const thread_id = `hilo-prueba-${siguiente++}`;
        hilos.unshift({ thread_id, titulo: "", turnos: 0, ultima_ruta: "", creado: "", actualizado: "" });
        return json({ thread_id }, 201);
      }
      if (url === "/api/v1/sesiones/yo/hilos") return json(hilos);
      const m = /^\/api\/v1\/sesiones\/yo\/hilos\/([^/]+)\/mensajes$/.exec(url);
      if (m) return json(opciones.mensajes?.[decodeURIComponent(m[1])] ?? []);
    }
    if (url.endsWith("/ignis/stream")) return new Response("", { status: opciones.stream ?? 200 });
    throw new TypeError("Failed to fetch");
  }) as typeof fetch;

  return { fetchSimulado, llamadas };
}
