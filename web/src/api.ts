/** Cliente de la API FastAPI (/api/v1). Todas las rutas son relativas al mismo origen. */

import type { CampoFichaApi, EntradaMoto } from "./modelos/moto";

export const ENSAMBLAJE = "freno_disco";
export const ENSAMBLAJE_MOTO = "moto_honda";
const BASE = "/api/v1";

export interface DatoEmpresa {
  texto: string;
  url: string;
  fragmento_id: string;
  origen: string;
}
export interface Parametro {
  nombre: string;
  valor: number;
  unidad: string;
  procedencia: string;
  fuente: string | null;
}
export interface Maquina {
  id: string;
  pregunta: string;
  una_linea: string;
  relacion: string;
  ruta: string;
  idea_principal: string;
  datos_empresa: DatoEmpresa[];
  parametros: Parametro[];
}
export interface Pieza {
  id: string;
  nombre: string;
  tipo: string;
  descripcion: string;
  funcion: string;
  material: string | null;
  subconjunto: string;
  dimensiones_m: Record<string, number>;
  relacionadas: string[];
  retirar_antes: string[];
  metadatos: Record<string, string>;
  referencia_documental: string;
}
export interface NodoJerarquia {
  id: string;
  nombre: string;
  tipo: string;
  hijos: NodoJerarquia[];
}
export interface Lectura {
  posicion: number[];
  rotacion_grados: number[];
}
export interface RespuestaPieza {
  pieza_id: string;
  pregunta: string;
  intencion: string;
  respuesta_modelo: string;
  documentado: { fragmento_id: string; texto: string; url: string; origen: string }[];
  advertencia: string;
}
export interface ArticulacionApi {
  id: string;
  tipo: string;
  padre: string | null;
  hijo: string;
  eje: number[];
  origen: number[];
  maestra: string | null;
  relacion: number | null;
}
export interface EnsamblajeApi {
  id: string;
  parametros: Record<string, number>;
}
export interface Animacion {
  duracion_por_pieza_s: number;
  solape: number;
  orden_desmontaje: string[];
  orden_reensamblaje: string[];
}
/** Sistema funcional del ensamblaje (vista «explorador», fase 14): texto de la definición del ensamblaje. */
export interface SistemaApi {
  id: string;
  nombre: string;
  funcion: string;
  piezas: string[];
}
export interface ResumenEnsamblaje {
  id: string;
  nombre: string;
  advertencia: string;
  piezas: number;
  articulaciones: number;
}

async function pedir<T>(ruta: string, init?: RequestInit): Promise<T> {
  const r = await fetch(BASE + ruta, {
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
    throw new Error(`HTTP ${r.status}: ${detalle}`);
  }
  return (await r.json()) as T;
}

/* ---------- motocicleta de referencia con fichas Honda (ADR-017) ---------- */
export interface FuenteFichaApi {
  id: string;
  descripcion: string;
  url: string | null;
  fecha_consulta: string | null;
  estado_acceso: string | null;
}
export interface SupuestoApi {
  clave: string;
  valor: number | number[] | string;
  unidad: string;
  descripcion: string;
  etiqueta: string;
}
export interface FichaMotoApi {
  id: string;
  nombre: string;
  categoria: string;
  versiones: string[];
  grupos: Record<string, Record<string, CampoFichaApi>>;
  por_version: Record<string, Record<string, CampoFichaApi>>;
  pendientes_de_confirmar: { campo: string; detalle: string }[];
  fuentes: FuenteFichaApi[];
  supuestos: SupuestoApi[];
  ensamblaje_id: string;
  titulo_biblioteca: string;
}
export interface RespuestaModeloApi {
  id: string;
  pregunta: string;
  respuesta: string;
  campos: string[];
  fuentes: string[];
  estado: "publicado" | "no_publicado" | "supuesto";
}
export interface CalculoMotoApi {
  resultado: { velocidad_kmh: number; estado_motor: string; radio_llanta_m: number; relacion_total: number | null; rpm_efectivas: number };
  ficha_aplicada: { modelo: string; version: string; aplicados: Record<string, string>; conservados_genericos: string[] } | null;
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
export interface RespuestaQa {
  pregunta: string;
  respuesta: string;
  fuentes: { fragmento_id: string; titulo: string; url: string }[];
  fundamentada: boolean;
  confianza: string;
  proveedor: string;
  modelo: string;
}

const enviar = (cuerpo: unknown): RequestInit => ({ method: "POST", body: JSON.stringify(cuerpo) });

/** Cliente del simulador para un ensamblaje (el freno sigue con `freno_disco` exactamente igual). */
export function crearApi(ensamblaje: string) {
  const e = `/simulador/ensamblajes/${ensamblaje}`;
  return {
    maquinas: () => pedir<Maquina[]>("/maquinas"),
    maquina: (id: string) => pedir<Maquina>(`/maquinas/${id}`),
    resumen: () => pedir<ResumenEnsamblaje[]>("/simulador/ensamblajes"),
    piezas: () => pedir<Pieza[]>(`${e}/piezas`),
    jerarquia: () => pedir<NodoJerarquia>(`${e}/jerarquia`),
    sistemas: () => pedir<SistemaApi[]>(`${e}/sistemas`),
    articulaciones: () => pedir<ArticulacionApi[]>(`${e}/articulaciones`),
    ensamblaje: () => pedir<EnsamblajeApi>(`${e}`),
    despiece: (factor: number) => pedir<Record<string, number[]>>(`${e}/despiece?factor=${factor}`),
    animacion: () => pedir<Animacion>(`${e}/animacion`),
    cinematica: (valores: Record<string, number>) => pedir<Record<string, Lectura>>(`${e}/cinematica`, enviar({ valores })),
    preguntar: (pieza_id: string, pregunta: string) => pedir<RespuestaPieza>(`${e}/preguntar`, enviar({ pieza_id, pregunta })),
    guardarEstado: (nombre: string, estado: Record<string, unknown>) =>
      pedir<{ id: number }>(`${e}/estados`, enviar({ nombre, estado })),
    evento: (tipo: string, pieza_id: string | null, detalle: Record<string, unknown> = {}) =>
      pedir<unknown>(`${e}/eventos`, enviar({ tipo, pieza_id, detalle })).catch(() => undefined),
    /* Fichas Honda, FAQ del visor y Q&A (no dependen del ensamblaje). */
    fichaMoto: (id: string) => pedir<FichaMotoApi>(`/motos/${id}`),
    faqModelo: (id: string) => pedir<RespuestaModeloApi[]>(`/motos/${id}/faq`),
    calculoMoto: (id: string, entrada: EntradaMoto, conFicha: boolean) =>
      pedir<CalculoMotoApi>(`/motos/${id}/calculo?con_ficha=${conFicha}`, enviar(entrada)),
    faqVisor: () => pedir<FaqVisor>("/faq-visor"),
    qa: (pregunta: string) => pedir<RespuestaQa>("/tareas/qa", enviar({ pregunta })),
  };
}

export const api = crearApi(ENSAMBLAJE);
export const apiMoto = crearApi(ENSAMBLAJE_MOTO);
