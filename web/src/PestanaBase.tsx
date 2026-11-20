/**
 * «Base de conocimiento — Qdrant» (solo lectura): cifras del corpus Gold (`GET /api/v1/base/estadisticas`) y estado de
 * la colección vectorial de IGNIS (`GET /api/v1/base/vectorial`). Cada bloque tiene sus estados de carga, vacío y
 * error; si el backend no responde no se muestra ninguna cifra.
 */
import { useCallback, useEffect, useState, type ReactNode } from "react";
import { api, ErrorApi, type EstadisticasBase, type InfoVectorial } from "./api";
import { Icono } from "./IgnisIconos";

type Carga<T> = { tipo: "cargando" } | { tipo: "error"; mensaje: string } | { tipo: "listo"; datos: T };

const MODOS: Record<InfoVectorial["modo"], string> = {
  local: "Local (archivo en disco)",
  memoria: "En memoria",
  servidor: "Servidor Qdrant",
};

/** Mensaje para el usuario sin trazas ni detalles internos del servidor. */
function mensajeError(e: unknown): string {
  if (e instanceof ErrorApi) return `El backend respondió con un error (HTTP ${e.estado}). Vuelve a intentarlo más tarde.`;
  return "No se pudo conectar con el backend. Comprueba que la API esté en marcha y vuelve a intentarlo.";
}

/** Carga de un endpoint de solo lectura con «Reintentar»; la reutiliza la pestaña Preguntas frecuentes. */
export function useCarga<T>(pedir: () => Promise<T>) {
  const [estado, setEstado] = useState<Carga<T>>({ tipo: "cargando" });
  const cargar = useCallback(() => {
    let vivo = true;
    setEstado({ tipo: "cargando" });
    pedir()
      .then((datos) => vivo && setEstado({ tipo: "listo", datos }))
      .catch((e: unknown) => vivo && setEstado({ tipo: "error", mensaje: mensajeError(e) }));
    return () => {
      vivo = false;
    };
  }, [pedir]);
  useEffect(() => cargar(), [cargar]);
  return { estado, cargar };
}

function Dato({ etiqueta, children }: { etiqueta: string; children: ReactNode }) {
  return (
    <div>
      <span className="ig-sesion-etiqueta">{etiqueta}</span>
      <strong>{children}</strong>
    </div>
  );
}

/** Estados de carga, error y vacío de un bloque; con datos, dibuja `children`. */
export function Bloque<T>({
  titulo,
  carga,
  reintentar,
  vacio,
  children,
}: {
  titulo: string;
  carga: Carga<T>;
  reintentar: () => void;
  vacio: (d: T) => string | null;
  children: (d: T) => ReactNode;
}) {
  if (carga.tipo === "cargando")
    return (
      <div className="ig-esqueleto" aria-busy="true" aria-label={`Cargando: ${titulo}`}>
        <span className="ig-esqueleto-linea ancha" />
        <span className="ig-esqueleto-linea" />
      </div>
    );
  if (carga.tipo === "error")
    return (
      <div className="ig-vacio-tarjeta" role="alert">
        <strong>No se pudo cargar: {titulo}</strong>
        <p>{carga.mensaje}</p>
        <button className="ignis-btn" onClick={reintentar}>
          Reintentar
        </button>
      </div>
    );
  const motivoVacio = vacio(carga.datos);
  if (motivoVacio)
    return (
      <div className="ig-vacio-tarjeta" role="status">
        <strong>{motivoVacio}</strong>
      </div>
    );
  return <>{children(carga.datos)}</>;
}

const entero = (n: number) => n.toLocaleString("es-CO");

