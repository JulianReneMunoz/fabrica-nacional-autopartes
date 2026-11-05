/** Modo experimento: predecir, ejecutar, comparar. */
import { useState } from "react";
import type { DefExperimento } from "../../maquinas/tipos";

export interface Experimento extends DefExperimento {
  explicacion: string;
  aplicar: () => void;
}

/** Une el texto declarativo (`maquinas/<id>.ts`) con la explicación calculada y la acción de la página. */
export function armarExperimentos(defs: DefExperimento[], impl: { explicacion: string; aplicar: () => void }[]): Experimento[] {
  return defs.map((d, i) => ({ ...d, ...impl[i] }));
}

export function ModoExperimento({ experimentos }: { experimentos: Experimento[] }) {
  const [indice, setIndice] = useState(0);
  const [elegida, setElegida] = useState<number | null>(null);
  const [revelado, setRevelado] = useState(false);
  const exp = experimentos[indice];
  const siguiente = () => {
    setIndice((indice + 1) % experimentos.length);
    setElegida(null);
    setRevelado(false);
  };
  return (
    <section className="panel experimento" aria-label="Modo experimento">
      <h3>Modo experimento {indice + 1}/{experimentos.length}</h3>
      <p className="sin-margen">
        <b>Predicción:</b> {exp.pregunta}
      </p>
      <div className="opciones">
        {exp.opciones.map((o, i) => (
          <button
            key={o.texto}
            className={[elegida === i ? "elegida" : "", revelado && o.correcta ? "correcta" : ""].join(" ")}
            onClick={() => !revelado && setElegida(i)}
            aria-pressed={elegida === i}
          >
            {o.texto}
          </button>
        ))}
      </div>
      <div className="barra">
        <button
          className="boton"
          disabled={elegida === null || revelado}
          onClick={() => {
            exp.aplicar();
            setRevelado(true);
          }}
        >
          Ejecutar y comparar
        </button>
        <button className="boton secundario" onClick={siguiente}>Siguiente</button>
      </div>
      {revelado && (
        <p className="respuesta" role="status">
          {elegida !== null && exp.opciones[elegida].correcta ? "Predicción correcta. " : "La predicción no coincide. "}
          {exp.explicacion}
        </p>
      )}
    </section>
  );
}
