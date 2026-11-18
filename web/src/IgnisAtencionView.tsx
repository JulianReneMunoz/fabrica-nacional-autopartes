/**
 * Pestaña «Atención — IGNIS» (prompt v2, sección 2): escenario 3D con el auto, conversación por texto y voz y
 * columna de recursos. La barra lateral y el encabezado global viven en App.tsx. Estilos en ignis.css.
 *
 * Estados (ignisStateMachine.ts): auto → escribiendo / escuchando → pensando → respondiendo / hablando →
 * (mostrando_archivo) → auto tras ESPERA_A_REPOSO_MS. El escáner del auto toma el modo del estado y la amplitud
 * del objeto compartido (analizador del TTS o del micrófono; pulsos por tecla, token o palabra).
 */
import { Component, lazy, Suspense, useCallback, useEffect, useMemo, useReducer, useRef, useState, type ReactNode } from "react";
import { crearAmplitud, pulsarAmplitud } from "./escanerIgnis";
import { CASOS_VALIDACION } from "./ignisCasos";
import {
  conversar,
  ErrorSesionIgnis,
  etiquetaRuta,
  normalizarCita,
  type AdjuntoIgnis,
  type CitaIgnis,
  type EventoConversacion,
} from "./ignisCliente";
import { useIgnis } from "./ignisContexto";
import { ErrorSesion, mensajesHilo, type MensajeHiloDTO } from "./ignisSesion";
import { Icono, type NombreIcono } from "./IgnisIconos";
import {
  DURACION_ENTREGA_MS,
  enTurno,
  ESPERA_A_REPOSO_MS,
  ETIQUETA_ESTADO,
  PAUSA_TECLADO_MS,
  transicionarEstadoIgnis,
  type EstadoAvatarIgnis,
} from "./ignisStateMachine";
import { extraerOraciones, MicrofonoIgnis, VozIgnis } from "./ignisVoz";
import type { AccionCamara } from "./IgnisCanvas3D";

const IgnisCanvas3D = lazy(() => import("./IgnisCanvas3D"));

/** Límite del backend (`SolicitudChatIgnis.mensaje`, 1–2000 caracteres). */
export const MAX_MENSAJE = 2000;

/** Póster estático del auto (captura del propio GLB) para cuando no hay WebGL o el modelo no carga. */
const URL_POSTER = `${import.meta.env.BASE_URL}assets/ignis_auto_poster.jpg`;

interface Mensaje {
  id: number;
  rol: "usuario" | "ignis" | "sistema";
  texto: string;
  porVoz?: boolean;
  citas?: CitaIgnis[];
  ruta?: string;
  score?: number;
  blindaje?: boolean;
  bloqueada?: boolean;
  adjuntos?: AdjuntoIgnis[];
  error?: boolean;
  pendiente?: boolean;
}

/**
 * Recursos de la columna E. Se habilitan solo si el archivo existe (HEAD). Son ilustrativos del proyecto: se
 * marcan `demostrativo` (no son datos de Fanalca).
 */
const RECURSOS = [
  { id: "plano", titulo: "Plano técnico 2D", detalle: "PNG · plano ilustrativo", url: `${import.meta.env.BASE_URL}assets/blueprint_2d.png`, icono: "plano" as NombreIcono, borde: "rojo", accion: "Descargar plano 2D" },
  { id: "modelo", titulo: "Modelo 3D del auto", detalle: "GLB · ignis_auto", url: `${import.meta.env.BASE_URL}models/ignis_auto.glb`, icono: "cubo" as NombreIcono, borde: "naranja", accion: "Descargar modelo 3D" },
];

/** Turno guardado en el servidor → mensaje de la conversación (ruta y citas incluidas). */
function mensajeDesdeHistorial(m: MensajeHiloDTO, id: number): Mensaje {
  return {
    id,
    rol: m.rol === "user" ? "usuario" : "ignis",
    texto: m.contenido,
    ruta: m.ruta ?? undefined,
    citas: m.citas.map(normalizarCita).filter((c): c is CitaIgnis => c !== null),
  };
}

const SALUDO: Mensaje = { id: 0, rol: "ignis", texto: "Hola, soy IGNIS. Escríbeme o pulsa el micrófono para empezar." };

function soportaWebGL(): boolean {
  try {
    const c = document.createElement("canvas");
    return !!(c.getContext("webgl2") ?? c.getContext("webgl"));
  } catch {
    return false;
  }
}

function prefiereMenosMovimiento(): boolean {
  return typeof window !== "undefined" && !!window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
}

type ReconocimientoVoz = {
  lang: string;
  interimResults: boolean;
  continuous: boolean;
  onresult: ((e: { results: ArrayLike<ArrayLike<{ transcript: string }>> }) => void) | null;
  onerror: ((e: { error: string }) => void) | null;
  onend: (() => void) | null;
  start: () => void;
  stop: () => void;
};

