/**
 * Etiquetas de cifras pegadas a su pieza: una caja HTML por clave y una línea guía SVG con un punto sobre la pieza.
 * La escena 3D (EscenaFreno, EscenaMoto) las posiciona en cada fotograma con `modelos/etiquetas.ts`
 * (anclaje en la pieza, caja cercana, sin solapes ni recortes) escribiendo en las referencias recibidas.
 */
import type { MutableRefObject, ReactNode } from "react";

export interface EtiquetaDef {
  clave: string;
  /** Clases de énfasis: «fuerza», «movimiento», «alerta»; vacío = neutra. */
  clase?: string;
  contenido: ReactNode | null;
}
export type RefsEtiquetas = MutableRefObject<Record<string, HTMLDivElement | null>>;
export type RefsLineas = MutableRefObject<Record<string, { linea: SVGLineElement | null; punto: SVGCircleElement | null }>>;

export function EtiquetasPieza({ etiquetas, divs, lineas }: { etiquetas: EtiquetaDef[]; divs: RefsEtiquetas; lineas: RefsLineas }) {
  return (
    <>
      <svg className="guias-etiquetas" aria-hidden="true">
        {etiquetas.map((e) => (
          <g key={e.clave}>
            <line
              ref={(l) => {
                lineas.current[e.clave] = { ...(lineas.current[e.clave] ?? { punto: null }), linea: l };
              }}
              data-guia={e.clave}
            />
            <circle
              ref={(c) => {
                lineas.current[e.clave] = { ...(lineas.current[e.clave] ?? { linea: null }), punto: c };
              }}
              r="3.5"
            />
          </g>
        ))}
      </svg>
      {etiquetas.map((e) => (
        <div
          key={e.clave}
          ref={(d) => {
            divs.current[e.clave] = d;
          }}
          className={`etiqueta-3d ${e.clase ?? ""}`}
          data-etiqueta={e.clave}
          style={e.contenido === null ? { display: "none" } : undefined}
        >
          {e.contenido}
        </div>
      ))}
    </>
  );
}