function Estadisticas({ e }: { e: EstadisticasBase }) {
  return (
    <>
      <div className="ig-sesion-datos ig-base-cifras">
        <Dato etiqueta="Documentos">{entero(e.documentos)}</Dato>
        <Dato etiqueta="Fragmentos">{entero(e.fragmentos)}</Dato>
        <Dato etiqueta="Tokens aproximados">{entero(e.tokens_aprox)}</Dato>
        <Dato etiqueta="URL distintas">{entero(e.urls.length)}</Dato>
        <Dato etiqueta="Generado">{e.generado_en ?? "—"}</Dato>
      </div>
      <div className="ig-tabla-contenedor">
        <table className="ig-tabla">
          <caption className="sr">Fragmentos por origen y por sección</caption>
          <thead>
            <tr>
              <th scope="col">Agrupación</th>
              <th scope="col">Valor</th>
              <th scope="col">Fragmentos</th>
            </tr>
          </thead>
          <tbody>
            {Object.entries(e.origenes).map(([k, n]) => (
              <tr key={`o-${k}`}>
                <td>Origen</td>
                <td>{k}</td>
                <td className="numero">{entero(n)}</td>
              </tr>
            ))}
            {Object.entries(e.secciones).map(([k, n]) => (
              <tr key={`s-${k}`}>
                <td>Sección</td>
                <td>{k}</td>
                <td className="numero">{entero(n)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}

function Vectorial({ v }: { v: InfoVectorial }) {
  return (
    <>
      <div className="ig-sesion-datos ig-base-vectorial">
        <Dato etiqueta="Disponible">{v.disponible ? "Sí" : "No"}</Dato>
        <Dato etiqueta="Modo">{MODOS[v.modo] ?? v.modo}</Dato>
        <Dato etiqueta="Colección">
          <code>{v.coleccion}</code>
        </Dato>
        {v.disponible ? (
          <>
            <Dato etiqueta="Puntos">{entero(v.puntos)}</Dato>
            <Dato etiqueta="Tipo de búsqueda">{v.tipo_busqueda === "hnsw" ? "HNSW (aproximada)" : "Exacta"}</Dato>
          </>
        ) : null}
        <Dato etiqueta="Recuperador de IGNIS">{v.recuperador_ignis ?? "—"}</Dato>
      </div>
      {!v.disponible ? (
        <p className="ignis-aviso" role="status">
          Motivo: {v.motivo || "sin motivo informado"}
        </p>
      ) : null}
      {v.explicacion ? <p className="ig-vacio-motivo">{v.explicacion}</p> : null}
      {v.campos_payload.length ? (
        <p>
          <span className="ig-sesion-etiqueta">Campos del payload</span>{" "}
          {v.campos_payload.map((c) => (
            <code key={c}>{c} </code>
          ))}
        </p>
      ) : null}
    </>
  );
}

export default function PestanaBase() {
  const estadisticas = useCarga(api.estadisticasBase);
  const vectorial = useCarga(api.infoVectorial);
  return (
    <section className="ig-pestana" aria-labelledby="titulo-base">
      <header className="ig-pestana-cab">
        <span className="ig-pestana-icono" aria-hidden="true">
          <Icono nombre="base" tamano={22} />
        </span>
        <h1 id="titulo-base">Base de conocimiento — Qdrant</h1>
      </header>
      <p className="ig-vacio-motivo">Cifras del corpus Gold y estado de la colección vectorial de IGNIS. Solo lectura.</p>

      <h2 className="ig-sesion-subtitulo">Corpus</h2>
      <Bloque
        titulo="estadísticas del corpus"
        carga={estadisticas.estado}
        reintentar={estadisticas.cargar}
        vacio={(e) => (e.documentos === 0 && e.fragmentos === 0 ? "La base de conocimiento aún no tiene documentos" : null)}
      >
        {(e) => <Estadisticas e={e} />}
      </Bloque>

      <h2 className="ig-sesion-subtitulo">Base vectorial</h2>
      <Bloque titulo="estado de la base vectorial" carga={vectorial.estado} reintentar={vectorial.cargar} vacio={() => null}>
        {(v) => <Vectorial v={v} />}
      </Bloque>
    </section>
  );
}
