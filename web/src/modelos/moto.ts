/**
 * Cálculo didáctico de la motocicleta de referencia (réplica de
 * `fabrica_autopartes.simulador.fisica_moto`, verificada con Vitest contra `referencia_moto.json`,
 * que exporta Python con `scripts/exportar_referencia_web.py`). Se replica en el cliente para que los
 * controles respondan en cada fotograma; la API (`POST /api/v1/motos/{id}/calculo`) sigue siendo la
 * referencia y el visor la consulta para contrastar.
 *
 * Relaciones:
 *   D_llanta [mm] = rin·25,4 + 2·ancho·perfil/100          (medida ancho/perfil-rin)
 *   v [km/h]      = rpm · 2π·R · 60 / (1000 · i_primaria · i_marcha · i_final)
 *   V [cm³]       = π/4 · D² · carrera
 *   x(θ)          = r·cos θ + √(L² − r²·sin² θ),  r = carrera/2      (θ = 0 en el PMS)
 *   φ(θ)          = asin(r·sin θ / L)                                 (inclinación de la biela)
 *   v_cadena      = ω_piñón·r_piñón = ω_corona·r_corona
 *   dinámica      = `pasoMoto`: la velocidad es una variable de estado continua; con marcha engranada las rpm se
 *                   DERIVAN de ella (rpm = v·i_total·60/(2π·R)); el acelerador da a = k·acelerador, el freno una
 *                   deceleración de `calcularFreno`, y en neutro la velocidad decae por rozamiento.
 *
 * SUPUESTOS: cada valor no publicado en la ficha es un «supuesto didáctico» (valor típico de la
 * categoría). La geometría y la animación no validan propiedades mecánicas.
 */
import { calcularFreno, type EntradaFreno, type ResultadoFreno } from "./freno";

export const ID_MOTO = "moto_honda";
export const ETIQUETA_SUPUESTO = "supuesto didáctico";
export const FASES_CICLO = ["admision", "compresion", "expansion", "escape"] as const;
export type FaseCiclo = (typeof FASES_CICLO)[number];

export interface Supuesto {
  clave: string;
  valor: number | number[] | string;
  unidad: string;
  descripcion: string;
  etiqueta: string;
}

const s = (clave: string, valor: number | number[] | string, unidad: string, descripcion: string): Supuesto => ({
  clave,
  valor,
  unidad,
  descripcion,
  etiqueta: ETIQUETA_SUPUESTO,
});

