/**
 * Voz de IGNIS (prompt v2, secciones 2.3 y 2.4).
 * - Segmenta el texto que llega por streaming en oraciones.
 * - Cola de lectura: POST /api/v1/tts (WAV generado en el servidor) → cadena de Web Audio → AnalyserNode.
 * - Respaldo: speechSynthesis del navegador si /tts no responde.
 * - Expone la amplitud en un objeto mutable (sin re-renderizar React) para el escáner del auto:
 *   con TTS es la medida real del analizador; con speechSynthesis, un pulso por palabra (`onboundary`).
 * - `MicrofonoIgnis` mide el volumen del micrófono con su propio analizador mientras se escucha.
 */
import { leerAmplitud, pulsarAmplitud, type AmplitudCompartida } from "./escanerIgnis";

export type { AmplitudCompartida } from "./escanerIgnis";

/** Separa oraciones completas; devuelve las completas y el resto pendiente. */
export function extraerOraciones(texto: string): { oraciones: string[]; resto: string } {
  // Una oración termina en . ! ? … (con comillas o paréntesis de cierre opcionales) seguida de espacio.
  // «3.5» no corta porque después del punto no hay espacio. Lo que queda sin espacio final sigue pendiente.
  const oraciones: string[] = [];
  let inicio = 0;
  for (let i = 0; i < texto.length; i++) {
    if (!".!?…".includes(texto[i])) continue;
    let fin = i + 1;
    while (fin < texto.length && "\"»”)'".includes(texto[fin])) fin++;
    if (fin < texto.length && /\s/.test(texto[fin])) {
      const o = texto.slice(inicio, fin).trim();
      if (o) oraciones.push(o);
      inicio = fin;
      i = fin;
    }
  }
  return { oraciones, resto: texto.slice(inicio).replace(/^\s+/, "") };
}

export interface OpcionesVoz {
  amplitud: AmplitudCompartida;
  alIniciar?: () => void;
  alTerminar?: () => void;
  alOracion?: (oracion: string) => void;
}

export class VozIgnis {
  private cola: string[] = [];
  private activa = false;
  private silencio = false;
  private vol = 0.8;
  private ritmo = 1;
  private ctx: AudioContext | null = null;
  private fuente: AudioBufferSourceNode | null = null;
  private generacion = 0;
  private ttsDisponible = true;

  constructor(private readonly op: OpcionesVoz) {}

  get hablando(): boolean {
    return this.activa;
  }

  silenciar(valor: boolean) {
    this.silencio = valor;
    if (valor) this.detener();
  }

  volumen(v: number) {
    this.vol = Math.min(1, Math.max(0, v));
  }

  /** Velocidad de lectura (0,7–1,4). Se aplica desde la oración siguiente. */
  velocidad(v: number) {
    this.ritmo = Math.min(1.4, Math.max(0.7, v));
  }

  encolar(oracion: string) {
    const o = oracion.trim();
    if (!o) return;
    this.cola.push(o);
    if (!this.activa) void this.procesar();
  }

  /** Corta la lectura actual y vacía la cola. */
  detener() {
    this.generacion++;
    this.cola = [];
    try {
      this.fuente?.stop();
    } catch {
      /* ya detenida */
    }
    if (typeof window !== "undefined" && "speechSynthesis" in window) window.speechSynthesis.cancel();
    this.soltarAmplitud();
    if (this.activa) {
      this.activa = false;
      this.op.alTerminar?.();
    }
  }

  private async procesar() {
    const gen = this.generacion;
    this.activa = true;
    this.op.alIniciar?.();
    while (this.cola.length > 0 && gen === this.generacion) {
      const oracion = this.cola.shift()!;
      this.op.alOracion?.(oracion);
      if (this.silencio) continue;
      try {
        if (!this.ttsDisponible) throw new Error("tts no disponible");
        await this.leerConTts(oracion, gen);
      } catch {
        this.ttsDisponible = false;
        await this.leerConNavegador(oracion, gen);
      }
    }
    if (gen === this.generacion) {
      this.activa = false;
      this.soltarAmplitud();
      this.op.alTerminar?.();
    }
  }

  private soltarAmplitud() {
    if (this.op.amplitud.fuente === "analizador") this.op.amplitud.fuente = "ninguna";
    this.op.amplitud.valor = 0;
  }

