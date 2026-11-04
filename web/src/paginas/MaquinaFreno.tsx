/**
 * Máquina 1 — Freno de disco con pinza flotante (caso principal del simulador 3D v2.0).
 * Pregunta: ¿cómo convierte un freno de disco la presión hidráulica en fuerza de frenado?
 * Relación: T = 2·μ·p·A·r.   Controles del mecanismo: presión, μ, velocidad, despiece.
 */
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import * as THREE from "three";
import type { OrbitControls as OrbitControlsImpl } from "three-stdlib";
import { api, type Animacion, type NodoJerarquia, type Pieza, type RespuestaPieza, type Lectura } from "../api";
import {
  BandaTour,
  CabeceraMaquina,
  Chip,
  Deslizador,
  Insignia,
  ModoExperimento,
  PanelEmpresa,
  Pasos,
  Reproduccion,
  RevisionCritica,
  useMaquina,
  useTour,
  type Experimento,
  type PasoTour,
} from "../componentes/anatomia";
import { calcularFreno, ENTRADA_FRENO_DEFECTO, estadoRueda } from "../modelos/freno";
import EscenaFreno, { type EstadoEscena, type GeometriaDespiece, type LecturaLocal } from "./EscenaFreno";

type Modo = "ensamblado" | "manual" | "despiece" | "reensamblaje" | "frenado";

const T_PRESION = 0.5; // s: la presión llega a la pinza
const T_APRIETE = 0.8; // s: holgura cerrada, inicia la fricción
const AMPLIACION = 20;
const PASOS = [
  "La presión hidráulica llega a la pinza",
  "El pistón empuja la pastilla interna: F = p · A",
  "La pinza flotante se desliza y aprieta la pastilla externa",
  "La fricción en ambas caras produce el par: T = 2 · μ · F · r",
  "El par decelera la rueda hasta detenerla",
];
const PREGUNTAS = [
  "¿Qué función cumple?",
  "¿Qué debe retirarse antes?",
  "¿Cómo se mueve?",
  "¿Qué dice la documentación de la empresa?",
];

