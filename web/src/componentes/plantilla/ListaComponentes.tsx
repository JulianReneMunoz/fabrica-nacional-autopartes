import { InsigniaFuente } from "./InsigniaFuente";

/** Componentes de una máquina 2D (lista declarada en `maquinas/<id>.ts`). */
export function ListaComponentes({ lista }: { lista: { nombre: string; funcion: string }[] }) {
  return (
    <div>
      <p className="aviso">
        <InsigniaFuente fuente="supuesto" /> Descripción didáctica de los elementos del esquema 2D.
      </p>
      <ul className="datos" aria-label="Componentes de la máquina">
        {lista.map((c) => (
          <li key={c.nombre}>
            <b>{c.nombre}</b>: {c.funcion}
          </li>
        ))}
      </ul>
    </div>
  );
}
