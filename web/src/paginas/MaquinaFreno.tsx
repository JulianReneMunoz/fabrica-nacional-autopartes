/**
 * Máquina 1 — Freno de disco con pinza flotante (caso principal del simulador 3D v2.0).
 * Pregunta: ¿cómo convierte un freno de disco la presión hidráulica en fuerza de frenado?
 * Relación: T = 2·μ·p·A·r.   Controles del mecanismo: presión, μ, velocidad, despiece.
 */
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import * as THREE from "three";
import type { OrbitControls as OrbitControlsImpl } from "three-stdlib";
import { api, type Animacion, type NodoJerarquia, type Pieza, type RespuestaPieza, type Lectura } from "../api";
import { fmt, hashRecorrido, useMaquina, useTour, type PasoTour } from "../componentes/anatomia";
import { ChipDato } from "../componentes/plantilla/ChipDato";
import { Deslizador, ControlesDeclarados } from "../componentes/plantilla/controles";
import { EtiquetasPieza, type RefsLineas } from "../componentes/plantilla/EtiquetaPieza";
import { InsigniaFuente } from "../componentes/plantilla/InsigniaFuente";
import { armarExperimentos } from "../componentes/plantilla/ModoExperimento";
import { FaqFanalcaAuto } from "../componentes/plantilla/PanelFaq";
import { PlantillaMaquina } from "../componentes/plantilla/PlantillaMaquina";
import { FRENO } from "../maquinas";
import { calcularFreno, ENTRADA_FRENO_DEFECTO, estadoRueda } from "../modelos/freno";
import EscenaFreno, { type EstadoEscena, type GeometriaDespiece, type LecturaLocal } from "./EscenaFreno";

type Modo = "ensamblado" | "manual" | "despiece" | "reensamblaje" | "frenado";

const T_PRESION = 0.5; // s: la presión llega a la pinza
const T_APRIETE = 0.8; // s: holgura cerrada, inicia la fricción
const AMPLIACION = 20;
const PREGUNTAS = [
  "¿Qué función cumple?",
  "¿Qué debe retirarse antes?",
  "¿Cómo se mueve?",
  "¿Qué dice la documentación de la empresa?",
];

const clamp01 = (x: number) => Math.min(Math.max(x, 0), 1);
const v3 = (a: number[]) => new THREE.Vector3(a[0], a[1], a[2]);

