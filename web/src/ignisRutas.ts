/**
 * Rutas de la aplicación IGNIS v2 (prompt v2, sección 1): barra lateral agrupada y redirecciones.
 * Módulo puro, sin React. El enrutador es por hash (`#/atencion`) porque FastAPI sirve el build en /app.
 */
import type { NombreIcono } from "./IgnisIconos";

export type IdPestana =
  | "atencion"
  | "faq"
  | "qa"
  | "proceso-datos"
  | "corpus"
  | "base"
  | "agente"
  | "herramientas"
  | "router"
  | "prompts"
  | "configuracion"
  | "rayos-x"
  | "seguridad"
  | "auditoria"
  | "panel"
  | "evaluacion"
  | "mlflow"
  | "kanban"
  | "arquitectura"
  | "sesion"
  | "ajustes";

export interface Pestana {
  id: IdPestana;
  etiqueta: string;
  icono: NombreIcono;
  /** Identificador del PR del plan que la implementa (no es el número real de GitHub). */
  pr: string;
  /** Qué mostrará la pestaña: se usa en el estado vacío mientras el endpoint no exista. */
  descripcion: string;
}

export interface GrupoNavegacion {
  titulo: string;
  pestanas: Pestana[];
}

export const GRUPOS: GrupoNavegacion[] = [
  {
    titulo: "Conversación",
    pestanas: [
      { id: "atencion", etiqueta: "Atención — IGNIS", icono: "auto", pr: "#38", descripcion: "Chat por texto y voz con IGNIS." },
      { id: "faq", etiqueta: "Preguntas frecuentes", icono: "faq", pr: "#38c", descripcion: "FAQ del corpus con búsqueda, citas y «Preguntar a IGNIS»." },
      { id: "qa", etiqueta: "Consulta puntual Q&A", icono: "chat", pr: "#38c", descripcion: "Pregunta sin memoria con el proveedor, el modelo y el modo de contexto elegidos." },
    ],
  },
  {
    titulo: "Datos y conocimiento",
    pestanas: [
      { id: "proceso-datos", etiqueta: "Proceso de datos", icono: "datos", pr: "#38c", descripcion: "Web scraping → bronce → plata → oro: fuentes, conteos por etapa, descartes, duplicados y última corrida." },
      { id: "corpus", etiqueta: "Corpus", icono: "corpus", pr: "#38c", descripcion: "Documentos y fragmentos con búsqueda y metadatos (URL, sección, fecha) y versión del corpus." },
      { id: "base", etiqueta: "Base de conocimiento — Qdrant", icono: "base", pr: "#34", descripcion: "Colección, vectores, parámetros HNSW y búsqueda híbrida, densa o léxica con puntaje por recuperador." },
    ],
  },
  {
    titulo: "Agente",
    pestanas: [
      { id: "agente", etiqueta: "Agente y memoria", icono: "memoria", pr: "#29", descripcion: "Hilos del usuario (checkpointer), memorias del Store y recorte de contexto." },
      { id: "herramientas", etiqueta: "Herramientas LangChain", icono: "herramienta", pr: "tools", descripcion: "Herramientas @tool con su esquema Pydantic, descripción y últimas llamadas." },
      { id: "router", etiqueta: "Router", icono: "ruta", pr: "#32", descripcion: "Decisiones recientes del router con puntaje y justificación." },
      { id: "prompts", etiqueta: "Prompts", icono: "prompt", pr: "#41", descripcion: "Prompt del sistema, estilo de respuesta y versiones v1–v3 en solo lectura." },
      { id: "configuracion", etiqueta: "Configuración de agentes", icono: "deslizadores", pr: "#38b", descripcion: "Proveedor, modelo y modo de contexto permitidos (lista blanca), k y modo de recuperación." },
    ],
  },
  {
    titulo: "Calidad y seguridad",
    pestanas: [
      { id: "rayos-x", etiqueta: "Rayos-X y validación", icono: "escaner", pr: "#40", descripcion: "Pipeline del turno con estados reales, evidencia y los casos 1 a 6." },
      { id: "seguridad", etiqueta: "Seguridad RAG", icono: "escudo", pr: "#33", descripcion: "Contadores de blindaje, moderación, citas verificadas y rechazos por umbral." },
      { id: "auditoria", etiqueta: "Auditoría", icono: "lista", pr: "#38c", descripcion: "Turnos de IGNIS y Q&A con consulta anonimizada, ruta, rechazo, blindaje y tiempos; exportar CSV." },
    ],
  },
  {
    titulo: "Observabilidad",
    pestanas: [
      { id: "panel", etiqueta: "Panel", icono: "grafica", pr: "monitor", descripcion: "Monitor RAG en vivo: consultas, latencia, rechazo, blindaje, tokens y costo." },
      { id: "evaluacion", etiqueta: "Evaluación", icono: "objetivo", pr: "#36", descripcion: "recall@5/@10, nDCG@10 y MRR@10 por modo sobre las 25 consultas etiquetadas." },
      { id: "mlflow", etiqueta: "Experimentos MLflow", icono: "matraz", pr: "#45", descripcion: "Corridas de evaluación y de prompts con parámetros, métricas y comparación." },
    ],
  },
  {
    titulo: "Proyecto",
    pestanas: [
      { id: "kanban", etiqueta: "Tablero Kanban", icono: "kanban", pr: "#46", descripcion: "PR del proyecto agrupados por estado, sincronizados con GitHub." },
      { id: "arquitectura", etiqueta: "Arquitectura y API", icono: "arquitectura", pr: "#42", descripcion: "Diagramas del grafo, memoria, herramientas, router y sesiones; estado de los servicios." },
    ],
  },
];

