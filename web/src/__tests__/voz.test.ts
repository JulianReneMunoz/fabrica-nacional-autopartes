import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { crearAmplitud } from "../escanerIgnis";
import {
  AVISO_VOZ_ESPANA,
  ESPERA_LIMITE_PALABRA_MS,
  PERIODO_PULSO_MS,
  VOCES_PREFERIDAS,
  VozIgnis,
  elegirVoz,
  type VozNavegador,
} from "../ignisVoz";

const voz = (name: string, lang: string, localService = true): VozNavegador => ({ name, lang, localService });

describe("elegirVoz (respaldo del navegador)", () => {
  it("prefiere las voces de la lista, las locales antes que las remotas", () => {
    const voces = [
      voz("Google español de Estados Unidos", "es-US", false),
      voz("Microsoft Dalia Online", "es-MX", false),
      voz("Microsoft Sabina - Spanish (Mexico)", "es-MX", true),
    ];
    expect(elegirVoz(voces)).toEqual({ voz: voces[2], aviso: false });
    expect(VOCES_PREFERIDAS[0]).toBe("Microsoft Sabina");
  });

  it("entre preferidas remotas respeta el orden de la lista", () => {
    const voces = [voz("Google español de Estados Unidos", "es-US", false), voz("Paulina", "es-MX", false)];
    expect(elegirVoz(voces).voz?.name).toBe("Paulina");
  });

  it("sin preferidas usa otra voz local es-MX, es-US, es-419 o es-CO, en ese orden", () => {
    expect(elegirVoz([voz("Otra CO", "es-CO"), voz("Otra 419", "es-419")]).voz?.name).toBe("Otra 419");
    expect(elegirVoz([voz("Remota MX", "es-MX", false), voz("Local CO", "es_CO")]).voz?.name).toBe("Local CO");
  });

  it("es-ES solo como último recurso y con aviso; sin voz en español, null con aviso", () => {
    expect(elegirVoz([voz("Microsoft Helena", "es-ES"), voz("English", "en-US")])).toMatchObject({
      voz: { name: "Microsoft Helena" },
      aviso: true,
    });
    expect(elegirVoz([voz("English", "en-US")])).toEqual({ voz: null, aviso: true });
  });
});

/* ------------------------------------------------------------------ entorno de audio simulado */
interface Nodo {
  tipo: string;
  destinos: Nodo[];
  connect: (n: Nodo) => Nodo;
}

function crearNodo(tipo: string, extra: Record<string, unknown> = {}): Nodo {
  const nodo: Nodo = {
    tipo,
    destinos: [],
    connect: (n: Nodo) => {
      nodo.destinos.push(n);
      return n;
    },
    ...extra,
  };
  return nodo;
}

class AudioContextSimulado {
  static creados: string[] = [];
  state = "running";
  destination = crearNodo("salida");
  resume = async () => undefined;
  decodeAudioData = async () => ({ duracion: 1 });
  private registrar(tipo: string, extra: Record<string, unknown> = {}) {
    AudioContextSimulado.creados.push(tipo);
    return crearNodo(tipo, extra);
  }
  createBufferSource() {
    const fuente = this.registrar("fuente", { buffer: null, playbackRate: { value: 0 }, onended: null as null | (() => void) });
    (fuente as unknown as { start: () => void }).start = () =>
      setTimeout(() => (fuente as unknown as { onended: () => void }).onended(), 0);
    ultimaFuente = fuente;
    return fuente;
  }
  createAnalyser() {
    return this.registrar("analizador", { fftSize: 0, getByteTimeDomainData: (b: Uint8Array) => b.fill(128) });
  }
  createGain() {
    return this.registrar("ganancia", { gain: { value: 0 } });
  }
  createOscillator() {
    return this.registrar("oscilador");
  }
  createBiquadFilter() {
    return this.registrar("filtro");
  }
  createWaveShaper() {
    return this.registrar("saturacion");
  }
  createDelay() {
    return this.registrar("eco");
  }
}
let ultimaFuente: Nodo | null = null;

class UtteranceSimulada {
  voice: VozNavegador | null = null;
  lang = "";
  pitch = 0;
  rate = 0;
  volume = 0;
  onboundary: (() => void) | null = null;
  onend: (() => void) | null = null;
  onerror: (() => void) | null = null;
  constructor(readonly text: string) {}
}

function instalarNavegador(voces: VozNavegador[], estadoTts: number) {
  const habladas: UtteranceSimulada[] = [];
  vi.stubGlobal("AudioContext", AudioContextSimulado);
  vi.stubGlobal("requestAnimationFrame", () => 1);
  vi.stubGlobal("cancelAnimationFrame", () => undefined);
  vi.stubGlobal("SpeechSynthesisUtterance", UtteranceSimulada);
  vi.stubGlobal("speechSynthesis", {
    getVoices: () => voces,
    speak: (u: UtteranceSimulada) => habladas.push(u),
    cancel: () => undefined,
  });
  vi.stubGlobal("fetch", async () =>
    estadoTts === 200
      ? new Response(new Uint8Array(64), { status: 200, headers: { "Content-Type": "audio/wav" } })
      : new Response("Falta la voz", { status: estadoTts }),
  );
  return habladas;
}

