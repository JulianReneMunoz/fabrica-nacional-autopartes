/** Controles estándar: deslizadores operables con teclado y con aria-label, y reproducción con velocidad. */
import type { DefControl } from "../../maquinas/tipos";
import { fmt } from "../anatomia";

export function Deslizador(props: {
  etiqueta: string;
  valor: number;
  min: number;
  max: number;
  paso: number;
  unidad: string;
  alCambiar: (v: number) => void;
  formato?: (v: number) => string;
}) {
  const id = `ctl-${props.etiqueta.replace(/\W+/g, "-")}`;
  const texto = props.formato ? props.formato(props.valor) : props.valor.toLocaleString("es-CO");
  const completo = `${texto}${props.unidad ? ` ${props.unidad}` : ""}`;
  return (
    <div className="control">
      <label htmlFor={id}>{props.etiqueta}</label>
      <output htmlFor={id}>{completo}</output>
      <input
        id={id}
        type="range"
        aria-label={props.etiqueta}
        aria-valuetext={completo}
        min={props.min}
        max={props.max}
        step={props.paso}
        value={props.valor}
        onChange={(e) => props.alCambiar(Number(e.target.value))}
      />
    </div>
  );
}

/** Deslizadores declarados en `maquinas/<id>.ts` y enlazados a los valores de la página. */
export function ControlesDeclarados(props: {
  defs: DefControl[];
  valores: Record<string, number>;
  alCambiar: (id: string, v: number) => void;
}) {
  return (
    <>
      {props.defs.map((d) => (
        <Deslizador
          key={d.id}
          etiqueta={d.etiqueta}
          valor={props.valores[d.id]}
          min={d.min}
          max={d.max}
          paso={d.paso}
          unidad={d.unidad}
          formato={d.decimales ? (v) => fmt(v, d.decimales) : undefined}
          alCambiar={(v) => props.alCambiar(d.id, v)}
        />
      ))}
    </>
  );
}

export interface PropsReproduccion {
  corriendo: boolean;
  alCorrer: () => void;
  alPausar: () => void;
  alReiniciar: () => void;
  escala: number;
  alEscala: (v: number) => void;
}

export function Reproduccion(props: PropsReproduccion) {
  return (
    <div className="barra" role="group" aria-label="Reproducción">
      {props.corriendo ? (
        <button className="boton" onClick={props.alPausar}>❚❚ Pausar</button>
      ) : (
        <button className="boton" onClick={props.alCorrer}>▶ Correr</button>
      )}
      <button className="boton secundario" onClick={props.alReiniciar}>↺ Reiniciar</button>
      <label className="chip chip-neutro">
        Velocidad
        <select aria-label="Velocidad de simulación" value={props.escala} onChange={(e) => props.alEscala(Number(e.target.value))}>
          <option value={1}>1×</option>
          <option value={0.5}>0,5×</option>
          <option value={0.25}>0,25× (lenta)</option>
          <option value={0.1}>0,1× (muy lenta)</option>
        </select>
      </label>
    </div>
  );
}
