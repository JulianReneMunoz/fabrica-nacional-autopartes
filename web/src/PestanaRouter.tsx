/**
 * «Router» (R08, rúbrica 2.3): decisiones del router en los turnos de la sesión actual, tomadas de los metadatos
 * que ya llegan por SSE a Atención (ruta, puntaje, justificación y herramienta @tool del caso 3). Sin datos
 * simulados ni endpoint propio: sin turnos se muestra el estado vacío.
 *
 * No guarda ni muestra el texto de las preguntas (Ley 1581 de 2012): cada fila se identifica por su número de
 * turno. Los turnos de crisis personal no se listan.
 */
import { etiquetaModeracion, etiquetaRuta, type HerramientaIgnis } from "./ignisCliente";
import { useIgnis } from "./ignisContexto";
import { Icono } from "./IgnisIconos";
import { hashDe } from "./ignisRutas";

function Herramienta({ h }: { h: HerramientaIgnis }) {
  const tipo = h.argumentos.tipo_consulta;
  return (
    <div className="ig-router-herramienta">
      <code>{h.nombre}</code>
      {tipo ? <span>tipo_consulta: {tipo}</span> : null}
      <span>
        {h.fuenteArchivo || "sin archivo"} · {h.verificado ? "verificado" : "sin verificar"}
      </span>
      <details>
        <summary>Resumen de la salida</summary>
        <p>
          {h.resumen.totalClaves === 1 ? "1 clave" : `${h.resumen.totalClaves} claves`}
          {h.resumen.claves.length ? `: ${h.resumen.claves.join(", ")}` : ""}
        </p>
        {Object.keys(h.resumen.elementos).length ? (
          <ul>
            {Object.entries(h.resumen.elementos).map(([clave, n]) => (
              <li key={clave}>
                {clave}: {n === 1 ? "1 elemento" : `${n} elementos`}
              </li>
            ))}
          </ul>
        ) : null}
      </details>
    </div>
  );
}

export default function PestanaRouter() {
  const { decisiones } = useIgnis();
  return (
    <section className="ig-pestana" aria-labelledby="titulo-router">
      <header className="ig-pestana-cab">
        <span className="ig-pestana-icono" aria-hidden="true">
          <Icono nombre="ruta" tamano={22} />
        </span>
        <h1 id="titulo-router">Router</h1>
      </header>
      <p className="ig-vacio-motivo">
        Decisiones del router en los turnos de esta sesión: ruta, puntaje, justificación, herramienta usada y blindaje. No se
        guarda el texto de las preguntas; se borran al cerrar la sesión.
      </p>

      {decisiones.length === 0 ? (
        <div className="ig-vacio-tarjeta" role="status">
          <strong>Aún no hay turnos en esta sesión</strong>
          <p>
            Escribe a IGNIS en <a href={hashDe("atencion")}>Atención</a>: cada respuesta agrega aquí la decisión del
            router.
          </p>
        </div>
      ) : (
        <div className="ig-tabla-contenedor">
          <table className="ig-tabla ig-router-tabla">
            <caption className="sr">Decisiones del router por turno</caption>
            <thead>
              <tr>
                <th scope="col">Turno</th>
                <th scope="col">Ruta</th>
                <th scope="col">Puntaje</th>
                <th scope="col">Justificación</th>
                <th scope="col">Herramienta</th>
              </tr>
            </thead>
            <tbody>
              {[...decisiones].reverse().map((d) => (
                <tr key={d.turno}>
                  <td className="numero">{d.turno}</td>
                  <td>
                    <span className="ignis-insignia ruta" title={`Ruta del router: ${d.ruta}`}>
                      {etiquetaRuta(d.ruta)}
                    </span>
                    {d.blindaje ? (
                      <span className="ignis-insignia blindaje">
                        <Icono nombre="escudo" tamano={13} /> Blindaje activado
                      </span>
                    ) : null}
                    {d.categoriaModeracion ? (
                      <span className="ig-router-moderacion">Moderación: {etiquetaModeracion(d.categoriaModeracion)}</span>
                    ) : null}
                  </td>
                  <td className="numero">{d.score !== undefined ? d.score.toFixed(2) : "—"}</td>
                  <td>{d.justificacion || "—"}</td>
                  <td>{d.herramienta ? <Herramienta h={d.herramienta} /> : <span className="ig-vacio-motivo">Sin herramienta</span>}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
