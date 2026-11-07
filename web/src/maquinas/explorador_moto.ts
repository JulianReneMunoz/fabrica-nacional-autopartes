/**
 * Vista «Explorador de la motocicleta» (fase 14) sobre el ensamblaje genérico `moto_honda`.
 * Aquí solo vive la configuración de la interfaz (rótulos de la plantilla, iconos, anclas de las etiquetas y
 * lecciones relacionadas). El texto informativo de sistemas y piezas sale de la definición del ensamblaje
 * (`GET /simulador/ensamblajes/moto_honda/sistemas` y `/piezas`); los datos, de la ficha con fuente y estado.
 */
import type { Ancla } from "../paginas/EscenaMoto";
import type { DefinicionMaquina } from "./tipos";

export const EXPLORADOR_MOTO: DefinicionMaquina = {
  id: "moto_explorador",
  ruta: "#/maquina/moto_honda/explorador",
  navegacion: "Explorador",
  pregunta: "¿Qué sistemas forman una motocicleta y qué hace cada uno?",
  formula: "pieza → sistema → función",
  contexto:
    "Las piezas del ensamblaje genérico moto_honda se agrupan en diez sistemas; cada texto sale de la definición del ensamblaje, de la ficha técnica con su fuente o de la base de conocimiento con cita.",
  idea: "Una motocicleta es una cadena de sistemas: el motor genera el giro, la transmisión lo adapta, las ruedas lo llevan al suelo, y los frenos, la suspensión y la dirección lo controlan.",
  pasos: [
    "Pasar el cursor sobre la moto: cada pieza muestra su contorno",
    "Pulsar una pieza, una etiqueta o un botón de la franja inferior: se encuadra su sistema y el resto se atenúa",
    "Leer en el panel la función del sistema y de cada una de sus piezas",
    "Revisar los datos de la ficha técnica relacionados, con su fuente y su estado",
    "Preguntar sobre una pieza o abrir la lección de la máquina relacionada",
  ],
  experimentos: [
    {
      pregunta: "¿Qué sistema convierte la presión hidráulica en fricción contra un disco?",
      opciones: [
        { texto: "Los frenos", correcta: true },
        { texto: "La suspensión", correcta: false },
        { texto: "La transmisión", correcta: false },
      ],
    },
    {
      pregunta: "¿Qué piezas llevan el giro de la caja de cambios a la rueda trasera?",
      opciones: [
        { texto: "El silenciador y el colector", correcta: false },
        { texto: "El piñón, la cadena y la corona", correcta: true },
        { texto: "El monoamortiguador y el basculante", correcta: false },
      ],
    },
  ],
  controles: [],
  pestanas: ["sistema", "empresa", "faq"],
  duracionRecorrido: 0,
  lamina: "moto_honda",
  enBiblioteca: false, // se abre desde la tarjeta de la moto («Explorar piezas») y desde la navegación
  revisionExtra: [
    "Sin logotipos ni marca: el proyecto no es un canal oficial",
    "Se usa el GLB genérico moto_honda: sin fotos ni diseños de motos comerciales",
    "Sin datos comerciales: el explorador no es un catálogo de venta",
    "Un dato que no existe en la ficha se muestra como «No publicado»",
  ],
};

/** Sistemas de la franja inferior, en el orden del ensamblaje. El nombre y la función llegan del backend. */
export const ORDEN_SISTEMAS = [
  "motor",
  "transmision",
  "frenos",
  "suspension",
  "iluminacion",
  "electrico",
  "carroceria",
  "ruedas",
  "escape",
  "direccion",
] as const;
export type IdSistema = (typeof ORDEN_SISTEMAS)[number];

