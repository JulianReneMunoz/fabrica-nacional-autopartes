/**
 * Máquina 4 — Motocicleta de referencia genérica con fichas Honda (ADR-017).
 * Pregunta: ¿cómo convierte una motocicleta Honda el giro del motor en velocidad de la rueda,
 * y la palanca en fuerza de frenado?
 * Relaciones: v = rpm·2π·R·60 / (1000·i_prim·i_marcha·i_final);  x(θ) = r·cos θ + √(L² − r²·sin² θ);  T = 2·μ·p·A·r.
 *
 * Los parámetros de cálculo son «valores típicos de la categoría — supuesto didáctico» (modelos/moto.ts);
 * «Ver con ficha de…» aplica solo los campos `publicado` de la ficha curada. El modelo de freno
 * (`calcularFreno`, `estadoRueda`) se reutiliza de `modelos/freno.ts`. Todo giro se anima con un
 * factor de cámara lenta visible: el cigüeñal da cientos de vueltas por segundo en la realidad.
 */
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import * as THREE from "three";
import type { OrbitControls as OrbitControlsImpl } from "three-stdlib";
import { apiMoto, type Animacion, type FaqVisor, type FichaMotoApi, type NodoJerarquia, type Pieza, type RespuestaModeloApi, type RespuestaQa } from "../api";
import { BandaTour, Chip, Deslizador, Insignia, ModoExperimento, PanelEmpresa, Reproduccion, RevisionCritica, useMaquina, useTour, type Experimento, type PasoTour } from "../componentes/anatomia";
import {
  DiagramaCiclo,
  FaqFanalca,
  FaqModelos,
  FichaTecnica,
  fmt,
  InsigniaSupuesto,
  NO_PUBLICADO,
  Pestanas,
  piezasDeCampo,
} from "../componentes/panelesMoto";
import { estadoRueda } from "../modelos/freno";
import {
  ajusteDesdeFicha,
  anguloBielaRad,
  calcularMoto,
  ENTRADA_MOTO_DEFECTO,
  ETIQUETA_SUPUESTO,
  FACTOR_LENTO_DEFECTO,
  FACTORES_LENTO,
  FASES_INFO,
  faseCiclo,
  frenosMoto,
  GEOMETRIA_MOTOR,
  LIMITES,
  MEDIDA_DELANTERA_DEMO,
  posicionPistonM,
  RADIO_CORONA_M,
  RADIO_PINON_M,
  radioLlantaM,
  sanearEntrada,
  SUPUESTOS,
  textoMarcha,
  velocidadAngularRadS,
  type EntradaMoto,
  type FrenoRueda,
  type PalancaMoto,
  type VersionMoto,
} from "../modelos/moto";
import EscenaMoto, { type EstadoMoto, type GeometriaDespieceMoto, type PeticionCamara, type Vec3 } from "./EscenaMoto";

const ID_FICHA = "cb160f";
const G = 9.80665;
const RADIO_BASE_TRASERO = radioLlantaM(String(SUPUESTOS.medida_llanta_trasera.valor));
const RADIO_DELANTERA_M = radioLlantaM(MEDIDA_DELANTERA_DEMO);
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
  rpm: number;
  marcha: number;
  palanca: PalancaMoto;
  fuerza: number;
  cbs: boolean;
}
const CTL0: Ctl = { rpm: RALENTI, marcha: 0, palanca: "delantera", fuerza: 0, cbs: false };

const CAMARAS: Record<string, { pos: Vec3; objetivo: Vec3; nombre: string }> = {
  general: { nombre: "General", pos: [0.75, 0.75, 2.3], objetivo: [0.05, 0.42, 0] },
  motor: { nombre: "Motor", pos: [0.3, 0.5, 0.58], objetivo: [0, 0.43, 0] },
  despiece: { nombre: "Despiece", pos: [1.3, 0.95, 3.7], objetivo: [0.05, 0.5, 0] },
  transmision: { nombre: "Transmisión", pos: [-0.42, 0.48, 1.05], objetivo: [-0.42, 0.31, 0.06] },
  frenos: { nombre: "Frenos", pos: [0.1, 0.5, 2.35], objetivo: [0.05, 0.3, 0] },
};

const clamp01 = (x: number) => Math.min(Math.max(x, 0), 1);
const suave = (x: number) => x * x * (3 - 2 * x);
const lerp = (a: number, b: number, u: number) => a + (b - a) * u;