const esperarMicrotareas = async () => {
  for (let i = 0; i < 10; i++) await Promise.resolve();
};

describe("VozIgnis", () => {
  beforeEach(() => {
    AudioContextSimulado.creados = [];
    ultimaFuente = null;
  });
  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  it("con /tts reproduce la voz del servidor sin cadena de robotización y a playbackRate 1.0", async () => {
    instalarNavegador([], 200);
    const terminado = new Promise<void>((resolver) => {
      new VozIgnis({ amplitud: crearAmplitud(), alTerminar: resolver }).encolar("Hola, soy IGNIS.");
    });
    await terminado;
    expect(AudioContextSimulado.creados).toEqual(["fuente", "analizador", "ganancia"]);
    expect(AudioContextSimulado.creados).not.toContain("oscilador");
    const fuente = ultimaFuente as unknown as Nodo & { playbackRate: { value: number } };
    expect(fuente.playbackRate.value).toBe(1);
    // fuente → analizador → ganancia → salida
    expect(fuente.destinos[0].tipo).toBe("analizador");
    expect(fuente.destinos[0].destinos[0].tipo).toBe("ganancia");
    expect(fuente.destinos[0].destinos[0].destinos[0].tipo).toBe("salida");
  });

  it.each([503, 401])("con /tts %i pasa a speechSynthesis con la voz elegida, pitch 1 y rate 0.95", async (estado) => {
    const habladas = instalarNavegador([voz("Microsoft Helena", "es-ES"), voz("Microsoft Sabina", "es-MX")], estado);
    new VozIgnis({ amplitud: crearAmplitud() }).encolar("Hola.");
    await vi.waitFor(() => expect(habladas).toHaveLength(1));
    const u = habladas[0];
    expect(u.voice?.name).toBe("Microsoft Sabina");
    expect(u.lang).toBe("es-MX");
    expect(u.pitch).toBe(1);
    expect(u.rate).toBeCloseTo(0.95);
    expect(AudioContextSimulado.creados).toEqual([]);
    u.onend?.();
  });

  it("con solo voz es-ES avisa una sola vez", async () => {
    const habladas = instalarNavegador([voz("Microsoft Helena", "es-ES")], 503);
    const avisos: string[] = [];
    const vozIgnis = new VozIgnis({ amplitud: crearAmplitud(), alAviso: (m) => avisos.push(m) });
    vozIgnis.encolar("Primera.");
    vozIgnis.encolar("Segunda.");
    await vi.waitFor(() => expect(habladas).toHaveLength(1));
    habladas[0].onend?.();
    await vi.waitFor(() => expect(habladas).toHaveLength(2));
    habladas[1].onend?.();
    expect(avisos).toEqual([AVISO_VOZ_ESPANA]);
  });

  it("sin onboundary en 400 ms emite pulsos a 4 Hz mientras habla; con onboundary, un pulso por palabra", async () => {
    vi.useFakeTimers();
    const habladas = instalarNavegador([voz("Paulina", "es-MX")], 503);
    const amplitud = crearAmplitud();
    new VozIgnis({ amplitud }).encolar("Una oración larga para el respaldo del navegador.");
    await esperarMicrotareas();
    await vi.waitFor(() => expect(habladas).toHaveLength(1));

    vi.advanceTimersByTime(ESPERA_LIMITE_PALABRA_MS - 1);
    expect(amplitud.eventos).toBe(0);
    vi.advanceTimersByTime(1 + PERIODO_PULSO_MS * 4);
    expect(amplitud.eventos).toBe(4);

    habladas[0].onend?.();
    vi.advanceTimersByTime(PERIODO_PULSO_MS * 4);
    expect(amplitud.eventos).toBe(4); // al terminar se detienen los pulsos

    const otra = crearAmplitud();
    const habladas2 = instalarNavegador([voz("Paulina", "es-MX")], 503);
    new VozIgnis({ amplitud: otra }).encolar("Otra oración.");
    await esperarMicrotareas();
    await vi.waitFor(() => expect(habladas2).toHaveLength(1));
    habladas2[0].onboundary?.();
    habladas2[0].onboundary?.();
    vi.advanceTimersByTime(ESPERA_LIMITE_PALABRA_MS + PERIODO_PULSO_MS * 2);
    expect(otra.eventos).toBe(2); // hubo palabras: sin pulsos de respaldo
    habladas2[0].onend?.();
  });
});