/** Espejo exacto de `SUPUESTOS_REFERENCIA` (Python): mismas claves y mismos valores. */
export const SUPUESTOS: Record<string, Supuesto> = Object.fromEntries(
  [
    s("cilindrada_nominal_cm3", 150, "cm3", "Cilindrada nominal de referencia, típica de la categoría; no tomada de un nombre comercial."),
    s("diametro_mm", 57, "mm", "Diámetro del cilindro, valor típico de la categoría."),
    s("carrera_mm", 58.7, "mm", "Carrera, valor típico de la categoría."),
    s("longitud_biela_mm", 105, "mm", "Distancia entre centros de la biela, valor típico de la categoría."),
    s("medida_llanta_trasera", "130/70-17", "ancho/perfil-rin", "Medida de llanta trasera típica de la categoría."),
    s("ralenti_rpm", 1400, "rpm", "Régimen de ralentí típico de la categoría."),
    s("corte_encendido_rpm", 9500, "rpm", "Régimen de corte del limitador, valor típico de la categoría."),
    s("n_marchas", 5, "-", "Número de marchas, valor típico de la categoría."),
    s("relacion_primaria", 3.35, "-", "Relación primaria, valor típico de la categoría."),
    s("relaciones_marcha", [2.8, 1.9, 1.4, 1.1, 0.95], "-", "Relaciones de caja, valores típicos (no publicadas)."),
    s("relacion_final", 3, "-", "Transmisión final: corona 42 / piñón 14, valor típico de la categoría."),
    s("presion_bar_por_newton", 0.3, "bar/N", "Presión hidráulica por newton aplicado en la palanca (ejemplo)."),
    s("reparto_cbs_delantero", 0.4, "-", "Fracción de la presión que el CBS envía al disco delantero con la palanca trasera."),
    s("coeficiente_friccion", 0.4, "-", "μ pastilla-disco típico de la categoría."),
    s("adherencia_neumatico", 0.9, "-", "μ neumático-calzada típico de la categoría."),
    s("diametro_piston_m", 0.03, "m", "Diámetro del pistón de pinza típico de la categoría."),
    s("radio_efectivo_m", 0.1, "m", "Radio efectivo del disco típico de la categoría."),
    s("masa_por_rueda_kg", 120, "kg", "Masa equivalente por rueda (moto y conductor) típica de la categoría."),
    s("inercia_rueda_kg_m2", 0.9, "kg·m2", "Inercia de la rueda típica de la categoría."),
    s("medida_llanta_delantera", "90/80-17", "ancho/perfil-rin", "Medida de llanta delantera típica de la categoría (la lámina no la publica)."),
    s("aceleracion_max_m_s2", 3, "m/s2", "Aceleración con el acelerador a fondo: a = k·acelerador (dinámica simplificada)."),
    s("rozamiento_m_s2", 0.5, "m/s2", "Deceleración constante por rodadura (neutro y marcha sin acelerar)."),
    s("arrastre_aero_1_m", 0.0023, "1/m", "Coeficiente del arrastre aerodinámico: a = c·v²."),
    s("tau_rpm_libre_s", 0.25, "s", "Constante de tiempo con que las rpm libres (neutro) siguen al acelerador."),
    s("rpm_tope_libre", 11000, "rpm", "rpm que pediría el acelerador a fondo en neutro (sin limitador)."),
    s("banda_limitador_rpm", 100, "rpm", "Banda bajo el corte donde la aceleración se anula progresivamente (limitador suave)."),
    s("acelerador_minimo_sin_ahogo", 0.2, "-", "Acelerador mínimo (0-1) para que el embrague patine sin ahogar en marchas altas."),
    s("marcha_minima_ahogo", 3, "-", "Desde esta marcha, rpm derivadas bajo el ralentí y poco acelerador ahogan el motor; en las marchas bajas el embrague patina (arranque)."),
  ].map((x) => [x.clave, x] as const),
);

const num = (clave: string): number => SUPUESTOS[clave].valor as number;
const lista = (clave: string): number[] => SUPUESTOS[clave].valor as number[];

export const MEDIDA_TRASERA_CB160F = "140/70-17";
/** Radios de paso del piñón y la corona (m) del modelo 3D; su cociente es la relación final (42/14 = 3). */
export const RADIO_PINON_M = 0.03;
export const RADIO_CORONA_M = 0.09;
/** Posiciones del modelo 3D base (llanta trasera genérica 130/70-17): ejes del piñón y de la corona (= eje de la rueda trasera). */
export const EJE_PINON: readonly [number, number] = [-0.15, 0.3069];
export const EJE_CORONA: readonly [number, number] = [-0.64, 0.3069];

/** Llanta delantera del modelo 3D (supuesto didáctico; la lámina no la publica). */
export const MEDIDA_DELANTERA_DEMO = String(SUPUESTOS.medida_llanta_delantera.valor);
export const LIMITES = { rpm: [0, 20000], marcha: [0, 6], fuerza: [0, 600] } as const;
export const FACTORES_LENTO = [50, 100, 200, 500] as const;
export const FACTOR_LENTO_DEFECTO = 200;

const redondear = (x: number, d: number) => {
  const f = 10 ** d;
  return Math.round(x * f) / f;
};
const acotar = (x: number, a: number, b: number, defecto = a) => (Number.isFinite(x) ? Math.min(Math.max(x, a), b) : defecto);

/* ---------- llantas, velocidad, cilindrada ---------- */
const PATRON_MEDIDA = /^(\d{2,3})\/(\d{2})-(\d{2})$/;

export function parsearMedidaLlanta(medida: string): [number, number, number] {
  const m = PATRON_MEDIDA.exec(medida.trim());
  if (!m) throw new Error(`Medida de llanta inválida: '${medida}' (formato ancho/perfil-rin)`);
  return [Number(m[1]), Number(m[2]), Number(m[3])];
}
export function diametroLlantaMm(medida: string): number {
  const [ancho, perfil, rin] = parsearMedidaLlanta(medida);
  return rin * 25.4 + (2 * ancho * perfil) / 100;
}
export const radioLlantaM = (medida: string) => diametroLlantaMm(medida) / 2000;
export const relacionTotal = (primaria: number, marcha: number, final: number) => primaria * marcha * final;
export function velocidadKmh(rpm: number, radioM: number, primaria: number, marcha: number, final: number): number {
  return (rpm * 2 * Math.PI * radioM * 60) / (1000 * relacionTotal(primaria, marcha, final));
}
export const cilindradaCm3 = (diametroMm: number, carreraMm: number) => ((Math.PI / 4) * diametroMm ** 2 * carreraMm) / 1000;

