/**
 * Prensa excéntrica de estampado (máquina demostrativa del método Anatomy).
 *
 * Relación medible:  F = L · t · τ   (fuerza de corte = perímetro · espesor · resistencia al corte)
 * Cinemática biela-manivela (posición del carro medida desde el punto muerto superior):
 *   s(θ) = r(1 − cos θ) + l − √(l² − r² sin² θ)
 *
 * Valores de τ: rangos típicos publicados para aceros de embutición y estructurales
 * (τ ≈ 0,8 · resistencia a la tracción). Son DEMOSTRATIVOS, no especificaciones de Fanalca.
 */

export interface Material {
  id: string;
  nombre: string;
  tau_mpa: number;
}

export const MATERIALES: Material[] = [
  { id: "dc04", nombre: "Acero de embutición (DC04)", tau_mpa: 280 },
  { id: "s355", nombre: "Acero estructural (S355)", tau_mpa: 400 },
  { id: "hsla", nombre: "Acero alta resistencia (HSLA 420)", tau_mpa: 450 },
];

export interface EntradaPrensa {
  perimetro_mm: number;
  espesor_mm: number;
  tau_mpa: number;
  capacidad_t: number;
  radio_manivela_mm: number;
  longitud_biela_mm: number;
}

export const ENTRADA_PRENSA_DEFECTO: EntradaPrensa = {
  perimetro_mm: 1200,
  espesor_mm: 2,
  tau_mpa: 280,
  capacidad_t: 200,
  radio_manivela_mm: 120,
  longitud_biela_mm: 600,
};

const KN_POR_T = 9.80665;

export function fuerzaCorte(e: EntradaPrensa) {
  const fuerza_n = e.perimetro_mm * e.espesor_mm * e.tau_mpa; // mm·mm·N/mm² = N
  const fuerza_kn = fuerza_n / 1000;
  const toneladas = fuerza_kn / KN_POR_T;
  const uso = toneladas / e.capacidad_t;
  return { fuerza_kn, toneladas, uso, excede: uso > 1 };
}

/** Desplazamiento del carro (mm) desde el punto muerto superior para un ángulo θ (rad). */
export function carrera(e: EntradaPrensa, theta: number): number {
  const r = e.radio_manivela_mm;
  const l = e.longitud_biela_mm;
  return r * (1 - Math.cos(theta)) + l - Math.sqrt(l * l - r * r * Math.sin(theta) ** 2);
}

/** Ángulo de manivela en que el punzón toca la lámina (inicio del corte) y la atraviesa. */
export function ventanaCorte(e: EntradaPrensa) {
  const recorrido = 2 * e.radio_manivela_mm;
  const contacto = recorrido - e.espesor_mm - 4; // 4 mm de penetración del punzón (demostrativo)
  const busca = (objetivo: number) => {
    let lo = 0;
    let hi = Math.PI;
    for (let i = 0; i < 60; i++) {
      const mid = (lo + hi) / 2;
      if (carrera(e, mid) < objetivo) lo = mid;
      else hi = mid;
    }
    return lo;
  };
  return { inicio: busca(contacto), fin: busca(contacto + e.espesor_mm) };
}
