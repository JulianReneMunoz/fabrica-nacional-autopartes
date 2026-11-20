/**
 * Cliente de la API FastAPI del M1 (/api/v1) para las pestañas Corpus, Proceso de datos, Auditoría, FAQ y Q&A.
 * Todas las rutas son relativas al mismo origen. Los tipos reflejan los modelos Pydantic del backend
 * (`api/esquemas.py` y `domain/modelos.py`). El simulador, las máquinas y las motos ya no se usan en el frontend.
 */

const BASE = "/api/v1";

/* ---------------------------------------------------------------- tipos */
export interface Pagina<T> {
  elementos: T[];
  total: number;
  pagina: number;
  tamano: number;
}

export interface Fragmento {
  id: string;
  documento_id: string;
  url: string;
  titulo: string;
  seccion: string;
  encabezado: string;
  idioma: string;
  texto: string;
  tokens_aprox: number;
  orden: number;
  origen: "scraping" | "semilla" | "lectura_web";
}

export interface FragmentoBuscado {
  fragmento: Fragmento;
  puntaje: number | null;
}

export interface EstadisticasBase {
  documentos: number;
  fragmentos: number;
  tokens_aprox: number;
  secciones: Record<string, number>;
  origenes: Record<string, number>;
  urls: string[];
  generado_en: string | null;
}

/** Estado de la colección Qdrant de IGNIS (`InfoVectorial` en `domain/modelos.py`). */
export interface InfoVectorial {
  disponible: boolean;
  motivo: string;
  modo: "local" | "memoria" | "servidor";
  coleccion: string;
  puntos: number;
  dimension: number | null;
  distancia: string | null;
  hnsw_m: number;
  hnsw_ef_construct: number;
  umbral_busqueda_exacta_kb: number | null;
  vectores_indexados: number;
  tipo_busqueda: "exacta" | "hnsw";
  explicacion: string;
  campos_payload: string[];
  modelo: string;
  revision: string;
  generado_en: string | null;
  recuperador_ignis: string | null;
}

export interface Fuente {
  fragmento_id: string;
  titulo: string;
  url: string;
}

export interface RespuestaQa {
  pregunta: string;
  respuesta: string;
  fuentes: Fuente[];
  fundamentada: boolean;
  confianza: "alta" | "media" | "baja" | "ninguna";
  version_prompt: string;
  proveedor: string;
  modelo: string;
  modo_contexto: string;
  recuperador: "bm25" | "semantico" | "no_aplica";
  latencia_ms: number;
}

/** Búsqueda web complementaria (ADR-019): fuera de la base verificada. */
export interface RespuestaWebApi {
  pregunta: string;
  respuesta: string;
  hallazgos: { dato: string; url: string; fecha_consulta: string }[];
  encontrado: boolean;
  etiqueta: string;
  fecha_consulta: string;
  proveedor: string;
  modelo: string;
  latencia_ms: number;
}

export interface ItemFaq {
  pregunta: string;
  respuesta: string;
  fuentes: string[];
}

export interface ResultadoFaq {
  items: ItemFaq[];
  version_prompt: string;
  proveedor: string;
  modelo: string;
  latencia_ms: number;
  advertencias: string[];
}

export interface ResultadoResumen {
  resumen: string;
  enfoque: string;
  version_prompt: string;
  proveedor: string;
  modelo: string;
  latencia_ms: number;
}

export interface RespuestaAgente {
  pregunta: string;
  respuesta: string;
  fuentes: Fuente[];
  thread_id: string;
  proveedor: string;
  modelo: string;
  version_prompt: string;
  llamadas_herramienta: number;
  fundamentada: boolean;
  bloqueada: boolean;
  limite_alcanzado: boolean;
  rechazo: boolean;
}

export interface ItemFaqVisor {
  id: string;
  categoria: string;
  pregunta: string;
  respuesta: string;
  rechazo: boolean;
  fundamentada: boolean;
  confianza: string;
  fuentes: { fragmento_id: string; url: string }[];
}

export interface FaqVisor {
  generado: string;
  proveedor: string;
  modelo: string;
  version_prompt: string;
  advertencia: string;
  total: number;
  items: ItemFaqVisor[];
}