function constructorReconocimiento(): (new () => ReconocimientoVoz) | null {
  if (typeof window === "undefined") return null;
  const w = window as unknown as { SpeechRecognition?: new () => ReconocimientoVoz; webkitSpeechRecognition?: new () => ReconocimientoVoz };
  return w.SpeechRecognition ?? w.webkitSpeechRecognition ?? null;
}

/** Póster del auto; si la imagen tampoco existe, queda el texto. */
function Poster({ motivo }: { motivo: string }) {
  const [sinImagen, setSinImagen] = useState(false);
  return (
    <div className="ignis-sin-webgl">
      {sinImagen ? null : <img className="ignis-poster" src={URL_POSTER} alt="Auto IGNIS (imagen fija)" onError={() => setSinImagen(true)} />}
      <p>{motivo}</p>
    </div>
  );
}

/** Si el GLB no carga (red, decodificador), se muestra el póster en vez de romper la pestaña. */
class LimiteEscena extends Component<{ children: ReactNode }, { fallo: boolean }> {
  state = { fallo: false };
  static getDerivedStateFromError() {
    return { fallo: true };
  }
  render() {
    return this.state.fallo ? <Poster motivo="No se pudo cargar el modelo 3D del auto. El chat funciona igual." /> : this.props.children;
  }
}

