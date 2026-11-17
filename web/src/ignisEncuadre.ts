/**
 * Encuadre automático del auto IGNIS (sección 2.1 del prompt v2). Módulo puro, sin Three.js.
 *
 * El auto se aproxima por su esfera envolvente (centro y radio del Box3 del GLB). La distancia de la cámara es
 * la mínima que deja la esfera completa dentro del campo de visión vertical y del horizontal, con un margen.
 */

/** Dirección de la cámara respecto del centro del auto: tres cuartos delanteros (frente +X), algo elevada. */
export const DIRECCION_ENCUADRE: readonly [number, number, number] = [0.78, 0.32, 0.62];

/** Margen sobre la esfera envolvente (1 = la esfera toca los bordes del lienzo). */
export const MARGEN_ENCUADRE = 1.12;

/** Límites del zoom manual: múltiplos del radio del auto. */
export const ZOOM_MIN = 0.55;
export const ZOOM_MAX = 2.6;

/**
 * Distancia de la cámara al centro para que una esfera de `radio` quepa entera.
 * @param fovGrados campo de visión vertical de la cámara
 * @param aspecto ancho / alto del lienzo
 */
export function distanciaEncuadre(radio: number, fovGrados: number, aspecto: number, margen = MARGEN_ENCUADRE): number {
  const r = Math.max(1e-3, radio) * margen;
  const fovV = (Math.max(1, Math.min(170, fovGrados)) * Math.PI) / 180;
  const fovH = 2 * Math.atan(Math.tan(fovV / 2) * Math.max(0.1, aspecto));
  const limitante = Math.min(fovV, fovH);
  return r / Math.sin(limitante / 2);
}

/** Posición de la cámara: centro + dirección normalizada × distancia de encuadre. */
export function posicionEncuadre(
  centro: readonly [number, number, number],
  radio: number,
  fovGrados: number,
  aspecto: number,
  direccion: readonly [number, number, number] = DIRECCION_ENCUADRE,
): [number, number, number] {
  const largo = Math.hypot(...direccion) || 1;
  const d = distanciaEncuadre(radio, fovGrados, aspecto);
  return [centro[0] + (direccion[0] / largo) * d, centro[1] + (direccion[1] / largo) * d, centro[2] + (direccion[2] / largo) * d];
}

/** Distancias mínima y máxima de los controles de órbita para un auto de `radio`. */
export function limitesZoom(radio: number, fovGrados: number, aspecto: number): { min: number; max: number } {
  const base = distanciaEncuadre(radio, fovGrados, aspecto);
  return { min: base * ZOOM_MIN, max: base * ZOOM_MAX };
}