const fmt = (v: number, d = 0) => v.toLocaleString("es-CO", { minimumFractionDigits: d, maximumFractionDigits: d });
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
    const lienzo = document.querySelector<HTMLCanvasElement>(".escenario canvas");
    if (!lienzo) return;
    const a = document.createElement("a");
    a.href = lienzo.toDataURL("image/png");
    a.download = `freno_disco_${modo}_${Date.now()}.png`;
    a.click();
    api.evento("captura", seleccion, { modo });
  };
  const reiniciarCamara = () => {
    controles.current?.reset();
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
  const experimentos: Experimento[] = [
    {
      pregunta: "Si la presión pasa de 25 a 50 bar, ¿qué le ocurre al par de frenado?",
      opciones: [
        { texto: "Se duplica", correcta: true },
        { texto: "Se cuadruplica", correcta: false },
        { texto: "No cambia: depende solo de μ", correcta: false },
      ],
      explicacion: `T = 2·μ·p·A·r es lineal en p: ${fmt(r25.par_frenado_nm)} → ${fmt(r50.par_frenado_nm)} N·m. ${
        r50.rueda_bloqueada ? "Con 50 bar la deceleración supera g·μ del neumático: la rueda se bloquea (modelo sin ABS)." : ""
      }`,
      aplicar: () => {
        setPresion(50);
        iniciar("frenado");
      },
    },
    {
      pregunta: "Si μ entre pastilla y disco baja de 0,40 a 0,30, ¿qué ocurre con la distancia de detención a 25 bar?",
      opciones: [
        { texto: "Disminuye", correcta: false },
        { texto: "Aumenta alrededor de un tercio", correcta: true },
        { texto: "No cambia", correcta: false },
      ],
      explicacion: `a ∝ μ y d = v²/2a, así d ∝ 1/μ: ${fmt(rBase.distancia_detencion_m ?? 0, 1)} m → ${fmt(
        rMu.distancia_detencion_m ?? 0,
        1,
      )} m.`,
      aplicar: () => {
        setPresion(25);
        setVelocidad(60);
        setMu(0.3);
        iniciar("frenado");
      },
    },
    {
      pregunta: "Con la misma presión, si la velocidad pasa de 60 a 120 km/h, ¿cuánto cambia la distancia?",
      opciones: [
        { texto: "Se duplica", correcta: false },
        { texto: "Se cuadruplica", correcta: true },
        { texto: "Se mantiene", correcta: false },
      ],
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
  ];

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
  const banda = useTour(tour, pasosTour, 29);

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

  return (
    <>
      <CabeceraMaquina
        maquina={maquina}
        respaldo={{
          pregunta: "¿Cómo convierte un freno de disco la presión hidráulica en fuerza de frenado?",
          relacion: "T = 2 · μ · p · A · r",
          idea: "La presión empuja un solo pistón; la pinza flotante reacciona y aprieta el disco por ambas caras.",
        }}
      />
      {errorSim && <p className="aviso error">API del simulador: {errorSim}</p>}

      <div className="maquina">
        <div>
          <div className="escenario" data-testid="escenario-freno" data-modo={modo}>
            <div className="superpuesto" role="toolbar" aria-label="Modos y herramientas de vista">
              <button className={`boton ${modo === "ensamblado" ? "activo" : "secundario"}`} onClick={() => iniciar("ensamblado")}>Ensamblado</button>
              <button className={`boton ${modo === "despiece" ? "activo" : "secundario"}`} onClick={() => iniciar("despiece")}>Despiece</button>
              <button className={`boton ${modo === "reensamblaje" ? "activo" : "secundario"}`} onClick={() => iniciar("reensamblaje")}>Reensamblar</button>
              <button className={`boton ${modo === "frenado" ? "activo" : "secundario"}`} onClick={() => iniciar("frenado")}>Frenar</button>
              <button className="boton secundario" onClick={reiniciarCamara} title="Reiniciar cámara">⌖ Cámara</button>
              <button className={`boton ${seccion ? "activo" : "secundario"}`} onClick={() => setSeccion(!seccion)} aria-pressed={seccion}>◧ Sección</button>
              <button className="boton secundario" onClick={captura}>⤓ PNG</button>
              <button className="boton secundario" onClick={guardar}>Guardar vista</button>
            </div>
            <EscenaFreno
              estado={escena}
              geometria={geometria}
              alSeleccionar={seleccionar}
              alFotograma={setLectura}
              etiquetas={divsEtiqueta}
              controles={controles}
            />
            {(["piston", "disco", "rueda"] as const).map((k) => (
              <div
                key={k}
                ref={(d) => {
                  divsEtiqueta.current[k] = d;
                }}
                className={`etiqueta-3d ${k === "piston" ? "fuerza" : k === "rueda" ? "movimiento" : ""}`}
                data-etiqueta={k}
                style={{ position: "absolute", left: 0, top: 0, display: etiquetas ? "block" : "none", zIndex: 1 }}
              >
                {etiquetas?.[k]}
              </div>
            ))}
            <span className="leyenda-escena">
              geometría procedural demostrativa · {ampliar ? `holguras ampliadas ×${AMPLIACION} (solo visual)` : "holguras a escala real"} · arrastrar: orbitar · rueda: zoom · clic: seleccionar
            </span>
            <BandaTour {...banda} />
          </div>

          <div className="lecturas" aria-label="Lecturas">
            <Chip etiqueta="p" valor={`${fmt(presion)} bar`} />
            <Chip etiqueta="F = p·A" valor={`${fmt(resultado.fuerza_piston_n / 1000, 2)} kN`} tono="fuerza" />
            <Chip etiqueta="F fricción" valor={`${fmt(resultado.fuerza_friccion_total_n / 1000, 2)} kN`} tono="fuerza" />
            <Chip etiqueta="T" valor={`${fmt(resultado.par_frenado_nm)} N·m`} tono="fuerza" />
            <Chip etiqueta="a" valor={`${fmt(resultado.deceleracion_g, 2)} g`} tono="movimiento" />
            <Chip etiqueta="t detención" valor={`${fmt(resultado.tiempo_detencion_s ?? 0, 2)} s`} tono="movimiento" />
            <Chip etiqueta="d detención" valor={`${fmt(resultado.distancia_detencion_m ?? 0, 1)} m`} tono="movimiento" />
            <Chip etiqueta="v" valor={`${fmt(velocidadActual)} km/h`} tono="movimiento" />
            <Chip etiqueta="t sim" valor={`${fmt(tSim, 2)} s`} />
            {resultado.rueda_bloqueada ? (
              <Chip etiqueta="Estado" valor="rueda bloqueada (a > g·μ neumático)" tono="alerta" />
            ) : (
              <Chip etiqueta="Estado" valor="sin bloqueo" tono="correcto" />
            )}
          </div>

          <div className="maquina" style={{ gridTemplateColumns: "1fr 1fr" }}>
            <section className="panel">
              <h3>Mecanismo paso a paso</h3>
              <Pasos pasos={PASOS} actual={pasoActual} />
            </section>
            <ModoExperimento experimentos={experimentos} />
          </div>
        </div>

        <aside>
          <section className="panel" aria-label="Controles">
            <h3>Controles</h3>
            <Deslizador etiqueta="Presión hidráulica" valor={presion} min={0} max={80} paso={1} unidad="bar" alCambiar={setPresion} />
            <Deslizador etiqueta="μ pastilla-disco" valor={mu} min={0.2} max={0.6} paso={0.01} unidad="" alCambiar={setMu} formato={(v) => fmt(v, 2)} />
            <Deslizador etiqueta="Velocidad inicial" valor={velocidad} min={10} max={140} paso={5} unidad="km/h" alCambiar={setVelocidad} />
            <Deslizador
              etiqueta="Despiece manual"
              valor={factorManual}
              min={0}
              max={1}
              paso={0.01}
              unidad=""
              formato={(v) => fmt(v, 2)}
              alCambiar={(v) => {
                setFactorManual(v);
                setModo("manual");
                setCorriendo(false);
              }}
            />
            <Reproduccion
              corriendo={corriendo}
              alCorrer={() => (modo === "ensamblado" || modo === "manual" ? iniciar("frenado") : setCorriendo(true))}
              alPausar={() => setCorriendo(false)}
              alReiniciar={reiniciar}
              escala={escala}
              alEscala={setEscala}
            />
            <div style={{ marginTop: 12 }}>
              <Deslizador etiqueta="Transparencia" valor={transparencia} min={0} max={0.9} paso={0.05} unidad="" formato={(v) => fmt(v, 2)} alCambiar={setTransparencia} />
              <label style={{ fontSize: 13 }}>
                <input type="checkbox" checked={ampliar} onChange={(e) => setAmpliar(e.target.checked)} /> Ampliar holguras ×{AMPLIACION} (solo visual)
              </label>
            </div>
            {estadoGuardado && <p className="aviso" role="status">{estadoGuardado}</p>}
          </section>

          <section className="panel" aria-label="Árbol de componentes">
            <h3>Árbol de componentes</h3>
            {jerarquia ? (
              <ul className="arbol">
                {jerarquia.hijos.map((g) => (
                  <li key={g.id}>
                    <div className="grupo">{g.nombre}</div>
                    <ul className="arbol">
                      {g.hijos.map((h) => (
                        <li key={h.id} className="nodo">
                          <input
                            type="checkbox"
                            aria-label={`Visible: ${h.nombre}`}
                            checked={!ocultas.has(h.id)}
                            onChange={() => conmutar(h.id)}
                          />
                          <button
                            className={`nombre ${seleccion === h.id ? "sel" : ""}`}
                            onClick={() => seleccionar(seleccion === h.id ? null : h.id)}
                            data-pieza={h.id}
                          >
                            {h.nombre}
                          </button>
                          <button
                            className="nombre"
                            title="Aislar"
                            aria-label={`Aislar ${h.nombre}`}
                            onClick={() => setAislada(aislada === h.id ? null : h.id)}
                          >
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
              <button className="boton secundario" style={{ marginTop: 8 }} onClick={() => { setOcultas(new Set()); setAislada(null); }}>
                Mostrar todo
              </button>
            )}
          </section>

          <section className="panel ficha" aria-label="Ficha de la pieza">
            <h3>Ficha de la pieza</h3>
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
                <dd><Insignia tipo="demostrativo" /> {pieza.referencia_documental}</dd>
              </dl>
            )}
          </section>

          <section className="panel" aria-label="Preguntar sobre la pieza">
            <h3>Preguntar (RAG)</h3>
            <div className="barra" style={{ marginBottom: 8 }}>
              {PREGUNTAS.map((p) => (
                <button key={p} className="boton secundario" style={{ fontSize: 12, padding: "4px 8px" }} disabled={!seleccion} onClick={() => { setPregunta(p); preguntar(p); }}>
                  {p}
                </button>
              ))}
            </div>
            <form onSubmit={(e) => { e.preventDefault(); preguntar(pregunta); }} className="barra">
              <input aria-label="Pregunta" value={pregunta} onChange={(e) => setPregunta(e.target.value)} style={{ flex: 1, minWidth: 0, padding: 6 }} />
              <button className="boton" disabled={!seleccion || consultando}>{consultando ? "…" : "Preguntar"}</button>
            </form>
            {respuesta && (
              <div style={{ marginTop: 10 }} data-testid="respuesta-pieza">
                <p className="respuesta"><Insignia tipo="demostrativo" />{respuesta.respuesta_modelo}</p>
                {respuesta.documentado.length > 0 && (
                  <ul className="datos">
                    {respuesta.documentado.map((d) => (
                      <li key={d.fragmento_id}>
                        <Insignia tipo={d.origen} />{d.texto}<br />
                        <a href={d.url} target="_blank" rel="noreferrer">{d.url}</a>
                      </li>
                    ))}
                  </ul>
                )}
                <p className="aviso" style={{ marginTop: 8 }}>{respuesta.advertencia}</p>
              </div>
            )}
          </section>

          <div style={{ marginTop: 12 }}>
            <PanelEmpresa maquina={maquina} error={error} />
          </div>
          <div style={{ marginTop: 12 }}>
            <RevisionCritica extra={["Despiece reversible y orden de desmontaje validado por la API", "Holguras ampliadas declaradas en la escena"]} />
          </div>
        </aside>
      </div>
    </>
  );
}
