/**
 * Cálculo simplificado del freno de disco (réplica exacta de
 * `fabrica_autopartes.simulador.fisica_freno.calcular`, verificada con Vitest contra
 * `referencia_freno.json`, que exporta Python). Se replica en el cliente para que los
 * controles respondan en cada fotograma; la API sigue siendo la referencia.
 *
 * Fórmulas estándar; parámetros DEMOSTRATIVOS. La animación reproduce estos números,
 * pero no valida propiedades mecánicas reales.
 */

export const BAR_A_PA = 1e5;
export const G = 9.80665;

export interface EntradaFreno {
  presion_bar: number;
  diametro_piston_m: number;
  coeficiente_friccion: number;
  radio_efectivo_m: number;
  velocidad_kmh: number;
  radio_neumatico_m: number;
  masa_cuarto_vehiculo_kg: number;
  inercia_rueda_kg_m2: number;
  adherencia_neumatico: number;
}

export interface ResultadoFreno {
  area_piston_m2: number;
  fuerza_piston_n: number;
  fuerza_sujecion_por_pastilla_n: number;
  fuerza_friccion_total_n: number;
  par_frenado_nm: number;
  inercia_equivalente_kg_m2: number;
  deceleracion_rad_s2: number;
  deceleracion_m_s2: number;
  deceleracion_g: number;
  rueda_bloqueada: boolean;
  tiempo_detencion_s: number | null;
  distancia_detencion_m: number | null;
  rpm_inicial: number;
}

export const ENTRADA_FRENO_DEFECTO: EntradaFreno = {
  presion_bar: 25,
  diametro_piston_m: 0.054,
  coeficiente_friccion: 0.4,
  radio_efectivo_m: 0.115,
  velocidad_kmh: 60,
  radio_neumatico_m: 0.3,
  masa_cuarto_vehiculo_kg: 300,
  inercia_rueda_kg_m2: 1.2,
  adherencia_neumatico: 0.9,
};

const redondear = (x: number, d: number) => {
  const f = 10 ** d;
  return Math.round(x * f) / f;
};

export function calcularFreno(e: EntradaFreno): ResultadoFreno {
  const area = (Math.PI * e.diametro_piston_m ** 2) / 4;
  const fuerza = e.presion_bar * BAR_A_PA * area;
  const friccion = 2 * e.coeficiente_friccion * fuerza;
  const par = friccion * e.radio_efectivo_m;
  const inercia = e.inercia_rueda_kg_m2 + e.masa_cuarto_vehiculo_kg * e.radio_neumatico_m ** 2;
  const alfa = par / inercia;
  const aFreno = alfa * e.radio_neumatico_m;
  const limite = G * e.adherencia_neumatico;
  const bloqueada = aFreno > limite;
  const a = Math.min(aFreno, limite);
  const v = e.velocidad_kmh / 3.6;
  return {
    area_piston_m2: redondear(area, 8),
    fuerza_piston_n: redondear(fuerza, 3),
    fuerza_sujecion_por_pastilla_n: redondear(fuerza, 3),
    fuerza_friccion_total_n: redondear(friccion, 3),
    par_frenado_nm: redondear(par, 3),
    inercia_equivalente_kg_m2: redondear(inercia, 4),
    deceleracion_rad_s2: redondear(alfa, 4),
    deceleracion_m_s2: redondear(a, 4),
    deceleracion_g: redondear(a / G, 4),
    rueda_bloqueada: bloqueada,
    tiempo_detencion_s: a > 0 ? redondear(v / a, 4) : null,
    distancia_detencion_m: a > 0 ? redondear(v ** 2 / (2 * a), 4) : null,
    rpm_inicial: redondear(((v / e.radio_neumatico_m) * 60) / (2 * Math.PI), 3),
  };
}

/**
 * Estado de la rueda y del vehículo a los `t` segundos de aplicar el freno (deceleración constante).
 * Sin bloqueo, rueda y vehículo deceleran juntos (a = α·R). Con bloqueo (modelo sin ABS), la rueda
 * se detiene con α = (T − μ_n·m_¼·g·R) / I_rueda mientras el vehículo desliza con a = g·μ_n.
 */
export function estadoRueda(e: EntradaFreno, r: ResultadoFreno, t: number) {
  const R = e.radio_neumatico_m;
  const v0 = e.velocidad_kmh / 3.6;
  const w0 = v0 / R;
  const alfa = r.rueda_bloqueada
    ? (r.par_frenado_nm - e.adherencia_neumatico * e.masa_cuarto_vehiculo_kg * G * R) / e.inercia_rueda_kg_m2
    : r.deceleracion_m_s2 / R;
  const tRueda = alfa > 0 ? w0 / alfa : Infinity;
  const tr = Math.min(Math.max(t, 0), tRueda);
  const w = Math.max(w0 - alfa * tr, 0);
  const angulo = w0 * tr - 0.5 * alfa * tr * tr;
  const a = r.deceleracion_m_s2;
  const tVehiculo = a > 0 ? v0 / a : Infinity;
  const tv = Math.min(Math.max(t, 0), tVehiculo);
  const v = Math.max(v0 - a * tv, 0);
  const recorrido = v0 * tv - 0.5 * a * tv * tv;
  return {
    w,
    angulo,
    velocidad_kmh: v * 3.6,
    recorrido_m: recorrido,
    rueda_detenida: tr >= tRueda,
    detenido: tv >= tVehiculo,
    t_detencion: tVehiculo,
  };
}
