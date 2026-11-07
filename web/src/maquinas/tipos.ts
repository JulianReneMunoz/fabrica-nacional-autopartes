/** Definición declarativa de una máquina: texto, controles y pestañas. Las páginas solo aportan escena y lógica. */
export type IdPestana = "sistema" | "componentes" | "empresa" | "ficha" | "faq";

export interface DefControl {
  id: string;
  etiqueta: string;
  min: number;
  max: number;
  paso: number;
  unidad: string;
  decimales?: number;
}

export interface DefExperimento {
  pregunta: string;
  opciones: { texto: string; correcta: boolean }[];
}

export interface DefComponente {
  nombre: string;
  funcion: string;
}

export interface DefinicionMaquina {
  id: string;
  ruta: string;
  /** Etiqueta de la navegación principal. */
  navegacion: string;
  pregunta: string;
  formula: string;
  /** Una línea de contexto bajo la fórmula. */
  contexto: string;
  /** Idea principal: una sola frase. */
  idea: string;
  pasos: string[];
  experimentos: DefExperimento[];
  controles: DefControl[];
  pestanas: IdPestana[];
  /** Lista estática de componentes (máquinas 2D; las 3D la obtienen del backend). */
  componentes?: DefComponente[];
  /** Duración del recorrido automático (s); 0 = la vista no tiene recorrido. */
  duracionRecorrido: number;
  /** Texto breve para la biblioteca y la lámina. */
  lamina: "freno" | "prensa" | "linea" | "moto_honda";
  revisionExtra: string[];
  /** `false` = la vista no tiene tarjeta propia en la biblioteca (solo navegación); por omisión, sí. */
  enBiblioteca?: boolean;
  /** Botones adicionales de la tarjeta (p. ej. «Explorar piezas» en la moto). */
  enlacesExtra?: { texto: string; ruta: string }[];
}
