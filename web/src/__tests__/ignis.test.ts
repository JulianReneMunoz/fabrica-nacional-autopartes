import { describe, expect, it } from "vitest";
import { avanzarAmplitud, crearAmplitud, leerAmplitud, modoDesdeConversacion, pulsarAmplitud } from "../escanerIgnis";
import { CASOS_VALIDACION } from "../ignisCasos";
import {
  crearLectorSSE,
  etiquetaModeracion,
  etiquetaRuta,
  interpretarEvento,
  normalizarHerramienta,
  normalizarOrigen,
  urlAdjuntoPermitida,
  type EventoConversacion,
} from "../ignisCliente";
import { distanciaEncuadre, limitesZoom, posicionEncuadre } from "../ignisEncuadre";
import { ESTADOS_IGNIS, ETIQUETA_ESTADO, transicionarEstadoIgnis, type EstadoAvatarIgnis, type EventoIgnis } from "../ignisStateMachine";
import { extraerOraciones } from "../ignisVoz";

const EVENTOS: EventoIgnis[] = [
  { type: "TECLA" },
  { type: "PAUSA_TECLADO" },
  { type: "ACTIVAR_MICROFONO" },
  { type: "FINALIZAR_ESCUCHA" },
  { type: "ENVIAR_CONSULTA" },
  { type: "RECIBIR_TEXTO" },
  { type: "INICIAR_HABLA" },
  { type: "MOSTRAR_ENTREGABLE" },
  { type: "VOLVER_A_REPOSO" },
  { type: "FORZAR_AUTO" },
];

describe("máquina de estados de IGNIS (solo auto)", () => {
  const t = transicionarEstadoIgnis;

  it("ningún evento lleva a un estado fuera de los siete del auto (sin robot)", () => {
    const permitidos = new Set<string>(ESTADOS_IGNIS);
    expect(ESTADOS_IGNIS).toEqual(["auto", "escribiendo", "escuchando", "pensando", "respondiendo", "hablando", "mostrando_archivo"]);
    for (const estado of ESTADOS_IGNIS) {
      for (const evento of EVENTOS) {
        const siguiente = t(estado, evento);
        expect(permitidos.has(siguiente), `${estado} + ${evento.type} → ${siguiente}`).toBe(true);
        expect(siguiente).not.toMatch(/robot|transform/);
      }
    }
    expect(Object.keys(ETIQUETA_ESTADO).sort()).toEqual([...ESTADOS_IGNIS].sort());
  });

  it("escribir lleva a «escribiendo» y la pausa del teclado vuelve a reposo", () => {
    expect(t("auto", { type: "TECLA" })).toBe("escribiendo");
    expect(t("escribiendo", { type: "TECLA" })).toBe("escribiendo");
    expect(t("escribiendo", { type: "PAUSA_TECLADO" })).toBe("auto");
    // Mientras IGNIS responde o habla, el teclado no cambia el estado.
    expect(t("respondiendo", { type: "TECLA" })).toBe("respondiendo");
    expect(t("hablando", { type: "TECLA" })).toBe("hablando");
  });

  it("recorre el turno de texto: pensando → respondiendo → reposo", () => {
    let e: EstadoAvatarIgnis = "escribiendo";
    e = t(e, { type: "ENVIAR_CONSULTA" });
    expect(e).toBe("pensando");
    e = t(e, { type: "RECIBIR_TEXTO" });
    expect(e).toBe("respondiendo");
    expect(t(e, { type: "RECIBIR_TEXTO" })).toBe("respondiendo");
    expect(t(e, { type: "VOLVER_A_REPOSO" })).toBe("auto");
  });

  it("con voz pasa a «hablando», entrega el archivo y vuelve a reposo", () => {
    let e: EstadoAvatarIgnis = t("auto", { type: "ENVIAR_CONSULTA" });
    e = t(e, { type: "RECIBIR_TEXTO" });
    e = t(e, { type: "INICIAR_HABLA" });
    expect(e).toBe("hablando");
    e = t(e, { type: "MOSTRAR_ENTREGABLE" });
    expect(e).toBe("mostrando_archivo");
    expect(t(e, { type: "VOLVER_A_REPOSO" })).toBe("auto");
  });

  it("el micrófono abre «escuchando» salvo mientras se espera la respuesta", () => {
    expect(t("auto", { type: "ACTIVAR_MICROFONO" })).toBe("escuchando");
    expect(t("hablando", { type: "ACTIVAR_MICROFONO" })).toBe("escuchando");
    expect(t("pensando", { type: "ACTIVAR_MICROFONO" })).toBe("pensando");
    expect(t("escuchando", { type: "FINALIZAR_ESCUCHA" })).toBe("auto");
  });

  it("ignora eventos que no aplican y no vuelve a reposo desde la escucha", () => {
    expect(t("auto", { type: "RECIBIR_TEXTO" })).toBe("auto");
    expect(t("auto", { type: "INICIAR_HABLA" })).toBe("auto");
    expect(t("auto", { type: "MOSTRAR_ENTREGABLE" })).toBe("auto");
    expect(t("escuchando", { type: "VOLVER_A_REPOSO" })).toBe("escuchando");
    expect(t("pensando", { type: "VOLVER_A_REPOSO" })).toBe("auto");
  });

  it("cada estado tiene su modo de escáner", () => {
    expect(modoDesdeConversacion("auto")).toBe("reposo");
    expect(modoDesdeConversacion("escribiendo")).toBe("escuchando");
    expect(modoDesdeConversacion("escuchando")).toBe("escuchando");
    expect(modoDesdeConversacion("pensando")).toBe("pensando");
    expect(modoDesdeConversacion("respondiendo")).toBe("hablando");
    expect(modoDesdeConversacion("hablando")).toBe("hablando");
  });
});

