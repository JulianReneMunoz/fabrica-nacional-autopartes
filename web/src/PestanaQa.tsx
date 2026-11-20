/**
 * «Consulta puntual Q&A»: una pregunta sin memoria contra `POST /api/v1/tareas/qa`. Cada consulta es independiente:
 * la pregunta no se guarda en el navegador ni en el contexto de IGNIS. Sin datos simulados: con el backend caído solo
 * se muestra un mensaje de error, sin URL ni detalles técnicos.
 */
import { useState, type FormEvent } from "react";
import { api, type RespuestaQa } from "./api";
import { Icono } from "./IgnisIconos";
import { ListaFuentes } from "./origenFuentes";
import { mensajeError } from "./PestanaBase";

export const MAX_PREGUNTA = 500;

type Recuperador = "" | "bm25" | "semantico";

type Estado = { tipo: "inicial" } | { tipo: "cargando" } | { tipo: "error"; mensaje: string } | { tipo: "listo"; datos: RespuestaQa };

export function sinRespaldo(r: RespuestaQa): boolean {
  return !r.fundamentada || r.confianza === "ninguna";
}

function Resultado({ r }: { r: RespuestaQa }) {
  const respaldo = !sinRespaldo(r);
  return (
    <article className="ig-qa-resultado" aria-label="Resultado de la consulta">
      {!respaldo ? (
        <p className="ignis-insignia" role="status">
          Sin respaldo en la base
        </p>
      ) : null}
      <p className="ig-qa-respuesta">{r.respuesta}</p>
      <div className="ig-sesion-datos">
        <div>
          <span className="ig-sesion-etiqueta">Confianza</span>
          <strong>{r.confianza}</strong>
        </div>
        <div>
          <span className="ig-sesion-etiqueta">Fundamentada</span>
          <strong>{r.fundamentada ? "Sí" : "No"}</strong>
        </div>
      </div>
      {r.fuentes.length ? (
        <>
          <h2 className="ig-sesion-subtitulo">Fuentes</h2>
          <ListaFuentes fuentes={r.fuentes} className="ig-qa-fuentes" />
        </>
      ) : null}
      <footer className="ig-vacio-motivo ig-qa-pie">
        Modelo: {r.proveedor} / {r.modelo} · Prompt: {r.version_prompt} · Contexto: {r.modo_contexto} · Recuperador:{" "}
        {r.recuperador} · Latencia: {r.latencia_ms} ms
      </footer>
    </article>
  );
}

export default function PestanaQa() {
  const [pregunta, setPregunta] = useState("");
  const [recuperador, setRecuperador] = useState<Recuperador>("");
  const [estado, setEstado] = useState<Estado>({ tipo: "inicial" });

  const cargando = estado.tipo === "cargando";
  const vacia = pregunta.trim() === "";

  const consultar = (e: FormEvent) => {
    e.preventDefault();
    if (cargando || vacia) return;
    setEstado({ tipo: "cargando" });
    // Sin recuperador elegido no se envía el campo: el backend usa el suyo por defecto.
    api
      .qa(pregunta.trim(), recuperador ? { recuperador } : {})
      .then((datos) => setEstado({ tipo: "listo", datos }))
      .catch((err: unknown) => setEstado({ tipo: "error", mensaje: mensajeError(err) }));
  };

  return (
    <section className="ig-pestana" aria-labelledby="titulo-qa">
      <header className="ig-pestana-cab">
        <span className="ig-pestana-icono" aria-hidden="true">
          <Icono nombre="chat" tamano={22} />
        </span>
        <h1 id="titulo-qa">Consulta puntual Q&amp;A</h1>
      </header>
      <p className="ignis-aviso" role="note">
        Consulta sin memoria: cada pregunta es independiente. No escribas datos personales.
      </p>

      <form className="ig-qa-formulario" onSubmit={consultar}>
        <label className="ig-sesion-etiqueta" htmlFor="ig-qa-pregunta">
          Pregunta
        </label>
        <textarea
          id="ig-qa-pregunta"
          className="ignis-input"
          value={pregunta}
          onChange={(e) => setPregunta(e.target.value)}
          maxLength={MAX_PREGUNTA}
          required
          rows={3}
          autoComplete="off"
          placeholder="Escribe una pregunta sobre Fanalca"
        />
        <span className="ig-vacio-motivo">
          {pregunta.length}/{MAX_PREGUNTA}
        </span>
        <div className="ig-sesion-datos">
          <div>
            <label className="ig-sesion-etiqueta" htmlFor="ig-qa-recuperador">
              Recuperador
            </label>
            <select
              id="ig-qa-recuperador"
              className="ignis-select"
              value={recuperador}
              onChange={(e) => setRecuperador(e.target.value as Recuperador)}
            >
              <option value="">Por defecto del backend</option>
              <option value="bm25">bm25</option>
              <option value="semantico">semantico</option>
            </select>
          </div>
        </div>
        <button type="submit" className="ignis-btn" disabled={cargando || vacia}>
          {cargando ? "Consultando…" : "Consultar"}
        </button>
      </form>

      {cargando ? (
        <div className="ig-esqueleto" aria-busy="true" aria-label="Consultando">
          <span className="ig-esqueleto-linea ancha" />
          <span className="ig-esqueleto-linea" />
        </div>
      ) : null}
      {estado.tipo === "error" ? (
        <div className="ig-vacio-tarjeta" role="alert">
          <strong>No se pudo completar la consulta</strong>
          <p>{estado.mensaje}</p>
        </div>
      ) : null}
      {estado.tipo === "listo" ? <Resultado r={estado.datos} /> : null}
    </section>
  );
}
