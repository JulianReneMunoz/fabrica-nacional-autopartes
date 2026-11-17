/**
 * Estado compartido entre el encabezado global y las pestañas: hilo activo (`thread_id`) y estado de los servicios.
 *
 * - El `thread_id` se guarda en localStorage solo hasta que existan las sesiones de usuario (#44); entonces el
 *   hilo pasa a ligarse al `user_id` seudónimo en el backend y la cookie httpOnly reemplaza este almacenamiento.
 * - API: se consulta `GET /salud` al montar y cada 30 s. SSE: lo informa la última conversación de Atención.
 */
import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { api } from "./api";

export type EstadoServicio = "comprobando" | "en_linea" | "reconectando" | "sin_conexion" | "sin_datos" | "respaldo";

export interface ContextoIgnisApp {
  hilo: string;
  /** Crea y activa un hilo nuevo; devuelve su id. */
  nuevoHilo: () => string;
  api: EstadoServicio;
  sse: EstadoServicio;
  /** Atención informa el origen de la última respuesta. */
  reportarSse: (estado: EstadoServicio) => void;
}

const CLAVE_HILO = "ignis.thread_id";
const INTERVALO_SALUD_MS = 30_000;

export const crearIdHilo = () => `hilo-${Date.now().toString(36)}${Math.random().toString(36).slice(2, 6)}`;

function leerHilo(): string {
  try {
    const guardado = localStorage.getItem(CLAVE_HILO);
    if (guardado && /^[A-Za-z0-9_-]{1,64}$/.test(guardado)) return guardado;
  } catch {
    /* almacenamiento no disponible */
  }
  return crearIdHilo();
}

function guardarHilo(id: string) {
  try {
    localStorage.setItem(CLAVE_HILO, id);
  } catch {
    /* almacenamiento no disponible */
  }
}

const Contexto = createContext<ContextoIgnisApp | null>(null);

export function ProveedorIgnis({ children }: { children: ReactNode }) {
  const [hilo, setHilo] = useState(leerHilo);
  const [estadoApi, setEstadoApi] = useState<EstadoServicio>("comprobando");
  const [sse, setSse] = useState<EstadoServicio>("sin_datos");
  const ultimoApi = useRef<EstadoServicio>("comprobando");

  useEffect(() => guardarHilo(hilo), [hilo]);

  useEffect(() => {
    let vivo = true;
    const comprobar = () => {
      api
        .salud()
        .then(() => "en_linea" as const)
        .catch(() => (ultimoApi.current === "en_linea" ? ("reconectando" as const) : ("sin_conexion" as const)))
        .then((e) => {
          if (!vivo) return;
          ultimoApi.current = e;
          setEstadoApi(e);
        });
    };
    comprobar();
    const id = window.setInterval(comprobar, INTERVALO_SALUD_MS);
    return () => {
      vivo = false;
      window.clearInterval(id);
    };
  }, []);

  const nuevoHilo = useCallback(() => {
    const id = crearIdHilo();
    setHilo(id);
    return id;
  }, []);

  const valor = useMemo<ContextoIgnisApp>(
    () => ({ hilo, nuevoHilo, api: estadoApi, sse, reportarSse: setSse }),
    [hilo, nuevoHilo, estadoApi, sse],
  );
  return <Contexto.Provider value={valor}>{children}</Contexto.Provider>;
}

export function useIgnis(): ContextoIgnisApp {
  const c = useContext(Contexto);
  if (!c) throw new Error("useIgnis debe usarse dentro de ProveedorIgnis");
  return c;
}