describe("amplitud del escáner", () => {
  it("cada tecla, token o palabra suma un pulso que se apaga solo", () => {
    const a = crearAmplitud();
    pulsarAmplitud(a);
    const v1 = avanzarAmplitud(a, 1 / 60);
    expect(v1).toBeGreaterThan(0.3);
    expect(a.eventos).toBe(0);
    let v = v1;
    for (let i = 0; i < 120; i++) v = avanzarAmplitud(a, 1 / 60);
    expect(v).toBe(0);
    expect(a.fuente).toBe("ninguna");
  });

  it("un analizador activo manda sobre los pulsos", () => {
    const a = crearAmplitud();
    a.fuente = "analizador";
    a.valor = 0.62;
    pulsarAmplitud(a, 5);
    expect(a.eventos).toBe(0);
    expect(avanzarAmplitud(a, 1 / 60)).toBeCloseTo(0.62);
  });

  it("leerAmplitud mide el RMS del AnalyserNode (silencio = 0)", () => {
    const silencio = { getByteTimeDomainData: (b: Uint8Array) => b.fill(128) };
    expect(leerAmplitud(silencio, new Uint8Array(new ArrayBuffer(64)))).toBe(0);
    const fuerte = { getByteTimeDomainData: (b: Uint8Array) => b.forEach((_, i) => (b[i] = i % 2 ? 255 : 0)) };
    expect(leerAmplitud(fuerte, new Uint8Array(new ArrayBuffer(64)))).toBe(1);
  });
});

describe("encuadre automático del auto", () => {
  it("el auto completo cabe: más lejos con un lienzo angosto que con uno ancho", () => {
    const ancho = distanciaEncuadre(2.5, 34, 16 / 9);
    const angosto = distanciaEncuadre(2.5, 34, 0.6);
    expect(angosto).toBeGreaterThan(ancho);
    // La esfera de radio r a distancia d ocupa como mucho el campo de visión vertical.
    expect(Math.asin((2.5 * 1.12) / ancho) * 2).toBeLessThanOrEqual((34 * Math.PI) / 180 + 1e-9);
  });

  it("la cámara queda en la dirección pedida y los límites del zoom rodean el encuadre", () => {
    const [x, y, z] = posicionEncuadre([0, 0.6, 0], 2.5, 34, 1.5, [1, 0, 0]);
    expect(y).toBeCloseTo(0.6);
    expect(z).toBeCloseTo(0);
    expect(x).toBeCloseTo(distanciaEncuadre(2.5, 34, 1.5));
    const { min, max } = limitesZoom(2.5, 34, 1.5);
    expect(min).toBeLessThan(x);
    expect(max).toBeGreaterThan(x);
  });
});

