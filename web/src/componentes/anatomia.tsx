/**
 * Hooks comunes del método Anatomy: datos de la máquina (base de conocimiento vía API), reloj de simulación
 * con cámara lenta y recorrido automático (< 30 s, grabable). Con `prefers-reduced-motion: reduce` el
 * recorrido automático no se inicia solo: solo arranca desde el botón «Recorrido 30 s».
 */
import { useCallback, useEffect, useRef, useState } from "react";
import { api, type Maquina } from "../api";

export const fmt = (v: number, d = 0) => v.toLocaleString("es-CO", { minimumFractionDigits: d, maximumFractionDigits: d });

/* ---------- datos de la máquina ---------- */
export function useMaquina(id: string) {
  const [maquina, setMaquina] = useState<Maquina | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    api.maquina(id).then(setMaquina, (e: Error) => setError(e.message));
  }, [id]);
  return { maquina, error };
}

/* ---------- preferencia de movimiento reducido ---------- */
const CONSULTA_REDUCIDO = "(prefers-reduced-motion: reduce)";
export function prefiereMovimientoReducido(): boolean {
  return typeof window !== "undefined" && typeof window.matchMedia === "function" && window.matchMedia(CONSULTA_REDUCIDO).matches;
}
export function useMovimientoReducido(): boolean {
  const [reducido, setReducido] = useState(prefiereMovimientoReducido);
  useEffect(() => {
    if (typeof window.matchMedia !== "function") return;
    const mq = window.matchMedia(CONSULTA_REDUCIDO);
    const alCambiar = () => setReducido(mq.matches);
    mq.addEventListener?.("change", alCambiar);
    return () => mq.removeEventListener?.("change", alCambiar);
  }, []);
  return reducido;
}

/* ---------- reloj de simulación con cámara lenta ---------- */
export function useReloj(escala: number) {
  const [corriendo, setCorriendo] = useState(false);
  const [t, setT] = useState(0);
  const ultimo = useRef<number | null>(null);
  const escalaRef = useRef(escala);
  escalaRef.current = escala;
  useEffect(() => {
    if (!corriendo) {
      ultimo.current = null;
      return;
    }
    let id = 0;
    const paso = (ahora: number) => {
      if (ultimo.current !== null) {
        const dt = Math.min((ahora - ultimo.current) / 1000, 0.1);
        setT((v) => v + dt * escalaRef.current);
      }
      ultimo.current = ahora;
      id = requestAnimationFrame(paso);
    };
    id = requestAnimationFrame(paso);
    return () => cancelAnimationFrame(id);
  }, [corriendo]);
  const reiniciar = useCallback(() => {
    setCorriendo(false);
    setT(0);
  }, []);
  return { t, setT, corriendo, setCorriendo, reiniciar };
}

/* ---------- recorrido automático (< 30 s) ---------- */
export interface PasoTour {
  en: number; // segundo de inicio
  texto: string;
  accion?: () => void;
}

declare global {
  interface Window {
    __tour?: { estado: "corriendo" | "terminado"; duracion: number };
  }
}

export function useTour(solicitado: boolean, pasos: PasoTour[], duracion: number) {
  const reducido = useMovimientoReducido();
  // El botón «Recorrido 30 s» añade `inicio=manual`: es una orden explícita y sí arranca con movimiento reducido.
  const manual = typeof window !== "undefined" && /[?&]inicio=manual/.test(window.location.hash);
  const bloqueado = solicitado && reducido && !manual;
  const activo = solicitado && !bloqueado;
  const [indice, setIndice] = useState(-1);
  const [transcurrido, setTranscurrido] = useState(0);
  const pasosRef = useRef(pasos);
  pasosRef.current = pasos;
  useEffect(() => {
    if (!activo) return;
    window.__tour = { estado: "corriendo", duracion };
    const inicio = performance.now();
    let ejecutado = -1;
    let id = 0;
    const ciclo = () => {
      const s = (performance.now() - inicio) / 1000;
      setTranscurrido(s);
      const lista = pasosRef.current;
      while (ejecutado + 1 < lista.length && lista[ejecutado + 1].en <= s) {
        ejecutado += 1;
        lista[ejecutado].accion?.();
        setIndice(ejecutado);
      }
      if (s < duracion) id = requestAnimationFrame(ciclo);
      else window.__tour = { estado: "terminado", duracion };
    };
    // Breve margen para que la escena cargue antes del primer paso.
    const espera = window.setTimeout(() => (id = requestAnimationFrame(ciclo)), 400);
    return () => {
      window.clearTimeout(espera);
      cancelAnimationFrame(id);
    };
  }, [activo, duracion]);
  const texto = activo && indice >= 0 ? pasos[indice].texto : bloqueado ? "Movimiento reducido activo: el recorrido no se inicia solo. Pulsar «Recorrido 30 s» para verlo." : null;
  return { texto, transcurrido: activo ? Math.min(transcurrido, duracion) : 0, duracion, bloqueadoPorMovimiento: bloqueado };
}

export function BandaTour({ texto, transcurrido, duracion, bloqueadoPorMovimiento }: { texto: string | null; transcurrido: number; duracion: number; bloqueadoPorMovimiento?: boolean }) {
  if (!texto) return null;
  return (
    <div className="tour-banda" role="status" aria-live="polite">
      <span>{texto}</span>
      {!bloqueadoPorMovimiento && (
        <span className="progreso">
          {transcurrido.toFixed(1)} / {duracion} s
        </span>
      )}
    </div>
  );
}

/** Ruta del recorrido de una máquina lanzado desde el botón (orden explícita: respeta el movimiento reducido). */
export const hashRecorrido = (ruta: string) => `${ruta}?tour=1&inicio=manual`;
