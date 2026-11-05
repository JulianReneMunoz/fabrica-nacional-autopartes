/**
 * Cinemática del conjunto pistón-biela-cigüeñal sobre un cilindro INCLINADO (puro, sin three ni React).
 * El eje del cilindro `u` sale de la articulación `j_piston` del simulador; el pistón y el bulón se mueven a lo
 * largo de `u` (x(θ) de `moto.ts`), la muñequilla gira alrededor del centro del cigüeñal en sentido horario y
 * la biela se inclina φ = asin(r·sin θ / L) respecto al eje.
 */
import { anguloBielaRad, posicionPistonM } from "./moto";

export interface PuntoXY {
  x: number;
  y: number;
}
export interface Mecanismo {
  /** Desplazamiento del pistón desde el PMS a lo largo de `u` (m, ≤ 0 hacia el cigüeñal). */
  desplazamiento: number;
  /** Posición del bulón del pistón y de la muñequilla en el plano de la moto. */
  bulon: PuntoXY;
  muneca: PuntoXY;
  /** Giro de la biela respecto a su pose base (rad). */
  phi: number;
}

export function mecanismoMotor(thetaRad: number, ejeCilindro: readonly [number, number], centro: readonly [number, number], carreraM: number, bielaM: number): Mecanismo {
  const [ux, uy] = ejeCilindro;
  const r = carreraM / 2;
  const x = posicionPistonM(thetaRad, carreraM, bielaM);
  const ct = Math.cos(-thetaRad);
  const st = Math.sin(-thetaRad);
  return {
    desplazamiento: x - posicionPistonM(0, carreraM, bielaM),
    bulon: { x: centro[0] + x * ux, y: centro[1] + x * uy },
    muneca: { x: centro[0] + r * (ux * ct - uy * st), y: centro[1] + r * (ux * st + uy * ct) },
    phi: anguloBielaRad(thetaRad, carreraM, bielaM),
  };
}
