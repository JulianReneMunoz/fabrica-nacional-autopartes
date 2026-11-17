/**
 * Niveles de calidad visual de la escena de IGNIS (Fase 6, opción A).
 *
 * Módulo puro (sin React ni WebGL) para poder probarlo en jsdom. La escena arranca en el nivel indicado por
 * `?calidad=alto|medio|bajo` o, si no hay parámetro, en «alto»; luego `PerformanceMonitor` baja o sube un nivel
 * según los fps medidos.
 */
export type NivelCalidad = "alto" | "medio" | "bajo";

export interface ConfigCalidad {
  /** Rango de densidad de píxeles del lienzo. */
  dpr: [number, number];
  /** Resolución del piso reflectante; 0 = sin reflejos (piso mate + sombra de contacto). */
  reflector: number;
  /** Oclusión ambiental N8AO (contactos entre piezas y con el piso). */
  oclusion: boolean;
  /** Bloom, AgX, viñeta y SMAA. Sin posprocesado el tone mapping lo hace el renderer. */
  posprocesado: boolean;
  /** Tamaño del mapa de sombras de la luz principal. */
  sombra: number;
}

export const CONFIG_CALIDAD: Record<NivelCalidad, ConfigCalidad> = {
  alto: { dpr: [1, 2], reflector: 1024, oclusion: true, posprocesado: true, sombra: 2048 },
  medio: { dpr: [1, 1.5], reflector: 512, oclusion: false, posprocesado: true, sombra: 1024 },
  bajo: { dpr: [1, 1], reflector: 0, oclusion: false, posprocesado: false, sombra: 512 },
};

const ORDEN: NivelCalidad[] = ["bajo", "medio", "alto"];

export function bajarNivel(nivel: NivelCalidad): NivelCalidad {
  return ORDEN[Math.max(0, ORDEN.indexOf(nivel) - 1)];
}

export function subirNivel(nivel: NivelCalidad): NivelCalidad {
  return ORDEN[Math.min(ORDEN.length - 1, ORDEN.indexOf(nivel) + 1)];
}

/** Lee `calidad=` de la cadena de búsqueda o del hash (`#/atencion?calidad=bajo`). */
export function nivelDesdeUrl(busqueda: string, hash = ""): NivelCalidad | null {
  const extraer = (texto: string) => {
    const i = texto.indexOf("?");
    return i >= 0 ? new URLSearchParams(texto.slice(i + 1)).get("calidad") : null;
  };
  const valor = extraer(busqueda.startsWith("?") ? busqueda : `?${busqueda}`) ?? extraer(hash);
  return valor === "alto" || valor === "medio" || valor === "bajo" ? valor : null;
}

/** Nivel inicial: el de la URL si existe; si no, «alto» (PerformanceMonitor lo ajusta en caliente). */
export function nivelInicial(busqueda: string, hash = ""): NivelCalidad {
  return nivelDesdeUrl(busqueda, hash) ?? "alto";
}