export default function MaquinaFreno({ tour }: { tour: boolean }) {
  const { maquina, error } = useMaquina("freno");
  const [piezas, setPiezas] = useState<Pieza[]>([]);
  const [jerarquia, setJerarquia] = useState<NodoJerarquia | null>(null);
  const [animacion, setAnimacion] = useState<Animacion | null>(null);
  const [geometria, setGeometria] = useState<GeometriaDespiece | null>(null);
  const [errorSim, setErrorSim] = useState<string | null>(null);

  useEffect(() => {
    const plena = { j_piston: 0.001, j_pinza_flotante: 0.0005 };
    Promise.all([
      api.piezas(),
      api.jerarquia(),
      api.animacion(),
      api.despiece(0),
      api.despiece(1),
      api.cinematica({}),
      api.cinematica(plena),
    ]).then(([p, j, an, d0, d1, c0, c1]) => {
      setPiezas(p);
      setJerarquia(j);
      setAnimacion(an);
      const delta: GeometriaDespiece["delta"] = {};
      const deltaApriete: GeometriaDespiece["deltaApriete"] = {};
      for (const id of Object.keys(d0)) {
        delta[id] = v3(d1[id]).sub(v3(d0[id]));
        const dc = v3(c1[id].posicion).sub(v3(c0[id].posicion));
        if (dc.lengthSq() > 0) deltaApriete[id] = dc;
      }
      setGeometria({ delta, deltaApriete });
    }, (e: Error) => setErrorSim(e.message));
  }, []);

  /* ---------- mecanismo ---------- */
  const [presion, setPresion] = useState(ENTRADA_FRENO_DEFECTO.presion_bar);
  const [mu, setMu] = useState(ENTRADA_FRENO_DEFECTO.coeficiente_friccion);
  const [velocidad, setVelocidad] = useState(ENTRADA_FRENO_DEFECTO.velocidad_kmh);
  const [factorManual, setFactorManual] = useState(0);
  const entrada = useMemo(
    () => ({ ...ENTRADA_FRENO_DEFECTO, presion_bar: presion, coeficiente_friccion: mu, velocidad_kmh: velocidad }),
    [presion, mu, velocidad],
  );
  const resultado = useMemo(() => calcularFreno(entrada), [entrada]);

  /* ---------- vista ---------- */
  const [modo, setModo] = useState<Modo>("ensamblado");
  const [escala, setEscala] = useState(0.25);
  const [corriendo, setCorriendo] = useState(false);
  const [tSim, setTSim] = useState(0);
  const [seleccion, setSeleccion] = useState<string | null>(null);
  const [ocultas, setOcultas] = useState<Set<string>>(new Set());
  const [aislada, setAislada] = useState<string | null>(null);
  const [transparencia, setTransparencia] = useState(0);
  const [seccion, setSeccion] = useState(false);
  const [ampliar, setAmpliar] = useState(true);
  const [lectura, setLectura] = useState<LecturaLocal | null>(null);
  const [lecturaApi, setLecturaApi] = useState<Lectura | null>(null);
  const controles = useRef<OrbitControlsImpl | null>(null);
  const divsEtiqueta = useRef<Record<string, HTMLDivElement | null>>({});
  const lineas: RefsLineas = useRef({});

  const escena = useRef<EstadoEscena>({
    despiece: {},
    apriete: 0,
    ampliacion: AMPLIACION,
    angulo: 0,
    seleccion: null,
    ocultas: new Set(),
    aislada: null,
    transparencia: 0,
    seccion: false,
    autoGiro: false,
    reencuadrar: 0,
  });
  Object.assign(escena.current, {
    seleccion,
    ocultas,
    aislada,
    transparencia,
    seccion,
    ampliacion: ampliar ? AMPLIACION : 1,
  });

  // Reloj de simulación por referencia; React solo se actualiza cada ~100 ms para las lecturas.
  const reloj = useRef({ t: 0, angulo0: 0 });
  const vivo = useRef({ modo, corriendo, escala, entrada, resultado, factorManual, animacion });
  vivo.current = { modo, corriendo, escala, entrada, resultado, factorManual, animacion };

  useEffect(() => {
    let id = 0;
    let previo = performance.now();
    let aviso = 0;
    const ciclo = (ahora: number) => {
      const dt = Math.min((ahora - previo) / 1000, 0.1);
      previo = ahora;
      const v = vivo.current;
      const e = escena.current;
      if (v.corriendo) reloj.current.t += dt * v.escala;
      const t = reloj.current.t;
      const ids = v.animacion?.orden_desmontaje ?? [];
      const d = v.animacion?.duracion_por_pieza_s ?? 0.35;
      const paso = d * (1 - (v.animacion?.solape ?? 0.5));
      const total = paso * Math.max(ids.length - 1, 0) + d;
      const progreso = (i: number) => clamp01((t - i * paso) / d);
      if (v.modo === "ensamblado") {
        for (const p of ids) e.despiece[p] = 0;
        e.apriete = 0;
      } else if (v.modo === "manual") {
        for (const p of ids) e.despiece[p] = v.factorManual;
        e.apriete = 0;
      } else if (v.modo === "despiece" || v.modo === "reensamblaje") {
        const orden = v.modo === "despiece" ? ids : (v.animacion?.orden_reensamblaje ?? []);
        orden.forEach((p, i) => (e.despiece[p] = v.modo === "despiece" ? progreso(i) : 1 - progreso(i)));
        e.apriete = 0;
        if (v.corriendo && t >= total) setCorriendo(false);
      } else if (v.modo === "frenado") {
        for (const p of ids) e.despiece[p] = 0;
        const w0 = v.entrada.velocidad_kmh / 3.6 / v.entrada.radio_neumatico_m;
        e.apriete = clamp01((t - T_PRESION) / (T_APRIETE - T_PRESION));
        const giro = t < T_APRIETE ? w0 * t : w0 * T_APRIETE + estadoRueda(v.entrada, v.resultado, t - T_APRIETE).angulo;
        e.angulo = reloj.current.angulo0 + giro;
        const st = estadoRueda(v.entrada, v.resultado, t - T_APRIETE);
        if (v.corriendo && t > T_APRIETE && st.detenido && st.rueda_detenida && t - T_APRIETE > st.t_detencion + 0.3)
          setCorriendo(false);
      }
      if (ahora - aviso > 100) {
        aviso = ahora;
        setTSim(t);
      }
      id = requestAnimationFrame(ciclo);
    };
    id = requestAnimationFrame(ciclo);
    return () => cancelAnimationFrame(id);
  }, []);

  const iniciar = useCallback((m: Modo) => {
    reloj.current.angulo0 = escena.current.angulo;
    reloj.current.t = 0;
    setTSim(0);
    setModo(m);
    setCorriendo(m !== "ensamblado" && m !== "manual");
    api.evento(m === "frenado" ? "frenado" : m === "reensamblaje" ? "reensamblaje" : "despiece", null, { modo: m });
  }, []);
  const reiniciar = useCallback(() => {
    reloj.current.t = 0;
    reloj.current.angulo0 = 0;
    escena.current.angulo = 0;
    setTSim(0);
    setCorriendo(false);
  }, []);

  const seleccionar = useCallback((id: string | null) => {
    setSeleccion(id);
    setLecturaApi(null);
    if (id) api.evento("seleccion", id);
  }, []);

  /* ---------- lecturas derivadas ---------- */
  const st = estadoRueda(entrada, resultado, Math.max(tSim - T_APRIETE, 0));
  const enFrenado = modo === "frenado";
  const velocidadActual = enFrenado && tSim > T_APRIETE ? st.velocidad_kmh : velocidad;
  const pasoActual = !enFrenado
    ? -1
    : tSim < T_PRESION
      ? 0
      : tSim < (T_PRESION + T_APRIETE) / 2
        ? 1
        : tSim < T_APRIETE
          ? 2
          : tSim < T_APRIETE + 0.25
            ? 3
            : 4;
  const etiquetas =
    modo === "ensamblado" || modo === "frenado"
      ? {
          piston: `F = ${fmt(resultado.fuerza_piston_n / 1000, 2)} kN`,
          disco: `T = ${fmt(resultado.par_frenado_nm)} N·m`,
          rueda: `v = ${fmt(velocidadActual)} km/h`,
        }
      : null;

  /* ---------- herramientas de vista ---------- */
  const captura = () => {
    const lienzo = document.querySelector<HTMLCanvasElement>("[data-testid=escenario-freno] canvas");
    if (!lienzo) return;
    const a = document.createElement("a");
    a.href = lienzo.toDataURL("image/png");
    a.download = `freno_disco_${modo}_${Date.now()}.png`;
    a.click();
    api.evento("captura", seleccion, { modo });
  };
  const reiniciarCamara = () => {
    escena.current.reencuadrar += 1; // vuelve al encuadre automático (fit to bounds)
    api.evento("camara", null, { accion: "reiniciar" });
  };
  const [estadoGuardado, setEstadoGuardado] = useState<string | null>(null);
  const guardar = () => {
    const cam = controles.current?.object.position;
    api
      .guardarEstado(`Vista ${new Date().toLocaleString("es-CO")}`, {
        modo: modo === "manual" ? "despiece" : modo,
        factor_despiece: modo === "manual" ? factorManual : modo === "despiece" ? 1 : 0,
        velocidad_animacion: Math.max(escala, 0.1),
        ocultas: [...ocultas],
        transparencia: Math.min(transparencia, 0.9),
        seleccionada: seleccion,
        valores_articulacion: {},
        camara: cam ? [cam.x, cam.y, cam.z] : null,
      })
      .then((r) => setEstadoGuardado(`Estado #${r.id} guardado`), (e: Error) => setEstadoGuardado(e.message));
  };
  const verificarApi = () => {
    if (!seleccion) return;
    const valores: Record<string, number> = {
      j_rueda: THREE.MathUtils.radToDeg(escena.current.angulo) % 360,
      j_piston: 0.001 * escena.current.apriete,
      j_pinza_flotante: 0.0005 * escena.current.apriete,
    };
    api.cinematica(valores).then((r) => setLecturaApi(r[seleccion]), (e: Error) => setErrorSim(e.message));
  };

  /* ---------- preguntas a la base de conocimiento ---------- */
  const [pregunta, setPregunta] = useState(PREGUNTAS[0]);
  const [respuesta, setRespuesta] = useState<RespuestaPieza | null>(null);
  const [consultando, setConsultando] = useState(false);
  const preguntar = (texto: string) => {
    if (!seleccion) return;
    setConsultando(true);
    api
      .preguntar(seleccion, texto)
      .then(setRespuesta, (e: Error) => setErrorSim(e.message))
      .finally(() => setConsultando(false));
  };

  /* ---------- experimentos ---------- */
  const r50 = calcularFreno({ ...entrada, presion_bar: 50 });
  const r25 = calcularFreno({ ...entrada, presion_bar: 25 });
  const rMu = calcularFreno({ ...ENTRADA_FRENO_DEFECTO, coeficiente_friccion: 0.3 });
  const rBase = calcularFreno(ENTRADA_FRENO_DEFECTO);
  const r120 = calcularFreno({ ...ENTRADA_FRENO_DEFECTO, velocidad_kmh: 120 });
  const experimentos = armarExperimentos(FRENO.experimentos, [
    {
      explicacion: `T = 2·μ·p·A·r es lineal en p: ${fmt(r25.par_frenado_nm)} → ${fmt(r50.par_frenado_nm)} N·m. ${
        r50.rueda_bloqueada ? "Con 50 bar la deceleración supera g·μ del neumático: la rueda se bloquea (modelo sin ABS)." : ""
      }`,
      aplicar: () => {
        setPresion(50);
        iniciar("frenado");
      },
    },
    {
      explicacion: `a ∝ μ y d = v²/2a, así d ∝ 1/μ: ${fmt(rBase.distancia_detencion_m ?? 0, 1)} m → ${fmt(rMu.distancia_detencion_m ?? 0, 1)} m.`,
      aplicar: () => {
        setPresion(25);
        setVelocidad(60);
        setMu(0.3);
        iniciar("frenado");
      },
    },
    {
      explicacion: `d = v²/2a: al duplicar v la distancia se multiplica por 4 (${fmt(rBase.distancia_detencion_m ?? 0, 1)} m → ${fmt(
        r120.distancia_detencion_m ?? 0,
        1,
      )} m). El par no depende de la velocidad.`,
      aplicar: () => {
        setPresion(25);
        setMu(0.4);
        setVelocidad(120);
        iniciar("frenado");
      },
    },
  ]);

  /* ---------- recorrido automático (< 30 s) ---------- */
  const pasosTour: PasoTour[] = [
    { en: 0, texto: "Freno de disco: una pinza flotante abraza el disco que gira con la rueda", accion: () => {
      escena.current.autoGiro = true;
      setPresion(25); setMu(0.4); setVelocidad(60); setEscala(0.25); setSeleccion(null);
      iniciar("ensamblado");
    } },
    { en: 3, texto: "Correr: 25 bar llegan al pistón y la pinza cierra la holgura", accion: () => {
      escena.current.autoGiro = false;
      iniciar("frenado");
    } },
    { en: 8, texto: "F = p·A en el pistón; el par T = 2·μ·F·r detiene la rueda sin bloquearla" },
    { en: 12, texto: "Despiece: orden de desmontaje calculado por el backend (orden topológico)", accion: () => {
      setEscala(1); iniciar("despiece");
    } },
    { en: 16, texto: "Selección: pistón de la pinza — función y procedencia en la ficha", accion: () => setSeleccion("piston") },
    { en: 19, texto: "Experimento: 50 bar duplican el par y la rueda se bloquea (modelo sin ABS)", accion: () => {
      setSeleccion(null); setPresion(50); setEscala(0.25); iniciar("frenado");
    } },
    { en: 24, texto: "Reensamblaje: el orden inverso devuelve cada pieza a su posición exacta", accion: () => {
      setEscala(1); iniciar("reensamblaje");
    } },
    { en: 27.5, texto: "Modelo demostrativo: la animación no valida propiedades mecánicas", accion: () => {
      escena.current.autoGiro = true;
    } },
  ];
  const banda = useTour(tour, pasosTour, FRENO.duracionRecorrido);

  /* ---------- render ---------- */
  const pieza = piezas.find((p) => p.id === seleccion) ?? null;
  const conmutar = (id: string) =>
    setOcultas((prev) => {
      const s = new Set(prev);
      if (s.has(id)) s.delete(id);
      else s.add(id);
      api.evento("visibilidad", id, { oculta: s.has(id) });
      return s;
    });

  const valores = { presion, mu, velocidad, despiece: factorManual };
  const cambiar = (id: string, v: number) => {
    if (id === "presion") setPresion(v);
    else if (id === "mu") setMu(v);
    else if (id === "velocidad") setVelocidad(v);
    else {
      setFactorManual(v);
      setModo("manual");
      setCorriendo(false);
    }
  };

  const arbol = (
    <>
      {jerarquia ? (
        <ul className="arbol">
          {jerarquia.hijos.map((g) => (
            <li key={g.id}>
              <div className="grupo">{g.nombre}</div>
              <ul className="arbol">
                {g.hijos.map((h) => (
                  <li key={h.id} className="nodo">
                    <input type="checkbox" aria-label={`Visible: ${h.nombre}`} checked={!ocultas.has(h.id)} onChange={() => conmutar(h.id)} />
                    <button className={`nombre ${seleccion === h.id ? "sel" : ""}`} onClick={() => seleccionar(seleccion === h.id ? null : h.id)} data-pieza={h.id}>
                      {h.nombre}
                    </button>
                    <button className="nombre" title="Aislar" aria-label={`Aislar ${h.nombre}`} onClick={() => setAislada(aislada === h.id ? null : h.id)}>
                      {aislada === h.id ? "◉" : "○"}
                    </button>
                  </li>
                ))}
              </ul>
            </li>
          ))}
        </ul>
      ) : (
        <p className="aviso">Cargando jerarquía…</p>
      )}
      {(ocultas.size > 0 || aislada) && (
        <button className="boton secundario" onClick={() => { setOcultas(new Set()); setAislada(null); }}>
          Mostrar todo
        </button>
      )}
      <section className="ficha" aria-label="Ficha de la pieza">
        <h4>Ficha de la pieza</h4>
        {!pieza && <p className="aviso">Seleccionar una pieza en la escena o en el árbol.</p>}
        {pieza && (
          <dl>
            <dt>Pieza</dt>
            <dd data-testid="ficha-nombre">{pieza.nombre}</dd>
            <dt>Función</dt>
            <dd>{pieza.funcion}</dd>
            {pieza.material && (<><dt>Material (demostrativo)</dt><dd>{pieza.material}</dd></>)}
            <dt>Dimensiones (mm)</dt>
            <dd className="num">
              {Object.entries(pieza.dimensiones_m).map(([k, v]) => `${k.replace(/_/g, " ")} ${fmt(v * 1000, 1)}`).join(" · ")}
            </dd>
            <dt>Retirar antes</dt>
            <dd>{pieza.retirar_antes.length ? pieza.retirar_antes.join(", ") : "—"}</dd>
            <dt>Relacionadas</dt>
            <dd>{pieza.relacionadas.join(", ") || "—"}</dd>
            <dt>Posición / ángulo (escena)</dt>
            <dd className="num" data-testid="lectura-posicion">
              {lectura
                ? `x ${fmt(lectura.posicion[0] * 1000, 1)} · y ${fmt(lectura.posicion[1] * 1000, 1)} · z ${fmt(lectura.posicion[2] * 1000, 1)} mm · θz ${fmt(lectura.angulo_z_grados, 1)}°`
                : "—"}
            </dd>
            <dt>Posición / ángulo (API, validado)</dt>
            <dd className="num">
              {lecturaApi
                ? `x ${fmt(lecturaApi.posicion[0] * 1000, 1)} · y ${fmt(lecturaApi.posicion[1] * 1000, 1)} · z ${fmt(lecturaApi.posicion[2] * 1000, 1)} mm · θ ${lecturaApi.rotacion_grados.map((g) => fmt(g, 1)).join(", ")}°`
                : <button className="boton secundario" onClick={verificarApi}>Verificar en API</button>}
            </dd>
            <dt>Procedencia</dt>
            <dd><InsigniaFuente fuente="demostrativo" /> {pieza.referencia_documental}</dd>
          </dl>
        )}
      </section>
    </>
  );

  const faq = (
    <>
      <section aria-label="Preguntar sobre la pieza">
        <h4>Preguntar sobre la pieza (RAG)</h4>
        <div className="barra">
          {PREGUNTAS.map((p) => (
            <button key={p} className="boton secundario" disabled={!seleccion} onClick={() => { setPregunta(p); preguntar(p); }}>
              {p}
            </button>
          ))}
        </div>
        {!seleccion && <p className="aviso">Seleccionar una pieza (pestaña Componentes o en la escena) para preguntar.</p>}
        <form onSubmit={(e) => { e.preventDefault(); preguntar(pregunta); }} className="barra">
          <input aria-label="Pregunta" value={pregunta} onChange={(e) => setPregunta(e.target.value)} style={{ flex: 1, minWidth: 0 }} />
          <button className="boton" disabled={!seleccion || consultando}>{consultando ? "…" : "Preguntar"}</button>
        </form>
        {respuesta && (
          <div data-testid="respuesta-pieza">
            <p className="respuesta"><InsigniaFuente fuente="demostrativo" />{respuesta.respuesta_modelo}</p>
            {respuesta.documentado.length > 0 && (
              <ul className="datos">
                {respuesta.documentado.map((d) => (
                  <li key={d.fragmento_id}>
                    <InsigniaFuente fuente={d.origen} />{d.texto}<br />
                    <a href={d.url} target="_blank" rel="noreferrer">{d.url}</a>
                  </li>
                ))}
              </ul>
            )}
            <p className="aviso">{respuesta.advertencia}</p>
          </div>
        )}
      </section>
      <h4>FAQ de Fanalca</h4>
      <FaqFanalcaAuto />
    </>
  );

  return (
    <PlantillaMaquina
      def={FRENO}
      maquina={maquina}
      errorApi={error}
      avisos={errorSim && <p className="aviso error">API del simulador: {errorSim}</p>}
      barra={{
        ensamblado: { alPulsar: () => iniciar("ensamblado"), activo: modo === "ensamblado" },
        despiece: { alPulsar: () => iniciar("despiece"), activo: modo === "despiece" },
        seccion: { alPulsar: () => setSeccion(!seccion), activo: seccion },
        camara: { alPulsar: reiniciarCamara, titulo: "Reiniciar cámara (encuadre automático)" },
        png: { alPulsar: captura },
        guardar: { alPulsar: guardar },
        recorrido: { alPulsar: () => { window.location.hash = hashRecorrido(FRENO.ruta); }, deshabilitado: tour },
      }}
      escenarioProps={{ "data-testid": "escenario-freno", "data-modo": modo }}
      lienzo={
        <EscenaFreno
          estado={escena}
          geometria={geometria}
          alSeleccionar={seleccionar}
          alFotograma={setLectura}
          etiquetas={divsEtiqueta}
          lineas={lineas}
          controles={controles}
        />
      }
      capas={
        <EtiquetasPieza
          divs={divsEtiqueta}
          lineas={lineas}
          etiquetas={[
            { clave: "piston", clase: "fuerza", contenido: etiquetas?.piston ?? null },
            { clave: "disco", contenido: etiquetas?.disco ?? null },
            { clave: "rueda", clase: "movimiento", contenido: etiquetas?.rueda ?? null },
          ]}
        />
      }
      leyenda={`geometría procedural demostrativa · ${ampliar ? `holguras ampliadas ×${AMPLIACION} (solo visual)` : "holguras a escala real"} · arrastrar: orbitar · rueda: zoom`}
      banda={banda}
      controles={<ControlesDeclarados defs={FRENO.controles} valores={valores} alCambiar={cambiar} />}
      reproduccion={{
        corriendo,
        alCorrer: () => (modo === "ensamblado" || modo === "manual" ? iniciar("frenado") : setCorriendo(true)),
        alPausar: () => setCorriendo(false),
        alReiniciar: reiniciar,
        escala,
        alEscala: setEscala,
      }}
      controlesExtra={
        <div className="sub-controles">
          <div className="barra">
            <button className={`boton ${modo === "frenado" ? "activo" : "secundario"}`} onClick={() => iniciar("frenado")}>Frenar</button>
            <button className={`boton ${modo === "reensamblaje" ? "activo" : "secundario"}`} onClick={() => iniciar("reensamblaje")}>Reensamblar</button>
          </div>
          <Deslizador etiqueta="Transparencia" valor={transparencia} min={0} max={0.9} paso={0.05} unidad="" formato={(v) => fmt(v, 2)} alCambiar={setTransparencia} />
          <label className="cbs">
            <input type="checkbox" checked={ampliar} onChange={(e) => setAmpliar(e.target.checked)} /> Ampliar holguras ×{AMPLIACION} (solo visual)
          </label>
          {estadoGuardado && <p className="aviso" role="status">{estadoGuardado}</p>}
        </div>
      }
      contenidoPestanas={{ componentes: arbol, faq }}
      chips={
        <>
          <ChipDato etiqueta="p" valor={`${fmt(presion)} bar`} />
          <ChipDato etiqueta="F = p·A" valor={`${fmt(resultado.fuerza_piston_n / 1000, 2)} kN`} variante="dato" />
          <ChipDato etiqueta="F fricción" valor={`${fmt(resultado.fuerza_friccion_total_n / 1000, 2)} kN`} variante="dato" />
          <ChipDato etiqueta="T" valor={`${fmt(resultado.par_frenado_nm)} N·m`} variante="dato" />
          <ChipDato etiqueta="a" valor={`${fmt(resultado.deceleracion_g, 2)} g`} variante="dato" />
          <ChipDato etiqueta="t detención" valor={`${fmt(resultado.tiempo_detencion_s ?? 0, 2)} s`} variante="dato" />
          <ChipDato etiqueta="d detención" valor={`${fmt(resultado.distancia_detencion_m ?? 0, 1)} m`} variante="dato" />
          <ChipDato etiqueta="v" valor={`${fmt(velocidadActual)} km/h`} variante="dato" />
          <ChipDato etiqueta="t sim" valor={`${fmt(tSim, 2)} s`} />
          {resultado.rueda_bloqueada ? (
            <ChipDato etiqueta="Estado" valor="rueda bloqueada (a > g·μ neumático)" variante="estado" ok={false} />
          ) : (
            <ChipDato etiqueta="Estado" valor="sin bloqueo" variante="estado" ok />
          )}
        </>
      }
      pasoActual={pasoActual}
      experimentos={experimentos}
    />
  );
}