/* ---------- biela-manivela y ciclo de 4 tiempos ---------- */
/** Distancia eje del cigüeñal–bulón; máxima (PMS) en θ = 0, mínima (PMI) en θ = π. */
export function posicionPistonM(thetaRad: number, carreraM: number, bielaM: number): number {
  const r = carreraM / 2;
  return r * Math.cos(thetaRad) + Math.sqrt(bielaM ** 2 - (r * Math.sin(thetaRad)) ** 2);
}
/** Inclinación de la biela respecto al eje del cilindro: φ = asin(r·sin θ / L). */
export function anguloBielaRad(thetaRad: number, carreraM: number, bielaM: number): number {
  return Math.asin(((carreraM / 2) * Math.sin(thetaRad)) / bielaM);
}
export function faseCiclo(theta720Grados: number): FaseCiclo {
  const t = ((theta720Grados % 720) + 720) % 720;
  return FASES_CICLO[Math.floor(t / 180)];
}

export const GEOMETRIA_MOTOR = {
  get carreraM() {
    return num("carrera_mm") / 1000;
  },
  get bielaM() {
    return num("longitud_biela_mm") / 1000;
  },
  levanteValvulaM: 0.005,
} as const;

/** Paleta Okabe-Ito (segura para daltonismo); cada fase además lleva rótulo textual. */
export const FASES_INFO: Record<FaseCiclo, { nombre: string; color: string; pistón: string; detalle: string }> = {
  admision: { nombre: "Admisión", color: "#0072b2", pistón: "baja", detalle: "La válvula de admisión abre y entra mezcla." },
  compresion: { nombre: "Compresión", color: "#e69f00", pistón: "sube", detalle: "Ambas válvulas cerradas: la mezcla se comprime." },
  expansion: { nombre: "Expansión", color: "#d55e00", pistón: "baja", detalle: "La chispa enciende la mezcla y empuja el pistón." },
  escape: { nombre: "Escape", color: "#6b6b6b", pistón: "sube", detalle: "La válvula de escape abre y salen los gases." },
};

/** Levante (m) de la válvula de admisión: lóbulo senoidal durante la carrera de admisión (0–180°). */
export function levanteAdmision(theta720: number, levante = GEOMETRIA_MOTOR.levanteValvulaM): number {
  const t = ((theta720 % 720) + 720) % 720;
  return t < 180 ? levante * Math.sin((Math.PI * t) / 180) : 0;
}
/** Levante (m) de la válvula de escape: lóbulo senoidal durante la carrera de escape (540–720°). */
export function levanteEscape(theta720: number, levante = GEOMETRIA_MOTOR.levanteValvulaM): number {
  const t = ((theta720 % 720) + 720) % 720;
  return t >= 540 ? levante * Math.sin((Math.PI * (t - 540)) / 180) : 0;
}
/** Intensidad (0–1) de la chispa: salta en el PMS de la compresión (360°) y se apaga en 30° de giro. */
export function intensidadChispa(theta720: number): number {
  const t = ((theta720 % 720) + 720) % 720;
  return t >= 360 && t < 390 ? 1 - (t - 360) / 30 : 0;
}

/* ---------- cadena ---------- */
export const velocidadAngularRadS = (rpm: number) => (rpm * 2 * Math.PI) / 60;
export const velocidadAngularPinonRadS = (rpm: number, primaria: number, marcha: number) =>
  velocidadAngularRadS(rpm) / (primaria * marcha);
export const velocidadAngularCoronaRadS = (rpm: number, primaria: number, marcha: number, final: number) =>
  velocidadAngularPinonRadS(rpm, primaria, marcha) / final;
export const velocidadCadenaMS = (rpm: number, primaria: number, marcha: number, radioPinon = RADIO_PINON_M) =>
  velocidadAngularPinonRadS(rpm, primaria, marcha) * radioPinon;