/** Pestañas del pie de la barra lateral. */
export const PESTANAS_PIE: Pestana[] = [
  { id: "sesion", etiqueta: "Mi sesión", icono: "usuario", pr: "#44", descripcion: "Alias, hilos del usuario con reabrir, «Nuevo hilo» y «Cerrar sesión»." },
  { id: "ajustes", etiqueta: "Ajustes", icono: "ajustes", pr: "#38c", descripcion: "Voz (silenciar, volumen, velocidad), tamaño de subtítulos y calidad gráfica." },
];

export const TODAS_LAS_PESTANAS: Pestana[] = [...GRUPOS.flatMap((g) => g.pestanas), ...PESTANAS_PIE];

export const PESTANA_INICIO: IdPestana = "atencion";

const POR_ID = new Map(TODAS_LAS_PESTANAS.map((p) => [p.id, p]));

export function pestanaPorId(id: IdPestana): Pestana {
  return POR_ID.get(id) ?? POR_ID.get(PESTANA_INICIO)!;
}

export function hashDe(id: IdPestana): string {
  return `#/${id}`;
}

export interface RutaResuelta {
  id: IdPestana;
  /** Parámetros después de «?» (por ejemplo `calidad=bajo`). */
  parametros: URLSearchParams;
  /** Hash canónico al que hay que redirigir, o null si el actual ya es válido. */
  redirigirA: string | null;
}

/**
 * Resuelve el hash a una pestaña. Las rutas del M1 retiradas (biblioteca, máquinas, prensa, línea, moto,
 * explorador, simulador, robot) y cualquier ruta desconocida redirigen a Atención, conservando los parámetros.
 */
export function resolverRuta(hash: string): RutaResuelta {
  const limpio = hash.replace(/^#/, "");
  const [ruta, consulta = ""] = limpio.split("?");
  const parametros = new URLSearchParams(consulta);
  const segmento = ruta.replace(/^\/+/, "").split("/")[0] as IdPestana;
  if (POR_ID.has(segmento) && ruta === `/${segmento}`) return { id: segmento, parametros, redirigirA: null };
  const destino = POR_ID.has(segmento) ? segmento : PESTANA_INICIO;
  return { id: destino, parametros, redirigirA: hashDe(destino) + (consulta ? `?${consulta}` : "") };
}