export interface Interaccion {
  id: number;
  fecha: string | null;
  tarea: string;
  canal: string;
  entrada: string;
  salida: string;
  proveedor: string;
  modelo: string;
  version_prompt: string;
  modo_contexto: string;
  fuentes: unknown[];
  fundamentada: boolean | null;
  latencia_ms: number;
}

export interface Ejecucion {
  id: number;
  inicio: string | null;
  fin: string | null;
  etapa: string;
  estado: string;
  detalle: Record<string, unknown>;
}

export interface Salud {
  estado: string;
  version: string;
  fragmentos: number;
  proveedor_llm: string;
  modelo_llm: string;
}

/** Opciones comunes de las tareas LLM del M1 (`OpcionesLLM`). */
export interface OpcionesLlm {
  proveedor?: string;
  modelo?: string;
  version_prompt?: string;
}

/* ---------------------------------------------------------------- transporte */
/** Error de la API con el código HTTP; el mensaje que ve el usuario lo arma cada pestaña. */
export class ErrorApi extends Error {
  constructor(
    readonly estado: number,
    mensaje: string,
  ) {
    super(mensaje);
    this.name = "ErrorApi";
  }
}

async function pedir<T>(ruta: string, init?: RequestInit): Promise<T> {
  const r = await fetch(ruta.startsWith("/salud") ? ruta : BASE + ruta, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
  });
  if (!r.ok) {
    let detalle = r.statusText;
    try {
      const j = await r.json();
      detalle = typeof j.detail === "string" ? j.detail : JSON.stringify(j.detail);
    } catch {
      /* respuesta sin JSON */
    }
    throw new ErrorApi(r.status, `HTTP ${r.status}: ${detalle}`);
  }
  return (await r.json()) as T;
}

const enviar = (cuerpo: unknown): RequestInit => ({ method: "POST", body: JSON.stringify(cuerpo) });

function consulta(parametros: Record<string, string | number | undefined | null>): string {
  const p = new URLSearchParams();
  for (const [k, v] of Object.entries(parametros)) if (v !== undefined && v !== null && v !== "") p.set(k, String(v));
  const s = p.toString();
  return s ? `?${s}` : "";
}

/* ---------------------------------------------------------------- endpoints */
export const api = {
  salud: () => pedir<Salud>("/salud"),
  /* Corpus Gold */
  estadisticasBase: () => pedir<EstadisticasBase>("/base/estadisticas"),
  infoVectorial: () => pedir<InfoVectorial>("/base/vectorial"),
  fragmentos: (f: { q?: string; seccion?: string; pagina?: number; tamano?: number } = {}) =>
    pedir<Pagina<FragmentoBuscado>>(`/base/fragmentos${consulta(f)}`),
  fragmento: (id: string) => pedir<Fragmento>(`/base/fragmentos/${encodeURIComponent(id)}`),
  /* Auditoría y proceso de datos */
  interacciones: (f: { pagina?: number; tamano?: number; tarea?: "qa" | "faq" | "resumen" } = {}) =>
    pedir<Pagina<Interaccion>>(`/auditoria/interacciones${consulta(f)}`),
  ejecuciones: () => pedir<Ejecucion[]>("/pipeline/ejecuciones"),
  /* Tareas LLM del M1 */
  qa: (pregunta: string, opciones: OpcionesLlm & { modo_contexto?: string; recuperador?: "bm25" | "semantico" } = {}) =>
    pedir<RespuestaQa>("/tareas/qa", enviar({ pregunta, ...opciones })),
  qaWeb: (pregunta: string) => pedir<RespuestaWebApi>("/tareas/qa-web", enviar({ pregunta })),
  faq: (n_preguntas = 8, opciones: OpcionesLlm = {}) => pedir<ResultadoFaq>("/tareas/faq", enviar({ n_preguntas, ...opciones })),
  resumen: (enfoque?: string, opciones: OpcionesLlm = {}) => pedir<ResultadoResumen>("/tareas/resumen", enviar({ enfoque, ...opciones })),
  /* Agente con memoria y FAQ precalculada */
  agente: (pregunta: string, thread_id: string) => pedir<RespuestaAgente>("/agente", enviar({ pregunta, thread_id })),
  faqVisor: () => pedir<FaqVisor>("/faq-visor"),
};
