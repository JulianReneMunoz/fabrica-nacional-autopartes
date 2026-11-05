import type { Maquina } from "../../api";
import { InsigniaFuente } from "./InsigniaFuente";
import { TextoEnLinea } from "./TextoEnLinea";

/** Datos de la empresa: cada dato lleva su insignia de procedencia y su URL; los parámetros sin fuente se marcan. */
export function PanelEmpresa({ maquina, error }: { maquina: Maquina | null; error: string | null }) {
  return (
    <section aria-label="Datos de la empresa">
      {error && <p className="aviso error">Sin conexión con la API: {error}</p>}
      {!maquina && !error && <p className="aviso">Consultando la base de conocimiento…</p>}
      {maquina && (
        <ul className="datos">
          {maquina.datos_empresa.map((d) => (
            <li key={d.fragmento_id}>
              <InsigniaFuente fuente={d.origen} />
              <TextoEnLinea texto={d.texto} />
              <br />
              <a href={d.url} target="_blank" rel="noreferrer">{d.url}</a>
            </li>
          ))}
          {maquina.parametros.map((p) => (
            <li key={p.nombre}>
              <InsigniaFuente fuente={p.procedencia} />
              {p.nombre.replace(/_/g, " ")}: <b className="num">{p.valor.toLocaleString("es-CO")}</b> {p.unidad}
              {p.fuente && (
                <>
                  <br />
                  <a href={p.fuente} target="_blank" rel="noreferrer">{p.fuente}</a>
                </>
              )}
            </li>
          ))}
        </ul>
      )}
      <p className="aviso">Cifras demostrativas; los datos de la empresa provienen de fuentes oficiales citadas por URL.</p>
    </section>
  );
}