  private async leerConTts(oracion: string, gen: number) {
    const r = await fetch("/api/v1/tts", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ texto: oracion }),
    });
    if (!r.ok) throw new Error(`TTS HTTP ${r.status}`);
    const datos = await r.arrayBuffer();
    if (gen !== this.generacion) return;
    const AC = window.AudioContext ?? (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
    this.ctx ??= new AC();
    const ctx = this.ctx;
    if (ctx.state === "suspended") await ctx.resume();
    const buffer = await ctx.decodeAudioData(datos);

    // Cadena de robotización: paso banda → modulador en anillo (≈40 Hz) → saturación suave → eco metálico.
    const fuente = ctx.createBufferSource();
    fuente.buffer = buffer;
    fuente.playbackRate.value = this.ritmo;
    const pasoBanda = ctx.createBiquadFilter();
    pasoBanda.type = "bandpass";
    pasoBanda.frequency.value = 1100;
    pasoBanda.Q.value = 0.9;
    const anillo = ctx.createGain();
    anillo.gain.value = 0.55;
    const osc = ctx.createOscillator();
    osc.frequency.value = 40;
    const prof = ctx.createGain();
    prof.gain.value = 0.45;
    osc.connect(prof).connect(anillo.gain);
    const sat = ctx.createWaveShaper();
    const curva = new Float32Array(256);
    for (let i = 0; i < 256; i++) {
      const x = (i / 255) * 2 - 1;
      curva[i] = Math.round(Math.tanh(2.2 * x) * 12) / 12; // cuantización leve (efecto «bitcrusher» suave)
    }
    sat.curve = curva;
    const eco = ctx.createDelay(0.2);
    eco.delayTime.value = 0.045;
    const ecoGanancia = ctx.createGain();
    ecoGanancia.gain.value = 0.28;
    const analizador = ctx.createAnalyser();
    analizador.fftSize = 512;
    const salida = ctx.createGain();
    salida.gain.value = this.vol;

    fuente.connect(pasoBanda).connect(anillo).connect(sat);
    sat.connect(analizador);
    sat.connect(eco).connect(ecoGanancia).connect(analizador);
    analizador.connect(salida).connect(ctx.destination);

    const muestras = new Uint8Array(new ArrayBuffer(analizador.fftSize));
    let animacion = 0;
    const medir = () => {
      this.op.amplitud.fuente = "analizador";
      this.op.amplitud.valor = leerAmplitud(analizador, muestras);
      animacion = requestAnimationFrame(medir);
    };

    this.fuente = fuente;
    await new Promise<void>((resolver) => {
      fuente.onended = () => {
        cancelAnimationFrame(animacion);
        osc.stop();
        this.soltarAmplitud();
        resolver();
      };
      osc.start();
      fuente.start();
      medir();
    });
    this.fuente = null;
  }

  private leerConNavegador(oracion: string, gen: number): Promise<void> {
    if (typeof window === "undefined" || !("speechSynthesis" in window) || gen !== this.generacion) return Promise.resolve();
    return new Promise((resolver) => {
      const u = new SpeechSynthesisUtterance(oracion);
      u.lang = "es-CO";
      u.pitch = 0.4;
      u.rate = 0.95 * this.ritmo;
      u.volume = this.vol;
      // speechSynthesis no expone el audio: cada palabra leída (onboundary) es un pulso de amplitud.
      u.onboundary = () => pulsarAmplitud(this.op.amplitud);
      // Algunos navegadores no disparan «onend» (sin voces instaladas): un tope evita que la cola quede colgada.
      const tope = window.setTimeout(() => terminar(), Math.max(3000, oracion.length * 110));
      let terminado = false;
      const terminar = () => {
        if (terminado) return;
        terminado = true;
        window.clearTimeout(tope);
        resolver();
      };
      u.onend = terminar;
      u.onerror = terminar;
      window.speechSynthesis.speak(u);
    });
  }
}

/**
 * Volumen del micrófono para el escáner mientras IGNIS escucha. Usa su propio AnalyserNode sobre
 * getUserMedia; el reconocimiento de voz (Web Speech API) sigue por separado. El audio no sale del navegador.
 */
export class MicrofonoIgnis {
  private ctx: AudioContext | null = null;
  private flujo: MediaStream | null = null;
  private animacion = 0;
  private activo = false;

  constructor(private readonly amplitud: AmplitudCompartida) {}

  /** Devuelve false si no hay permiso o el navegador no expone getUserMedia (el escáner usa eventos). */
  async iniciar(): Promise<boolean> {
    if (this.activo) return true;
    if (typeof navigator === "undefined" || !navigator.mediaDevices?.getUserMedia) return false;
    this.activo = true;
    try {
      const flujo = await navigator.mediaDevices.getUserMedia({ audio: true });
      if (!this.activo) {
        flujo.getTracks().forEach((p) => p.stop());
        return false;
      }
      this.flujo = flujo;
      const AC = window.AudioContext ?? (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
      this.ctx = new AC();
      const analizador = this.ctx.createAnalyser();
      analizador.fftSize = 512;
      this.ctx.createMediaStreamSource(flujo).connect(analizador);
      const muestras = new Uint8Array(new ArrayBuffer(analizador.fftSize));
      const medir = () => {
        this.amplitud.fuente = "analizador";
        this.amplitud.valor = leerAmplitud(analizador, muestras);
        this.animacion = requestAnimationFrame(medir);
      };
      medir();
      return true;
    } catch {
      this.activo = false;
      return false;
    }
  }

  detener() {
    this.activo = false;
    cancelAnimationFrame(this.animacion);
    this.flujo?.getTracks().forEach((p) => p.stop());
    this.flujo = null;
    void this.ctx?.close().catch(() => undefined);
    this.ctx = null;
    if (this.amplitud.fuente === "analizador") this.amplitud.fuente = "ninguna";
    this.amplitud.valor = 0;
  }
}
