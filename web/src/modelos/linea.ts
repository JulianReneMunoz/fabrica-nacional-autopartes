/**
 * Línea de ensamble de chasises (máquina demostrativa del método Anatomy).
 *
 * Relación medible:  takt = tiempo disponible / demanda
 * Estaciones mínimas: N = ⌈contenido de trabajo / takt⌉
 * Ciclo por estación (balanceo ideal): c = contenido / estaciones
 * Si c > takt, la línea produce menos de lo demandado y la cola crece.
 *
 * La capacidad anual (p. ej. 24.000 chasises/año en Bogotá) proviene de la base de conocimiento
 * cuando la API la entrega; turnos, días y contenido de trabajo son DEMOSTRATIVOS.
 */

export interface EntradaLinea {
  demanda_anual: number;
  dias_anio: number;
  turnos_dia: number;
  horas_turno: number;
  contenido_min: number;
  estaciones: number;
}

export const ENTRADA_LINEA_DEFECTO: EntradaLinea = {
  demanda_anual: 24000,
  dias_anio: 288,
  turnos_dia: 2,
  horas_turno: 8,
  contenido_min: 240,
  estaciones: 22,
};

export function calcularLinea(e: EntradaLinea) {
  const disponible_min = e.dias_anio * e.turnos_dia * e.horas_turno * 60;
  const takt_min = disponible_min / e.demanda_anual;
  const estaciones_min = Math.ceil(e.contenido_min / takt_min - 1e-9);
  const ciclo_min = e.contenido_min / e.estaciones;
  const capacidad_maxima_anual = disponible_min / ciclo_min;
  return {
    disponible_min,
    takt_min,
    estaciones_min,
    ciclo_min,
    capacidad_maxima_anual,
    produccion_anual: Math.min(capacidad_maxima_anual, e.demanda_anual),
    deficit_anual: Math.max(e.demanda_anual - capacidad_maxima_anual, 0),
    cumple: ciclo_min <= takt_min + 1e-9,
  };
}

/** Cola acumulada (chasises) tras `t_min` minutos de operación cuando c > takt. */
export function colaAcumulada(e: EntradaLinea, t_min: number): number {
  const { takt_min, ciclo_min } = calcularLinea(e);
  if (ciclo_min <= takt_min) return 0;
  return Math.floor(t_min / takt_min) - Math.floor(t_min / ciclo_min);
}