export const velocidadCadenaDesdeCoronaMS = (rpm: number, primaria: number, marcha: number, final: number, radioCorona = RADIO_CORONA_M) =>
  velocidadAngularCoronaRadS(rpm, primaria, marcha, final) * radioCorona;

export interface PuntoCadena {
  x: number;
  y: number;
}
export interface TrazadoCadena {
  longitud: number;
  /** Punto de la cadena a la distancia `s` (m) sobre el lazo; el lazo circula en sentido horario. */
  punto: (s: number) => PuntoCadena;
}

/**
 * Lazo de la cadena: tangentes exteriores entre la corona y el piñón y arcos sobre ambos. Circula en
 * sentido horario (visto desde el lado +Z), igual que las ruedas al avanzar hacia +X.
 */
export function trazadoCadena(
  centroPinon: readonly [number, number] = EJE_PINON,
  centroCorona: readonly [number, number] = EJE_CORONA,
  rp = RADIO_PINON_M,
  rc = RADIO_CORONA_M,
): TrazadoCadena {
  const dx = centroPinon[0] - centroCorona[0];
  const dy = centroPinon[1] - centroCorona[1];
  const d = Math.hypot(dx, dy);
  const base = Math.atan2(dy, dx);
  const beta = Math.acos((rc - rp) / d); // ángulo del punto de tangencia respecto a la línea de centros
  const aSup = base + beta; // normal de la tangente superior
  const aInf = base - beta; // normal de la tangente inferior
  const pt = (c: readonly [number, number], r: number, a: number): PuntoCadena => ({ x: c[0] + r * Math.cos(a), y: c[1] + r * Math.sin(a) });
  const cSup = pt(centroCorona, rc, aSup);
  const pSup = pt(centroPinon, rp, aSup);
  const pInf = pt(centroPinon, rp, aInf);
  const cInf = pt(centroCorona, rc, aInf);
  const lTan = Math.hypot(pSup.x - cSup.x, pSup.y - cSup.y);
  const barridoPinon = aSup - aInf; // horario: aSup → aInf
  const barridoCorona = 2 * Math.PI - barridoPinon; // horario: aInf → aSup (por detrás)
  const l1 = lTan;
  const l2 = l1 + rp * barridoPinon;
  const l3 = l2 + lTan;
  const longitud = l3 + rc * barridoCorona;
  return {
    longitud,
    punto: (sIn: number) => {
      const s = ((sIn % longitud) + longitud) % longitud;
      if (s < l1) {
        const u = s / lTan;
        return { x: cSup.x + (pSup.x - cSup.x) * u, y: cSup.y + (pSup.y - cSup.y) * u };
      }
      if (s < l2) return pt(centroPinon, rp, aSup - (s - l1) / rp);
      if (s < l3) {
        const u = (s - l2) / lTan;
        return { x: pInf.x + (cInf.x - pInf.x) * u, y: pInf.y + (cInf.y - pInf.y) * u };
      }
      return pt(centroCorona, rc, aInf - (s - l3) / rc);
    },
  };
}

/* ---------- entrada, saneamiento y resultado ---------- */
export type VersionMoto = "STD" | "DLX";
export type PalancaMoto = "delantera" | "trasera";
export type EstadoMotor = "normal" | "limitador" | "ahogado" | "neutro" | "patinaje" | "embrague";

export interface EntradaMoto {
  version: VersionMoto;
  rpm: number;
  marcha: number; // 0 = neutro
  palanca: PalancaMoto;
  fuerza_palanca_n: number;
  cbs: boolean;
  velocidad_inicial_kmh: number | null;
}

export const ENTRADA_MOTO_DEFECTO: EntradaMoto = {
  version: "DLX",
  rpm: 1400,
  marcha: 0,
  palanca: "delantera",
  fuerza_palanca_n: 0,
  cbs: false,
  velocidad_inicial_kmh: null,
};