interface Instantanea {
  theta720: number;
  vKmh: number;
  wTras: number;
  wPinon: number;
  vCadena: number;
  aVeh: number;
  tFreno: number;
  rpmMotor: number;
  despiece: number;
  detenida: boolean;
}
const INST0: Instantanea = { theta720: 0, vKmh: 0, wTras: 0, wPinon: 0, vCadena: 0, aVeh: 0, tFreno: 0, rpmMotor: RALENTI, despiece: 0, detenida: false };

export default function MaquinaMoto({ tour }: { tour: boolean }) {
  const { maquina, error } = useMaquina("moto_honda");

  /* ---------- datos del simulador y de las fichas ---------- */
  const [piezas, setPiezas] = useState<Pieza[]>([]);
  const [jerarquia, setJerarquia] = useState<NodoJerarquia | null>(null);
  const [animacion, setAnimacion] = useState<Animacion | null>(null);
  const [geometria, setGeometria] = useState<GeometriaDespieceMoto | null>(null);
  const [errorSim, setErrorSim] = useState<string | null>(null);
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
  const cbsDisponible = conFicha ? ajuste?.cbsDisponible !== false : true;
  const entradaDe = useCallback(
    (c: Ctl): EntradaMoto =>
      sanearEntrada({ ...ENTRADA_MOTO_DEFECTO, version, rpm: c.rpm, marcha: c.marcha, palanca: c.palanca, fuerza_palanca_n: c.fuerza, cbs: c.cbs && cbsDisponible }),
    [version, cbsDisponible],
  );
  const entrada = useMemo(() => entradaDe(ctl), [entradaDe, ctl]);
  const resultado = useMemo(() => calcularMoto(entrada, medida), [entrada, medida]);

  /* ---------- vista ---------- */
  const [corriendo, setCorriendo] = useState(true);
  const [escala, setEscala] = useState(1);
  const [factorLento, setFactorLento] = useState<number>(FACTOR_LENTO_DEFECTO);
  const [frenando, setFrenando] = useState(false);
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
  const controles = useRef<OrbitControlsImpl | null>(null);
  const divsEtiqueta = useRef<Record<string, HTMLDivElement | null>>({});
  const etiquetasVisibles = useRef(true);
  etiquetasVisibles.current = etiquetas;

  const escena = useRef<EstadoMoto>({
    despiece: {},
    theta720: 0,
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
    enfoque: null,
    transparencia: 0,
    autoGiro: false,
    camara: null,
  });
  const subconjuntoDe = useMemo(() => Object.fromEntries(piezas.map((p) => [p.id, p.subconjunto])), [piezas]);
  const enfoque = useMemo(() => (corte ? new Set(piezas.filter((p) => p.subconjunto === "motor" || PIEZAS_MOTOR.has(p.id)).map((p) => p.id)) : null), [corte, piezas]);
  const radioTrasero = radioLlantaM(medida ?? String(SUPUESTOS.medida_llanta_trasera.valor));
  Object.assign(escena.current, {
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
    theta720: 0,
    angTras: 0,
    angDel: 0,
    angPin: 0,
    cadenaS: 0,
    comp: 0,
    despT: 0,
    vms: 0,
    freno: { activo: false, t: 0, v0: 0 },
    rampa: null as null | { desde: number; hasta: number; dur: number; t: number },
    sucio: false,
    sec: { activa: false, t: 0, paso: -1 },
  });
  const vivo = useRef({ corriendo, escala, factorLento, entradaDe, medida, despieceOn, grupoDe: {} as Record<string, number>, nGrupos: 0, acciones: [] as (() => void)[], tiempos: [] as number[] });
  vivo.current.corriendo = corriendo;
  vivo.current.escala = escala;
  vivo.current.factorLento = factorLento;
  vivo.current.entradaDe = entradaDe;
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

  const fijarCtl = useCallback((p: Partial<Ctl>) => {
    const antes = ctlRef.current;
    ctlRef.current = { ...antes, ...p };
    const fr = reloj.current.freno;
    if (fr.activo && (p.fuerza !== undefined || p.palanca !== undefined || p.cbs !== undefined)) {
      fr.v0 = reloj.current.vms * 3.6; // la nueva fuerza parte de la velocidad actual (sin saltos)
      fr.t = 0;
    }
    setCtl(ctlRef.current);
  }, []);
  const iniciarFreno = useCallback(() => {
    const v = vivo.current;
    const r = calcularMoto(v.entradaDe(ctlRef.current), v.medida);
    if (ctlRef.current.fuerza <= 0) fijarCtl({ fuerza: 160 });
    reloj.current.freno = { activo: true, t: 0, v0: r.velocidad_kmh };
    reloj.current.vms = r.velocidad_kmh / 3.6;
    setFrenando(true);
    apiMoto.evento("frenado", null, { palanca: ctlRef.current.palanca, v0_kmh: r.velocidad_kmh });
  }, [fijarCtl]);
  const soltarFreno = useCallback(() => {
    reloj.current.freno = { activo: false, t: 0, v0: 0 };
    setFrenando(false);
  }, []);
  const irACamara = useCallback((clave: string) => {
    const c = CAMARAS[clave];
    const peticion: PeticionCamara = { id: Date.now() + Math.random(), pos: c.pos, objetivo: c.objetivo };
    escena.current.camara = peticion;
  }, []);
  const reiniciar = useCallback(() => {
    const r = reloj.current;
    Object.assign(r, { t: 0, theta720: 0, angTras: 0, angDel: 0, angPin: 0, cadenaS: 0, comp: 0, despT: 0, vms: 0, rampa: null, sucio: false, sec: { activa: false, t: 0, paso: -1 } });
    r.freno = { activo: false, t: 0, v0: 0 };
    ctlRef.current = CTL0;
    setCtl(CTL0);
    setFrenando(false);
    setDespieceOn(false);
    setCorte(false);
    setSecActiva(false);
    setPasoSec(-1);
    setSnap(INST0);
  }, []);

  // Secuencia: arranque → acelerar → cambiar marcha → frenar con CBS → despiece.
  const acciones = useMemo(
    () => [
      () => {
        soltarFreno();
        setDespieceOn(false);
        setCorte(false);
        reloj.current.rampa = null;
        fijarCtl({ rpm: RALENTI, marcha: 0, fuerza: 0, palanca: "delantera", cbs: false });
        irACamara("general");
      },
      () => {
        fijarCtl({ marcha: 1 });
        reloj.current.rampa = { desde: ctlRef.current.rpm, hasta: 5500, dur: 3.5, t: 0 };
      },
      () => {
        fijarCtl({ marcha: 3 });
        reloj.current.rampa = { desde: ctlRef.current.rpm, hasta: 6500, dur: 1.5, t: 0 };
      },
      () => {
        setModeloSel("dlx");
        reloj.current.rampa = null;
        fijarCtl({ palanca: "trasera", cbs: true, fuerza: 180 });
        irACamara("frenos");
        window.setTimeout(iniciarFreno, 0);
      },
      () => {
        soltarFreno();
        fijarCtl({ rpm: RALENTI, marcha: 0, fuerza: 0 });
        setDespieceOn(true);
        irACamara("despiece");
      },
    ],
    [fijarCtl, iniciarFreno, soltarFreno, irACamara],
  );
  vivo.current.acciones = acciones;
  vivo.current.tiempos = [0, 5, 9.5, 14, 21];
  const TOTAL_SEC = 29;

  useEffect(() => {
    let id = 0;
    let previo = performance.now();
    let aviso = 0;
    const ciclo = (ahora: number) => {
      const dtReal = Math.min((ahora - previo) / 1000, 0.1);
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
      // rampa del acelerador
      if (rl.rampa && dt > 0) {
        rl.rampa.t += dt;
        const u = clamp01(rl.rampa.t / rl.rampa.dur);
        ctlRef.current = { ...ctlRef.current, rpm: Math.round(lerp(rl.rampa.desde, rl.rampa.hasta, suave(u))) };
        rl.sucio = true;
        if (u >= 1) rl.rampa = null;
      }

      const c = ctlRef.current;
      const ent = v.entradaDe(c);
      const r = calcularMoto(ent, v.medida);
      const K = v.factorLento;
      const fr = rl.freno;
      let vms: number;
      let wTras: number;
      let wDel: number;
      let aVeh = 0;
      if (fr.activo) {
        fr.t += dt;
        const fs = frenosMoto(ent, v.medida, fr.v0);
        aVeh = ((fs.delantero?.resultado.deceleracion_m_s2 ?? 0) + (fs.trasero?.resultado.deceleracion_m_s2 ?? 0)) / 2;
        vms = Math.max(fr.v0 / 3.6 - aVeh * fr.t, 0);
        // Rueda bloqueada (modelo sin ABS): gira según `estadoRueda`; si no, rueda con la moto.
        const rueda = (f: FrenoRueda | null, radio: number) =>
          f && f.resultado.rueda_bloqueada ? (estadoRueda(f.entrada, f.resultado, fr.t).w * fs.radio) / radio : vms / radio;
        wTras = rueda(fs.trasero, fs.radio);
        wDel = rueda(fs.delantero, RADIO_DELANTERA_M);
      } else {
        vms = r.velocidad_kmh / 3.6;
        wTras = vms / r.radio_llanta_m;
        wDel = vms / RADIO_DELANTERA_M;
      }
      rl.vms = vms;
      // El embrague se acciona al frenar: el motor vuelve al ralentí y la transmisión sigue a la rueda.
      const rpmMotor = r.estado_motor === "ahogado" ? 0 : fr.activo ? Math.min(RALENTI, c.rpm) : r.rpm_efectivas;
      const wPinon = wTras * FINAL; // ω_piñón = ω_corona · i_final
      const vCadena = wPinon * RADIO_PINON_M; // v = ω_piñón · r_piñón (= ω_corona · r_corona)
      rl.theta720 = (rl.theta720 + (((velocidadAngularRadS(rpmMotor) / K) * dt * 180) / Math.PI)) % 720;
      rl.angTras -= (wTras / K) * dt;
      rl.angDel -= (wDel / K) * dt;
      rl.angPin -= (wPinon / K) * dt;
      rl.cadenaS += (vCadena / K) * dt;
      const objetivoComp = fr.activo && vms > 0 ? 0.07 * clamp01(aVeh / (0.9 * G)) : 0;
      rl.comp += (objetivoComp - rl.comp) * (1 - Math.exp(-dt * 6));

      // despiece animado por ensamblaje
      const dGrupo = 1.0;
      const paso = dGrupo * 0.5;
      const total = paso * Math.max(v.nGrupos - 1, 0) + dGrupo;
      rl.despT = Math.min(Math.max(rl.despT + (v.despieceOn ? dt : -dt), 0), total);
      for (const [pid, gi] of Object.entries(v.grupoDe)) e.despiece[pid] = suave(clamp01((rl.despT - gi * paso) / dGrupo));

      Object.assign(e, {
        theta720: rl.theta720,
        angRuedaTras: rl.angTras,
        angRuedaDel: rl.angDel,
        angPinon: rl.angPin,
        cadenaS: rl.cadenaS,
        compresionHorquilla: rl.comp,
        motorEnMarcha: rpmMotor > 0,
        estadoMotor: r.estado_motor,
      });
      e.alerta.clear();
      if (r.rueda_delantera_bloqueada && fr.activo) ["disco_delantero", "llanta_delantera", "caliper_delantero"].forEach((p) => e.alerta.add(p));
      if (r.rueda_trasera_bloqueada && fr.activo) ["disco_trasero", "llanta_trasera", "caliper_trasero"].forEach((p) => e.alerta.add(p));
      if (r.estado_motor === "limitador") e.alerta.add("bujia");
      if (r.estado_motor === "ahogado") e.alerta.add("ciguenal");

      if (ahora - aviso > 100) {
        aviso = ahora;
        if (rl.sucio) {
          rl.sucio = false;
          setCtl(ctlRef.current);
        }
        setSnap({
          theta720: rl.theta720,
          vKmh: vms * 3.6,
          wTras,
          wPinon,
          vCadena,
          aVeh,
          tFreno: fr.t,
          rpmMotor,
          despiece: total > 0 ? rl.despT / total : 0,
          detenida: fr.activo && vms <= 0,
        });
      }
      id = requestAnimationFrame(ciclo);
    };
    id = requestAnimationFrame(ciclo);
    return () => cancelAnimationFrame(id);
  }, []);

  const reproducirSecuencia = useCallback(
    (desde = 0) => {
      const sec = reloj.current.sec;
      sec.activa = true;
      sec.t = vivo.current.tiempos[desde] ?? 0;
      sec.paso = desde - 1;
      setSecActiva(true);
      setCorriendo(true);
    },
    [],
  );
  const pausarSecuencia = () => {
    reloj.current.sec.activa = false;
    setSecActiva(false);
  };

  /* ---------- lecturas derivadas (a partir del estado de React: responden de inmediato a los controles) ---------- */
  const g = ctl.marcha >= 1 ? (SUPUESTOS.relaciones_marcha.valor as number[])[ctl.marcha - 1] : null;
  const estadoMotor = resultado.estado_motor;
  const rpmMotor = estadoMotor === "ahogado" ? 0 : frenando ? Math.min(RALENTI, ctl.rpm) : resultado.rpm_efectivas;
  const vMostrada = frenando ? snap.vKmh : resultado.velocidad_kmh;
  const enDespiece = despieceOn && snap.despiece > 0.02;
  const estadoTexto = enDespiece
    ? "DESPIECE"
    : frenando
      ? snap.detenida
        ? "DETENIDA"
        : "FRENANDO"
      : !corriendo
        ? "PAUSA"
        : estadoMotor === "ahogado"
          ? "MOTOR AHOGADO"
          : estadoMotor === "limitador"
            ? "LIMITADOR"
            : rpmMotor <= 0
              ? "MOTOR APAGADO"
              : "EN MARCHA";
  const wCorona = frenando ? snap.wTras : vMostrada / 3.6 / resultado.radio_llanta_m;
  const wPinon = frenando ? snap.wPinon : wCorona * FINAL;
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
  const textoDisco = (f: typeof fd, bloqueada: boolean, lado: string) =>
    f ? `${lado}: F ${fmt(f.fuerza_piston_n / 1000, 2)} kN · T ${fmt(f.par_frenado_nm)} N·m${bloqueada ? " · BLOQUEADA" : ""}` : `${lado}: sin accionar`;

  /* ---------- verificación contra la API (el backend valida; el visor contrasta) ---------- */
  useEffect(() => {
    const temporizador = window.setTimeout(() => {
      apiMoto.calculoMoto(ID_FICHA, entrada, conFicha).then(
        (r) => {
          const dif = Math.abs(r.resultado.velocidad_kmh - resultado.velocidad_kmh);
          setVerificacion(dif < 1e-3 ? `API verificada: v = ${fmt(r.resultado.velocidad_kmh, 1)} km/h, igual al cálculo local` : `La API difiere del cálculo local (Δ ${fmt(dif, 3)} km/h)`);
        },
        (e: Error) => setVerificacion(`API sin verificar: ${e.message}`),
      );
    }, 400);
    return () => window.clearTimeout(temporizador);
  }, [entrada, conFicha, resultado.velocidad_kmh]);

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
  const rLim = calcularMoto({ ...ENTRADA_MOTO_DEFECTO, rpm: 11000, marcha: 3 }, medida);
  const rTope = calcularMoto({ ...ENTRADA_MOTO_DEFECTO, rpm: CORTE, marcha: 3 }, medida);
  const rBloq = calcularMoto({ ...ENTRADA_MOTO_DEFECTO, rpm: 5000, marcha: 3, palanca: "delantera", fuerza_palanca_n: 400 }, medida);
  const rSuave = calcularMoto({ ...ENTRADA_MOTO_DEFECTO, rpm: 5000, marcha: 3, palanca: "delantera", fuerza_palanca_n: 100 }, medida);
  const experimentos: Experimento[] = [
    {
      pregunta: `En 3.ª, si el acelerador pasa de ${fmt(CORTE)} a 11.000 rpm, ¿qué ocurre con la velocidad?`,
      opciones: [
        { texto: "Aumenta alrededor de un 16 %", correcta: false },
        { texto: "No aumenta: el limitador corta la chispa", correcta: true },
        { texto: "Disminuye porque el motor se ahoga", correcta: false },
      ],
      explicacion: `Por encima del corte (${fmt(CORTE)} rpm, ${ETIQUETA_SUPUESTO}) el limitador corta la chispa: las rpm efectivas quedan en ${fmt(rLim.rpm_efectivas)} y la velocidad en ${fmt(rLim.velocidad_kmh, 1)} km/h, igual que a ${fmt(CORTE)} rpm (${fmt(rTope.velocidad_kmh, 1)} km/h).`,
      aplicar: () => {
        soltarFreno();
        fijarCtl({ marcha: 3, rpm: 11000, fuerza: 0 });
      },
    },
    {
      pregunta: `Con 5.ª engranada y el acelerador en 900 rpm (ralentí ${fmt(RALENTI)}), ¿qué ocurre?`,
      opciones: [
        { texto: "La moto avanza muy despacio", correcta: false },
        { texto: "El motor se ahoga: la rueda se detiene", correcta: true },
        { texto: "El limitador sube las rpm", correcta: false },
      ],
      explicacion: `Con marcha engranada, bajo el ralentí (${fmt(RALENTI)} rpm, ${ETIQUETA_SUPUESTO}) el motor no sostiene el giro: se ahoga, la relación total deja de aplicarse y la velocidad es 0 km/h.`,
      aplicar: () => {
        soltarFreno();
        fijarCtl({ marcha: 5, rpm: 900, fuerza: 0 });
      },
    },
    {
      pregunta: "Palanca delantera con 400 N y sin CBS a unos 41 km/h, ¿qué le ocurre a la rueda delantera?",
      opciones: [
        { texto: "Se bloquea (modelo sin ABS)", correcta: true },
        { texto: "Frena sin bloquearse", correcta: false },
        { texto: "Se detiene tras exactamente 1 s", correcta: false },
      ],
      explicacion: `Con 400 N el disco entrega T = ${fmt(rBloq.freno_delantero?.par_frenado_nm ?? 0)} N·m y la deceleración pedida (${fmt(rBloq.freno_delantero?.deceleracion_g ?? 0, 2)} g) supera la adherencia (${num("adherencia_neumatico")} g, ${ETIQUETA_SUPUESTO}): la rueda se bloquea. Con 100 N entrega ${fmt(rSuave.freno_delantero?.par_frenado_nm ?? 0)} N·m y no se bloquea.`,
      aplicar: () => {
        fijarCtl({ marcha: 3, rpm: 5000, palanca: "delantera", fuerza: 400, cbs: false });
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
    {
      en: 4,
      texto: "Acelerar: 1.ª marcha y subida de rpm; piñón, cadena y rueda giran con la relación real",
      accion: () => {
        fijarCtl({ marcha: 1 });
        reloj.current.rampa = { desde: ctlRef.current.rpm, hasta: 5500, dur: 3.5, t: 0 };
        irACamara("transmision");
      },
    },
    {
      en: 9,
      texto: "Cambiar a 3.ª: la rueda gira una fracción menor de las vueltas del motor",
      accion: () => {
        fijarCtl({ marcha: 3 });
        reloj.current.rampa = { desde: ctlRef.current.rpm, hasta: 6500, dur: 1.5, t: 0 };
        irACamara("general");
      },
    },
    {
      en: 13,
      texto: "Frenar con CBS: la palanca trasera reparte la presión entre ambos discos",
      accion: () => {
        reloj.current.rampa = null;
        fijarCtl({ palanca: "trasera", cbs: true, fuerza: 180 });
        irACamara("frenos");
        window.setTimeout(iniciarFreno, 0);
      },
    },
    {
      en: 18,
      texto: "Despiece por ensamblaje: cada conjunto se separa en el orden calculado por el backend",
      accion: () => {
        soltarFreno();
        fijarCtl({ rpm: RALENTI, marcha: 0, fuerza: 0 });
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
    <div className="moto-lab" data-testid="moto-lab" data-modelo={modeloSel}>
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
        <div className="dato grande">
          <span className="rotulo">rpm</span>
          <b className="num" data-testid="cab-rpm">{fmt(rpmMotor)}</b>
        </div>
        <div className="dato grande">
          <span className="rotulo">Marcha</span>
          <b className="num" data-testid="cab-marcha">{ctl.marcha === 0 ? "N" : `${ctl.marcha}.ª`}</b>
        </div>
        <div className="dato grande">
          <span className="rotulo">Velocidad</span>
          <b className="num" data-testid="cab-velocidad">{fmt(vMostrada, 1)} <small>km/h</small></b>
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
                      <dd className="num">{fmt(rpmMotor)} rpm {frenando && <small>(embrague accionado)</small>}</dd>
                      <dt>θ cigüeñal</dt>
                      <dd className="num" data-testid="theta">{fmt(snap.theta720 % 360)}° (ciclo {fmt(snap.theta720)}° de 720°)</dd>
                      <dt>Fase 4T</dt>
                      <dd><b style={{ color: FASES_INFO[faseActual].color }}>{FASES_INFO[faseActual].nombre}</b></dd>
                      <dt>x pistón (desde el PMS)</dt>
                      <dd className="num">{fmt(xPiston, 1)} mm · carrera 2r = {fmt(carrera * 1000, 1)} mm</dd>
                      <dt>Biela φ = asin(r·sin θ / L)</dt>
                      <dd className="num">{fmt(phiGrados, 1)}°</dd>
                      <dt>Cilindrada V = π/4·D²·carrera</dt>
                      <dd className="num">{fmt(resultado.cilindrada_calculada_cm3, 1)} cm³ frente a {fmt(resultado.cilindrada_referencia_cm3)} cm³ ({fmt(resultado.diferencia_cilindrada_pct, 2)} %) <InsigniaSupuesto /></dd>
                      <dt>Cámara lenta</dt>
                      <dd className="num">animación a 1/{factorLento} de la velocidad real</dd>
                    </dl>
                  </section>
                  <section aria-label="Transmisión">
                    <h4>Transmisión <InsigniaSupuesto /></h4>
                    <dl className="lecturas-lista">
                      <dt>Relaciones</dt>
                      <dd className="num">primaria {fmt(PRIMARIA, 2)} · marcha {g === null ? "N" : fmt(g, 2)} · final {fmt(FINAL, 2)}</dd>
                      <dt>Relación total</dt>
                      <dd className="num">{resultado.relacion_total === null ? "—" : fmt(resultado.relacion_total, 2)}</dd>
                      <dt>ω piñón / ω corona</dt>
                      <dd className="num">{fmt(wPinon, 1)} / {fmt(wCorona, 1)} rad/s</dd>
                      <dt>Cadena v = ω·r (piñón)</dt>
                      <dd className="num" data-testid="v-cadena-pinon">{fmt(vCadenaPinon, 2)} m/s</dd>
                      <dt>Cadena v = ω·r (corona)</dt>
                      <dd className="num" data-testid="v-cadena-corona">{fmt(vCadenaCorona, 2)} m/s</dd>
                      <dt>Llanta trasera</dt>
                      <dd className="num">{textoLlanta}; R = {fmt(resultado.radio_llanta_m, 4)} m</dd>
                      <dt>Velocidad de la moto</dt>
                      <dd className="num">{fmt(vMostrada, 1)} km/h</dd>
                    </dl>
                    <p className="aviso">{cambioMarcha}</p>
                    {verificacion && <p className="aviso" data-testid="verificacion-api">{verificacion}</p>}
                  </section>
                  <section aria-label="Frenos">
                    <h4>Frenos <InsigniaSupuesto /></h4>
                    <dl className="lecturas-lista">
                      <dt>Disco delantero</dt>
                      <dd className="num">{fd ? `F ${fmt(fd.fuerza_piston_n / 1000, 2)} kN · T ${fmt(fd.par_frenado_nm)} N·m · ${fd.rueda_bloqueada ? "bloqueada" : "sin bloqueo"}` : "sin accionar"}</dd>
                      <dt>Disco trasero</dt>
                      <dd className="num">{ft ? `F ${fmt(ft.fuerza_piston_n / 1000, 2)} kN · T ${fmt(ft.par_frenado_nm)} N·m · ${ft.rueda_bloqueada ? "bloqueada" : "sin bloqueo"}` : "sin accionar"}</dd>
                      <dt>Fuerza total de pistones</dt>
                      <dd className="num">{fmt(resultado.fuerza_pistones_total_n / 1000, 2)} kN {entrada.cbs && "(suma conservada con CBS)"}</dd>
                      <dt>Deceleración de la moto</dt>
                      <dd className="num">{frenando ? `${fmt(snap.aVeh, 2)} m/s² (${fmt(snap.aVeh / G, 2)} g)` : "—"}</dd>
                    </dl>
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
          <div className="escenario moto-escenario" data-testid="escenario-moto" data-modo={estadoTexto}>
            <div className="superpuesto" role="toolbar" aria-label="Reproducción y vista">
              <Reproduccion
                corriendo={corriendo}
                alCorrer={() => setCorriendo(true)}
                alPausar={() => setCorriendo(false)}
                alReiniciar={reiniciar}
                escala={escala}
                alEscala={setEscala}
              />
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
            </div>
            <EscenaMoto estado={escena} geometria={geometria} alSeleccionar={seleccionar} etiquetas={divsEtiqueta} etiquetasVisibles={etiquetasVisibles} controles={controles} />
            {(
              [
                ["motor", "etiqueta-3d", <>{fmt(rpmMotor)} rpm · θ {fmt(snap.theta720 % 360)}°<br />{FASES_INFO[faseActual].nombre} · 1/{factorLento} real</>],
                ["cilindrada", "etiqueta-3d fuerza", <>V = {fmt(resultado.cilindrada_calculada_cm3, 1)} cm³ · ficha {fmt(resultado.cilindrada_referencia_cm3)}<br />{ETIQUETA_SUPUESTO}</>],
                ["transmision", "etiqueta-3d movimiento", <>cadena {fmt(vCadenaPinon, 2)} m/s = ω·r<br />piñón {fmt(wPinon, 1)} rad/s</>],
                ["rueda", "etiqueta-3d movimiento", <>{resultado.relacion_total === null ? "relación —" : `i total ${fmt(resultado.relacion_total, 2)}`} · {fmt(vMostrada, 1)} km/h<br />ω rueda {fmt(wCorona, 1)} rad/s</>],
                ["disco_del", `etiqueta-3d fuerza${resultado.rueda_delantera_bloqueada ? " alerta" : ""}`, <>{textoDisco(fd, resultado.rueda_delantera_bloqueada, "Del.")}</>],
                ["disco_tras", `etiqueta-3d fuerza${resultado.rueda_trasera_bloqueada ? " alerta" : ""}`, <>{textoDisco(ft, resultado.rueda_trasera_bloqueada, "Tras.")}</>],
              ] as const
            ).map(([k, clase, contenido]) => (
              <div
                key={k}
                ref={(d) => {
                  divsEtiqueta.current[k] = d;
                }}
                className={`${clase} etiqueta-moto`}
                data-etiqueta={k}
                style={{ position: "absolute", left: 0, top: 0, zIndex: 1 }}
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
                <select aria-label="Ver con ficha de…" value={modeloSel} onChange={(e) => { setModeloSel(e.target.value as ModeloSel); apiMoto.evento("camara", null, { modelo: e.target.value }); }}>
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
                valor={ctl.rpm}
                min={0}
                max={11000}
                paso={100}
                unidad="rpm"
                alCambiar={(v) => {
                  reloj.current.rampa = null;
                  fijarCtl({ rpm: v });
                }}
                formato={(v) => fmt(v)}
              />
              <p className="marcas-rpm">ralentí {fmt(RALENTI)} · corte {fmt(CORTE)} rpm <InsigniaSupuesto /></p>
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
              <p className="marcas-rpm">{cbsDisponible ? `Reparto del CBS: ${fmt(num("reparto_cbs_delantero") * 100)} % delantero (${ETIQUETA_SUPUESTO})` : "CBS solo en la versión DLX según la lámina"}</p>
              <div className="barra">
                {frenando ? (
                  <button className="boton activo" onClick={soltarFreno}>Soltar freno</button>
                ) : (
                  <button className="boton" onClick={iniciarFreno} disabled={resultado.velocidad_kmh <= 0} title={resultado.velocidad_kmh <= 0 ? "Engranar una marcha y acelerar para tener velocidad" : "Aplicar el freno"}>Frenar</button>
                )}
                <span className="aviso">{resultado.velocidad_kmh <= 0 && !frenando ? "Moto detenida: engranar y acelerar" : frenando ? `t = ${fmt(snap.tFreno, 1)} s` : "Listo para frenar"}</span>
              </div>
            </section>
          </div>

          <ModoExperimento experimentos={experimentos} />
          <div className="lecturas" aria-label="Lecturas">
            <Chip etiqueta="R llanta" valor={`${fmt(resultado.radio_llanta_m, 4)} m`} />
            <Chip etiqueta="i total" valor={resultado.relacion_total === null ? "—" : fmt(resultado.relacion_total, 2)} />
            <Chip etiqueta="v" valor={`${fmt(vMostrada, 1)} km/h`} tono="movimiento" />
            <Chip etiqueta="F pistones" valor={`${fmt(resultado.fuerza_pistones_total_n / 1000, 2)} kN`} tono="fuerza" />
            {resultado.rueda_delantera_bloqueada || resultado.rueda_trasera_bloqueada ? (
              <Chip etiqueta="Estado" valor="rueda bloqueada (a > g·μ neumático)" tono="alerta" />
            ) : (
              <Chip etiqueta="Estado" valor="sin bloqueo" tono="correcto" />
            )}
            {estadoMotor === "limitador" && <Chip etiqueta="Motor" valor={`limitador: corta la chispa a ${fmt(CORTE)} rpm`} tono="alerta" />}
            {estadoMotor === "ahogado" && <Chip etiqueta="Motor" valor={`ahogado: rpm < ralentí ${fmt(RALENTI)} con marcha engranada`} tono="alerta" />}
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
              "Cámara lenta del motor siempre visible (1/200 de la velocidad real por omisión)",
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
        Modelo demostrativo: el embrague no se modela (la rueda sigue al motor con marcha engranada; al frenar se acciona) y la animación no valida propiedades mecánicas. {NO_PUBLICADO}: dato sin fuente verificable.
      </p>
    </div>
  );
}
