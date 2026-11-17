/**
 * Escáner rojo del frontal de IGNIS: barrido de lado a lado con estela.
 * Módulo puro (sin Three.js), probado con Vitest. Lo usa useEscanerIgnis.ts.
 *
 * Modos (coinciden con la máquina de estados del avatar):
 *  - reposo:     los segmentos centrales laten suavemente.
 *  - escuchando: la luz se abre del centro hacia afuera según el volumen del micrófono.
 *  - pensando:   barrido lento.
 *  - hablando:   barrido rápido; el brillo y la velocidad siguen la amplitud de la voz.
 */

export type ModoEscaner = 'reposo' | 'escuchando' | 'pensando' | 'hablando';

export interface OpcionesEscaner {
  /** Número de segmentos LED (el modelo trae 12: seg_00 … seg_11). */
  segmentos: number;
  /** Segundos de un recorrido completo izquierda → derecha → izquierda al hablar. */
  periodoHablando: number;
  /** Segundos del recorrido completo al pensar. */
  periodoPensando: number;
  /** Constante de tiempo de la estela, en segundos (más alto = estela más larga). */
  estela: number;
  /** Ancho del núcleo encendido, en segmentos. */
  anchoNucleo: number;
}

export const OPCIONES_POR_DEFECTO: OpcionesEscaner = {
  segmentos: 12,
  periodoHablando: 1.6,
  periodoPensando: 3.2,
  estela: 0.10,
  anchoNucleo: 1.15,
};

export interface EstadoEscaner {
  /** Fase del barrido en vueltas (0..1 = un recorrido de ida y vuelta). */
  fase: number;
  /** Tiempo acumulado, en segundos (para el latido de reposo). */
  tiempo: number;
  /** Nivel de cada segmento, 0..1. */
  niveles: number[];
}

export function crearEstado(opts: OpcionesEscaner = OPCIONES_POR_DEFECTO): EstadoEscaner {
  return { fase: 0, tiempo: 0, niveles: new Array(opts.segmentos).fill(0) };
}

/** Posición 0..1 del núcleo para una fase dada: ida y vuelta con frenado suave en los extremos. */
export function posicionBarrido(fase: number): number {
  const u = ((fase % 1) + 1) % 1;
  const triangulo = u < 0.5 ? u * 2 : 2 - u * 2;
  return 0.5 - 0.5 * Math.cos(Math.PI * triangulo);
}

/** Brillo de un segmento según su distancia al núcleo (0..1). */
export function nucleo(i: number, posicion: number, n: number, ancho: number): number {
  const centro = posicion * (n - 1);
  return Math.max(0, 1 - Math.abs(i - centro) / ancho);
}

const limitar = (x: number) => Math.min(1, Math.max(0, x));

/**
 * Avanza el escáner dt segundos. No muta `prev`.
 * @param amplitud 0..1: volumen de la voz (hablando) o del micrófono (escuchando).
 */
export function pasoEscaner(
  prev: EstadoEscaner,
  dt: number,
  modo: ModoEscaner,
  amplitud = 0,
  opts: OpcionesEscaner = OPCIONES_POR_DEFECTO,
): EstadoEscaner {
  const n = opts.segmentos;
  const a = limitar(amplitud);
  const tiempo = prev.tiempo + dt;
  let fase = prev.fase;
  const objetivo = new Array<number>(n).fill(0);
  let estela = opts.estela;

  if (modo === 'hablando') {
    fase += (dt / opts.periodoHablando) * (0.75 + 0.6 * a);
    const pos = posicionBarrido(fase);
    const brillo = 0.45 + 0.55 * a;
    for (let i = 0; i < n; i++) objetivo[i] = brillo * nucleo(i, pos, n, opts.anchoNucleo);
  } else if (modo === 'pensando') {
    fase += dt / opts.periodoPensando;
    const pos = posicionBarrido(fase);
    for (let i = 0; i < n; i++) objetivo[i] = 0.7 * nucleo(i, pos, n, opts.anchoNucleo * 1.3);
    estela = opts.estela * 1.6;
  } else if (modo === 'escuchando') {
    const centro = (n - 1) / 2;
    const medio = 0.6 + a * (n / 2);
    for (let i = 0; i < n; i++) {
      const d = Math.abs(i - centro);
      objetivo[i] = d <= medio ? 1 - 0.55 * (d / (n / 2)) : 0;
    }
    estela = opts.estela * 0.6;
  } else {
    const latido = 0.18 + 0.12 * Math.sin((2 * Math.PI * tiempo) / 3);
    for (let i = 0; i < n; i++) objetivo[i] = latido * nucleo(i, 0.5, n, 2.2);
    estela = opts.estela * 2;
  }

  const decaimiento = Math.exp(-dt / Math.max(estela, 1e-3));
  const niveles = prev.niveles.map((v, i) => limitar(Math.max(v * decaimiento, objetivo[i])));
  return { fase, tiempo, niveles };
}