/** El visor no confía en valores del cliente: acota y reemplaza lo no finito antes de calcular. */
export function sanearEntrada(e: EntradaMoto): EntradaMoto {
  const version: VersionMoto = e.version === "STD" ? "STD" : "DLX";
  return {
    version,
    rpm: acotar(e.rpm, LIMITES.rpm[0], LIMITES.rpm[1], num("ralenti_rpm")),
    marcha: Math.round(acotar(e.marcha, 0, Math.min(LIMITES.marcha[1], num("n_marchas")), 0)),
    palanca: e.palanca === "trasera" ? "trasera" : "delantera",
    fuerza_palanca_n: acotar(e.fuerza_palanca_n, LIMITES.fuerza[0], LIMITES.fuerza[1], 0),
    cbs: version === "DLX" && e.cbs === true,
    velocidad_inicial_kmh: e.velocidad_inicial_kmh === null ? null : acotar(e.velocidad_inicial_kmh, 0, 200, 0),
  };
}

export interface ResultadoMoto {
  radio_llanta_m: number;
  medida_llanta: string;
  relacion_total: number | null;
  rpm_efectivas: number;
  estado_motor: EstadoMotor;
  velocidad_kmh: number;
  cilindrada_calculada_cm3: number;
  cilindrada_referencia_cm3: number;
  diferencia_cilindrada_pct: number;
  freno_delantero: ResultadoFreno | null;
  freno_trasero: ResultadoFreno | null;
  fuerza_pistones_total_n: number;
  rueda_delantera_bloqueada: boolean;
  rueda_trasera_bloqueada: boolean;
}

/** Entrada de `calcularFreno` para un disco de la moto (misma construcción que `_freno` en Python). */
export function entradaFrenoMoto(presionBar: number, velocidadKmh_: number, radioM: number): EntradaFreno {
  return {
    presion_bar: Math.min(presionBar, 200),
    diametro_piston_m: num("diametro_piston_m"),
    coeficiente_friccion: num("coeficiente_friccion"),
    adherencia_neumatico: num("adherencia_neumatico"),
    radio_efectivo_m: num("radio_efectivo_m"),
    velocidad_kmh: Math.min(velocidadKmh_, 200),
    radio_neumatico_m: radioM,
    masa_cuarto_vehiculo_kg: num("masa_por_rueda_kg"),
    inercia_rueda_kg_m2: num("inercia_rueda_kg_m2"),
  };
}

/** Presión (delantera, trasera) según palanca y CBS. Con CBS la suma se conserva. */
export function repartirPresion(e: Pick<EntradaMoto, "palanca" | "cbs">, presionTotalBar: number): [number, number] {
  if (e.palanca === "delantera") return [presionTotalBar, 0];
  if (e.cbs) {
    const f = num("reparto_cbs_delantero");
    return [presionTotalBar * f, presionTotalBar * (1 - f)];
  }
  return [0, presionTotalBar];
}

export interface FrenoRueda {
  entrada: EntradaFreno;
  resultado: ResultadoFreno;
}

/** Discos accionados (delantero, trasero); cada uno con el radio de su propia llanta (la delantera es 90/80-17). */
export function frenosMoto(
  entrada: Pick<EntradaMoto, "palanca" | "cbs" | "fuerza_palanca_n" | "version">,
  medidaLlanta: string | null | undefined,
  velocidadKmh_: number,
): { delantero: FrenoRueda | null; trasero: FrenoRueda | null; radio: number; radioDelantero: number } {
  const e = sanearEntrada({ ...ENTRADA_MOTO_DEFECTO, ...entrada });
  const radio = radioLlantaM(medidaLlanta ?? String(SUPUESTOS.medida_llanta_trasera.valor));
  const radioDelantero = radioLlantaM(MEDIDA_DELANTERA_DEMO);
  const [pDel, pTras] = repartirPresion(e, e.fuerza_palanca_n * num("presion_bar_por_newton"));
  const construir = (p: number, r: number): FrenoRueda | null => {
    if (p <= 0) return null;
    const en = entradaFrenoMoto(p, velocidadKmh_, r);
    return { entrada: en, resultado: calcularFreno(en) };
  };
  return { delantero: construir(pDel, radioDelantero), trasero: construir(pTras, radio), radio, radioDelantero };
}

const medidaTrasera = (m?: string | null) => m ?? String(SUPUESTOS.medida_llanta_trasera.valor);

