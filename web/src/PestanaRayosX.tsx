/**
 * «Rayos-X y validación» (solo lectura): recorrido del último turno y lista de turnos de la sesión actual, a partir
 * de las decisiones del router que Atención ya registra en el contexto (las mismas de la pestaña Router). Sin
 * endpoint propio ni datos simulados: sin turnos se muestra el estado vacío.
 *
 * No muestra el texto de las preguntas ni datos personales (Ley 1581 de 2012): cada turno se identifica por su
 * número. Las citas y las fuentes de datos se ven junto a cada respuesta en Atención; el registro del turno que
 * comparte el contexto no las incluye.
 */
import type { ReactNode } from "react";
import { etiquetaModeracion, etiquetaRuta } from "./ignisCliente";
import { useIgnis, type DecisionRouterTurno } from "./ignisContexto";
import { Icono } from "./IgnisIconos";
import { hashDe } from "./ignisRutas";
import { Herramienta } from "./PestanaRouter";

function Dato({ etiqueta, children }: { etiqueta: string; children: ReactNode }) {
  return (
    <div>
      <span className="ig-sesion-etiqueta">{etiqueta}</span>
      <strong>{children}</strong>
    </div>
  );
}

function UltimoTurno({ d }: { d: DecisionRouterTurno }) {
  return (
    <article className="ig-vacio-tarjeta ig-rayos-ultimo" aria-labelledby="titulo-rayos-ultimo">
      <h2 id="titulo-rayos-ultimo" className="ig-sesion-subtitulo">
        Último turno (n.º {d.turno})
      </h2>
      <div className="ig-sesion-datos">
        <Dato etiqueta="Ruta">
          <span className="ignis-insignia ruta" title={`Ruta del router: ${d.ruta}`}>
            {etiquetaRuta(d.ruta)}
          </span>
        </Dato>
        <Dato etiqueta="Puntaje">{d.score !== undefined ? d.score.toFixed(2) : "—"}</Dato>
        <Dato etiqueta="Blindaje activado">{d.blindaje ? "Sí" : "No"}</Dato>
        <Dato etiqueta="Moderación">
          {d.categoriaModeracion ? etiquetaModeracion(d.categoriaModeracion) : d.bloqueada ? "Bloqueado" : "Sin bloqueo"}
        </Dato>
      </div>
      <p>
        <span className="ig-sesion-etiqueta">Justificación del router</span> {d.justificacion || "—"}
      </p>
      <div>
        <span className="ig-sesion-etiqueta">Herramienta</span>{" "}
        {d.herramienta ? <Herramienta h={d.herramienta} /> : <span className="ig-vacio-motivo">Sin herramienta</span>}
      </div>
      <p className="ig-vacio-motivo">
        Citas y fuentes de datos: se muestran junto a la respuesta en <a href={hashDe("atencion")}>Atención</a>; el
        registro del turno no las conserva.
      </p>
    </article>
  );
}

export default function PestanaRayosX() {
  const { decisiones } = useIgnis();
  const ultimo = decisiones[decisiones.length - 1];
  return (
    <section className="ig-pestana" aria-labelledby="titulo-rayos-x">
      <header className="ig-pestana-cab">
        <span className="ig-pestana-icono" aria-hidden="true">
          <Icono nombre="escaner" tamano={22} />
        </span>
        <h1 id="titulo-rayos-x">Rayos-X y validación</h1>
      </header>
      <p className="ig-vacio-motivo">
        Recorrido de cada turno de esta sesión: ruta del router, puntaje, herramienta, blindaje y moderación. Solo
        lectura; no se guarda el texto de las preguntas y se borra al cerrar la sesión.
      </p>

      {!ultimo ? (
        <div className="ig-vacio-tarjeta" role="status">
          <strong>Aún no hay turnos en esta sesión</strong>
          <p>
            Envía una pregunta en <a href={hashDe("atencion")}>Atención</a> para ver aquí su recorrido.
          </p>
        </div>
      ) : (
        <>
          <UltimoTurno d={ultimo} />
          <h2 className="ig-sesion-subtitulo">Turnos de la sesión</h2>
          <div className="ig-tabla-contenedor">
            <table className="ig-tabla ig-rayos-tabla">
              <caption className="sr">Turnos de la sesión con su ruta, del más reciente al más antiguo</caption>
              <thead>
                <tr>
                  <th scope="col">Turno</th>
                  <th scope="col">Ruta</th>
                  <th scope="col">Puntaje</th>
                  <th scope="col">Herramienta</th>
                  <th scope="col">Blindaje</th>
                </tr>
              </thead>
              <tbody>
                {[...decisiones].reverse().map((d) => (
                  <tr key={d.turno}>
                    <td className="numero">{d.turno}</td>
                    <td>
                      <span className="ignis-insignia ruta">{etiquetaRuta(d.ruta)}</span>
                      {d.categoriaModeracion ? (
                        <span className="ig-router-moderacion">Moderación: {etiquetaModeracion(d.categoriaModeracion)}</span>
                      ) : null}
                    </td>
                    <td className="numero">{d.score !== undefined ? d.score.toFixed(2) : "—"}</td>
                    <td>{d.herramienta ? <code>{d.herramienta.nombre}</code> : "—"}</td>
                    <td>{d.blindaje ? "Sí" : "No"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </section>
  );
}
