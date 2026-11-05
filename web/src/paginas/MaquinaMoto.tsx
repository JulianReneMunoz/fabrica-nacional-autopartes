/**
 * Máquina 4 — Motocicleta de referencia genérica con fichas Honda (ADR-017).
 * Pregunta: ¿cómo convierte una motocicleta Honda el giro del motor en velocidad de la rueda,
 * y la palanca en fuerza de frenado?
 * Relaciones: v = rpm·2π·R·60 / (1000·i_prim·i_marcha·i_final);  x(θ) = r·cos θ + √(L² − r²·sin² θ);  T = 2·μ·p·A·r.
 *
 * La velocidad es una VARIABLE DE ESTADO continua (`pasoMoto`, modelos/moto.ts): con marcha engranada las rpm se
 * derivan de ella; el acelerador da una aceleración, el freno una deceleración (`calcularFreno`) y en neutro la
 * moto rueda libre. Los parámetros son «valores típicos de la categoría — supuesto didáctico»; «Ver con ficha
 * de…» aplica solo los campos `publicado`. Todo giro se anima con un factor de cámara lenta visible.
 */
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import * as THREE from "three";
import type { OrbitControls as OrbitControlsImpl } from "three-stdlib";
import { apiMoto, type Animacion, type ArticulacionApi, type FaqVisor, type FichaMotoApi, type NodoJerarquia, type Pieza, type RespuestaModeloApi, type RespuestaQa } from "../api";
import { BandaTour, Chip, Deslizador, Insignia, ModoExperimento, PanelEmpresa, Reproduccion, RevisionCritica, useMaquina, useTour, type Experimento, type PasoTour } from "../componentes/anatomia";
import { DiagramaCiclo, FaqFanalca, FaqModelos, FichaTecnica, fmt, InsigniaSupuesto, NO_PUBLICADO, Pestanas, piezasDeCampo } from "../componentes/panelesMoto";
import { estadoRueda } from "../modelos/freno";
import {
  ajusteDesdeFicha,
  anguloBielaRad,
  calcularMoto,
  calcularMotoDesdeEstado,
  chispaPermitida,
  ENTRADA_MOTO_DEFECTO,
  ESTADO_DINAMICO_INICIAL,
  ETIQUETA_SUPUESTO,
  FACTOR_LENTO_DEFECTO,
  FACTORES_LENTO,
  FASES_INFO,
  faseCiclo,
  frenosMoto,
  GEOMETRIA_MOTOR,
  LIMITES,
  MEDIDA_DELANTERA_DEMO,
  pasoMoto,
  posicionPistonM,
  RADIO_CORONA_M,
  RADIO_PINON_M,
  radioLlantaM,
  SUPUESTOS,
  textoMarcha,
  velocidadAngularRadS,
  velocidadMsEnCorte,
  type EstadoDinamico,
  type MandoMoto,
  type PalancaMoto,
  type VersionMoto,
} from "../modelos/moto";
import EscenaMoto, { type Calidad, GEOMETRIA_MOVIL_DEFECTO, geometriaMovil, type EstadoMoto, type GeometriaDespieceMoto, type GeometriaMovil, type PeticionCamara, type Vec3 } from "./EscenaMoto";

const ID_FICHA = "cb160f";
const G = 9.80665;
const RADIO_DELANTERA_M = radioLlantaM(MEDIDA_DELANTERA_DEMO);
const RADIO_BASE_TRASERO = radioLlantaM(String(SUPUESTOS.medida_llanta_trasera.valor));
const num = (clave: string) => SUPUESTOS[clave].valor as number;
const RALENTI = num("ralenti_rpm");
const CORTE = num("corte_encendido_rpm");
const FINAL = num("relacion_final");
const PRIMARIA = num("relacion_primaria");
const MARCHAS = Array.from({ length: num("n_marchas") + 1 }, (_, i) => i); // 0 = neutro
const PIEZAS_MOTOR = new Set(["cilindro", "piston", "biela", "ciguenal", "valvula_admision", "valvula_escape", "bujia"]);
const FRASE_FINAL =
  "La velocidad es el giro del motor dividido por las relaciones de transmisión y multiplicado por la circunferencia de la llanta; el freno invierte el camino y convierte la fuerza de la mano en torque sobre la rueda.";
const PREGUNTA = "¿Cómo convierte una motocicleta Honda el giro del motor en velocidad de la rueda, y la palanca en fuerza de frenado?";

type ModeloSel = "generica" | "std" | "dlx";
const MODELOS: Record<ModeloSel, { nombre: string; version: VersionMoto; etiqueta: string }> = {
  generica: { nombre: "Moto de referencia genérica", version: "DLX", etiqueta: "Genérica" },
  std: { nombre: "CB 160F", version: "STD", etiqueta: "CB 160F STD" },
  dlx: { nombre: "CB 160F", version: "DLX", etiqueta: "CB 160F DLX" },
};

interface Ctl {
  acelerador: number; // 0..1
  marcha: number;
  palanca: PalancaMoto;
  fuerza: number;
  cbs: boolean;
  freno: boolean;
}
const CTL0: Ctl = { acelerador: 0, marcha: 0, palanca: "delantera", fuerza: 0, cbs: false, freno: false };

// Presets de cámara para la moto de ~1,30 m entre ejes (puntos duros del backend): centro hacia x ≈ 0,01 m.
const CAMARAS: Record<string, { pos: Vec3; objetivo: Vec3; nombre: string }> = {
  lateral: { nombre: "Lateral", pos: [0.01, 0.5, 2.55], objetivo: [0.01, 0.43, 0] },
  cuartos: { nombre: "3/4", pos: [1.55, 0.9, 2.1], objetivo: [0.01, 0.43, 0] },
  general: { nombre: "General", pos: [0.9, 0.75, 2.25], objetivo: [0.01, 0.43, 0] },
  motor: { nombre: "Motor", pos: [0.52, 0.5, 0.66], objetivo: [0.11, 0.43, 0] },
  despiece: { nombre: "Despiece", pos: [1.9, 1.0, 2.9], objetivo: [0.0, 0.45, 0] },
  transmision: { nombre: "Transmisión", pos: [-0.4, 0.45, 1.15], objetivo: [-0.4, 0.31, 0.075] },
  frenos: { nombre: "Frenos", pos: [0.1, 0.5, 2.4], objetivo: [0.01, 0.3, 0] },
};

const clamp01 = (x: number) => Math.min(Math.max(x, 0), 1);
const suave = (x: number) => x * x * (3 - 2 * x);

interface Instantanea {
  theta720: number;
  est: EstadoDinamico;
  wTras: number;
  wPinon: number;
  vCadena: number;
  despiece: number;
  chispas: number;
  ciclos: number;
}
const INST0: Instantanea = { theta720: 0, est: ESTADO_DINAMICO_INICIAL, wTras: 0, wPinon: 0, vCadena: 0, despiece: 0, chispas: 0, ciclos: 0 };
const TEXTO_MODO: Record<string, string> = {
  neutro: "neutro: rpm libres",
  normal: "marcha engranada: rpm = v·i_total",
  limitador: "limitador: corta la chispa",
  ahogado: "motor ahogado",
  patinaje: "embrague patinando (arranque)",
  embrague: "embrague accionado (frenando)",
};