function componer(
  e: Pick<EntradaMoto, "palanca" | "cbs" | "fuerza_palanca_n" | "version">,
  medida: string,
  rpm: number,
  estado: EstadoMotor,
  vKmh: number,
  ratio: number | null,
  vFrenado: number,
): ResultadoMoto {
  const fs = frenosMoto(e, medida, vFrenado);
  const fDel = fs.delantero?.resultado ?? null;
  const fTras = fs.trasero?.resultado ?? null;
  const total = [fDel, fTras].reduce((a, f) => a + (f?.fuerza_piston_n ?? 0), 0);
  const nominal = num("cilindrada_nominal_cm3");
  const calculada = cilindradaCm3(num("diametro_mm"), num("carrera_mm"));
  return {
    radio_llanta_m: redondear(fs.radio, 5),
    medida_llanta: medida,
    relacion_total: ratio === null ? null : redondear(ratio, 4),
    rpm_efectivas: redondear(rpm, 3),
    estado_motor: estado,
    velocidad_kmh: redondear(vKmh, 3),
    cilindrada_calculada_cm3: redondear(calculada, 3),
    cilindrada_referencia_cm3: nominal,
    diferencia_cilindrada_pct: redondear(((calculada - nominal) / nominal) * 100, 3),
    freno_delantero: fDel,
    freno_trasero: fTras,
    fuerza_pistones_total_n: redondear(total, 3),
    // Sin movimiento no hay bloqueo que informar.
    rueda_delantera_bloqueada: Boolean(fDel?.rueda_bloqueada) && vFrenado > 0,
    rueda_trasera_bloqueada: Boolean(fTras?.rueda_bloqueada) && vFrenado > 0,
  };
}

const relacionMarcha = (marcha: number) => lista("relaciones_marcha")[marcha - 1];

/** Instantánea «de lección»: velocidad desde rpm y marcha (v = rpm·2πR / i_total) con marcha engranada. */
export function calcularMoto(entrada: EntradaMoto, medidaLlanta?: string | null): ResultadoMoto {
  const e = sanearEntrada(entrada);
  const medida = medidaTrasera(medidaLlanta);
  const radio = radioLlantaM(medida);
  const ralenti = num("ralenti_rpm");
  const corte = num("corte_encendido_rpm");
  let rpm = e.rpm;
  let estado: EstadoMotor = "normal";
  if (rpm > corte) {
    rpm = corte;
    estado = "limitador";
  }
  if (e.marcha >= 1 && e.rpm < ralenti) estado = e.marcha >= num("marcha_minima_ahogo") ? "ahogado" : "patinaje";
  let ratio: number | null = null;
  let v = 0;
  if (e.marcha === 0) estado = estado === "limitador" ? "limitador" : "neutro";
  else if (estado !== "ahogado") {
    const g = relacionMarcha(e.marcha);
    ratio = relacionTotal(num("relacion_primaria"), g, num("relacion_final"));
    v = velocidadKmh(rpm, radio, num("relacion_primaria"), g, num("relacion_final"));
  }
  return componer(e, medida, rpm, estado, v, ratio, e.velocidad_inicial_kmh ?? v);
}

/* ---------- dinámica: la velocidad es una variable de estado continua ---------- */
export interface MandoMoto {
  version: VersionMoto;
  acelerador: number; // 0..1
  marcha: number;
  palanca: PalancaMoto;
  fuerza_palanca_n: number;
  cbs: boolean;
  freno: boolean;
}
export const MANDO_DEFECTO: MandoMoto = { version: "DLX", acelerador: 0, marcha: 0, palanca: "delantera", fuerza_palanca_n: 0, cbs: false, freno: false };

export interface EstadoDinamico {
  v_ms: number;
  rpm_motor: number;
  modo: EstadoMotor;
  t_freno_s: number;
  a_ms2: number;
}
export const ESTADO_DINAMICO_INICIAL: EstadoDinamico = { v_ms: 0, rpm_motor: 1400, modo: "neutro", t_freno_s: 0, a_ms2: 0 };

export function sanearMando(m: MandoMoto): MandoMoto {
  const e = sanearEntrada({ ...ENTRADA_MOTO_DEFECTO, version: m.version, marcha: m.marcha, palanca: m.palanca, fuerza_palanca_n: m.fuerza_palanca_n, cbs: m.cbs });
  return { version: e.version, acelerador: acotar(m.acelerador, 0, 1, 0), marcha: e.marcha, palanca: e.palanca, fuerza_palanca_n: e.fuerza_palanca_n, cbs: e.cbs, freno: m.freno === true };
}

