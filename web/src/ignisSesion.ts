/**
 * Cliente de las sesiones por usuario seudónimo (ADR-033).
 *
 * La sesión vive en la cookie httpOnly `ignis_sesion`, cifrada por el servidor: el frontend no la lee ni la guarda
 * (nada en el almacenamiento del navegador). Las peticiones van al mismo origen, así que el navegador envía la
 * cookie solo.
 */

const BASE = "/api/v1/sesiones";

export interface SesionDTO {
  alias: string;
  user_id_corto: string;
}

export interface HiloDTO {
  thread_id: string;
  titulo: string;
  turnos: number;
  ultima_ruta: string;
  creado: string;
  actualizado: string;
}

export interface MensajeHiloDTO {
  rol: "user" | "assistant" | string;
  contenido: string;
  ruta: string | null;
  citas: Record<string, unknown>[];
}

/** Error HTTP de las sesiones con un mensaje para el usuario (los del servidor ya son genéricos). */
export class ErrorSesion extends Error {
  constructor(
    readonly estado: number,
    mensaje: string,
  ) {
    super(mensaje);
    this.name = "ErrorSesion";
  }
}

const MENSAJES: Record<number, string> = {
  401: "La sesión expiró: vuelve a entrar con tu alias.",
  403: "Ese hilo no pertenece a tu sesión.",
  404: "El hilo no existe.",
  422: "Alias no válido: usa de 3 a 32 letras, números o guiones, sin nombre completo, correo ni teléfono.",
};

async function pedir<T>(ruta: string, init?: RequestInit): Promise<T> {
  let r: Response;
  try {
    r = await fetch(BASE + ruta, {
      credentials: "same-origin",
      ...init,
      headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    });
  } catch {
    throw new ErrorSesion(0, "No fue posible conectar con el backend. Verifica que FastAPI esté en ejecución.");
  }
  if (!r.ok) {
    let mensaje = MENSAJES[r.status] ?? `Error del servidor (HTTP ${r.status}).`;
    // 503 sin IGNIS_SECRETO_SESION: el servidor explica qué falta; ese mensaje se muestra tal cual.
    if (r.status === 503) {
      try {
        const cuerpo = (await r.json()) as { mensaje?: unknown };
        if (typeof cuerpo.mensaje === "string") mensaje = cuerpo.mensaje;
      } catch {
        /* respuesta sin JSON */
      }
    }
    throw new ErrorSesion(r.status, mensaje);
  }
  return (r.status === 204 ? undefined : await r.json()) as T;
}

/** Sesión actual, o `null` si no hay (401). Otros errores (503, red) se lanzan para mostrarlos. */
export async function leerSesion(): Promise<SesionDTO | null> {
  try {
    return await pedir<SesionDTO>("/yo");
  } catch (e) {
    if (e instanceof ErrorSesion && e.estado === 401) return null;
    throw e;
  }
}

export const entrar = (alias: string) => pedir<SesionDTO>("", { method: "POST", body: JSON.stringify({ alias }) });
export const cerrarSesion = () => pedir<void>("/cerrar", { method: "POST" });
export const listarHilos = () => pedir<HiloDTO[]>("/yo/hilos");
export const crearHilo = () => pedir<{ thread_id: string }>("/yo/hilos", { method: "POST" });
export const mensajesHilo = (threadId: string) =>
  pedir<MensajeHiloDTO[]>(`/yo/hilos/${encodeURIComponent(threadId)}/mensajes`);

/**
 * Validación del alias en el cliente, con la misma regla que el backend (`services/sesiones.py`). Devuelve el
 * mensaje de error o `null` si es válido. El servidor vuelve a validar siempre.
 */
export function validarAlias(alias: string): string | null {
  const limpio = alias.trim().normalize("NFC");
  const valido =
    /^[A-Za-z0-9ÁÉÍÓÚÜÑáéíóúüñ-]{3,32}$/.test(limpio) &&
    !/^\d+$/.test(limpio) &&
    !/\d{6,}/.test(limpio) &&
    !/^\p{L}{2,}(?:-\p{L}{2,})+$/u.test(limpio);
  return valido ? null : MENSAJES[422];
}
