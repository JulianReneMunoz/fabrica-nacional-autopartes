/**
 * Máquina de estados de la conversación con IGNIS (prompt v2, sección 2.2). El avatar es solo el auto: lo único
 * que cambia con el estado es el escáner rojo del frente (ver `modoDesdeConversacion` en escanerIgnis.ts).
 * Módulo puro: sin React ni Three.js, para probarlo con Vitest. Los temporizadores viven en la vista.
 */
import { ESPERA_A_REPOSO } from "./escanerIgnis";

export type EstadoAvatarIgnis =
  | "auto"
  | "escribiendo"
  | "escuchando"
  | "pensando"
  | "respondiendo"
  | "hablando"
  | "mostrando_archivo";

export const ESTADOS_IGNIS: readonly EstadoAvatarIgnis[] = [
  "auto",
  "escribiendo",
  "escuchando",
  "pensando",
  "respondiendo",
  "hablando",
  "mostrando_archivo",
];

export type EventoIgnis =
  /** Una tecla en la caja de texto. */
  | { type: "TECLA" }
  /** Pasó `PAUSA_TECLADO_MS` sin teclas. */
  | { type: "PAUSA_TECLADO" }
  | { type: "ACTIVAR_MICROFONO" }
  | { type: "FINALIZAR_ESCUCHA" }
  /** Mensaje enviado: se espera el primer token. */
  | { type: "ENVIAR_CONSULTA" }
  /** Llegó texto por SSE (token u oración). */
  | { type: "RECIBIR_TEXTO" }
  /** Empezó a sonar el TTS. */
  | { type: "INICIAR_HABLA" }
  /** La respuesta trajo un adjunto y terminó de leerse: se muestra la entrega. */
  | { type: "MOSTRAR_ENTREGABLE" }
  /** Terminaron el texto y la voz y pasó `ESPERA_A_REPOSO_MS`. */
  | { type: "VOLVER_A_REPOSO" }
  | { type: "FORZAR_AUTO" };

/** Milisegundos sin teclas antes de volver a reposo (1,5 s). */
export const PAUSA_TECLADO_MS = 1500;
/** Espera tras el fin del texto y de la voz antes de volver a reposo (1,5 s, compartida con el escáner). */
export const ESPERA_A_REPOSO_MS = ESPERA_A_REPOSO * 1000;
/** Tiempo que se muestra la entrega de un archivo antes de volver a reposo. */
export const DURACION_ENTREGA_MS = 2200;

/** Estados en los que IGNIS está ocupado con un turno (el teclado no los interrumpe). */
export function enTurno(estado: EstadoAvatarIgnis): boolean {
  return estado === "pensando" || estado === "respondiendo" || estado === "hablando" || estado === "mostrando_archivo";
}

/**
 * Transición con guardas: un evento que no aplica al estado actual no lo cambia.
 * Ningún evento lleva a un estado fuera de `ESTADOS_IGNIS`.
 */
export function transicionarEstadoIgnis(actual: EstadoAvatarIgnis, evento: EventoIgnis): EstadoAvatarIgnis {
  switch (evento.type) {
    case "FORZAR_AUTO":
      return "auto";
    case "TECLA":
      return actual === "auto" || actual === "escribiendo" ? "escribiendo" : actual;
    case "PAUSA_TECLADO":
      return actual === "escribiendo" ? "auto" : actual;
    case "ACTIVAR_MICROFONO":
      // La vista detiene la voz antes de abrir el micrófono; mientras se espera la respuesta no se escucha.
      return actual === "pensando" || actual === "respondiendo" ? actual : "escuchando";
    case "FINALIZAR_ESCUCHA":
      return actual === "escuchando" ? "auto" : actual;
    case "ENVIAR_CONSULTA":
      return "pensando";
    case "RECIBIR_TEXTO":
      return actual === "pensando" ? "respondiendo" : actual;
    case "INICIAR_HABLA":
      return actual === "pensando" || actual === "respondiendo" ? "hablando" : actual;
    case "MOSTRAR_ENTREGABLE":
      return enTurno(actual) ? "mostrando_archivo" : actual;
    case "VOLVER_A_REPOSO":
      // «pensando» también vuelve: una respuesta con error o vacía nunca llega a «respondiendo».
      return enTurno(actual) ? "auto" : actual;
    default:
      return actual;
  }
}

/** Etiqueta del chip de estado en el escenario. */
export const ETIQUETA_ESTADO: Record<EstadoAvatarIgnis, string> = {
  auto: "En reposo",
  escribiendo: "Escribiendo",
  escuchando: "Escuchando",
  pensando: "Pensando",
  respondiendo: "Respondiendo",
  hablando: "Hablando",
  mostrando_archivo: "Entregando archivo",
};