/** Con prefers-reduced-motion: luz fija en el centro, sin barrido. */
export function nivelesSinMovimiento(modo: ModoEscaner, opts: OpcionesEscaner = OPCIONES_POR_DEFECTO): number[] {
  const n = opts.segmentos;
  const brillo = modo === 'reposo' ? 0.25 : 0.8;
  return Array.from({ length: n }, (_, i) => brillo * nucleo(i, 0.5, n, 2.2));
}

// ---------------------------------------------------------------------------
// Conexión con la conversación (texto y voz). El auto NO se transforma:
// solo cambia lo que hacen las luces del frontal.
// ---------------------------------------------------------------------------

/**
 * Estado de la conversación → modo del escáner.
 * Acepta los nombres de la máquina de estados de IGNIS (ignisStateMachine.ts);
 * cualquier otro valor (reposo o desconocido) cae en 'reposo'.
 */
export function modoDesdeConversacion(estado: string): ModoEscaner {
  switch (estado) {
    case 'escribiendo':      // el usuario teclea en la consola
    case 'escuchando':       // micrófono activo
      return 'escuchando';
    case 'pensando':         // mensaje enviado, esperando el primer token
      return 'pensando';
    case 'respondiendo':     // llegan tokens por SSE (con o sin voz)
    case 'hablando':         // suena el TTS
    case 'mostrando_archivo':
      return 'hablando';
    default:
      return 'reposo';
  }
}

/**
 * Amplitud 0..1 a partir de eventos discretos, para cuando no hay audio:
 * cada tecla pulsada, token SSE o palabra leída (onboundary) suma un pulso que se apaga solo.
 * @param eventos número de eventos ocurridos desde el frame anterior
 */
export function amplitudPorEventos(prev: number, dt: number, eventos: number, golpe = 0.35, caida = 0.18): number {
  return Math.min(1, prev * Math.exp(-dt / caida) + golpe * eventos);
}

/** Segundos que el escáner sigue en su modo tras el último evento, antes de volver a reposo. */
export const ESPERA_A_REPOSO = 1.5;

// ---------------------------------------------------------------------------
// Amplitud del escáner (sección 2.3 del prompt v2)
// ---------------------------------------------------------------------------

/** Volumen 0..1 (RMS ×4) a partir de un AnalyserNode: voz del TTS o micrófono. */
export function leerAmplitud(
  analizador: Pick<AnalyserNode, 'getByteTimeDomainData'>,
  buffer: Uint8Array<ArrayBuffer>,
): number {
  analizador.getByteTimeDomainData(buffer);
  let suma = 0;
  for (let i = 0; i < buffer.length; i++) {
    const v = (buffer[i] - 128) / 128;
    suma += v * v;
  }
  return buffer.length ? Math.min(1, Math.sqrt(suma / buffer.length) * 4) : 0;
}

/**
 * Amplitud compartida entre la voz, el chat y el escáner, sin pasar por el estado de React.
 * - `analizador`: hay un AnalyserNode activo (TTS o micrófono) que escribe `valor` en cada cuadro.
 * - `eventos`: no hay audio medible; cada tecla, token SSE o palabra (`onboundary`) suma un pulso.
 */
export interface AmplitudCompartida {
  valor: number;
  fuente: 'ninguna' | 'analizador' | 'eventos';
  /** Eventos ocurridos desde el último cuadro (solo con fuente «eventos»). */
  eventos: number;
}

export function crearAmplitud(): AmplitudCompartida {
  return { valor: 0, fuente: 'ninguna', eventos: 0 };
}

/** Registra un evento discreto (tecla, token o palabra). No pisa la medición de un analizador activo. */
export function pulsarAmplitud(a: AmplitudCompartida, n = 1): void {
  if (a.fuente === 'analizador') return;
  a.fuente = 'eventos';
  a.eventos += n;
}

/**
 * Avanza la amplitud un cuadro y devuelve el valor 0..1 para el escáner.
 * Con analizador se usa la medición tal cual; con eventos, `amplitudPorEventos` consume los pulsos.
 */
export function avanzarAmplitud(a: AmplitudCompartida, dt: number): number {
  if (a.fuente === 'analizador') return Math.min(1, Math.max(0, a.valor));
  a.valor = amplitudPorEventos(a.valor, dt, a.eventos);
  a.eventos = 0;
  if (a.valor < 1e-3) {
    a.valor = 0;
    a.fuente = 'ninguna';
  }
  return a.valor;
}