export default function MaquinaMoto({ tour }: { tour: boolean }) {
  const { maquina, error } = useMaquina("moto_honda");

  /* ---------- datos del simulador y de las fichas ---------- */
  const [piezas, setPiezas] = useState<Pieza[]>([]);
  const [jerarquia, setJerarquia] = useState<NodoJerarquia | null>(null);
  const [animacion, setAnimacion] = useState<Animacion | null>(null);
  const [geometria, setGeometria] = useState<GeometriaDespieceMoto | null>(null);
  const [errorSim, setErrorSim] = useState<string | null>(null);
  const [articulaciones, setArticulaciones] = useState<ArticulacionApi[] | null>(null);
  const [parametrosEns, setParametrosEns] = useState<Record<string, number> | null>(null);
  const [ficha, setFicha] = useState<FichaMotoApi | null>(null);
  const [errorFicha, setErrorFicha] = useState<string | null>(null);
  const [faqModelo, setFaqModelo] = useState<RespuestaModeloApi[] | null>(null);
  const [errorFaqModelo, setErrorFaqModelo] = useState<string | null>(null);
  const [faqVisor, setFaqVisor] = useState<FaqVisor | null>(null);
  const [errorFaqVisor, setErrorFaqVisor] = useState<string | null>(null);
  const [faltaFaq, setFaltaFaq] = useState(false);
  const [enVivo, setEnVivo] = useState<{ respuesta: RespuestaQa | null; error: string | null; consultando: boolean }>({ respuesta: null, error: null, consultando: false });

  useEffect(() => {
    const v3 = (a: number[]) => new THREE.Vector3(a[0], a[1], a[2]);
    Promise.all([apiMoto.piezas(), apiMoto.jerarquia(), apiMoto.animacion(), apiMoto.despiece(0), apiMoto.despiece(1)]).then(
      ([p, j, an, d0, d1]) => {
        setPiezas(p);
        setJerarquia(j);
        setAnimacion(an);
        const delta: GeometriaDespieceMoto["delta"] = {};
        for (const id of Object.keys(d0)) delta[id] = v3(d1[id]).sub(v3(d0[id]));
        setGeometria({ delta });
      },
      (e: Error) => setErrorSim(e.message),
    );
    apiMoto.articulaciones().then(setArticulaciones, () => setArticulaciones(null));
    apiMoto.ensamblaje().then((e) => setParametrosEns(e.parametros), () => setParametrosEns(null));
    apiMoto.fichaMoto(ID_FICHA).then(setFicha, (e: Error) => setErrorFicha(e.message));
    apiMoto.faqModelo(ID_FICHA).then(setFaqModelo, (e: Error) => setErrorFaqModelo(e.message));
    apiMoto.faqVisor().then(setFaqVisor, (e: Error) => {
      if (e.message.startsWith("HTTP 404")) setFaltaFaq(true);
      else setErrorFaqVisor(e.message);
    });
  }, []);

  /* ---------- controles (la referencia es la fuente para el bucle de animación) ---------- */
  const [modeloSel, setModeloSel] = useState<ModeloSel>("generica");
  const [ctl, setCtl] = useState<Ctl>(CTL0);
  const ctlRef = useRef<Ctl>(CTL0);
  const conFicha = modeloSel !== "generica";
  const version = MODELOS[modeloSel].version;
  const ajuste = useMemo(() => (conFicha ? ajusteDesdeFicha(ficha?.grupos, ficha?.por_version, version) : null), [conFicha, ficha, version]);
  const medida = ajuste?.medidaLlanta ?? null;
  // El CBS solo se habilita si la ficha publicada lo incluye (con la ficha sin cargar o no publicado: no).
  const cbsDisponible = conFicha ? ajuste?.cbsDisponible === true : true;
  const traseroGenerico = !conFicha || ajuste?.traseroPublicado !== true;
  const mandoDe = useCallback(
    (c: Ctl): MandoMoto => ({ version, acelerador: c.acelerador, marcha: c.marcha, palanca: c.palanca, fuerza_palanca_n: c.fuerza, cbs: c.cbs && cbsDisponible, freno: c.freno }),
    [version, cbsDisponible],
  );
  const mando = useMemo(() => mandoDe(ctl), [mandoDe, ctl]);

  /* ---------- vista ---------- */
  const [corriendo, setCorriendo] = useState(true);
  const [escala, setEscala] = useState(1);
  const [factorLento, setFactorLento] = useState<number>(FACTOR_LENTO_DEFECTO);
  const [despieceOn, setDespieceOn] = useState(false);
  const [corte, setCorte] = useState(false);
  const [etiquetas, setEtiquetas] = useState(true);
  const [autoGiro, setAutoGiro] = useState(false);
  const [transparencia, setTransparencia] = useState(0);
  const [seleccion, setSeleccion] = useState<string | null>(null);
  const [resaltadas, setResaltadas] = useState<Set<string>>(new Set());
  const [campoSel, setCampoSel] = useState<string | null>(null);
  const [aislado, setAislado] = useState<string | null>(null);
  const [pestIzq, setPestIzq] = useState<string | null>("vivo");
  const [pestDer, setPestDer] = useState<string | null>("ficha");
  const [cajon, setCajon] = useState<"izq" | "der" | null>(null);
  const [snap, setSnap] = useState<Instantanea>(INST0);
  const [pasoSec, setPasoSec] = useState(-1);
  const [secActiva, setSecActiva] = useState(false);
  const [verificacion, setVerificacion] = useState<string | null>(null);
  const [calidad, setCalidad] = useState<Calidad>("ligera");
  const [ssao, setSsao] = useState(!/[?&]ssao=0/.test(window.location.hash));
  const [avisoFreno, setAvisoFreno] = useState<string | null>(null);
  const controles = useRef<OrbitControlsImpl | null>(null);
  const divsEtiqueta = useRef<Record<string, HTMLDivElement | null>>({});
  const etiquetasVisibles = useRef(true);
  etiquetasVisibles.current = etiquetas;

  const escena = useRef<EstadoMoto>({
    despiece: {},
    theta720: 0,
    ciclo: 0,
    angRuedaTras: 0,
    angRuedaDel: 0,
    angPinon: 0,
    cadenaS: 0,
    compresionHorquilla: 0,
    escalaLlantaTrasera: 1,
    elevacionTrasera: 0,
    motorEnMarcha: true,
    estadoMotor: "neutro",
    seleccion: null,
    resaltadas: new Set(),
    alerta: new Set(),
    ocultas: new Set(),
    subconjuntoAislado: null,
    subconjuntoDe: {},
    tipoDe: {},
    enfoque: null,
    transparencia: 0,
    autoGiro: false,
    camara: null,
    geom: GEOMETRIA_MOVIL_DEFECTO,
    giraTrasera: new Set(["rin_trasero", "llanta_trasera", "cubo_trasero", "disco_trasero", "corona"]),
    giraDelantera: new Set(["rin_delantero", "llanta_delantera", "cubo_delantero", "disco_delantero"]),
    grupoHorquilla: new Set(["botella_izquierda", "botella_derecha", "cubo_delantero", "rin_delantero", "llanta_delantera", "disco_delantero", "caliper_delantero"]),
  });
  const lineas = useRef<Record<string, { linea: SVGLineElement | null; punto: SVGCircleElement | null }>>({});
  // Ejes, orígenes y conjuntos solidarios se derivan de las articulaciones y del árbol `montada_en` (no hay ids fijos).
  const geom: GeometriaMovil = useMemo(() => geometriaMovil(articulaciones, parametrosEns), [articulaciones, parametrosEns]);
  const conjuntos = useMemo(() => {
    const sigue = (maestra: string) =>
      new Set((articulaciones ?? []).filter((a) => a.id === maestra || a.maestra === maestra).filter((a) => a.relacion === null || a.relacion === 1).map((a) => a.hijo));
    const trasera = sigue("j_rueda_trasera");
    const delantera = sigue("j_rueda_delantera");
    const horquilla = new Set(["botella_izquierda", "botella_derecha"]);
    let crece = true;
    while (crece) {
      crece = false;
      for (const p of piezas) {
        const madre = p.metadatos?.montada_en;
        if (madre && horquilla.has(madre) && !horquilla.has(p.id)) {
          horquilla.add(p.id);
          crece = true;
        }
      }
    }
    return { trasera, delantera, horquilla };
  }, [articulaciones, piezas]);
  const subconjuntoDe = useMemo(() => Object.fromEntries(piezas.map((p) => [p.id, p.subconjunto])), [piezas]);
  const enfoque = useMemo(() => (corte ? new Set(piezas.filter((p) => p.subconjunto === "motor" || PIEZAS_MOTOR.has(p.id)).map((p) => p.id)) : null), [corte, piezas]);
  const radioTrasero = radioLlantaM(medida ?? String(SUPUESTOS.medida_llanta_trasera.valor));
  const tipoDe = useMemo(() => Object.fromEntries(piezas.map((p) => [p.id, p.tipo])), [piezas]);
  Object.assign(escena.current, {
    geom,
    tipoDe,
    ...(articulaciones && conjuntos.trasera.size > 0 ? { giraTrasera: conjuntos.trasera, giraDelantera: conjuntos.delantera } : {}),
    ...(piezas.length > 0 ? { grupoHorquilla: conjuntos.horquilla } : {}),
    seleccion,
    resaltadas,
    subconjuntoAislado: aislado,
    subconjuntoDe,
    enfoque,
    transparencia,
    autoGiro,
    escalaLlantaTrasera: radioTrasero / RADIO_BASE_TRASERO, // el GLB base lleva la llanta genérica 130/70-17
    elevacionTrasera: radioTrasero - RADIO_BASE_TRASERO,
  });

  /* ---------- reloj de simulación y bucle (refs mutables; React se actualiza cada ~100 ms) ---------- */
  const reloj = useRef({
    t: 0,
    est: ESTADO_DINAMICO_INICIAL as EstadoDinamico,
    theta720: 0,
    ciclo: 0,
    chispas: 0,
    angTras: 0,
    angDel: 0,
    angPin: 0,
    cadenaS: 0,
    comp: 0,
    despT: 0,
    v0Freno: 0,
    sec: { activa: false, t: 0, paso: -1 },
    wTras: 0,
    wPinon: 0,
    vCadena: 0,
  });
  const vivo = useRef({ corriendo, escala, factorLento, mandoDe, medida, despieceOn, grupoDe: {} as Record<string, number>, nGrupos: 0, acciones: [] as (() => void)[], tiempos: [] as number[] });
  vivo.current.corriendo = corriendo;
  vivo.current.escala = escala;
  vivo.current.factorLento = factorLento;
  vivo.current.mandoDe = mandoDe;
  vivo.current.medida = medida;
  vivo.current.despieceOn = despieceOn;

  // Grupos de despiece por ensamblaje, en el orden de desmontaje que calcula el backend.
  useEffect(() => {
    if (!animacion || piezas.length === 0) return;
    const orden: string[] = [];
    const grupoDe: Record<string, number> = {};
    for (const id of animacion.orden_desmontaje) {
      const sub = subconjuntoDe[id] ?? id;
      if (!orden.includes(sub)) orden.push(sub);
      grupoDe[id] = orden.indexOf(sub);
    }
    vivo.current.grupoDe = grupoDe;
    vivo.current.nGrupos = orden.length;
  }, [animacion, piezas, subconjuntoDe]);

  const instantanea = useCallback((): Instantanea => {
    const rl = reloj.current;
    return { theta720: rl.theta720, est: rl.est, wTras: rl.wTras, wPinon: rl.wPinon, vCadena: rl.vCadena, despiece: snapDespiece.current, chispas: rl.chispas, ciclos: rl.ciclo };
  }, []);
  const snapDespiece = useRef(0);

  /** Aplica un cambio de mandos o de estado al instante (dt = 0): cambian las rpm, nunca la velocidad. */
  const refrescar = useCallback(() => {
    const v = vivo.current;
    const rl = reloj.current;
    rl.est = pasoMoto(rl.est, v.mandoDe(ctlRef.current), 0, v.medida);
    const r = rl.est.v_ms / radioLlantaM(v.medida ?? String(SUPUESTOS.medida_llanta_trasera.valor));
    rl.wTras = r;
    rl.wPinon = r * FINAL;
    rl.vCadena = r * FINAL * RADIO_PINON_M;
    setSnap(instantanea());
  }, [instantanea]);

  const fijarCtl = useCallback(
    (p: Partial<Ctl>) => {
      ctlRef.current = { ...ctlRef.current, ...p };
      const rl = reloj.current;
      if (ctlRef.current.freno && (p.fuerza !== undefined || p.palanca !== undefined || p.cbs !== undefined)) {
        rl.v0Freno = rl.est.v_ms; // la nueva fuerza parte de la velocidad actual (sin saltos)
        rl.est = { ...rl.est, t_freno_s: 0 };
      }
      setCtl(ctlRef.current);
      refrescar();
    },
    [refrescar],
  );
  const fijarEstado = useCallback(
    (p: Partial<EstadoDinamico>) => {
      reloj.current.est = { ...reloj.current.est, ...p };
      refrescar();
    },
    [refrescar],
  );
  const iniciarFreno = useCallback(() => {
    const rl = reloj.current;
    if (ctlRef.current.fuerza <= 0) {
      setAvisoFreno("La palanca estaba en 0 N: se aplicaron 160 N (fuerza mínima visible).");
      ctlRef.current = { ...ctlRef.current, fuerza: 160 };
    } else setAvisoFreno(null);
    rl.v0Freno = rl.est.v_ms;
    rl.est = { ...rl.est, t_freno_s: 0 };
    ctlRef.current = { ...ctlRef.current, freno: true };
    setCtl(ctlRef.current);
    refrescar();
    apiMoto.evento("frenado", null, { palanca: ctlRef.current.palanca, v0_kmh: rl.est.v_ms * 3.6 });
  }, [refrescar]);
  const soltarFreno = useCallback(() => {
    // Se suelta el embrague con la velocidad actual: las rpm se derivan de ella (patina o se ahoga según la marcha).
    ctlRef.current = { ...ctlRef.current, freno: false };
    setCtl(ctlRef.current);
    refrescar();
  }, [refrescar]);
  const irACamara = useCallback((clave: string) => {
    const c = CAMARAS[clave];
    const peticion: PeticionCamara = { id: Date.now() + Math.random(), pos: c.pos, objetivo: c.objetivo };
    escena.current.camara = peticion;
  }, []);
  const reiniciar = useCallback((conservarSecuencia = false) => {
    const r = reloj.current;
    const sec = conservarSecuencia ? r.sec : { activa: false, t: 0, paso: -1 };
    Object.assign(r, { t: 0, est: ESTADO_DINAMICO_INICIAL, theta720: 0, ciclo: 0, chispas: 0, angTras: 0, angDel: 0, angPin: 0, cadenaS: 0, comp: 0, despT: 0, v0Freno: 0, sec, wTras: 0, wPinon: 0, vCadena: 0 });
    ctlRef.current = CTL0;
    setCtl(CTL0);
    setDespieceOn(false);
    setCorte(false);
    if (!conservarSecuencia) {
      setSecActiva(false);
      setPasoSec(-1);
    }
    setAvisoFreno(null);
    setSnap(INST0);
  }, []);

  // Secuencia: arranque → acelerar → cambiar marcha → frenar con CBS → despiece (sin saltos de velocidad).
  const acciones = useMemo(
    () => [
      () => {
        reiniciar(true);
        irACamara("general");
      },
      () => fijarCtl({ marcha: 1, acelerador: 1 }),
      () => fijarCtl({ marcha: 3, acelerador: 0.8 }),
      () => {
        setModeloSel("dlx");
        fijarCtl({ palanca: "trasera", cbs: true, fuerza: 180, acelerador: 0 });
        irACamara("frenos");
        window.setTimeout(iniciarFreno, 0);
      },
      () => {
        soltarFreno();
        fijarCtl({ marcha: 0, acelerador: 0, fuerza: 0 });
        setDespieceOn(true);
        irACamara("despiece");
      },
    ],
    [fijarCtl, iniciarFreno, soltarFreno, irACamara, reiniciar],
  );
  vivo.current.acciones = acciones;
  vivo.current.tiempos = [0, 4, 9, 14, 22];
  const TOTAL_SEC = 29;

  useEffect(() => {
    let id = 0;
    let previo = performance.now();
    let aviso = 0;
    const ciclo = (ahora: number) => {
      const dtReal = Math.min(Math.max((ahora - previo) / 1000, 0), 0.1);
      previo = ahora;
      const v = vivo.current;
      const e = escena.current;
      const rl = reloj.current;
      const dt = v.corriendo ? dtReal * v.escala : 0;
      rl.t += dt;

      // secuencia por pasos
      if (rl.sec.activa && dt > 0) {
        rl.sec.t += dt;
        let idx = -1;
        v.tiempos.forEach((tt, i) => {
          if (tt <= rl.sec.t) idx = i;
        });
        if (idx > rl.sec.paso) {
          rl.sec.paso = idx;
          v.acciones[idx]?.();
          setPasoSec(idx);
        }
        if (rl.sec.t >= TOTAL_SEC) {
          rl.sec.activa = false;
          setSecActiva(false);
        }
      }

      const c = ctlRef.current;
      const m = v.mandoDe(c);
      rl.est = pasoMoto(rl.est, m, dt, v.medida);
      const est = rl.est;
      const K = v.factorLento;
      const radioT = radioLlantaM(v.medida ?? String(SUPUESTOS.medida_llanta_trasera.valor));
      const frenando = m.freno && m.fuerza_palanca_n > 0;
      let wTras = est.v_ms / radioT;
      let wDel = est.v_ms / RADIO_DELANTERA_M;
      if (frenando) {
        // Rueda bloqueada (modelo sin ABS): gira según `estadoRueda` y se detiene antes que la moto.
        const fs = frenosMoto(m, v.medida, rl.v0Freno * 3.6);
        const bloqueada = (f: typeof fs.delantero, w: number) => (f && f.resultado.rueda_bloqueada ? Math.min(estadoRueda(f.entrada, f.resultado, est.t_freno_s).w, w) : w);
        wTras = bloqueada(fs.trasero, wTras);
        wDel = bloqueada(fs.delantero, wDel);
      }
      const wPinon = (est.v_ms / radioT) * FINAL; // ω_piñón = ω_corona · i_final (corona = rueda trasera)
      const vCadena = wPinon * RADIO_PINON_M; // v = ω_piñón · r_piñón (= ω_corona · r_corona)
      rl.wTras = wTras;
      rl.wPinon = wPinon;
      rl.vCadena = vCadena;

      // cigüeñal: θ de 0 a 720° (el ciclo completo); la chispa salta al cruzar los 360° (PMS de la compresión)
      const previoTheta = rl.theta720;
      let theta = previoTheta + (((velocidadAngularRadS(est.rpm_motor) / K) * dt * 180) / Math.PI);
      if (previoTheta < 360 && theta >= 360 && chispaPermitida(est.modo, rl.ciclo)) rl.chispas += 1;
      if (theta >= 720) {
        theta %= 720;
        rl.ciclo += 1;
      }
      rl.theta720 = theta;
      rl.angTras -= (wTras / K) * dt;
      rl.angDel -= (wDel / K) * dt;
      rl.angPin -= (wPinon / K) * dt;
      rl.cadenaS += (vCadena / K) * dt;
      const objetivoComp = frenando && est.v_ms > 0 ? 0.07 * clamp01(-est.a_ms2 / (0.9 * G)) : 0;
      rl.comp += (objetivoComp - rl.comp) * (1 - Math.exp(-dt * 6));

      // despiece animado por ensamblaje
      const dGrupo = 1.0;
      const paso = dGrupo * 0.5;
      const total = paso * Math.max(v.nGrupos - 1, 0) + dGrupo;
      rl.despT = Math.min(Math.max(rl.despT + (v.despieceOn ? dt : -dt), 0), total);
      for (const [pid, gi] of Object.entries(v.grupoDe)) e.despiece[pid] = suave(clamp01((rl.despT - gi * paso) / dGrupo));
      snapDespiece.current = total > 0 ? rl.despT / total : 0;

      Object.assign(e, {
        theta720: rl.theta720,
        ciclo: rl.ciclo,
        angRuedaTras: rl.angTras,
        angRuedaDel: rl.angDel,
        angPinon: rl.angPin,
        cadenaS: rl.cadenaS,
        compresionHorquilla: rl.comp,
        motorEnMarcha: est.rpm_motor > 0,
        estadoMotor: est.modo,
      });
      e.alerta.clear();
      if (frenando && est.v_ms > 0) {
        const fs = frenosMoto(m, v.medida, rl.v0Freno * 3.6);
        if (fs.delantero?.resultado.rueda_bloqueada) ["disco_delantero", "llanta_delantera", "caliper_delantero"].forEach((p) => e.alerta.add(p));
        if (fs.trasero?.resultado.rueda_bloqueada) ["disco_trasero", "llanta_trasera", "caliper_trasero"].forEach((p) => e.alerta.add(p));
      }
      if (est.modo === "limitador") e.alerta.add("bujia");
      if (est.modo === "ahogado") e.alerta.add("ciguenal");

      if (ahora - aviso > 100) {
        aviso = ahora;
        setSnap({ theta720: rl.theta720, est, wTras, wPinon, vCadena, despiece: snapDespiece.current, chispas: rl.chispas, ciclos: rl.ciclo });
      }
      id = requestAnimationFrame(ciclo);
    };
    id = requestAnimationFrame(ciclo);
    return () => cancelAnimationFrame(id);
  }, []);

  const reproducirSecuencia = useCallback((desde = 0) => {
    const sec = reloj.current.sec;
    sec.activa = true;
    sec.t = vivo.current.tiempos[desde] ?? 0;
    sec.paso = desde - 1;
    setSecActiva(true);
    setCorriendo(true);
  }, []);
  const pausarSecuencia = () => {
    reloj.current.sec.activa = false;
    setSecActiva(false);
  };

  /* ---------- lecturas derivadas del ESTADO (velocidad y rpm no se recalculan de golpe) ---------- */
  const est = snap.est;
  const resultado = useMemo(() => calcularMotoDesdeEstado(est, mando, medida), [est, mando, medida]);
  const g = ctl.marcha >= 1 ? (SUPUESTOS.relaciones_marcha.valor as number[])[ctl.marcha - 1] : null;
  const vKmh = est.v_ms * 3.6;
  const frenando = ctl.freno && ctl.fuerza > 0;
  const embrague = frenando ? "accionado" : est.modo === "patinaje" ? "patinando" : ctl.marcha === 0 ? "—" : "acoplado";
  const enDespiece = despieceOn && snap.despiece > 0.02;
  const estadoTexto = enDespiece
    ? "DESPIECE"
    : frenando
      ? est.v_ms > 0
        ? "FRENANDO"
        : "DETENIDA"
      : !corriendo
        ? "PAUSA"
        : est.modo === "ahogado"
          ? "MOTOR AHOGADO"
          : est.modo === "limitador"
            ? "LIMITADOR"
            : est.rpm_motor <= 0
              ? "MOTOR APAGADO"
              : "EN MARCHA";
  const wCorona = snap.wTras;
  const wPinon = snap.wPinon;
  const vCadenaPinon = wPinon * RADIO_PINON_M;
  const vCadenaCorona = wCorona * RADIO_CORONA_M;
  const carrera = GEOMETRIA_MOTOR.carreraM;
  const biela = GEOMETRIA_MOTOR.bielaM;
  const thetaRad = (snap.theta720 * Math.PI) / 180;
  const faseActual = faseCiclo(snap.theta720);
  const xPiston = (posicionPistonM(thetaRad, carrera, biela) - posicionPistonM(0, carrera, biela)) * 1000;
  const phiGrados = (anguloBielaRad(thetaRad, carrera, biela) * 180) / Math.PI;
  const fd = resultado.freno_delantero;
  const ft = resultado.freno_trasero;
  const bloqueoDel = resultado.rueda_delantera_bloqueada;
  const bloqueoTras = resultado.rueda_trasera_bloqueada;
  const hayBloqueo = bloqueoDel || bloqueoTras;
  // Con la palanca cargada y sin frenar, F/T/bloqueo son «previstos»; solo con el freno activo son reales.
  const textoDisco = (f: typeof fd, bloqueada: boolean, lado: string) => {
    if (!f) return `${lado}: sin accionar`;
    const base = `F ${fmt(f.fuerza_piston_n / 1000, 2)} kN · T ${fmt(f.par_frenado_nm)} N·m`;
    if (!frenando) return `${lado}: previsto ${base}${bloqueada ? " · bloqueo previsto" : ""}`;
    return `${lado}: ${base}${bloqueada ? " · BLOQUEADA" : ""}`;
  };
  const textoLeccion = ctl.marcha === 0 ? "sin tracción (neutro)" : resultado.relacion_total === null ? "—" : fmt(resultado.relacion_total, 2);

  /* ---------- verificación contra la API (el backend valida; el visor contrasta la fórmula de la lección) ---------- */
  const rpmRedondeada = Math.round(est.rpm_motor / 100) * 100;
  const claveVerificacion = `${modeloSel}|${ctl.marcha}|${ctl.palanca}|${ctl.fuerza}|${ctl.cbs && cbsDisponible}|${rpmRedondeada}`;
  useEffect(() => {
    const entrada = { ...ENTRADA_MOTO_DEFECTO, version, rpm: rpmRedondeada, marcha: ctl.marcha, palanca: ctl.palanca, fuerza_palanca_n: ctl.fuerza, cbs: ctl.cbs && cbsDisponible };
    const local = calcularMoto(entrada, medida);
    const temporizador = window.setTimeout(() => {
      apiMoto.calculoMoto(ID_FICHA, entrada, conFicha).then(
        (r) => {
          const dif = Math.abs(r.resultado.velocidad_kmh - local.velocidad_kmh);
          setVerificacion(
            dif < 1e-3
              ? `API verificada: a ${fmt(rpmRedondeada)} rpm la fórmula v = rpm·2πR/i da ${fmt(r.resultado.velocidad_kmh, 1)} km/h, igual al cálculo local`
              : `La API difiere del cálculo local (Δ ${fmt(dif, 3)} km/h)`,
          );
        },
        (e: Error) => setVerificacion(`API sin verificar: ${e.message}`),
      );
    }, 400);
    return () => window.clearTimeout(temporizador);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [claveVerificacion, conFicha, medida]);

  /* ---------- selección y resaltado ---------- */
  const seleccionar = useCallback((id: string | null) => {
    setSeleccion(id);
    if (id) apiMoto.evento("seleccion", id);
  }, []);
  const resaltarCampo = useCallback((ruta: string) => {
    setCampoSel((prev) => {
      const nuevo = prev === ruta ? null : ruta;
      setResaltadas(new Set(nuevo ? piezasDeCampo(nuevo) : []));
      return nuevo;
    });
  }, []);
  const resaltarCampos = useCallback((rutas: string[] | null) => {
    setCampoSel(null);
    setResaltadas(new Set(rutas ? rutas.flatMap(piezasDeCampo) : []));
  }, []);

  const preguntarEnVivo = (pregunta: string) => {
    setEnVivo({ respuesta: null, error: null, consultando: true });
    apiMoto.qa(pregunta).then(
      (r) => setEnVivo({ respuesta: r, error: null, consultando: false }),
      (e: Error) => setEnVivo({ respuesta: null, error: e.message, consultando: false }),
    );
  };

  const captura = () => {
    const lienzo = document.querySelector<HTMLCanvasElement>(".escenario canvas");
    if (!lienzo) return;
    const a = document.createElement("a");
    a.href = lienzo.toDataURL("image/png");
    a.download = `moto_honda_${Date.now()}.png`;
    a.click();
    apiMoto.evento("captura", seleccion, { modelo: modeloSel });
  };

  /* ---------- modo experimento: romper la regla ---------- */
  const vCorte3 = velocidadMsEnCorte(radioTrasero, PRIMARIA, (SUPUESTOS.relaciones_marcha.valor as number[])[2], FINAL) * 3.6;
  const rBloq = calcularMoto({ ...ENTRADA_MOTO_DEFECTO, rpm: 5000, marcha: 3, palanca: "delantera", fuerza_palanca_n: 400, velocidad_inicial_kmh: 41 }, medida);
  const rSuave = calcularMoto({ ...ENTRADA_MOTO_DEFECTO, rpm: 5000, marcha: 3, palanca: "delantera", fuerza_palanca_n: 100, velocidad_inicial_kmh: 41 }, medida);
  const experimentos: Experimento[] = [
    {
      pregunta: `En 3.ª, con el acelerador a fondo desde 72 km/h, ¿qué ocurre al llegar al corte de ${fmt(CORTE)} rpm?`,
      opciones: [
        { texto: "La velocidad sigue aumentando sin límite", correcta: false },
        { texto: "La velocidad se estabiliza: el limitador corta la chispa", correcta: true },
        { texto: "El motor se ahoga", correcta: false },
      ],
      explicacion: `Con marcha engranada las rpm se derivan de la velocidad (rpm = v·i_total). Al acercarse al corte (${fmt(CORTE)} rpm, ${ETIQUETA_SUPUESTO}) el limitador corta la chispa en ciclos alternos y la aceleración se anula: en 3.ª la velocidad se estabiliza en ${fmt(vCorte3, 1)} km/h.`,
      aplicar: () => {
        ctlRef.current = { ...ctlRef.current, freno: false };
        fijarCtl({ marcha: 3, acelerador: 1, fuerza: 0 });
        fijarEstado({ v_ms: 20 });
      },
    },
    {
      pregunta: "Con 5.ª engranada a unos 11 km/h y sin acelerar, ¿qué ocurre?",
      opciones: [
        { texto: "El motor se ahoga: las rpm derivadas caen bajo el ralentí", correcta: true },
        { texto: "El embrague patina y la moto sigue acelerando", correcta: false },
        { texto: "El limitador sube las rpm", correcta: false },
      ],
      explicacion: `A 11 km/h en 5.ª las rpm derivadas (v·i_total) quedan por debajo del ralentí (${fmt(RALENTI)} rpm, ${ETIQUETA_SUPUESTO}); con marcha alta y poco acelerador el motor se ahoga y la moto solo rueda por inercia. En marchas bajas el embrague patina (arranque).`,
      aplicar: () => {
        ctlRef.current = { ...ctlRef.current, freno: false };
        fijarCtl({ marcha: 5, acelerador: 0, fuerza: 0 });
        fijarEstado({ v_ms: 3 });
      },
    },
    {
      pregunta: "Palanca delantera con 400 N y sin CBS a unos 41 km/h, ¿qué le ocurre a la rueda delantera?",
      opciones: [
        { texto: "Se bloquea (modelo sin ABS)", correcta: true },
        { texto: "Frena sin bloquearse", correcta: false },
        { texto: "Se detiene tras exactamente 1 s", correcta: false },
      ],
      explicacion: `Con 400 N el disco entrega T = ${fmt(rBloq.freno_delantero?.par_frenado_nm ?? 0)} N·m y la deceleración pedida (${fmt(rBloq.freno_delantero?.deceleracion_g ?? 0, 2)} g) supera la adherencia (${num("adherencia_neumatico")} g, ${ETIQUETA_SUPUESTO}): la rueda se bloquea y manda la adherencia. Con 100 N entrega ${fmt(rSuave.freno_delantero?.par_frenado_nm ?? 0)} N·m y no se bloquea.`,
      aplicar: () => {
        fijarCtl({ marcha: 3, acelerador: 0, palanca: "delantera", fuerza: 400, cbs: false });
        fijarEstado({ v_ms: 41 / 3.6 });
        window.setTimeout(iniciarFreno, 0);
      },
    },
  ];

  /* ---------- recorrido automático (< 30 s) ---------- */
  const pasosTour: PasoTour[] = [
    {
      en: 0,
      texto: "Motocicleta de referencia: el motor gira en ralentí a cámara lenta (1/200 de la velocidad real)",
      accion: () => {
        reiniciar();
        setCorriendo(true);
        setEscala(1);
        setModeloSel("generica");
        setPestIzq("vivo");
        setPestDer("ficha");
        irACamara("general");
      },
    },
    { en: 4, texto: "Acelerar en 1.ª: la aceleración sube la velocidad y las rpm se derivan de ella; piñón, cadena y rueda giran con la relación real", accion: () => { fijarCtl({ marcha: 1, acelerador: 1 }); irACamara("transmision"); } },
    { en: 9, texto: "Cambiar a 3.ª: la velocidad no salta, solo cambian las rpm (rueda = menor fracción de las vueltas del motor)", accion: () => { fijarCtl({ marcha: 3, acelerador: 0.8 }); irACamara("general"); } },
    {
      en: 13,
      texto: "Frenar con CBS: la palanca trasera reparte la presión entre ambos discos y el embrague se acciona",
      accion: () => {
        fijarCtl({ palanca: "trasera", cbs: true, fuerza: 180, acelerador: 0 });
        irACamara("frenos");
        window.setTimeout(iniciarFreno, 0);
      },
    },
    {
      en: 19,
      texto: "Despiece por ensamblaje: cada conjunto se separa en el orden calculado por el backend",
      accion: () => {
        soltarFreno();
        fijarCtl({ marcha: 0, acelerador: 0, fuerza: 0 });
        setDespieceOn(true);
        irACamara("despiece");
      },
    },
    {
      en: 23,
      texto: "Corte del motor: el pistón sube y baja con la biela-manivela; la chispa salta en la expansión",
      accion: () => {
        setDespieceOn(false);
        setCorte(true);
        irACamara("motor");
      },
    },
    { en: 27.5, texto: "Modelo demostrativo: parámetros con «supuesto didáctico»; la animación no valida propiedades mecánicas" },
  ];
  const banda = useTour(tour, pasosTour, 29);

  /* ---------- render ---------- */
  const pieza = piezas.find((p) => p.id === seleccion) ?? null;
  const grupos = jerarquia?.hijos ?? [];
  const piezasVisibles = piezas.filter((p) => aislado === null || p.subconjunto === aislado);
  const cambioMarcha = textoMarcha(ctl.marcha, resultado.relacion_total);
  const textoLlanta = medida ? `${resultado.medida_llanta} (ficha publicada)` : `${resultado.medida_llanta} (${ETIQUETA_SUPUESTO})`;
  const clasePestana = (lado: "izq" | "der") => `moto-columna ${lado}${cajon === lado ? " cajon-abierto" : ""}`;

  return (
    <div className="moto-lab" data-testid="moto-lab" data-modelo={modeloSel} data-resaltadas={[...resaltadas].sort().join(",")} data-chispas={snap.chispas} data-ciclos={snap.ciclos} data-modo-motor={est.modo}>
      <div className="moto-titulo">
        <a href="#/" className="volver">← Biblioteca</a>
        <p className="moto-pregunta">{PREGUNTA}</p>
        <span className="relacion">v = rpm·2π·R / (i_prim · i_marcha · i_final)</span>
        <InsigniaSupuesto texto={`parámetros de cálculo: ${ETIQUETA_SUPUESTO}`} />
      </div>
      {errorSim && <p className="aviso error">API del simulador: {errorSim}</p>}

      <header className="moto-cabecera" aria-label="Estado de la motocicleta">
        <div className="dato">
          <span className="rotulo">Modelo</span>
          <b data-testid="cab-nombre">{MODELOS[modeloSel].nombre}</b>
        </div>
        <div className="dato">
          <span className="rotulo">Versión</span>
          <b data-testid="cab-version">{modeloSel === "generica" ? "referencia" : version}</b>
        </div>
        <div className="dato estado">
          <span className="rotulo">Estado</span>
          <b data-testid="estado" className={estadoTexto === "FRENANDO" || estadoTexto === "MOTOR AHOGADO" || estadoTexto === "LIMITADOR" ? "alerta" : ""}>{estadoTexto}</b>
        </div>
        <div className="dato">
          <span className="rotulo">Embrague</span>
          <b data-testid="cab-embrague" className={frenando ? "alerta" : ""}>{embrague === "accionado" ? "EMBRAGUE accionado" : embrague}</b>
        </div>
        <div className="dato grande">
          <span className="rotulo">rpm</span>
          <b className="num" data-testid="cab-rpm">{fmt(est.rpm_motor)}</b>
        </div>
        <div className="dato grande">
          <span className="rotulo">Marcha</span>
          <b className="num" data-testid="cab-marcha">{ctl.marcha === 0 ? "N" : `${ctl.marcha}.ª`}</b>
        </div>
        <div className="dato grande">
          <span className="rotulo">Velocidad</span>
          <b className="num" data-testid="cab-velocidad">{fmt(vKmh, 1)} <small>km/h</small></b>
        </div>
        <div className="botones-cajon">
          <button className="boton secundario" onClick={() => setCajon(cajon === "izq" ? null : "izq")} aria-expanded={cajon === "izq"}>☰ Datos</button>
          <button className="boton secundario" onClick={() => setCajon(cajon === "der" ? null : "der")} aria-expanded={cajon === "der"}>Ficha ☰</button>
        </div>
      </header>

      <div className="moto-cuerpo">
        {/* ---------------- columna izquierda ---------------- */}
        <aside className={clasePestana("izq")} aria-label="Datos en vivo y FAQ de Fanalca">
          <Pestanas
            etiqueta="Panel izquierdo"
            pestanas={[
              { id: "vivo", titulo: "Datos en vivo" },
              { id: "fanalca", titulo: "FAQ Fanalca" },
              { id: "empresa", titulo: "Empresa" },
            ]}
            activa={pestIzq}
            alCambiar={setPestIzq}
          >
            {(act) =>
              act === "vivo" ? (
                <div className="datos-vivo">
                  <section aria-label="Motor">
                    <h4>Motor <InsigniaSupuesto /></h4>
                    <DiagramaCiclo theta720={snap.theta720} />
                    <dl className="lecturas-lista">
                      <dt>n del motor</dt>
                      <dd className="num">{fmt(est.rpm_motor)} rpm · {TEXTO_MODO[est.modo]}</dd>
                      <dt>θ cigüeñal</dt>
                      <dd className="num" data-testid="theta">{fmt(snap.theta720 % 360)}° (ciclo {fmt(snap.theta720)}° de 720°)</dd>
                      <dt>Fase 4T</dt>
                      <dd><b style={{ color: FASES_INFO[faseActual].color }}>{FASES_INFO[faseActual].nombre}</b></dd>
                      <dt>x pistón (desde el PMS)</dt>
                      <dd className="num">{fmt(xPiston, 1)} mm · carrera 2r = {fmt(carrera * 1000, 1)} mm</dd>
                      <dt>Biela φ = asin(r·sin θ / L)</dt>
                      <dd className="num">{fmt(phiGrados, 1)}°</dd>
                      <dt>Cilindrada V = π/4·D²·carrera</dt>
                      <dd className="num">calculada {fmt(resultado.cilindrada_calculada_cm3, 1)} cm³; 150 cm³ nominal — {ETIQUETA_SUPUESTO} ({fmt(resultado.diferencia_cilindrada_pct, 2)} %)</dd>
                      <dt>Chispa</dt>
                      <dd className="num">salta en el PMS de la compresión, sin avance de encendido (simplificación) · chispas {snap.chispas} de {snap.ciclos} ciclos</dd>
                      <dt>Cámara lenta</dt>
                      <dd className="num">giros a 1/{factorLento} de la velocidad real; dinámica del frenado en tiempo real ({escala}×)</dd>
                    </dl>
                  </section>
                  <section aria-label="Transmisión">
                    <h4>Transmisión <InsigniaSupuesto /></h4>
                    <dl className="lecturas-lista">
                      <dt>Relaciones</dt>
                      <dd className="num">primaria {fmt(PRIMARIA, 2)} · marcha {g === null ? "N" : fmt(g, 2)} · final {fmt(FINAL, 2)}</dd>
                      <dt>Relación total</dt>
                      <dd className="num">{textoLeccion}</dd>
                      <dt>ω piñón / ω corona</dt>
                      <dd className="num">{fmt(wPinon, 1)} / {fmt(wCorona, 1)} rad/s</dd>
                      <dt>Cadena v = ω·r (piñón)</dt>
                      <dd className="num" data-testid="v-cadena-pinon">{fmt(vCadenaPinon, 2)} m/s</dd>
                      <dt>Cadena v = ω·r (corona)</dt>
                      <dd className="num" data-testid="v-cadena-corona">{fmt(vCadenaCorona, 2)} m/s</dd>
                      <dt>Llanta trasera</dt>
                      <dd className="num">{textoLlanta}; R = {fmt(resultado.radio_llanta_m, 4)} m</dd>
                      <dt>Velocidad de la moto (estado)</dt>
                      <dd className="num">{fmt(vKmh, 1)} km/h{ctl.marcha === 0 && vKmh > 0 ? " · rueda libre: decae por rozamiento (supuesto didáctico)" : ""}</dd>
                      <dt>v según rpm y relación</dt>
                      <dd className="num">{ctl.marcha === 0 ? "— (sin tracción: neutro)" : est.modo === "patinaje" ? "no rige: el embrague patina" : est.modo === "embrague" ? "no rige: embrague accionado" : `${fmt(vKmh, 1)} km/h`}</dd>
                    </dl>
                    <p className="aviso">{cambioMarcha}</p>
                    {verificacion && <p className="aviso" data-testid="verificacion-api">{verificacion}</p>}
                  </section>
                  <section aria-label="Frenos">
                    <h4>Frenos <InsigniaSupuesto /></h4>
                    <dl className="lecturas-lista">
                      <dt>Disco delantero {frenando ? "" : "(previsto)"}</dt>
                      <dd className="num">{fd ? `F ${fmt(fd.fuerza_piston_n / 1000, 2)} kN · T ${fmt(fd.par_frenado_nm)} N·m · ${frenando ? (bloqueoDel ? "bloqueada" : "sin bloqueo") : bloqueoDel ? "bloqueo previsto" : "sin bloqueo previsto"}` : "sin accionar"}</dd>
                      <dt>Disco trasero {frenando ? "" : "(previsto)"}{traseroGenerico ? " — disco genérico, supuesto didáctico" : ""}</dt>
                      <dd className="num">{ft ? `F ${fmt(ft.fuerza_piston_n / 1000, 2)} kN · T ${fmt(ft.par_frenado_nm)} N·m · ${frenando ? (bloqueoTras ? "bloqueada" : "sin bloqueo") : bloqueoTras ? "bloqueo previsto" : "sin bloqueo previsto"}` : "sin accionar"}</dd>
                      <dt>Fuerza total de pistones</dt>
                      <dd className="num">{fmt(resultado.fuerza_pistones_total_n / 1000, 2)} kN {mando.cbs && "(suma conservada con CBS)"}</dd>
                      <dt>Deceleración de la moto</dt>
                      <dd className="num">{frenando ? `${fmt(-est.a_ms2, 2)} m/s² (${fmt(-est.a_ms2 / G, 2)} g)` : "—"}</dd>
                    </dl>
                    <p className="aviso">Los discos usan un radio efectivo supuesto de {fmt(num("radio_efectivo_m"), 2)} m ({ETIQUETA_SUPUESTO}); la rueda delantera usa su propio radio ({MEDIDA_DELANTERA_DEMO}, supuesto).</p>
                  </section>
                  <details>
                    <summary>Parámetros de cálculo ({ETIQUETA_SUPUESTO})</summary>
                    <ul className="datos" data-testid="lista-supuestos">
                      {Object.values(SUPUESTOS).map((s) => (
                        <li key={s.clave}>
                          <InsigniaSupuesto /> <code>{s.clave}</code> = <b className="num">{Array.isArray(s.valor) ? s.valor.join(" · ") : String(s.valor)}</b> {s.unidad}
                          <br />
                          <span className="fecha">{s.descripcion}</span>
                        </li>
                      ))}
                    </ul>
                  </details>
                </div>
              ) : act === "fanalca" ? (
                <FaqFanalca datos={faqVisor} error={errorFaqVisor} faltaArchivo={faltaFaq} enVivo={enVivo} alPreguntar={preguntarEnVivo} />
              ) : (
                <PanelEmpresa maquina={maquina} error={error} />
              )
            }
          </Pestanas>
        </aside>

        {/* ---------------- centro ---------------- */}
        <section className="moto-centro" aria-label="Motocicleta en 3D">
          <div className="escenario moto-escenario" data-testid="escenario-moto" data-modo={estadoTexto} data-calidad={calidad}>
            <div className="superpuesto" role="toolbar" aria-label="Reproducción y vista">
              <Reproduccion corriendo={corriendo} alCorrer={() => setCorriendo(true)} alPausar={() => setCorriendo(false)} alReiniciar={() => reiniciar()} escala={escala} alEscala={setEscala} />
            </div>
            <div className="lento" role="status">
              <label>
                Cámara lenta del motor
                <select aria-label="Factor de cámara lenta" value={factorLento} onChange={(e) => setFactorLento(Number(e.target.value))}>
                  {FACTORES_LENTO.map((f) => (
                    <option key={f} value={f}>1/{f}</option>
                  ))}
                </select>
              </label>
              <b data-testid="escala-lenta">animación a 1/{factorLento} de la velocidad real</b>
              <small>giros a 1/{factorLento}; dinámica del frenado en tiempo real ({escala}×)</small>
            </div>
            <EscenaMoto estado={escena} geometria={geometria} alSeleccionar={seleccionar} etiquetas={divsEtiqueta} lineas={lineas} etiquetasVisibles={etiquetasVisibles} controles={controles} ssao={ssao} alCalidad={setCalidad} />
            <svg className="guias-etiquetas" aria-hidden="true">
              {["motor", "cilindrada", "transmision", "rueda", "disco_del", "disco_tras"].map((k) => (
                <g key={k}>
                  <line
                    ref={(l) => {
                      lineas.current[k] = { ...(lineas.current[k] ?? { punto: null }), linea: l };
                    }}
                    data-guia={k}
                  />
                  <circle
                    ref={(c) => {
                      lineas.current[k] = { ...(lineas.current[k] ?? { linea: null }), punto: c };
                    }}
                    r="3.5"
                  />
                </g>
              ))}
            </svg>
            {(
              [
                ["motor", "etiqueta-3d", <>{fmt(est.rpm_motor)} rpm · θ {fmt(snap.theta720 % 360)}°<br />{FASES_INFO[faseActual].nombre} · 1/{factorLento} real</>],
                ["cilindrada", "etiqueta-3d fuerza", <>150 cm³ nominal — {ETIQUETA_SUPUESTO}<br />calculada {fmt(resultado.cilindrada_calculada_cm3, 1)} cm³</>],
                ["transmision", "etiqueta-3d movimiento", <>cadena {fmt(vCadenaPinon, 2)} m/s = ω·r<br />piñón {fmt(wPinon, 1)} rad/s</>],
                ["rueda", "etiqueta-3d movimiento", <>{ctl.marcha === 0 ? "neutro: sin tracción" : `i total ${fmt(resultado.relacion_total ?? 0, 2)}`} · {fmt(vKmh, 1)} km/h<br />ω rueda {fmt(wCorona, 1)} rad/s</>],
                ["disco_del", `etiqueta-3d fuerza${frenando && bloqueoDel ? " alerta" : ""}`, <>{textoDisco(fd, bloqueoDel, "Del.")}</>],
                ["disco_tras", `etiqueta-3d fuerza${frenando && bloqueoTras ? " alerta" : ""}`, <>{textoDisco(ft, bloqueoTras, "Tras.")}{traseroGenerico && <><br /><small>disco genérico — supuesto didáctico</small></>}</>],
              ] as const
            ).map(([k, clase, contenido]) => (
              <div
                key={k}
                ref={(d) => {
                  divsEtiqueta.current[k] = d;
                }}
                className={`${clase} etiqueta-moto`}
                data-etiqueta={k}
                style={{ position: "absolute", left: 0, top: 0, zIndex: 2 }}
              >
                {contenido}
              </div>
            ))}
            <span className="leyenda-escena">geometría procedural demostrativa · arrastrar: orbitar · rueda: zoom · clic: seleccionar pieza</span>
            <BandaTour {...banda} />
          </div>

          <div className="moto-controles" role="group" aria-label="Controles">
            <section className="panel" aria-label="Modelo">
              <h3>Modelo</h3>
              <label className="selector">
                Ver con ficha de…
                <select
                  aria-label="Ver con ficha de…"
                  value={modeloSel}
                  onChange={(e) => {
                    const nuevo = e.target.value as ModeloSel;
                    setModeloSel(nuevo);
                    // El CBS no se reactiva solo al volver a la DLX: se apaga al pasar a un modelo sin CBS.
                    if (nuevo !== "dlx" && nuevo !== "generica") fijarCtl({ cbs: false });
                    apiMoto.evento("camara", null, { modelo: nuevo });
                  }}
                >
                  {(Object.keys(MODELOS) as ModeloSel[]).map((k) => (
                    <option key={k} value={k}>{MODELOS[k].etiqueta}</option>
                  ))}
                </select>
              </label>
              <p className="aviso" data-testid="nota-ficha">
                {conFicha
                  ? ajuste && ajuste.conservados.length > 0
                    ? `Aplica solo campos publicados (llanta trasera ${textoLlanta}). Conserva el valor genérico (${ETIQUETA_SUPUESTO}) en: ${ajuste.conservados.join(", ")}.`
                    : "Aplica los campos publicados de la ficha."
                  : `Genérica: todos los parámetros son ${ETIQUETA_SUPUESTO}; llanta trasera ${textoLlanta}.`}
              </p>
            </section>

            <section className="panel" aria-label="Motor y transmisión">
              <h3>Motor y transmisión</h3>
              <Deslizador
                etiqueta="Acelerador"
                valor={Math.round(ctl.acelerador * 100)}
                min={0}
                max={100}
                paso={5}
                unidad="%"
                alCambiar={(v) => fijarCtl({ acelerador: v / 100 })}
                formato={(v) => fmt(v)}
              />
              <p className="marcas-rpm">
                neutro: rpm libres ralentí {fmt(RALENTI)} → corte {fmt(CORTE)} · con marcha: a = k·acelerador ({fmt(num("aceleracion_max_m_s2"), 1)} m/s² a fondo) <InsigniaSupuesto />
              </p>
              <div className="marchas" role="radiogroup" aria-label="Marcha">
                {MARCHAS.map((m) => (
                  <button key={m} role="radio" aria-checked={ctl.marcha === m} data-marcha={m} className={`boton ${ctl.marcha === m ? "activo" : "secundario"}`} onClick={() => fijarCtl({ marcha: m })}>
                    {m === 0 ? "N" : m}
                  </button>
                ))}
              </div>
              <p className="aviso" data-testid="texto-marcha">{cambioMarcha}</p>
            </section>

            <section className="panel" aria-label="Freno">
              <h3>Freno</h3>
              <div className="barra" role="radiogroup" aria-label="Palanca de freno">
                {(["delantera", "trasera"] as const).map((p) => (
                  <button key={p} role="radio" aria-checked={ctl.palanca === p} data-palanca={p} className={`boton ${ctl.palanca === p ? "activo" : "secundario"}`} onClick={() => fijarCtl({ palanca: p })}>
                    Palanca {p}
                  </button>
                ))}
              </div>
              <Deslizador etiqueta="Fuerza en la palanca" valor={ctl.fuerza} min={LIMITES.fuerza[0]} max={LIMITES.fuerza[1]} paso={10} unidad="N" alCambiar={(v) => fijarCtl({ fuerza: v })} formato={(v) => fmt(v)} />
              <label className="cbs">
                <input type="checkbox" checked={ctl.cbs && cbsDisponible} disabled={!cbsDisponible} onChange={(e) => fijarCtl({ cbs: e.target.checked })} /> CBS (freno combinado)
              </label>
              <p className="marcas-rpm">
                {cbsDisponible ? `Reparto del CBS: ${fmt(num("reparto_cbs_delantero") * 100)} % delantero (${ETIQUETA_SUPUESTO})` : "CBS solo en la versión DLX según la lámina"}
                {traseroGenerico ? " · freno trasero: disco genérico — supuesto didáctico" : ""}
              </p>
              <div className="barra">
                {frenando ? (
                  <button className="boton activo" onClick={soltarFreno}>Soltar freno</button>
                ) : (
                  <button className="boton" onClick={iniciarFreno} disabled={est.v_ms <= 0} title={est.v_ms <= 0 ? "Engranar una marcha y acelerar para tener velocidad" : "Aplicar el freno"}>Frenar</button>
                )}
                <span className="aviso">{est.v_ms <= 0 && !frenando ? "Moto detenida: engranar y acelerar" : frenando ? `t = ${fmt(est.t_freno_s, 1)} s` : "Listo para frenar"}</span>
              </div>
              {avisoFreno && <p className="aviso" role="status" data-testid="aviso-freno">{avisoFreno}</p>}
            </section>
          </div>

          <ModoExperimento experimentos={experimentos} />
          <div className="lecturas" aria-label="Lecturas">
            <Chip etiqueta="R llanta" valor={`${fmt(resultado.radio_llanta_m, 4)} m`} />
            <Chip etiqueta="i total" valor={textoLeccion} />
            <Chip etiqueta="v" valor={`${fmt(vKmh, 1)} km/h`} tono="movimiento" />
            <Chip etiqueta={frenando ? "F pistones" : "F pistones (prevista)"} valor={`${fmt(resultado.fuerza_pistones_total_n / 1000, 2)} kN`} tono="fuerza" />
            {hayBloqueo && frenando ? (
              <Chip etiqueta="Estado" valor="rueda bloqueada (a > g·μ neumático)" tono="alerta" />
            ) : hayBloqueo ? (
              <Chip etiqueta="Estado" valor="bloqueo previsto (aún sin frenar)" tono="alerta" />
            ) : (
              <Chip etiqueta="Estado" valor="sin bloqueo" tono="correcto" />
            )}
            {est.modo === "limitador" && <Chip etiqueta="Motor" valor={`limitador: corta la chispa a ${fmt(CORTE)} rpm`} tono="alerta" />}
            {est.modo === "ahogado" && <Chip etiqueta="Motor" valor={`ahogado: rpm derivadas < ralentí ${fmt(RALENTI)} con marcha alta`} tono="alerta" />}
            {est.modo === "patinaje" && <Chip etiqueta="Embrague" valor="patinando (arranque): v ≠ fórmula" tono="alerta" />}
          </div>
        </section>

        {/* ---------------- columna derecha ---------------- */}
        <aside className={clasePestana("der")} aria-label="Ficha técnica, FAQ de modelos, ensamblajes y vista">
          <Pestanas
            etiqueta="Panel derecho"
            pestanas={[
              { id: "ficha", titulo: "Ficha técnica" },
              { id: "faq", titulo: "FAQ modelos" },
              { id: "ensamblajes", titulo: "Ensamblajes" },
              { id: "vista", titulo: "Vista" },
            ]}
            activa={pestDer}
            alCambiar={setPestDer}
          >
            {(act) =>
              act === "ficha" ? (
                <FichaTecnica ficha={ficha} error={errorFicha} seleccion={campoSel} alSeleccionar={resaltarCampo} />
              ) : act === "faq" ? (
                <FaqModelos items={faqModelo} error={errorFaqModelo} alAbrir={resaltarCampos} />
              ) : act === "ensamblajes" ? (
                <div>
                  <div className="chips-ensamblaje" role="group" aria-label="Aislar ensamblaje">
                    <button className={`chip-boton ${aislado === null ? "activo" : ""}`} aria-pressed={aislado === null} onClick={() => setAislado(null)}>Todo</button>
                    {grupos.map((gr) => (
                      <button key={gr.id} className={`chip-boton ${aislado === gr.id ? "activo" : ""}`} aria-pressed={aislado === gr.id} data-ensamblaje={gr.id} onClick={() => setAislado(aislado === gr.id ? null : gr.id)}>
                        {gr.nombre}
                      </button>
                    ))}
                  </div>
                  <ul className="lista-piezas" aria-label="Piezas">
                    {piezasVisibles.map((p) => (
                      <li key={p.id}>
                        <button className={seleccion === p.id ? "sel" : ""} data-pieza={p.id} onClick={() => seleccionar(seleccion === p.id ? null : p.id)}>
                          {p.nombre}
                        </button>
                      </li>
                    ))}
                  </ul>
                  <section className="panel ficha" aria-label="Pieza seleccionada">
                    <h3>Pieza seleccionada</h3>
                    {!pieza && <p className="aviso">Seleccionar una pieza en la escena o en la lista.</p>}
                    {pieza && (
                      <dl>
                        <dt>Pieza</dt>
                        <dd data-testid="ficha-nombre">{pieza.nombre}</dd>
                        <dt>Función</dt>
                        <dd>{pieza.funcion}</dd>
                        <dt>Ensamblaje</dt>
                        <dd>{pieza.subconjunto}</dd>
                        <dt>Procedencia</dt>
                        <dd><Insignia tipo="demostrativo" /> {pieza.referencia_documental}</dd>
                      </dl>
                    )}
                  </section>
                </div>
              ) : (
                <div className="vista">
                  <label className="cbs"><input type="checkbox" checked={etiquetas} onChange={(e) => setEtiquetas(e.target.checked)} /> Etiquetas con cifras</label>
                  <label className="cbs"><input type="checkbox" checked={despieceOn} onChange={(e) => { setDespieceOn(e.target.checked); irACamara(e.target.checked ? "despiece" : "general"); }} /> Despiece por ensamblaje</label>
                  <label className="cbs"><input type="checkbox" checked={corte} onChange={(e) => { setCorte(e.target.checked); if (e.target.checked) irACamara("motor"); }} /> Corte del motor</label>
                  <label className="cbs"><input type="checkbox" checked={ssao} disabled={calidad !== "alta"} onChange={(e) => setSsao(e.target.checked)} /> Oclusión ambiental (SSAO)</label>
                  <p className="aviso" data-testid="calidad-grafica">Calidad gráfica: {calidad === "alta" ? "alta (GPU: entorno de estudio con Lightformers y SSAO)" : "ligera (render por software: luces analíticas, sin SSAO)"}.</p>
                  <label className="cbs"><input type="checkbox" checked={autoGiro} onChange={(e) => setAutoGiro(e.target.checked)} /> Giro automático</label>
                  <Deslizador etiqueta="Transparencia" valor={transparencia} min={0} max={0.9} paso={0.05} unidad="" alCambiar={setTransparencia} formato={(v) => fmt(v, 2)} />
                  <h4>Cámara</h4>
                  <div className="barra">
                    {Object.entries(CAMARAS).map(([k, c]) => (
                      <button key={k} className="boton secundario" onClick={() => { irACamara(k); apiMoto.evento("camara", null, { vista: k }); }}>{c.nombre}</button>
                    ))}
                  </div>
                  <div className="barra" style={{ marginTop: 10 }}>
                    <button className="boton secundario" onClick={captura}>⤓ PNG</button>
                  </div>
                </div>
              )
            }
          </Pestanas>
          <RevisionCritica
            extra={[
              "Cada cifra indica su procedencia: ficha publicada, «No publicado» o supuesto didáctico",
              "Cámara lenta de los giros siempre visible (1/200 de la velocidad real por omisión)",
              "La velocidad es una variable de estado continua: al cambiar de marcha saltan las rpm, nunca la velocidad",
              "El piñón, la corona, la cadena y la rueda comparten la misma ω_corona·r_corona = ω_piñón·r_piñón",
              "Sin logotipos ni réplica de un modelo comercial; la lámina no se muestra",
            ]}
          />
        </aside>
      </div>
      {cajon && <button className="moto-velo" aria-label="Cerrar cajón" onClick={() => setCajon(null)} />}

      {/* ---------------- franja inferior: secuencia ---------------- */}
      <nav className="moto-secuencia" aria-label="Secuencia">
        <div className="barra">
          {secActiva ? (
            <button className="boton" onClick={pausarSecuencia}>❚❚ Pausar secuencia</button>
          ) : (
            <button className="boton" onClick={() => reproducirSecuencia(Math.max(pasoSec, 0))}>▶ Reproducir secuencia</button>
          )}
        </div>
        <ol className="pasos-secuencia">
          {["Arranque", "Acelerar", "Cambiar marcha", "Frenar con CBS", "Despiece"].map((t, i) => (
            <li key={t} className={i === pasoSec ? "actual" : i < pasoSec ? "hecho" : ""} aria-current={i === pasoSec ? "step" : undefined}>
              <button onClick={() => reproducirSecuencia(i)} data-paso={i}>
                <span className="n">{i + 1}</span>
                {t}
              </button>
            </li>
          ))}
        </ol>
      </nav>

      <p className="idea" data-testid="idea-principal">{FRASE_FINAL}</p>
      <p className="aviso" style={{ marginBottom: 8 }}>
        Modelo demostrativo: el embrague solo patina en el arranque (marchas bajas) y se acciona al frenar; la chispa salta en el PMS sin avance; los discos usan un radio efectivo supuesto; la animación no valida propiedades mecánicas. {NO_PUBLICADO}: dato sin fuente verificable.
      </p>
    </div>
  );
}