export default function IgnisAtencionView() {
  const { hilo, nuevoHilo, reportarSse, aperturas, sesionVencida } = useIgnis();
  const [estado, despachar] = useReducer(transicionarEstadoIgnis, "auto" as EstadoAvatarIgnis);
  const [mensajes, setMensajes] = useState<Mensaje[]>([SALUDO]);
  const [entrada, setEntrada] = useState("");
  const [transcripcion, setTranscripcion] = useState<string | null>(null);
  const [escuchando, setEscuchando] = useState(false);
  const [esperando, setEsperando] = useState(false);
  const [silenciar, setSilenciar] = useState(false);
  const [subtitulos, setSubtitulos] = useState(true);
  const [tamanoSub, setTamanoSub] = useState(1);
  const [volumen, setVolumen] = useState(0.8);
  const [subtitulo, setSubtitulo] = useState("");
  const [autoGiro, setAutoGiro] = useState(true);
  const [accionCamara, setAccionCamara] = useState<AccionCamara>({ tipo: "ninguna", n: 0 });
  const [vistaAmpliada, setVistaAmpliada] = useState(false);
  const [panelAbierto, setPanelAbierto] = useState(false);
  const [disponibles, setDisponibles] = useState<Record<string, boolean>>({});
  const [adjuntosSesion, setAdjuntosSesion] = useState<AdjuntoIgnis[]>([]);
  const [casoSel, setCasoSel] = useState(CASOS_VALIDACION[0].id);
  const [aviso, setAviso] = useState("");

  const webgl = useMemo(soportaWebGL, []);
  const reducido = useMemo(prefiereMenosMovimiento, []);
  const Reconocimiento = useMemo(constructorReconocimiento, []);

  const amplitud = useRef(crearAmplitud());
  const idMensaje = useRef(1);
  const estadoRef = useRef(estado);
  estadoRef.current = estado;
  const esperandoRef = useRef(false);
  const silenciarRef = useRef(silenciar);
  silenciarRef.current = silenciar;
  const entregaPendiente = useRef(false);
  // Hilo y apertura cuyo historial ya se muestra (null al montar: se carga el historial del hilo activo).
  const hiloVisto = useRef<string | null>(null);
  const aperturaVista = useRef(aperturas);
  // Envíos hechos en esta vista: la carga del historial no pisa una conversación que ya empezó.
  const envios = useRef(0);
  const reconocimiento = useRef<ReconocimientoVoz | null>(null);
  const microfono = useRef<MicrofonoIgnis | null>(null);
  const finMensajes = useRef<HTMLDivElement>(null);
  const temporizadorSub = useRef<number | undefined>(undefined);
  const temporizadorTeclado = useRef<number | undefined>(undefined);
  const temporizadorReposo = useRef<number | undefined>(undefined);

  /** Cierre del turno: con adjunto se muestra la entrega; después, ESPERA_A_REPOSO_MS y vuelta a reposo. */
  const cerrarTurno = useCallback(() => {
    window.clearTimeout(temporizadorReposo.current);
    let espera = ESPERA_A_REPOSO_MS;
    if (entregaPendiente.current) {
      entregaPendiente.current = false;
      despachar({ type: "MOSTRAR_ENTREGABLE" });
      espera = DURACION_ENTREGA_MS;
    }
    temporizadorReposo.current = window.setTimeout(() => despachar({ type: "VOLVER_A_REPOSO" }), espera);
  }, []);

  const voz = useRef<VozIgnis | null>(null);
  if (voz.current === null) {
    voz.current = new VozIgnis({
      amplitud: amplitud.current,
      // Voz de respaldo en español de España (sin voz del servidor ni voz latinoamericana): aviso único.
      alAviso: (mensaje) => setAviso(mensaje),
      alIniciar: () => {
        window.clearTimeout(temporizadorSub.current);
        // Silenciada, la cola solo recorre las oraciones para los subtítulos: el estado queda en «respondiendo».
        if (silenciarRef.current) return;
        window.clearTimeout(temporizadorReposo.current);
        despachar({ type: "INICIAR_HABLA" });
      },
      alOracion: (o) => setSubtitulo(`IGNIS: ${o}`),
      alTerminar: () => {
        temporizadorSub.current = window.setTimeout(() => setSubtitulo(""), 4000);
        if (!esperandoRef.current) cerrarTurno();
      },
    });
  }

  // Comprobación de los recursos descargables (el estado de la API lo lleva el encabezado global).
  useEffect(() => {
    let vivo = true;
    for (const r of RECURSOS) {
      fetch(r.url, { method: "HEAD" })
        .then((res) => {
          const tipo = res.headers.get("content-type") ?? "";
          if (vivo) setDisponibles((d) => ({ ...d, [r.id]: res.ok && !tipo.includes("text/html") }));
        })
        .catch(() => vivo && setDisponibles((d) => ({ ...d, [r.id]: false })));
    }
    return () => {
      vivo = false;
    };
  }, []);

  useEffect(() => {
    voz.current?.volumen(volumen);
  }, [volumen]);
  useEffect(() => {
    voz.current?.silenciar(silenciar);
  }, [silenciar]);
  useEffect(() => {
    finMensajes.current?.scrollIntoView?.({ block: "end" });
  }, [mensajes]);
  useEffect(
    () => () => {
      voz.current?.detener();
      reconocimiento.current?.stop();
      microfono.current?.detener();
      window.clearTimeout(temporizadorTeclado.current);
      window.clearTimeout(temporizadorReposo.current);
      window.clearTimeout(temporizadorSub.current);
    },
    [],
  );

  const reiniciarConversacion = useCallback((id: string, nota: string) => {
    hiloVisto.current = id;
    setMensajes([{ id: idMensaje.current++, rol: "sistema", texto: `${nota} (${id})` }]);
    setAdjuntosSesion([]);
  }, []);

  // Hilo activo nuevo («Nuevo hilo»), el más reciente al entrar o uno reabierto desde «Mi sesión»: se muestra su
  // historial guardado en el servidor (vacío en un hilo nuevo).
  useEffect(() => {
    if (!hilo) return;
    if (hilo === hiloVisto.current && aperturas === aperturaVista.current) return;
    hiloVisto.current = hilo;
    aperturaVista.current = aperturas;
    let vivo = true;
    setAdjuntosSesion([]);
    setMensajes([{ id: idMensaje.current++, rol: "sistema", texto: `Cargando el hilo (${hilo})…` }]);
    // Si el usuario envía un mensaje antes de que llegue el historial, el historial no pisa la conversación.
    const enviosAlCargar = envios.current;
    mensajesHilo(hilo)
      .then((lista) => {
        if (!vivo || envios.current !== enviosAlCargar) return;
        if (lista.length === 0) {
          setMensajes([SALUDO, { id: idMensaje.current++, rol: "sistema", texto: `Hilo nuevo (${hilo})` }]);
          return;
        }
        setMensajes([
          { id: idMensaje.current++, rol: "sistema", texto: `Hilo reabierto (${hilo})` },
          ...lista.map((m) => mensajeDesdeHistorial(m, idMensaje.current++)),
        ]);
      })
      .catch((e: unknown) => {
        if (!vivo || envios.current !== enviosAlCargar) return;
        if (e instanceof ErrorSesion && e.estado === 401) sesionVencida();
        setMensajes([{ id: idMensaje.current++, rol: "sistema", texto: e instanceof Error ? e.message : String(e) }]);
      });
    return () => {
      vivo = false;
    };
  }, [hilo, aperturas, sesionVencida]);

  const actualizar = useCallback((id: number, cambio: (m: Mensaje) => Mensaje) => {
    setMensajes((lista) => lista.map((m) => (m.id === id ? cambio(m) : m)));
  }, []);

  const enviar = useCallback(
    async (texto: string, opciones: { porVoz?: boolean; hiloNuevo?: boolean } = {}) => {
      const consulta = texto.trim().slice(0, MAX_MENSAJE);
      if (!consulta || esperandoRef.current) return;
      // El hilo activo lo prepara el contexto al entrar; mientras tanto no se envía (evita crear dos hilos).
      if (!hilo && !opciones.hiloNuevo) {
        setAviso("Preparando la sesión… vuelve a intentarlo en un momento.");
        return;
      }
      esperandoRef.current = true;
      envios.current += 1;
      setEsperando(true);
      // El hilo lo crea el servidor y lo liga al usuario de la sesión (caso 2B: hilo nuevo).
      let hiloActual = hilo ?? "";
      try {
        if (opciones.hiloNuevo) {
          hiloActual = await nuevoHilo();
          reiniciarConversacion(hiloActual, "Hilo nuevo para probar la memoria de largo plazo");
        }
      } catch (e) {
        esperandoRef.current = false;
        setEsperando(false);
        if (e instanceof ErrorSesion && e.estado === 401) sesionVencida();
        setAviso(e instanceof Error ? e.message : String(e));
        return;
      }
      voz.current?.detener();
      window.clearTimeout(temporizadorTeclado.current);
      window.clearTimeout(temporizadorReposo.current);
      entregaPendiente.current = false;
      setEntrada("");
      setTranscripcion(null);
      setAviso("");
      const idUsuario = idMensaje.current++;
      const idRespuesta = idMensaje.current++;
      setMensajes((l) => [
        ...l,
        { id: idUsuario, rol: "usuario", texto: consulta, porVoz: opciones.porVoz },
        { id: idRespuesta, rol: "ignis", texto: "", pendiente: true },
      ]);
      despachar({ type: "ENVIAR_CONSULTA" });

      let pendienteVoz = "";
      const alEvento = (e: EventoConversacion) => {
        if (e.tipo === "token" || e.tipo === "oracion") {
          const trozo = e.tipo === "oracion" ? `${e.texto} ` : e.texto;
          despachar({ type: "RECIBIR_TEXTO" });
          // Sin voz, cada token mueve el escáner; con voz, lo mueve el analizador del TTS.
          if (silenciarRef.current) pulsarAmplitud(amplitud.current);
          actualizar(idRespuesta, (m) => ({ ...m, texto: m.texto + trozo, pendiente: false }));
          pendienteVoz += trozo;
          const { oraciones, resto } = extraerOraciones(pendienteVoz);
          oraciones.forEach((o) => voz.current?.encolar(o));
          pendienteVoz = resto;
        } else if (e.tipo === "metadatos") {
          for (const adjunto of e.datos.adjuntos ?? []) alEvento({ tipo: "adjunto", adjunto });
          actualizar(idRespuesta, (m) => ({
            ...m,
            citas: e.datos.citas ?? m.citas,
            ruta: e.datos.ruta_router ?? m.ruta,
            score: e.datos.score_router ?? m.score,
            blindaje: e.datos.blindaje_activado || m.blindaje,
            bloqueada: e.datos.bloqueada || m.bloqueada,
          }));
        } else if (e.tipo === "adjunto") {
          entregaPendiente.current = true;
          actualizar(idRespuesta, (m) => (m.adjuntos?.some((a) => a.id === e.adjunto.id) ? m : { ...m, adjuntos: [...(m.adjuntos ?? []), e.adjunto] }));
          setAdjuntosSesion((l) => (l.some((a) => a.id === e.adjunto.id) ? l : [...l, e.adjunto]));
        } else if (e.tipo === "error") {
          actualizar(idRespuesta, (m) => ({ ...m, texto: m.texto || e.mensaje, error: true, pendiente: false }));
        } else if (e.tipo === "fin") {
          if (pendienteVoz.trim()) voz.current?.encolar(pendienteVoz);
          pendienteVoz = "";
        }
      };

      try {
        const origen = await conversar(consulta, hiloActual, alEvento);
        reportarSse(origen === "sse" ? "en_linea" : "respaldo");
      } catch (e) {
        if (e instanceof ErrorSesionIgnis) {
          // 401, 403 o 503: rechazo de sesión, no falta de conexión; no se usa el respaldo Q&A.
          actualizar(idRespuesta, (m) => ({ ...m, texto: e.message, error: true, pendiente: false }));
          if (e.estado === 401) sesionVencida();
        } else {
          reportarSse("sin_conexion");
          actualizar(idRespuesta, (m) => ({
            ...m,
            texto: "No fue posible conectar con el backend. Verifica que FastAPI esté en ejecución y vuelve a intentarlo.",
            error: true,
            pendiente: false,
          }));
        }
      } finally {
        esperandoRef.current = false;
        setEsperando(false);
        actualizar(idRespuesta, (m) => ({ ...m, pendiente: false, texto: m.texto.trim() || (m.error ? m.texto : "(sin respuesta)") }));
        if (!voz.current?.hablando) cerrarTurno();
      }
    },
    [actualizar, cerrarTurno, hilo, nuevoHilo, reiniciarConversacion, reportarSse, sesionVencida],
  );

  const alTeclear = (valor: string) => {
    setEntrada(valor.slice(0, MAX_MENSAJE));
    if (enTurno(estadoRef.current) || estadoRef.current === "escuchando") return;
    despachar({ type: "TECLA" });
    pulsarAmplitud(amplitud.current);
    window.clearTimeout(temporizadorTeclado.current);
    temporizadorTeclado.current = window.setTimeout(() => despachar({ type: "PAUSA_TECLADO" }), PAUSA_TECLADO_MS);
  };

  const alternarMicrofono = useCallback(() => {
    if (!Reconocimiento) return;
    if (reconocimiento.current) {
      reconocimiento.current.stop();
      return;
    }
    voz.current?.detener();
    window.clearTimeout(temporizadorReposo.current);
    const rec = new Reconocimiento();
    rec.lang = "es-CO";
    rec.interimResults = true;
    rec.continuous = false;
    rec.onresult = (e) => {
      const partes: string[] = [];
      for (let i = 0; i < e.results.length; i++) partes.push(e.results[i][0].transcript);
      setTranscripcion(partes.join(""));
    };
    rec.onerror = (e) => setAviso(e.error === "not-allowed" ? "Permiso de micrófono denegado." : `Micrófono: ${e.error}`);
    rec.onend = () => {
      reconocimiento.current = null;
      microfono.current?.detener();
      setEscuchando(false);
      despachar({ type: "FINALIZAR_ESCUCHA" });
    };
    reconocimiento.current = rec;
    setEscuchando(true);
    setTranscripcion("");
    despachar({ type: "ACTIVAR_MICROFONO" });
    microfono.current ??= new MicrofonoIgnis(amplitud.current);
    void microfono.current.iniciar();
    rec.start();
  }, [Reconocimiento]);

  const ejecutarCaso = () => {
    const caso = CASOS_VALIDACION.find((c) => c.id === casoSel);
    if (caso) void enviar(caso.consulta, { hiloNuevo: caso.hiloNuevo });
  };

  const exportarResumen = () => {
    const lineas = [`# Resumen de la atención — IGNIS`, ``, `- Hilo: ${hilo}`, `- Fecha: ${new Date().toLocaleString("es-CO")}`, ``];
    for (const m of mensajes) {
      if (m.rol === "sistema") continue;
      lineas.push(`**${m.rol === "usuario" ? "Usuario" : "IGNIS"}:** ${m.texto}`);
      if (m.ruta) lineas.push(`- Ruta del router: ${etiquetaRuta(m.ruta)}`);
      for (const c of m.citas ?? []) lineas.push(`- Fuente: ${c.titulo}${c.url ? ` — ${c.url}` : ` (${c.id})`} · origen: ${c.origen}`);
      for (const a of m.adjuntos ?? []) lineas.push(`- Adjunto: ${a.titulo} · origen: ${a.origen}`);
      lineas.push("");
    }
    const url = URL.createObjectURL(new Blob([lineas.join("\n")], { type: "text/markdown;charset=utf-8" }));
    const a = document.createElement("a");
    a.href = url;
    a.download = `resumen_${hilo}.md`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const camara = (tipo: AccionCamara["tipo"]) => setAccionCamara((a) => ({ tipo, n: a.n + 1 }));
  const hayRespuestas = mensajes.some((m) => m.rol === "ignis" && m.id > 0 && !m.pendiente);
  const ondas = escuchando || estado === "hablando";

  const tarjetasRecursos = (
    <>
      {RECURSOS.map((r) => (
        <div key={r.id} className={`ignis-tarjeta borde-${r.borde}${disponibles[r.id] ? "" : " inactiva"}`}>
          <div className="ignis-tarjeta-cab">
            <span className="ignis-tarjeta-icono">
              <Icono nombre={r.icono} tamano={22} />
            </span>
            <div>
              <strong>
                {r.titulo} <span className="ignis-origen">demostrativo</span>
              </strong>
              <small>{disponibles[r.id] ? r.detalle : "Se habilita cuando el archivo esté publicado"}</small>
            </div>
          </div>
          {disponibles[r.id] ? (
            <a className="ignis-btn bloque" href={r.url} download>
              <Icono nombre="descargar" tamano={16} /> {r.accion}
            </a>
          ) : (
            <button className="ignis-btn bloque" disabled>
              {r.accion}
            </button>
          )}
        </div>
      ))}
      <div className={`ignis-tarjeta borde-rojo${hayRespuestas ? "" : " inactiva"}`}>
        <div className="ignis-tarjeta-cab">
          <span className="ignis-tarjeta-icono">
            <Icono nombre="archivo" tamano={22} />
          </span>
          <div>
            <strong>Resumen de la atención</strong>
            <small>Conversación y fuentes, sin cifras inventadas</small>
          </div>
        </div>
        <button className="ignis-btn bloque" onClick={exportarResumen} disabled={!hayRespuestas}>
          <Icono nombre="descargar" tamano={16} /> Exportar resumen
        </button>
      </div>
      {adjuntosSesion.map((a) => (
        <div key={a.id} className="ignis-tarjeta borde-naranja resaltada">
          <div className="ignis-tarjeta-cab">
            <span className="ignis-tarjeta-icono">
              <Icono nombre="archivo" tamano={22} />
            </span>
            <div>
              <strong>
                {a.titulo} <span className="ignis-origen">{a.origen}</span>
              </strong>
              <small>{a.formato.toUpperCase()}</small>
            </div>
          </div>
          <a className="ignis-btn bloque" href={a.url} download>
            <Icono nombre="descargar" tamano={16} /> Descargar
          </a>
        </div>
      ))}
    </>
  );

  return (
    <div className={`ignis-app${vistaAmpliada ? " ampliada" : ""}${panelAbierto ? " panel-abierto" : ""}`} data-estado={estado}>
      {/* B — Encabezado del escenario */}
      <header className="ignis-encabezado">
        <div className="ignis-titulo">
          <span>IGNIS</span>
          <span className="ignis-chip-estado" role="status">
            {ETIQUETA_ESTADO[estado]}
          </span>
        </div>
        <button className="ignis-btn abrir-panel" onClick={() => setPanelAbierto((v) => !v)} aria-expanded={panelAbierto}>
          <Icono nombre="chat" tamano={18} /> {panelAbierto ? "Cerrar chat" : "Abrir chat"}
        </button>
      </header>

      {/* C — Escenario 3D */}
      <section className="ignis-escenario" aria-label="Escenario 3D del auto IGNIS">
        {webgl ? (
          <LimiteEscena>
            <Suspense fallback={<div className="ignis-cargando">Cargando el auto 3D…</div>}>
              <IgnisCanvas3D estado={estado} amplitud={amplitud.current} autoGiro={autoGiro} accionCamara={accionCamara} movimientoReducido={reducido} />
            </Suspense>
          </LimiteEscena>
        ) : (
          <Poster motivo="Este navegador no tiene WebGL: el auto 3D no se puede mostrar, pero el chat funciona igual." />
        )}

        <div className="ignis-barra-camara" role="toolbar" aria-label="Controles de cámara">
          <button className="ignis-herramienta" aria-pressed={autoGiro} onClick={() => setAutoGiro((v) => !v)} title="Giro automático en reposo" disabled={reducido}>
            <Icono nombre="girar" />
            <span className="sr">Giro automático en reposo</span>
          </button>
          <button className="ignis-herramienta" onClick={() => camara("acercar")} title="Acercar">
            <Icono nombre="acercar" />
            <span className="sr">Acercar</span>
          </button>
          <button className="ignis-herramienta" onClick={() => camara("alejar")} title="Alejar">
            <Icono nombre="alejar" />
            <span className="sr">Alejar</span>
          </button>
          <button className="ignis-herramienta" aria-pressed={vistaAmpliada} onClick={() => setVistaAmpliada((v) => !v)} title="Vista ampliada">
            <Icono nombre="ampliar" />
            <span className="sr">Vista ampliada</span>
          </button>
        </div>
        <button className="ignis-herramienta ignis-restablecer" onClick={() => camara("restablecer")} title="Restablecer vista">
          <Icono nombre="restablecer" />
          <span className="sr">Restablecer vista</span>
        </button>

        {subtitulos && subtitulo ? (
          <div className="ignis-subtitulos" style={{ fontSize: `${15 * tamanoSub}px` }}>
            {subtitulo}
          </div>
        ) : null}
        <div className="sr" aria-live="polite">
          {subtitulos ? subtitulo : ""}
        </div>
      </section>

      {/* D — Panel de atención (D1 conversación + E recursos) */}
      <section className="ignis-panel" aria-label="Atención al cliente">
        <header className="ignis-panel-cab">
          <h1>Atención al cliente — IGNIS</h1>
          <button className="ignis-btn icono-solo cerrar-panel" onClick={() => setPanelAbierto(false)} aria-label="Cerrar panel">
            <Icono nombre="cerrar" tamano={18} />
          </button>
        </header>

        <div className="ignis-casos">
          <label htmlFor="ignis-caso">Casos</label>
          <select id="ignis-caso" className="ignis-select" value={casoSel} onChange={(e) => setCasoSel(e.target.value)}>
            {CASOS_VALIDACION.map((c) => (
              <option key={c.id} value={c.id}>
                {c.etiqueta}
              </option>
            ))}
          </select>
          <button className="ignis-btn primario" onClick={ejecutarCaso} disabled={esperando}>
            Ejecutar
          </button>
        </div>

        <div className="ignis-cuerpo">
          {/* D1 — Conversación */}
          <div className="ignis-conversacion">
            <div className="ignis-mensajes" role="log" aria-label="Conversación">
              {mensajes.map((m) =>
                m.rol === "sistema" ? (
                  <p key={m.id} className="ignis-nota">
                    {m.texto}
                  </p>
                ) : (
                  <div key={m.id} className={`ignis-fila-msg ${m.rol}`}>
                    {m.rol === "ignis" ? (
                      <span className="ignis-avatar-msg" aria-hidden="true">
                        <Icono nombre="auto" tamano={18} />
                      </span>
                    ) : null}
                    <div className={`ignis-burbuja ${m.rol}${m.error ? " error" : ""}`}>
                      {m.pendiente ? (
                        <span className="ignis-escribiendo" aria-label="IGNIS está escribiendo">
                          <span />
                          <span />
                          <span />
                        </span>
                      ) : (
                        <p>
                          {m.porVoz ? (
                            <span className="ignis-por-voz" title="Enviado por voz">
                              <Icono nombre="mic" tamano={14} />
                            </span>
                          ) : null}
                          {m.texto}
                        </p>
                      )}
                      {m.ruta || m.blindaje || m.bloqueada ? (
                        <div className="ignis-metadatos" aria-label="Metadatos de la respuesta">
                          {m.ruta ? (
                            <span className="ignis-insignia ruta" title={`Ruta del router: ${m.ruta}`}>
                              <Icono nombre="ruta" tamano={13} /> {etiquetaRuta(m.ruta)}
                            </span>
                          ) : null}
                          {m.score !== undefined ? (
                            <span className="ignis-dato" title="Puntaje del router">
                              {m.score.toFixed(2)}
                            </span>
                          ) : null}
                          {m.citas ? <span className="ignis-dato">{m.citas.length === 1 ? "1 cita" : `${m.citas.length} citas`}</span> : null}
                          {m.blindaje ? (
                            <span className="ignis-insignia blindaje">
                              <Icono nombre="escudo" tamano={13} /> Blindaje activado
                            </span>
                          ) : null}
                          {m.bloqueada ? <span className="ignis-insignia bloqueada">Solicitud bloqueada</span> : null}
                        </div>
                      ) : null}
                      {m.citas && m.citas.length > 0 ? (
                        <div className="ignis-citas">
                          {m.citas.map((c) =>
                            c.url ? (
                              <a key={c.id} className="ignis-cita" href={c.url} target="_blank" rel="noreferrer" title={`${c.titulo} — ${c.url} (origen: ${c.origen})`}>
                                {c.titulo} <span className="ignis-origen">{c.origen}</span>
                              </a>
                            ) : (
                              <span key={c.id} className="ignis-cita" title={`Fragmento ${c.id}, sin URL (origen: ${c.origen})`}>
                                {c.titulo} · {c.id} <span className="ignis-origen">{c.origen}</span>
                              </span>
                            ),
                          )}
                        </div>
                      ) : null}
                      {m.adjuntos?.map((a) => (
                        <a key={a.id} className="ignis-adjunto-linea" href={a.url} download>
                          <Icono nombre="archivo" tamano={16} /> {a.titulo}
                          {a.formato ? ` · ${a.formato.toUpperCase()}` : ""} <span className="ignis-origen">{a.origen}</span>
                        </a>
                      ))}
                    </div>
                  </div>
                ),
              )}
              <div ref={finMensajes} />
            </div>

            <div className="ignis-recursos-compactos">{tarjetasRecursos}</div>

            <div className="ignis-controles" role="group" aria-label="Controles de voz">
              <label className="ignis-interruptor">
                <span>
                  <Icono nombre="micApagado" tamano={16} /> Silenciar voz
                </span>
                <input type="checkbox" role="switch" checked={silenciar} onChange={(e) => setSilenciar(e.target.checked)} />
              </label>
              <div className="ignis-fila-control">
                <span>
                  <Icono nombre="detener" tamano={16} /> Detener lectura
                </span>
                <button className="ignis-btn" onClick={() => voz.current?.detener()}>
                  Detener
                </button>
              </div>
              <label className="ignis-interruptor">
                <span>
                  <Icono nombre="subtitulos" tamano={16} /> Subtítulos
                </span>
                <input type="checkbox" role="switch" checked={subtitulos} onChange={(e) => setSubtitulos(e.target.checked)} />
              </label>
              <label className="ignis-fila-control">
                <span>Tamaño de subtítulos</span>
                <input type="range" min={0.8} max={1.4} step={0.1} value={tamanoSub} onChange={(e) => setTamanoSub(Number(e.target.value))} />
              </label>
              <label className="ignis-fila-control volumen-compacto">
                <span>
                  <Icono nombre="volumen" tamano={16} /> Volumen
                </span>
                <input type="range" min={0} max={1} step={0.05} value={volumen} onChange={(e) => setVolumen(Number(e.target.value))} />
              </label>
            </div>

            <form
              className="ignis-entrada"
              onSubmit={(e) => {
                e.preventDefault();
                void enviar(entrada);
              }}
            >
              <div className="ignis-entrada-campo">
                <textarea
                  className="ignis-input"
                  rows={1}
                  value={entrada}
                  maxLength={MAX_MENSAJE}
                  placeholder="Escribe un mensaje…"
                  aria-label="Mensaje para IGNIS"
                  aria-describedby="ignis-contador"
                  onChange={(e) => alTeclear(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && !e.shiftKey) {
                      e.preventDefault();
                      void enviar(entrada);
                    }
                  }}
                />
                <span id="ignis-contador" className={`ignis-contador${entrada.length >= MAX_MENSAJE ? " lleno" : ""}`}>
                  {entrada.length} / {MAX_MENSAJE}
                </span>
              </div>
              <button
                type="button"
                className={`ignis-mic-pequeno${escuchando ? " activo" : ""}`}
                onClick={alternarMicrofono}
                disabled={!Reconocimiento}
                title={Reconocimiento ? (escuchando ? "Terminar de escuchar" : "Hablar") : "Tu navegador no admite reconocimiento de voz (usa Chrome o Edge)"}
                aria-label={escuchando ? "Terminar de escuchar" : "Hablar por micrófono"}
              >
                <Icono nombre="mic" tamano={18} />
              </button>
              <button type="submit" className="ignis-btn primario" disabled={esperando || !hilo || !entrada.trim()}>
                <Icono nombre="enviar" tamano={16} /> Enviar
              </button>
            </form>
            <div className="ignis-transcripcion">
              <Icono nombre="lapiz" tamano={16} />
              <input
                className="ignis-input"
                value={transcripcion ?? ""}
                maxLength={MAX_MENSAJE}
                placeholder={escuchando ? "Escuchando…" : "Transcripción provisional…"}
                aria-label="Transcripción provisional (editable)"
                disabled={transcripcion === null && !escuchando}
                onChange={(e) => setTranscripcion(e.target.value)}
              />
              <button className="ignis-btn primario" disabled={!transcripcion?.trim() || esperando} onClick={() => void enviar(transcripcion ?? "", { porVoz: true })}>
                Usar transcripción
              </button>
              <button className="ignis-btn" disabled={transcripcion === null} onClick={() => setTranscripcion(null)}>
                Descartar
              </button>
            </div>
            {aviso ? (
              <p className="ignis-aviso" role="alert">
                {aviso}
              </p>
            ) : null}
          </div>

          {/* E — Recursos: la lista se desplaza sola; el micrófono queda fijo abajo. */}
          <aside className="ignis-recursos" aria-label="Recursos">
            <div className="ignis-recursos-lista">
              <div className="ignis-proyecto">
                <span>Fanalca / TAAML 2026-2S</span>
                <svg viewBox="0 0 240 80" role="img" aria-label="Miniatura del plano de IGNIS">
                  <rect width="240" height="80" fill="#1d4ed8" />
                  <path d="M0 20h240M0 40h240M0 60h240M60 0v80M120 0v80M180 0v80" stroke="#3b6ef0" strokeWidth="1" />
                  <path d="M22 62 L28 54 L60 49 L118 34 L150 34 L186 44 L216 48 L218 62 Z" fill="none" stroke="#fff" strokeWidth="2" />
                  <circle cx="66" cy="62" r="10" fill="none" stroke="#fff" strokeWidth="2" />
                  <circle cx="186" cy="62" r="11" fill="none" stroke="#fff" strokeWidth="2" />
                </svg>
              </div>
              {tarjetasRecursos}
              <label className="ignis-volumen">
                <Icono nombre="volumen" tamano={18} />
                <span className="sr">Volumen</span>
                <input type="range" min={0} max={1} step={0.05} value={volumen} onChange={(e) => setVolumen(Number(e.target.value))} />
              </label>
            </div>
            <div className="ignis-mic-fijo">
              <div className="ignis-mic-grande-zona">
                <span className={`ignis-ondas${ondas ? " activas" : ""}`} aria-hidden="true">
                  <i /><i /><i /><i /><i />
                </span>
                <button
                  className={`ignis-mic-grande${escuchando ? " activo" : ""}`}
                  onClick={alternarMicrofono}
                  disabled={!Reconocimiento}
                  aria-label={escuchando ? "Terminar de escuchar" : "Pulsar para hablar"}
                  title={Reconocimiento ? undefined : "Tu navegador no admite reconocimiento de voz (usa Chrome o Edge)"}
                >
                  <Icono nombre="mic" tamano={30} />
                </button>
                <span className={`ignis-ondas${ondas ? " activas" : ""}`} aria-hidden="true">
                  <i /><i /><i /><i /><i />
                </span>
              </div>
              <p className="ignis-mic-texto">{escuchando ? "escuchando… pulsa para terminar" : "pulsar para hablar"}</p>
            </div>
          </aside>
        </div>
      </section>
    </div>
  );
}
