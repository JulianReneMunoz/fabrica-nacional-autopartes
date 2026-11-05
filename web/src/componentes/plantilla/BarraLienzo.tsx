/**
 * Barra de herramientas estándar del lienzo. El orden es fijo para todas las máquinas:
 * Ensamblado · Despiece · Sección · Cámara · PNG · Guardar vista · Recorrido 30 s.
 * Cada máquina declara solo los botones que le aplican (las 2D no tienen despiece ni cámara).
 */
export interface BotonBarra {
  alPulsar: () => void;
  activo?: boolean;
  deshabilitado?: boolean;
  titulo?: string;
}
export interface PropsBarraLienzo {
  ensamblado?: BotonBarra;
  despiece?: BotonBarra;
  seccion?: BotonBarra;
  camara?: BotonBarra;
  png?: BotonBarra;
  guardar?: BotonBarra;
  recorrido?: BotonBarra;
}

const DEFINICION: [keyof PropsBarraLienzo, string, boolean][] = [
  ["ensamblado", "Ensamblado", true],
  ["despiece", "Despiece", true],
  ["seccion", "◧ Sección", true],
  ["camara", "⌖ Cámara", false],
  ["png", "⤓ PNG", false],
  ["guardar", "Guardar vista", false],
  ["recorrido", "Recorrido 30 s", false],
];

export function BarraLienzo(props: PropsBarraLienzo) {
  return (
    <div className="barra-lienzo" role="toolbar" aria-label="Modos y herramientas de vista">
      {DEFINICION.map(([clave, texto, conmutable]) => {
        const b = props[clave];
        if (!b) return null;
        return (
          <button
            key={clave}
            className={`boton ${b.activo ? "activo" : "secundario"}`}
            onClick={b.alPulsar}
            disabled={b.deshabilitado}
            title={b.titulo}
            aria-pressed={conmutable ? Boolean(b.activo) : undefined}
          >
            {texto}
          </button>
        );
      })}
    </div>
  );
}
