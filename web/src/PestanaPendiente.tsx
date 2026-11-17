/**
 * Estado vacío de una pestaña cuyo endpoint o implementación aún no existe (regla de honestidad de datos):
 * se dice qué mostrará y en qué PR del plan llega, sin datos simulados.
 */
import { Icono } from "./IgnisIconos";
import type { Pestana } from "./ignisRutas";

export default function PestanaPendiente({ pestana }: { pestana: Pestana }) {
  return (
    <section className="ig-pestana" aria-labelledby={`titulo-${pestana.id}`}>
      <header className="ig-pestana-cab">
        <span className="ig-pestana-icono" aria-hidden="true">
          <Icono nombre={pestana.icono} tamano={22} />
        </span>
        <h1 id={`titulo-${pestana.id}`}>{pestana.etiqueta}</h1>
      </header>
      <div className="ig-vacio-tarjeta" role="status">
        <strong>No disponible todavía ({pestana.pr})</strong>
        <p>{pestana.descripcion}</p>
        <p className="ig-vacio-motivo">
          Esta pestaña se habilita cuando exista su endpoint en la API. Mientras tanto no se muestran datos para no presentar
          cifras simuladas.
        </p>
      </div>
    </section>
  );
}
