/** Cliente de la API FastAPI (/api/v1). Todas las rutas son relativas al mismo origen. */

export const ENSAMBLAJE = "freno_disco";
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
export interface Animacion {
  duracion_por_pieza_s: number;
  solape: number;
  orden_desmontaje: string[];
  orden_reensamblaje: string[];
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

const enviar = (cuerpo: unknown): RequestInit => ({ method: "POST", body: JSON.stringify(cuerpo) });
const e = `/simulador/ensamblajes/${ENSAMBLAJE}`;

export const api = {
  maquinas: () => pedir<Maquina[]>("/maquinas"),
  maquina: (id: string) => pedir<Maquina>(`/maquinas/${id}`),
  resumen: () => pedir<ResumenEnsamblaje[]>("/simulador/ensamblajes"),
  piezas: () => pedir<Pieza[]>(`${e}/piezas`),
  jerarquia: () => pedir<NodoJerarquia>(`${e}/jerarquia`),
  despiece: (factor: number) => pedir<Record<string, number[]>>(`${e}/despiece?factor=${factor}`),
  animacion: () => pedir<Animacion>(`${e}/animacion`),
  cinematica: (valores: Record<string, number>) => pedir<Record<string, Lectura>>(`${e}/cinematica`, enviar({ valores })),
  preguntar: (pieza_id: string, pregunta: string) => pedir<RespuestaPieza>(`${e}/preguntar`, enviar({ pieza_id, pregunta })),
  guardarEstado: (nombre: string, estado: Record<string, unknown>) =>
    pedir<{ id: number }>(`${e}/estados`, enviar({ nombre, estado })),
  evento: (tipo: string, pieza_id: string | null, detalle: Record<string, unknown> = {}) =>
    pedir<unknown>(`${e}/eventos`, enviar({ tipo, pieza_id, detalle })).catch(() => undefined),
};
