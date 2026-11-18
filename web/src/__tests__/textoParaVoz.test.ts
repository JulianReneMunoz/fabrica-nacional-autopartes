import { afterEach, describe, expect, it, vi } from "vitest";
import { crearAmplitud } from "../escanerIgnis";
import { AVISO_DATOS, cortarJson, limpiarParaVoz, textoParaVoz, VozIgnis } from "../ignisVoz";

/**
 * Oraciones reales del motor de reglas (tal como las emite /ignis/stream, corpus semilla). Se leen sin JSON, [id],
 * URL, archivos ni markdown; el texto visible del chat no cambia.
 */
const ESTRUCTURADA = [
  'Dato exacto leído mediante consulta determinista con validación Pydantic desde `data/catalogo/motos_honda.yaml`: {"version_esquema": 1, "fuentes": {"lamina-cb160-std-dlx": {"descripcion": "Lámina comercial CB-160 (STD/DLX) aportada por el usuario; transcrita en docs/arquitectura/moto_honda.md (sección 3).',
  'No se muestra dentro de la aplicación.", "tipo": "documento_aportado_por_el_usuario", "url": null, "fecha_consulta": "2026-11-04"}, "motos.honda.com.co": {"descripcion": "Sitio oficial de Honda Motos Colombia.',
  "robots.txt permi.",
  "Origen: catálogo curado con fuente y estado por campo (https://motos.honda.com.co/).",
];
const MIXTO = [
  "Enrutamiento Mixto ejecutado.",
  '1) Cifras estructuradas (`data/gold/estadisticas.json`): {"documentos": 64, "fragmentos": 167, "tokens_aprox": 20958, "secciones": {"contacto": 1, "inicio": 8, "negocios/.',
  "Origen: corpus Gold (lectura_web, scraping) de 63 URL.",
  "2) Evidencia documental en corpus Fanalca: [sostenibilidad#001] (https://fanalca.com/en/sustainability/): ## Informes de sostenibilidad",
  "| [negocios-honda-autos#002] (https://fanalca.com/en/business/honda-autos/): ## Cifras de la unidad",
  "- 26 vitrinas en el país con servicio de ventas y posventa.",
];
const RAG = [
  "Según [sostenibilidad#001] (Sostenibilidad y Fundación Fanalca): ## Informes de sostenibilidad",
  "Según [sostenibilidad#000] (Sostenibilidad y Fundación Fanalca): # Sostenibilidad",
];

/** Lectura de una respuesta completa con el estado entre oraciones, como hace VozIgnis. */
function leer(oraciones: string[]): string[] {
  let profundidad = 0;
  return oraciones.map((o) => {
    const corte = cortarJson(o, profundidad);
    profundidad = corte.profundidad;
    return limpiarParaVoz(corte.visible);
  });
}

describe("textoParaVoz con respuestas reales", () => {
  it("herramienta estructurada: el JSON partido en varias oraciones se anuncia una vez y no se lee", () => {
    expect(leer(ESTRUCTURADA)).toEqual([
      `Dato exacto leído mediante consulta determinista con validación Pydantic desde: ${AVISO_DATOS}`,
      "", // dentro del JSON
      "", // resto truncado del JSON
      "Origen: catálogo curado con fuente y estado por campo.",
    ]);
  });

  it("mixto: sin enumeraciones, archivos, [id], URL, «|», viñetas ni markdown", () => {
    expect(leer(MIXTO)).toEqual([
      "Enrutamiento Mixto ejecutado.",
      `Cifras estructuradas: ${AVISO_DATOS}`,
      "Origen: corpus Gold lectura web, scraping de 63 URL.",
      "Evidencia documental en corpus Fanalca: Informes de sostenibilidad",
      "Cifras de la unidad",
      "26 vitrinas en el país con servicio de ventas y posventa.",
    ]);
  });

  it("rag_documental: «Según» con el título, sin [id] ni encabezados markdown", () => {
    expect(RAG.map(textoParaVoz)).toEqual([
      "Según Sostenibilidad y Fundación Fanalca: Informes de sostenibilidad",
      "Según Sostenibilidad y Fundación Fanalca: Sostenibilidad",
    ]);
  });

  it("ninguna lectura conserva restos técnicos", () => {
    for (const lectura of leer([...ESTRUCTURADA, ...MIXTO]).concat(RAG.map(textoParaVoz))) {
      expect(lectura).not.toMatch(/[{}[\]`|#_]|https?:|www\.|\.json|\.yaml|\.csv|\.pdf|\.glb|":/);
    }
  });
});

describe("reglas de textoParaVoz", () => {
  it.each([
    ["¿Cuál es el cilindraje de la CB 160F?", "¿Cuál es el cilindraje de la CB 160F?"],
    ["Cuál es el cilindraje de la CB 160F?", "¿Cuál es el cilindraje de la CB 160F?"],
    ["Hola!", "¡Hola!"],
    ["El 45% de las ventas.", "El 45 por ciento de las ventas."],
    ["Ruta → datos | documentos.", "Ruta, datos, documentos."],
    ["Ver **plano** en __modelo__.", "Ver plano en modelo."],
    ["> Cita del informe.", "Cita del informe."],
    ["• Primer punto.", "Primer punto."],
    ["Descargue plano_2d.pdf o ignis_auto.glb para revisarlo.", "Descargue o para revisarlo."],
    ["Visite www.fanalca.com para más datos.", "Visite para más datos."],
    ['Resultado: {"a": 1} listo.', `Resultado: ${AVISO_DATOS} listo.`],
    ["unidad_de_negocio y linea_producto", "Unidad de negocio y linea producto"],
  ])("%s → %s", (entrada, esperado) => {
    expect(textoParaVoz(entrada)).toBe(esperado);
  });

  it("una oración sin nada que leer queda vacía", () => {
    expect(textoParaVoz("[f12] (https://ejemplo.test/x)")).toBe("");
    expect(textoParaVoz('{"a": 1, "b": 2}')).toBe("Los datos aparecen en pantalla");
    expect(textoParaVoz(" | ")).toBe("");
  });
});

describe("VozIgnis lee el texto limpio y no cambia el texto visible", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("los subtítulos reciben la oración original y /tts recibe la lectura", async () => {
    const enviados: string[] = [];
    vi.stubGlobal("fetch", async (_url: string, init: RequestInit) => {
      enviados.push(JSON.parse(String(init.body)).texto);
      return new Response("Falta la voz", { status: 503 }); // sin voz: el respaldo no está en jsdom
    });
    const subtitulos: string[] = [];
    const terminado = new Promise<void>((resolver) => {
      const voz = new VozIgnis({ amplitud: crearAmplitud(), alOracion: (o) => subtitulos.push(o), alTerminar: resolver });
      RAG.forEach((o) => voz.encolar(o));
    });
    await terminado;
    expect(subtitulos).toEqual(RAG); // el texto visible no cambia
    expect(enviados).toEqual(["Según Sostenibilidad y Fundación Fanalca: Informes de sostenibilidad"]);
  });
});