describe("cliente SSE", () => {
  it("reconstruye eventos partidos entre fragmentos y con \\r\\n", () => {
    const eventos: EventoConversacion[] = [];
    const lector = crearLectorSSE((e) => eventos.push(e));
    lector.alimentar('data: {"tipo":"token","texto":"Hola"}\r\n\r\ndata: {"tipo":"tok');
    lector.alimentar('en","texto":" mundo"}\n\nevent: metadatos\ndata: {"ruta_router":"rag","citas":[{"fragmento_id":"f1","titulo":"Doc 1","url":"https://x.co"}]}\n\n');
    lector.cerrar();
    expect(eventos).toEqual([
      { tipo: "token", texto: "Hola" },
      { tipo: "token", texto: " mundo" },
      { tipo: "metadatos", datos: { ruta_router: "rag", score_router: undefined, blindaje_activado: false, bloqueada: false, citas: [{ id: "f1", titulo: "Doc 1", url: "https://x.co", origen: "demostrativo" }], adjuntos: undefined } },
    ]);
  });

  it("descarta adjuntos fuera de la lista blanca", () => {
    expect(interpretarEvento("adjunto", { id: "x", titulo: "Plano", url: "https://malicioso.com/a.pdf" })).toBeNull();
    expect(interpretarEvento("adjunto", { id: "x", url: "/app/assets/../../etc/passwd" })).toBeNull();
    const ok = interpretarEvento("adjunto", { id: "plano_ignis", tipo: "plano_2d", titulo: "Plano técnico 2D", formato: "pdf" });
    expect(ok).toMatchObject({ tipo: "adjunto", adjunto: { url: "/api/v1/adjuntos/plano_ignis", tipo: "plano_2d" } });
    expect(urlAdjuntoPermitida("//otro.com/x")).toBe(false);
  });

  it("conserva el origen de citas y adjuntos; sin origen válido se marcan demostrativo", () => {
    const meta = interpretarEvento(null, {
      tipo: "metadatos",
      citas: [
        { id: "f1", titulo: "Doc", url: "https://autopartesfanalca.com.co/", origen: "scraping" },
        { id: "f2", titulo: "Semilla", url: "", origen: "semilla" },
        { id: "f3", titulo: "Sin origen", url: "" },
      ],
      archivos_adjuntos: [{ url: "/app/assets/blueprint_2d.png", titulo: "Plano", tipo: "plano", formato: "PNG", origen: "demostrativo" }],
    });
    expect(meta).toMatchObject({ datos: { citas: [{ origen: "scraping" }, { origen: "semilla" }, { origen: "demostrativo" }] } });
    expect(meta).toMatchObject({ datos: { adjuntos: [{ origen: "demostrativo" }] } });
    expect(normalizarOrigen("lectura_web")).toBe("lectura_web");
    expect(normalizarOrigen("inventado")).toBe("demostrativo");
  });

  it("lee fuentes_datos, categoria_moderacion y normativa; descarta fuentes sin archivo y URL inválidas", () => {
    const meta = interpretarEvento(null, {
      tipo: "metadatos",
      fuentes_datos: [
        {
          archivo: "data/catalogo/ficha_fanalca.json",
          descripcion: "Ficha corporativa de Fanalca",
          origen: "lectura_web, scraping",
          urls: ["https://fanalca.com/", "javascript:alert(1)", "no es una url", "/relativa", 7],
        },
        { archivo: "", descripcion: "Sin archivo", origen: "scraping", urls: [] },
        null,
        "texto suelto",
        42,
        { archivo: "data/catalogo/motos_honda.yaml", origen: "inventado" },
      ],
      categoria_moderacion: "datos_de_terceros",
      normativa: "Ley 1581 de 2012",
    });
    expect(meta).toEqual({
      tipo: "metadatos",
      datos: expect.objectContaining({
        fuentes_datos: [
          {
            archivo: "data/catalogo/ficha_fanalca.json",
            descripcion: "Ficha corporativa de Fanalca",
            origen: "lectura_web, scraping",
            urls: ["https://fanalca.com/"],
          },
          { archivo: "data/catalogo/motos_honda.yaml", descripcion: "data/catalogo/motos_honda.yaml", origen: "demostrativo", urls: [] },
        ],
        categoria_moderacion: "datos_de_terceros",
        normativa: "Ley 1581 de 2012",
      }),
    });
    expect(etiquetaModeracion("amenaza_violencia")).toBe("Amenaza");
    expect(etiquetaModeracion("nueva")).toBe("nueva");
  });

  it("no interpreta etiquetas dentro del texto como adjuntos", () => {
    const e = interpretarEvento(null, { tipo: "token", texto: "[FILE_ATTACH: plano.pdf]" });
    expect(e).toEqual({ tipo: "token", texto: "[FILE_ATTACH: plano.pdf]" });
  });

  it("muestra las rutas del router con las etiquetas v2 sin cambiar el contrato", () => {
    expect(etiquetaRuta("rag_documental")).toBe("Documentos");
    expect(etiquetaRuta("herramienta_estructurada")).toBe("Datos");
    expect(etiquetaRuta("mixto")).toBe("Mixto");
    expect(etiquetaRuta("directo")).toBe("Directo");
    expect(etiquetaRuta("bloqueado_salvaguarda")).toBe("Bloqueado");
    expect(etiquetaRuta("ruta_nueva")).toBe("ruta_nueva");
  });
});