/** Iconos propios (trazo de 24×24, sin marcas): cada uno es una lista de trazados SVG. */
export const ICONOS_SISTEMA: Record<IdSistema, string[]> = {
  motor: ["M7 9h10v9H7z", "M5 11h2M5 14h2M17 11h2M17 14h2", "M9 6h6v3H9z", "M12 3v3"],
  transmision: ["M7 12m-3 0a3 3 0 1 0 6 0a3 3 0 1 0-6 0", "M17 12m-4 0a4 4 0 1 0 8 0a4 4 0 1 0-8 0", "M7 9l10-1M7 15l10 1"],
  frenos: ["M12 12m-7 0a7 7 0 1 0 14 0a7 7 0 1 0-14 0", "M12 12m-2 0a2 2 0 1 0 4 0a2 2 0 1 0-4 0", "M15 3h4v6h-4z"],
  suspension: ["M12 3v3", "M8 6l8 2-8 2 8 2-8 2 8 2", "M12 18v3", "M9 3h6M9 21h6"],
  iluminacion: ["M4 8a5 5 0 0 1 0 8z", "M4 8h4v8H4", "M11 9l9-2M11 12h9M11 15l9 2"],
  electrico: ["M13 3L6 13h5l-1 8 7-10h-5z"],
  carroceria: ["M3 15l4-6h6l3 3h5v3z", "M7 15v2M17 15v2", "M9 9l1-3h3"],
  ruedas: ["M12 12m-8 0a8 8 0 1 0 16 0a8 8 0 1 0-16 0", "M12 12m-2 0a2 2 0 1 0 4 0a2 2 0 1 0-4 0", "M12 4v6M12 14v6M4 12h6M14 12h6"],
  escape: ["M3 9h8l3 3h4", "M18 9h3v6h-3z", "M3 13h7l3 3h5"],
  direccion: ["M3 9c3 0 5 2 9 2s6-2 9-2", "M12 11v10", "M3 9v-2M21 9v-2", "M9 21h6"],
};

/** Lección relacionada: la máquina que explica el sistema (solo donde existe). */
export const LECCIONES: Partial<Record<IdSistema, { ruta: string; titulo: string }>> = {
  motor: { ruta: "#/maquina/moto_honda?vista=corte", titulo: "Corte del motor y ciclo de 4 tiempos" },
  frenos: { ruta: "#/maquina/freno", titulo: "Freno de disco: T = 2·μ·p·A·r" },
  transmision: { ruta: "#/maquina/moto_honda?vista=transmision", titulo: "Velocidad por marcha: piñón, cadena y corona" },
};

/** Etiquetas de sistema alrededor de la moto: el punto cae sobre la pieza ancla y la línea guía llega a la caja. */
export interface EtiquetaSistema {
  clave: string;
  texto: string;
  sistema: IdSistema;
  ancla: Ancla;
}
export const ETIQUETAS_SISTEMA: EtiquetaSistema[] = [
  { clave: "retrovisores", texto: "Retrovisores", sistema: "direccion", ancla: { pieza: "espejo_derecho", desfase: [0, 0, 0], pref: [70, -60] } },
  { clave: "manubrio", texto: "Manubrio", sistema: "direccion", ancla: { pieza: "manubrio", desfase: [0, 0, 0.12], pref: [-50, -95] } },
  { clave: "faro", texto: "Faro", sistema: "iluminacion", ancla: { pieza: "farola", desfase: [0.03, 0, 0], pref: [115, -35] } },
  { clave: "suspension_delantera", texto: "Suspensión delantera", sistema: "suspension", ancla: { pieza: "botella_derecha", desfase: [0, 0, 0], pref: [125, 10] } },
  { clave: "freno_delantero", texto: "Freno delantero", sistema: "frenos", ancla: { pieza: "disco_delantero", desfase: [0.07, 0.05, 0.005], pref: [110, 75] } },
  { clave: "transmision", texto: "Transmisión (cadena y kit)", sistema: "transmision", ancla: { pieza: "cadena", desfase: [-0.02, -0.07, 0.075], pref: [-20, 95] } },
  { clave: "motor", texto: "Motor", sistema: "motor", ancla: { pieza: "cilindro", desfase: [0.02, 0.02, 0.04], pref: [40, 115] } },
  { clave: "freno_trasero", texto: "Freno trasero", sistema: "frenos", ancla: { pieza: "disco_trasero", desfase: [-0.07, 0.07, 0], pref: [-115, 60] } },
  { clave: "suspension_trasera", texto: "Suspensión trasera", sistema: "suspension", ancla: { pieza: "monoamortiguador", desfase: [0, 0, 0], pref: [-70, -105] } },
  { clave: "escape", texto: "Escape", sistema: "escape", ancla: { pieza: "silenciador", desfase: [0, 0, 0], pref: [-40, 90] } },
  { clave: "asiento", texto: "Asiento", sistema: "carroceria", ancla: { pieza: "sillin", desfase: [0, 0.02, 0], pref: [10, -115] } },
];

/** Términos que el explorador no muestra nunca (no es un catálogo comercial). */
export const TERMINOS_PROHIBIDOS = /precio|disponibilidad|disponible|stock|carrito|referencia de repuesto|n\.º de parte|número de parte|\$\s?\d/i;
