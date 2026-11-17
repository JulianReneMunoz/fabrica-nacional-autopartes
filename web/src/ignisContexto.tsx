/**
 * Estado compartido entre el encabezado global y las pestañas: sesión del usuario seudónimo, hilo activo
 * (`thread_id`) y estado de los servicios.
 *
 * - La sesión es la cookie httpOnly que pone el backend (ADR-033); el frontend no guarda nada en el navegador.
 * - El hilo activo vive en memoria. Al entrar (o al recargar) se toma el hilo más reciente del usuario o se crea
 *   uno nuevo en el servidor, que lo liga al `user_id` seudónimo.
 * - API: se consulta `GET /salud` al montar y cada 30 s. SSE: lo informa la última conversación de Atención.
 */
import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { api } from "./api";
import {
  cerrarSesion as cerrarSesionApi,
  crearHilo,
  entrar as entrarApi,
  ErrorSesion,
  leerSesion,
  listarHilos,
  type SesionDTO,
} from "./ignisSesion";

export type EstadoServicio = "comprobando" | "en_linea" | "reconectando" | "sin_conexion" | "sin_datos" | "respaldo";

export type EstadoSesion =
  | { estado: "comprobando" }
  | { estado: "sin_sesion"; aviso?: string }
  | { estado: "activa"; alias: string; userIdCorto: string };

export interface ContextoIgnisApp {
  sesion: EstadoSesion;
  /** Hilo activo, o `null` mientras se prepara la sesión. */
  hilo: string | null;
  /** Aumenta cada vez que se abre un hilo existente (para que Atención cargue su historial). */
  aperturas: number;
  entrar: (alias: string) => Promise<void>;
  cerrarSesion: () => Promise<void>;
  /** La API respondió 401: la sesión venció o se borró la cookie. */
  sesionVencida: () => void;
  /** Crea y activa un hilo nuevo en el servidor; devuelve su id. */
  nuevoHilo: () => Promise<string>;
  /** Activa un hilo existente del usuario. */
  abrirHilo: (threadId: string) => void;
  api: EstadoServicio;
  sse: EstadoServicio;
  /** Atención informa el origen de la última respuesta. */
  reportarSse: (estado: EstadoServicio) => void;
}

const INTERVALO_SALUD_MS = 30_000;
const AVISO_VENCIDA = "La sesión expiró: vuelve a entrar con tu alias.";

const Contexto = createContext<ContextoIgnisApp | null>(null);

function activa(s: SesionDTO): EstadoSesion {
  return { estado: "activa", alias: s.alias, userIdCorto: s.user_id_corto };
}

export function ProveedorIgnis({ children }: { children: ReactNode }) {
  const [sesion, setSesion] = useState<EstadoSesion>({ estado: "comprobando" });
  const [hilo, setHilo] = useState<string | null>(null);
  const [aperturas, setAperturas] = useState(0);
  const [estadoApi, setEstadoApi] = useState<EstadoServicio>("comprobando");
  const [sse, setSse] = useState<EstadoServicio>("sin_datos");
  const ultimoApi = useRef<EstadoServicio>("comprobando");

  /** Hilo más reciente del usuario o uno nuevo. */
  const prepararHilo = useCallback(async () => {
    const hilos = await listarHilos();
    setHilo(hilos[0]?.thread_id ?? (await crearHilo()).thread_id);
  }, []);

  const iniciar = useCallback(
    async (s: SesionDTO) => {
      setSesion(activa(s));
      try {
        await prepararHilo();
      } catch (e) {
        if (e instanceof ErrorSesion && e.estado === 401) setSesion({ estado: "sin_sesion", aviso: AVISO_VENCIDA });
      }
    },
    [prepararHilo],
  );

  // Sesión existente (cookie de una visita anterior, aún vigente).
  useEffect(() => {
    let vivo = true;
    leerSesion()
      .then((s) => {
        if (!vivo) return;
        if (s) void iniciar(s);
        else setSesion({ estado: "sin_sesion" });
      })
      .catch((e: unknown) => {
        if (vivo) setSesion({ estado: "sin_sesion", aviso: e instanceof Error ? e.message : String(e) });
      });
    return () => {
      vivo = false;
    };
  }, [iniciar]);

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

  const entrar = useCallback(async (alias: string) => iniciar(await entrarApi(alias)), [iniciar]);

  const cerrarSesion = useCallback(async () => {
    try {
      await cerrarSesionApi();
    } finally {
      setHilo(null);
      setSesion({ estado: "sin_sesion" });
    }
  }, []);

  const sesionVencida = useCallback(() => {
    setHilo(null);
    setSesion({ estado: "sin_sesion", aviso: AVISO_VENCIDA });
  }, []);

  const nuevoHilo = useCallback(async () => {
    const { thread_id } = await crearHilo();
    setHilo(thread_id);
    return thread_id;
  }, []);

  const abrirHilo = useCallback((threadId: string) => {
    setHilo(threadId);
    setAperturas((n) => n + 1);
  }, []);

  const valor = useMemo<ContextoIgnisApp>(
    () => ({
      sesion,
      hilo,
      aperturas,
      entrar,
      cerrarSesion,
      sesionVencida,
      nuevoHilo,
      abrirHilo,
      api: estadoApi,
      sse,
      reportarSse: setSse,
    }),
    [sesion, hilo, aperturas, entrar, cerrarSesion, sesionVencida, nuevoHilo, abrirHilo, estadoApi, sse],
  );
  return <Contexto.Provider value={valor}>{children}</Contexto.Provider>;
}

export function useIgnis(): ContextoIgnisApp {
  const c = useContext(Contexto);
  if (!c) throw new Error("useIgnis debe usarse dentro de ProveedorIgnis");
  return c;
}