describe("segmentador de oraciones", () => {
  it("corta en fin de oración seguido de espacio y conserva el resto", () => {
    expect(extraerOraciones("Hola. ¿Cómo estás? Bien")).toEqual({ oraciones: ["Hola.", "¿Cómo estás?"], resto: "Bien" });
  });
  it("no corta decimales ni pierde texto", () => {
    const r = extraerOraciones("El valor es 3.5 metros. Siguiente");
    expect(r.oraciones).toEqual(["El valor es 3.5 metros."]);
    expect(r.resto).toBe("Siguiente");
  });
});

describe("casos de validación", () => {
  it("incluye los ocho casos de la tabla B", () => {
    expect(CASOS_VALIDACION.map((c) => c.id)).toEqual(["1", "2A", "2B", "3", "4A", "4B", "5", "6"]);
    expect(CASOS_VALIDACION.find((c) => c.id === "2B")?.hiloNuevo).toBe(true);
  });
});

describe("codificación", () => {
  // Vite entrega el contenido crudo de cada fuente; no hace falta acceso a disco.
  const fuentes = import.meta.glob("../**/*.{ts,tsx,css}", { query: "?raw", import: "default", eager: true }) as Record<string, string>;

  it("ningún archivo fuente tiene texto con codificación rota (mojibake) ni BOM", () => {
    expect(Object.keys(fuentes).length).toBeGreaterThan(10);
    const rotos = Object.entries(fuentes)
      .filter(([, texto]) => /Ã[\u0080-¿]|Â[\u0080-¿]|ðŸ|â€/.test(texto) || texto.startsWith("﻿"))
      .map(([ruta]) => ruta);
    expect(rotos).toEqual([]);
  });
});

describe("herramienta del turno en los metadatos (R08, caso 3)", () => {
  const HERRAMIENTA = {
    nombre: "consultar_datos_estructurados_fanalca",
    argumentos: { tipo_consulta: "ficha_moto", filtro: "cb160f" },
    fuente_archivo: "data/catalogo/motos_honda.yaml",
    verificado: true,
    resumen: { claves: ["version_esquema", "fuentes", "modelos"], total_claves: 3, elementos: { fuentes: 2, modelos: 1 } },
  };

  it("lee la herramienta y la justificación del router desde el evento de metadatos", () => {
    const e = interpretarEvento(null, { tipo: "metadatos", ruta_router: "herramienta_estructurada", justificacion_router: "Ficha técnica.", herramienta: HERRAMIENTA });
    expect(e?.tipo).toBe("metadatos");
    if (e?.tipo !== "metadatos") return;
    expect(e.datos.justificacion_router).toBe("Ficha técnica.");
    expect(e.datos.herramienta).toEqual({
      nombre: "consultar_datos_estructurados_fanalca",
      argumentos: { tipo_consulta: "ficha_moto", filtro: "cb160f" },
      fuenteArchivo: "data/catalogo/motos_honda.yaml",
      verificado: true,
      resumen: { claves: ["version_esquema", "fuentes", "modelos"], totalClaves: 3, elementos: { fuentes: 2, modelos: 1 } },
    });
  });

  it("sin herramienta o con un valor que no es un objeto, el campo queda vacío", () => {
    for (const herramienta of [undefined, null, "consultar", 3, [HERRAMIENTA], { argumentos: {} }]) {
      const e = interpretarEvento(null, { tipo: "metadatos", ruta_router: "directo", herramienta });
      expect(e?.tipo === "metadatos" && e.datos.herramienta).toBeFalsy();
    }
  });

  it("acota el resumen: claves y textos recortados, sin objetos anidados ni números no finitos", () => {
    const h = normalizarHerramienta({
      nombre: "x".repeat(200),
      argumentos: { tipo_consulta: "ficha_moto", anidado: { a: 1 }, lista: [1, 2] },
      verificado: "sí",
      resumen: {
        claves: [...Array.from({ length: 30 }, (_, i) => `clave_${i}`), { no: "texto" }],
        total_claves: 31,
        elementos: { fuentes: 2, raro: Number.NaN, texto: "3" },
      },
    })!;
    expect(h.nombre).toHaveLength(80);
    expect(h.argumentos).toEqual({ tipo_consulta: "ficha_moto" });
    expect(h.verificado).toBe(false);
    expect(h.resumen.claves).toHaveLength(10);
    expect(h.resumen.totalClaves).toBe(31);
    expect(h.resumen.elementos).toEqual({ fuentes: 2 });
    expect(h.fuenteArchivo).toBe("");
  });
});
