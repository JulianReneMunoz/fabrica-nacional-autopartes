/**
 * Voz de IGNIS (prompt v2, secciones 2.3 y 2.4; voz neuronal con Piper en el servidor).
 * - Segmenta el texto que llega por streaming en oraciones.
 * - Cola de lectura: POST /api/v1/tts (WAV de Piper, voz femenina es-MX) → fuente → analizador → ganancia →
 *   salida. Sin efectos: la voz suena tal como la genera el servidor, a `playbackRate` 1.0 (la velocidad se
 *   regula en el servidor con FNA_VOZ_LENGTH_SCALE para no alterar el tono).
 * - Respaldo: speechSynthesis del navegador si /tts falla (401, 503 sin modelo, red), con la voz que elige
 *   `elegirVoz` (es-MX y Latinoamérica primero; es-ES solo como último recurso, con un aviso una sola vez).
 * - Expone la amplitud en un objeto mutable (sin re-renderizar React) para el escáner del auto: con TTS es la
 *   medida real del analizador; con speechSynthesis, un pulso por palabra (`onboundary`) o, si el navegador no
 *   emite esos eventos, pulsos a 4 Hz mientras habla.
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
  /** Aviso para la interfaz (por ejemplo, voz de respaldo en español de España). Se emite una sola vez. */
  alAviso?: (mensaje: string) => void;
}

/** Voces preferidas del respaldo, en orden (nombre parcial, sin distinguir mayúsculas). */
export const VOCES_PREFERIDAS = ["Microsoft Sabina", "Microsoft Dalia", "Paulina", "Google español de Estados Unidos"];
/** Variantes de español aceptables sin aviso, en orden de preferencia. */
const IDIOMAS_LATAM = ["es-mx", "es-us", "es-419", "es-co"];

/** Lo que `elegirVoz` necesita de `SpeechSynthesisVoice` (permite probarla sin navegador). */
export interface VozNavegador {
  name: string;
  lang: string;
  localService: boolean;
}

export const AVISO_VOZ_ESPANA =
  "La voz del servidor no está disponible y el navegador solo tiene voz en español de España: se usa esa voz.";

const idioma = (v: VozNavegador) => v.lang.replace("_", "-").toLowerCase();

/**
 * Voz del respaldo: primero las de `VOCES_PREFERIDAS` (las locales antes que las remotas); si no hay, otra voz
 * local es-MX, es-US, es-419 o es-CO (en ese orden; después las remotas); es-ES solo como último recurso, con
 * `aviso: true`. Sin ninguna voz en español devuelve `voz: null` y `aviso: true`.
 */
export function elegirVoz<T extends VozNavegador>(voces: readonly T[]): { voz: T | null; aviso: boolean } {
  const indicePreferida = (v: T) =>
    VOCES_PREFERIDAS.findIndex((p) => v.name.toLowerCase().includes(p.toLowerCase()));
  const preferidas = voces
    .filter((v) => indicePreferida(v) >= 0)
    .sort((a, b) => Number(b.localService) - Number(a.localService) || indicePreferida(a) - indicePreferida(b));
  if (preferidas.length) return { voz: preferidas[0], aviso: false };

  const latam = voces
    .filter((v) => IDIOMAS_LATAM.includes(idioma(v)))
    .sort(
      (a, b) =>
        Number(b.localService) - Number(a.localService) ||
        IDIOMAS_LATAM.indexOf(idioma(a)) - IDIOMAS_LATAM.indexOf(idioma(b)),
    );
  if (latam.length) return { voz: latam[0], aviso: false };

  const espana = voces
    .filter((v) => idioma(v) === "es-es")
    .sort((a, b) => Number(b.localService) - Number(a.localService));
  return { voz: espana[0] ?? null, aviso: true };
}

/** Milisegundos sin `onboundary` antes de pasar a los pulsos de respaldo (4 Hz = cada 250 ms). */
export const ESPERA_LIMITE_PALABRA_MS = 400;
export const PERIODO_PULSO_MS = 250;

/* ------------------------------------------------------------------ texto para la voz */
/** Lo que se lee en lugar de un bloque JSON (el chat lo muestra completo). */
export const AVISO_DATOS = "los datos aparecen en pantalla";
const MARCA_DATOS = "\u0000DATOS\u0000";

