/**
 * Piezas comunes del método Anatomy: una pregunta, una relación medible, 2–4 controles,
 * correr/pausar/reiniciar, cámara lenta, cifras junto a las piezas, idea principal,
 * revisión crítica, recorrido automático (< 30 s, grabable) y modo experimento.
 */
import { useCallback, useEffect, useRef, useState, type ReactNode } from "react";
import { api, type Maquina } from "../api";

/* ---------- datos de la máquina (base de conocimiento vía API) ---------- */
export function useMaquina(id: string) {
  const [maquina, setMaquina] = useState<Maquina | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    api.maquina(id).then(setMaquina, (e: Error) => setError(e.message));
  }, [id]);
  return { maquina, error };
}

export function Insignia({ tipo }: { tipo: string }) {
  const textos: Record<string, string> = {
    scraping: "scraping",
    lectura_web: "lectura web",
    semilla: "semilla",
    demostrativo: "demostrativo",
    base_conocimiento: "base de conocimiento",
  };
  return <span className={`insignia ${tipo}`}>{textos[tipo] ?? tipo}</span>;
}

export function PanelEmpresa({ maquina, error }: { maquina: Maquina | null; error: string | null }) {
  return (
    <section className="panel" aria-label="Datos de la empresa">
      <h3>Datos de la empresa (web scraping)</h3>
      {error && <p className="aviso error">Sin conexión con la API: {error}</p>}
      {!maquina && !error && <p className="aviso">Consultando la base de conocimiento…</p>}
      {maquina && (
        <ul className="datos">
          {maquina.datos_empresa.map((d) => (
            <li key={d.fragmento_id}>
              <Insignia tipo={d.origen} />
              {d.texto}
              <br />
              <a href={d.url} target="_blank" rel="noreferrer">{d.url}</a>
            </li>
          ))}
          {maquina.parametros.map((p) => (
            <li key={p.nombre}>
              <Insignia tipo={p.procedencia} />
              {p.nombre.replace(/_/g, " ")}: <b className="num">{p.valor.toLocaleString("es-CO")}</b> {p.unidad}
              {p.fuente && (
                <>
                  <br />
                  <a href={p.fuente} target="_blank" rel="noreferrer">{p.fuente}</a>
                </>
              )}
            </li>
          ))}
        </ul>
      )}
      <p className="aviso" style={{ marginTop: 10 }}>
        Las cifras de la máquina son demostrativas; los datos de la empresa provienen de los sitios oficiales y
        se citan con su URL.
      </p>
    </section>
  );
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

export function Reproduccion(props: {
  corriendo: boolean;
  alCorrer: () => void;
  alPausar: () => void;
  alReiniciar: () => void;
  escala: number;
  alEscala: (v: number) => void;
}) {
  return (
    <div className="barra" role="group" aria-label="Reproducción">
      {props.corriendo ? (
        <button className="boton" onClick={props.alPausar}>❚❚ Pausar</button>
      ) : (
        <button className="boton" onClick={props.alCorrer}>▶ Correr</button>
      )}
      <button className="boton secundario" onClick={props.alReiniciar}>↺ Reiniciar</button>
      <label className="chip">
        Velocidad
        <select
          aria-label="Velocidad de simulación"
          value={props.escala}
          onChange={(e) => props.alEscala(Number(e.target.value))}
        >
          <option value={1}>1×</option>
          <option value={0.5}>0,5×</option>
          <option value={0.25}>0,25× (lenta)</option>
          <option value={0.1}>0,1× (muy lenta)</option>
        </select>
      </label>
    </div>
  );
}

export function Deslizador(props: {
  etiqueta: string;
  valor: number;
  min: number;
  max: number;
  paso: number;
  unidad: string;
  alCambiar: (v: number) => void;
  formato?: (v: number) => string;
}) {
  const id = `ctl-${props.etiqueta.replace(/\W+/g, "-")}`;
  const texto = props.formato ? props.formato(props.valor) : props.valor.toLocaleString("es-CO");
  return (
    <div className="control">
      <label htmlFor={id}>{props.etiqueta}</label>
      <output htmlFor={id}>
        {texto} {props.unidad}
      </output>
      <input
        id={id}
        type="range"
        min={props.min}
        max={props.max}
        step={props.paso}
        value={props.valor}
        onChange={(e) => props.alCambiar(Number(e.target.value))}
      />
    </div>
  );
}

export function Pasos({ pasos, actual }: { pasos: string[]; actual: number }) {
  return (
    <ol className="pasos" aria-label="Secuencia del mecanismo">
      {pasos.map((p, i) => (
        <li key={p} className={i === actual ? "actual" : undefined} aria-current={i === actual ? "step" : undefined}>
          {p}
        </li>
      ))}
    </ol>
  );
}

export function Chip({ etiqueta, valor, tono }: { etiqueta: string; valor: ReactNode; tono?: string }) {
  return (
    <span className={`chip ${tono ?? ""}`}>
      {etiqueta} <b>{valor}</b>
    </span>
  );
}

/* ---------- modo experimento: predecir, ejecutar, comparar ---------- */
export interface Experimento {
  pregunta: string;
  opciones: { texto: string; correcta: boolean }[];
  explicacion: string;
  aplicar: () => void;
}

export function ModoExperimento({ experimentos }: { experimentos: Experimento[] }) {
  const [indice, setIndice] = useState(0);
  const [elegida, setElegida] = useState<number | null>(null);
  const [revelado, setRevelado] = useState(false);
  const exp = experimentos[indice];
  const siguiente = () => {
    setIndice((indice + 1) % experimentos.length);
    setElegida(null);
    setRevelado(false);
  };
  return (
    <section className="panel experimento" aria-label="Modo experimento">
      <h3>Modo experimento {indice + 1}/{experimentos.length}</h3>
      <p style={{ margin: 0 }}>
        <b>Predicción:</b> {exp.pregunta}
      </p>
      <div className="opciones">
        {exp.opciones.map((o, i) => (
          <button
            key={o.texto}
            className={[elegida === i ? "elegida" : "", revelado && o.correcta ? "correcta" : ""].join(" ")}
            onClick={() => !revelado && setElegida(i)}
            aria-pressed={elegida === i}
          >
            {o.texto}
          </button>
        ))}
      </div>
      <div className="barra">
        <button
          className="boton"
          disabled={elegida === null || revelado}
          onClick={() => {
            exp.aplicar();
            setRevelado(true);
          }}
        >
          Ejecutar y comparar
        </button>
        <button className="boton secundario" onClick={siguiente}>Siguiente</button>
      </div>
      {revelado && (
        <p className="respuesta" role="status">
          {elegida !== null && exp.opciones[elegida].correcta ? "Predicción correcta. " : "La predicción no coincide. "}
          {exp.explicacion}
        </p>
      )}
    </section>
  );
}

/* ---------- revisión crítica (checklist Anatomy) ---------- */
export function RevisionCritica({ extra = [] }: { extra?: string[] }) {
  const base = [
    "Responde una sola pregunta con una relación medible",
    "Entre 2 y 4 controles; correr, pausar, reiniciar y cámara lenta",
    "Cifras junto a las piezas que las producen",
    "Idea principal en una frase",
    "Datos de empresa con URL; parámetros demostrativos marcados",
    "Sin procedimientos de reparación ni de seguridad",
  ];
  return (
    <details className="panel">
      <summary style={{ cursor: "pointer", fontSize: 13 }}>Revisión crítica</summary>
      <ul className="critica" style={{ marginTop: 8 }}>
        {[...base, ...extra].map((c) => (
          <li key={c}>{c}</li>
        ))}
      </ul>
    </details>
  );
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

export function useTour(activo: boolean, pasos: PasoTour[], duracion: number) {
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
  const texto = activo && indice >= 0 ? pasos[indice].texto : null;
  return { texto, transcurrido: Math.min(transcurrido, duracion), duracion };
}

export function BandaTour({ texto, transcurrido, duracion }: { texto: string | null; transcurrido: number; duracion: number }) {
  if (!texto) return null;
  return (
    <div className="tour-banda" role="status" aria-live="polite">
      <span>{texto}</span>
      <span className="progreso">
        {transcurrido.toFixed(1)} / {duracion} s
      </span>
    </div>
  );
}

export function CabeceraMaquina({ maquina, respaldo }: { maquina: Maquina | null; respaldo: { pregunta: string; relacion: string; idea: string } }) {
  return (
    <>
      <a href="#/" style={{ fontSize: 13 }}>← Biblioteca</a>
      <h1 className="titular" style={{ maxWidth: "32ch" }}>{maquina?.pregunta ?? respaldo.pregunta}</h1>
      <p className="idea">
        <span className="relacion" style={{ marginRight: 10 }}>{maquina?.relacion ?? respaldo.relacion}</span>
        {maquina?.idea_principal ?? respaldo.idea}
      </p>
    </>
  );
}