/** rpm del motor con marcha engranada: rpm = v / R · i_total · 60 / 2π. */
export const rpmDerivadas = (vMs: number, radioM: number, primaria: number, marcha: number, final: number) =>
  ((vMs / radioM) * relacionTotal(primaria, marcha, final) * 60) / (2 * Math.PI);
export const velocidadMsEnCorte = (radioM: number, primaria: number, marcha: number, final: number) =>
  (((num("corte_encendido_rpm") * 2 * Math.PI) / 60) * radioM) / relacionTotal(primaria, marcha, final);
export const resistenciaMS2 = (vMs: number) => (vMs > 0 ? num("rozamiento_m_s2") + num("arrastre_aero_1_m") * vMs * vMs : 0);

/** Avanza `dt` s. Función pura; misma lógica que `fisica_moto.paso_moto` (Python). */
export function pasoMoto(est: EstadoDinamico, mandoEntrada: MandoMoto, dt: number, medidaLlanta?: string | null): EstadoDinamico {
  if (!Number.isFinite(dt) || dt < 0) throw new Error("dt debe ser finito y no negativo");
  const mando = sanearMando(mandoEntrada);
  const medida = medidaTrasera(medidaLlanta);
  const radio = radioLlantaM(medida);
  const ralenti = num("ralenti_rpm");
  const corte = num("corte_encendido_rpm");
  const prim = num("relacion_primaria");
  const final = num("relacion_final");
  const banda = num("banda_limitador_rpm");
  const tau = num("tau_rpm_libre_s");
  const v = Math.max(est.v_ms, 0);
  const resist = resistenciaMS2(v);
  const frenando = mando.freno && mando.fuerza_palanca_n > 0;
  const k = num("aceleracion_max_m_s2") * mando.acelerador;
  const g = mando.marcha >= 1 ? relacionMarcha(mando.marcha) : null;
  let ahogo = false;
  let a: number;
  if (frenando) {
    const fs = frenosMoto(mando, medida, v * 3.6);
    const aFr = ((fs.delantero?.resultado.deceleracion_m_s2 ?? 0) + (fs.trasero?.resultado.deceleracion_m_s2 ?? 0)) / 2;
    a = -(aFr + resist);
  } else if (g === null) {
    a = -resist;
  } else {
    const rpmDer = rpmDerivadas(v, radio, prim, g, final);
    ahogo = rpmDer < ralenti && mando.marcha >= num("marcha_minima_ahogo") && mando.acelerador < num("acelerador_minimo_sin_ahogo");
    // Limitador suave: la aceleración se anula al acercarse al corte.
    const aMotor = ahogo ? 0 : k * Math.min(Math.max((corte - rpmDer) / banda, 0), 1);
    a = aMotor - resist;
  }
  let vNueva = v + a * dt;
  if (vNueva < 0 || (v === 0 && a < 0)) vNueva = 0;
  if (g !== null && !frenando && !ahogo) vNueva = Math.min(vNueva, velocidadMsEnCorte(radio, prim, g, final));
  let rpm: number;
  let modo: EstadoMotor;
  if (frenando) {
    modo = "embrague"; // el embrague se acciona al frenar: el motor queda libre
    rpm = est.rpm_motor + (ralenti - est.rpm_motor) * (1 - Math.exp(-dt / tau));
  } else if (g === null) {
    const objetivo = ralenti + mando.acelerador * (num("rpm_tope_libre") - ralenti);
    rpm = est.rpm_motor + (objetivo - est.rpm_motor) * (1 - Math.exp(-dt / tau));
    modo = "neutro";
    if (rpm >= corte - banda && objetivo >= corte - banda) {
      rpm = Math.min(rpm, corte);
      modo = "limitador";
    }
  } else if (ahogo) {
    rpm = 0;
    modo = "ahogado";
  } else {
    const rpmNueva = rpmDerivadas(vNueva, radio, prim, g, final);
    if (rpmNueva >= corte - banda) {
      rpm = Math.min(rpmNueva, corte);
      modo = "limitador";
    } else if (rpmNueva < ralenti) {
      rpm = ralenti;
      modo = "patinaje"; // embrague patinando: la relación de la lección no rige
    } else {
      rpm = rpmNueva;
      modo = "normal";
    }
  }
  return { v_ms: vNueva, rpm_motor: rpm, modo, t_freno_s: frenando ? est.t_freno_s + dt : 0, a_ms2: dt > 0 ? (vNueva - v) / dt : 0 };
}