/**
 * Corta los bloques JSON de una oración. `profundidad` es el número de llaves que quedaron abiertas en las
 * oraciones anteriores (el backend parte el JSON en varias oraciones): mientras sea mayor que cero, el texto se
 * descarta hasta que las llaves se cierran. Un `{"` o `{}` que abre un bloque se reemplaza por una marca que
 * `limpiarParaVoz` convierte en `AVISO_DATOS`. Función pura.
 */
export function cortarJson(oracion: string, profundidad = 0): { visible: string; profundidad: number } {
  let nivel = profundidad;
  // El backend recorta el JSON (json.dumps(...)[:420]), así que sus llaves pueden no cerrarse nunca. Con un bloque
  // abierto, una oración sin comillas ya no es JSON: si empieza en minúscula es el resto truncado («robots.txt
  // permi.») y se descarta; si no, el bloque terminó y la oración se lee normalmente («Origen: …»).
  if (nivel > 0 && !oracion.includes('"')) {
    nivel = 0;
    if (/^[\s\p{Ll}\d.,;:/-]/u.test(oracion)) return { visible: "", profundidad: 0 };
  }
  let visible = "";
  for (let i = 0; i < oracion.length; i++) {
    const c = oracion[i];
    if (nivel > 0) {
      if (c === "{") nivel++;
      else if (c === "}") nivel--;
      continue;
    }
    if (c === "{" && /^\{\s*("|\})/.test(oracion.slice(i, i + 40))) {
      visible += MARCA_DATOS;
      nivel = 1;
      continue;
    }
    visible += c;
  }
  return { visible, profundidad: nivel };
}

const EXTENSIONES = "json|jsonl|csv|pdf|glb|ya?ml|txt|md";

/**
 * Limpia una oración ya sin JSON para leerla en voz alta (no cambia el texto visible del chat): quita marcadores
 * `[id]`, URL, acentos graves, nombres de archivo, markdown y enumeraciones «1)»; convierte «|» y «→» en pausas,
 * «_» en espacios y «%» en «por ciento»; agrega «¿» o «¡» si faltan. Devuelve "" si no queda nada que leer.
 */
export function limpiarParaVoz(texto: string): string {
  let t = texto;
  t = t.replace(/\(\s*(?:https?:\/\/|www\.)[^)\s]*\s*\)/gi, " "); // paréntesis que solo contienen una URL
  t = t.replace(/(?:https?:\/\/|www\.)\S+/gi, " ");
  t = t.replace(/\[[^\]\s]{1,80}\]/g, " "); // marcadores [id] o [f12]
  t = t.replace(new RegExp(`[\\w./\\\\-]*\\.(?:${EXTENSIONES})\\b`, "gi"), " ");
  t = t.replace(/`/g, "");
  t = t.replace(/\*\*|__/g, "");
  t = t.replace(/(^|\s)#{1,6}\s*/g, "$1");
  t = t.replace(/(^|\s)>\s*/g, "$1");
  t = t.replace(/(^|\s)[-•]\s+/g, "$1");
  t = t.replace(/^\s*\d{1,2}\)\s*/, "");
  t = t.replace(/\s*[|→]\s*/g, ", ");
  t = t.replace(/_/g, " ");
  t = t.replace(/(\d)\s*%/g, "$1 por ciento").replace(/%/g, " por ciento");
  t = t.replace(/\(\s*\)/g, " ").replace(/[()]/g, "");
  t = t.split(MARCA_DATOS).join(` ${AVISO_DATOS} `);
  t = t.replace(new RegExp(`(${AVISO_DATOS}[\\s,.:;]*){2,}`, "g"), `${AVISO_DATOS} `);
  // Espacios y puntuación: sin espacio antes de los signos, sin signos repetidos ni al inicio.
  t = t.replace(/\s+/g, " ");
  t = t.replace(/\s+([,.;:?!…])/g, "$1");
  t = t.replace(/([,;:])(?:\s*[,;:])+/g, "$1");
  t = t.replace(/[,;:]\s*([.?!])/g, "$1");
  t = t.replace(/^[\s,.;:]+/, "").trim();
  if (!/[\p{L}\p{N}]/u.test(t)) return "";
  if (t.endsWith("?") && !t.includes("¿")) t = `¿${t}`;
  if (t.endsWith("!") && !t.includes("¡")) t = `¡${t}`;
  return t.charAt(0).toUpperCase() + t.slice(1);
}

/** Texto que se lee de una oración (sin estado: un JSON sin cerrar se corta al final de la oración). */
export function textoParaVoz(oracion: string): string {
  return limpiarParaVoz(cortarJson(oracion).visible);
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
  private avisado = false;
  /** Llaves de un bloque JSON abierto en una oración anterior (el backend lo parte en varias oraciones). */
  private profundidadJson = 0;
  private temporizadores: number[] = [];

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

  /**
   * Velocidad de lectura (0,7–1,4) para la voz del navegador. La voz de Piper se reproduce siempre a 1.0: su
   * velocidad la fija el servidor (FNA_VOZ_LENGTH_SCALE) para no alterar el tono.
   */
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
    this.profundidadJson = 0;
    this.limpiarTemporizadores();
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
      this.op.alOracion?.(oracion); // los subtítulos muestran el texto tal cual
      if (this.silencio) continue;
      // Lo que se lee: sin JSON, [id], URL, archivos ni markdown. Si no queda nada, la oración no se lee.
      const corte = cortarJson(oracion, this.profundidadJson);
      this.profundidadJson = corte.profundidad;
      const lectura = limpiarParaVoz(corte.visible);
      if (!lectura) continue;
      try {
        if (!this.ttsDisponible) throw new Error("tts no disponible");
        await this.leerConTts(lectura, gen);
      } catch {
        this.ttsDisponible = false;
        await this.leerConNavegador(lectura, gen);
      }
    }
    this.profundidadJson = 0;
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

  private limpiarTemporizadores() {
    for (const id of this.temporizadores) {
      window.clearTimeout(id);
      window.clearInterval(id);
    }
    this.temporizadores = [];
  }

  private async leerConTts(oracion: string, gen: number) {
    // 401 (sesión vencida), 503 (falta la voz en el servidor) o un fallo de red: el turno sigue con el respaldo.
    const r = await fetch("/api/v1/tts", {
      method: "POST",
      credentials: "same-origin",
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

    // Cadena directa, sin efectos: fuente → analizador (mueve los LED) → ganancia (volumen) → salida.
    const fuente = ctx.createBufferSource();
    fuente.buffer = buffer;
    fuente.playbackRate.value = 1; // la velocidad la fija el servidor; cambiarla aquí alteraría el tono
    const analizador = ctx.createAnalyser();
    analizador.fftSize = 512;
    const salida = ctx.createGain();
    salida.gain.value = this.vol;
    fuente.connect(analizador).connect(salida).connect(ctx.destination);

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
        this.soltarAmplitud();
        resolver();
      };
      fuente.start();
      medir();
    });
    this.fuente = null;
  }

  private leerConNavegador(oracion: string, gen: number): Promise<void> {
    if (typeof window === "undefined" || !("speechSynthesis" in window) || gen !== this.generacion) return Promise.resolve();
    return new Promise((resolver) => {
      const u = new SpeechSynthesisUtterance(oracion);
      const { voz, aviso } = elegirVoz(window.speechSynthesis.getVoices());
      if (voz) u.voice = voz;
      u.lang = voz?.lang ?? "es-MX";
      u.pitch = 1;
      u.rate = 0.95 * this.ritmo;
      u.volume = this.vol;
      if (aviso && !this.avisado) {
        this.avisado = true;
        this.op.alAviso?.(AVISO_VOZ_ESPANA);
      }

      // speechSynthesis no expone el audio: cada palabra leída (onboundary) es un pulso de amplitud. Si en
      // 400 ms no llega ninguno (algunos navegadores no los emiten), pulsos a 4 Hz mientras dure la lectura.
      let huboPalabra = false;
      u.onboundary = () => {
        huboPalabra = true;
        pulsarAmplitud(this.op.amplitud);
      };
      const espera = window.setTimeout(() => {
        if (huboPalabra || terminado) return;
        this.temporizadores.push(window.setInterval(() => pulsarAmplitud(this.op.amplitud), PERIODO_PULSO_MS));
      }, ESPERA_LIMITE_PALABRA_MS);
      // Algunos navegadores no disparan «onend» (sin voces instaladas): un tope evita que la cola quede colgada.
      const tope = window.setTimeout(() => terminar(), Math.max(3000, oracion.length * 110));
      this.temporizadores.push(espera, tope);
      let terminado = false;
      const terminar = () => {
        if (terminado) return;
        terminado = true;
        this.limpiarTemporizadores();
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
