import { FRENO } from "./freno";
import { LINEA } from "./linea";
import { MOTO_HONDA } from "./moto_honda";
import { PRENSA } from "./prensa";
import type { DefinicionMaquina } from "./tipos";

/** Registro único: la biblioteca, la navegación y el enrutador salen de aquí. Orden de la navegación. */
export const MAQUINAS: DefinicionMaquina[] = [FRENO, PRENSA, LINEA, MOTO_HONDA];
export const maquinaPorId = (id: string) => MAQUINAS.find((m) => m.id === id) ?? null;
export { FRENO, LINEA, MOTO_HONDA, PRENSA };