/** Instantánea derivada del estado dinámico (velocidad y rpm provienen del estado, no de la fórmula). */
export function calcularMotoDesdeEstado(est: EstadoDinamico, mandoEntrada: MandoMoto, medidaLlanta?: string | null): ResultadoMoto {
  const mando = sanearMando(mandoEntrada);
  const ratio = mando.marcha >= 1 ? relacionTotal(num("relacion_primaria"), relacionMarcha(mando.marcha), num("relacion_final")) : null;
  return componer(mando, medidaTrasera(medidaLlanta), est.rpm_motor, est.modo, est.v_ms * 3.6, ratio, est.v_ms * 3.6);
}

/** La chispa solo salta en el PMS de la compresión; con el limitador se suprime en ciclos alternos. */
export function chispaPermitida(modo: EstadoMotor, ciclo: number): boolean {
  return modo !== "ahogado" && !(modo === "limitador" && ciclo % 2 === 1);
}
export const intensidadChispaMotor = (theta720: number, ciclo: number, modo: EstadoMotor) =>
  chispaPermitida(modo, ciclo) ? intensidadChispa(theta720) : 0;


/* ---------- ficha técnica: lo que «Ver con ficha de…» puede aplicar ---------- */
export interface CampoFichaApi {
  valor: string | number | boolean | unknown[] | null;
  unidad: string | null;
  fuente: string | null;
  fecha_consulta: string | null;
  estado: "publicado" | "no_publicado" | "supuesto";
  observacion?: string | null;
}

export interface AjusteFicha {
  /** Medida de llanta trasera publicada, o `null` (se conserva el supuesto genérico). */
  medidaLlanta: string | null;
  /** La versión puede llevar CBS según la ficha publicada (DLX) o no (STD); `null` si no hay ficha. */
  cbsDisponible: boolean | null;
  /** El freno trasero de la versión está publicado en la ficha; si no, se conserva el disco genérico (supuesto). */
  traseroPublicado: boolean | null;
  /** Campos no publicados que conservan el valor genérico. */
  conservados: string[];
}

export function ajusteDesdeFicha(
  grupos: Record<string, Record<string, CampoFichaApi>> | undefined,
  porVersion: Record<string, Record<string, CampoFichaApi>> | undefined,
  version: VersionMoto,
): AjusteFicha {
  const publicado = (c: CampoFichaApi | undefined) => (c && c.estado === "publicado" && c.valor !== null ? c : null);
  const llanta = publicado(grupos?.llantas?.trasera);
  let medida: string | null = null;
  if (llanta && typeof llanta.valor === "string") {
    try {
      parsearMedidaLlanta(llanta.valor);
      medida = llanta.valor;
    } catch {
      medida = null; // medida no válida: se conserva el supuesto genérico
    }
  }
  const cbs = publicado(porVersion?.[version]?.cbs);
  const conservados: string[] = [];
  if (!medida) conservados.push("llantas.trasera");
  const trasero = publicado(porVersion?.[version]?.trasero);
  if (!trasero) conservados.push(`frenos.${version}.trasero`);
  if (!cbs) conservados.push(`frenos.${version}.cbs`);
  for (const [g, c] of [
    ["motor", "cilindrada"],
    ["motor", "diametro_x_carrera"],
    ["motor", "potencia"],
    ["transmision", "marchas"],
  ] as const) {
    if (!publicado(grupos?.[g]?.[c])) conservados.push(`${g}.${c}`);
  }
  return { medidaLlanta: medida, cbsDisponible: cbs ? cbs.valor === true : null, traseroPublicado: trasero ? true : null, conservados };
}

/** Texto breve de lo que cambió al engranar una marcha. */
export function textoMarcha(marcha: number, ratio: number | null): string {
  if (marcha === 0) return "Neutro: el motor gira sin mover la rueda.";
  if (ratio === null) return `Marcha ${marcha}.ª: el motor se ahoga por debajo del ralentí.`;
  return `Marcha ${marcha}.ª: la rueda gira 1/${ratio.toFixed(2).replace(".", ",")} de las vueltas del motor.`;
}
