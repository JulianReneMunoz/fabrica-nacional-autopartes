/**
 * «Corpus» (solo lectura): fragmentos del corpus Gold (`GET /api/v1/base/fragmentos`) con búsqueda por texto, filtro
 * por sección y paginación. Cada fragmento muestra su URL y su origen tal como los entrega el backend; al elegir uno
 * se ve su texto completo. Sin datos simulados: con el backend caído no se muestra ningún fragmento.
 */
import { useCallback, useEffect, useState } from "react";
import { api, type Fragmento, type Pagina, type FragmentoBuscado } from "./api";
import { Icono } from "./IgnisIconos";
import { Bloque, urlSegura, useCarga } from "./PestanaBase";

export const POR_PAGINA = 20;
const ESPERA_BUSQUEDA_MS = 300;

function Enlace({ url }: { url: string }) {
  return urlSegura(url) ? (
    <a href={url} target="_blank" rel="noopener noreferrer">
      {url}
    </a>
  ) : (
    <span>{url}</span>
  );
}

function Detalle({ f, cerrar }: { f: Fragmento; cerrar: () => void }) {
  return (
    <article className="ig-vacio-tarjeta ig-corpus-detalle" aria-label={`Fragmento ${f.id}`}>
      <strong>{f.encabezado || f.titulo}</strong>
      <p className="ig-vacio-motivo">
        <code>{f.id}</code> · Sección: {f.seccion} · Origen: {f.origen} · {f.tokens_aprox} tokens
      </p>
      <p className="ig-corpus-texto">{f.texto}</p>
      <p>
        <span className="ig-sesion-etiqueta">URL</span> <Enlace url={f.url} />
      </p>
      <button type="button" className="ignis-btn" onClick={cerrar}>
        Cerrar
      </button>
    </article>
  );
}

function Tabla({
  pagina,
  elegido,
  elegir,
}: {
  pagina: Pagina<FragmentoBuscado>;
  elegido: string | null;
  elegir: (f: Fragmento) => void;
}) {
  return (
    <div className="ig-tabla-contenedor">
      <table className="ig-tabla">
        <caption className="sr">Fragmentos del corpus</caption>
        <thead>
          <tr>
            <th scope="col">Título</th>
            <th scope="col">Sección</th>
            <th scope="col">Origen</th>
            <th scope="col">Tokens</th>
            <th scope="col">URL</th>
          </tr>
        </thead>
        <tbody>
          {pagina.elementos.map(({ fragmento: f }) => (
            <tr key={f.id} aria-selected={elegido === f.id}>
              <td>
                <button type="button" className="ig-enlace-boton" onClick={() => elegir(f)}>
                  {f.titulo || f.id}
                </button>
              </td>
              <td>{f.seccion}</td>
              <td>{f.origen}</td>
              <td className="numero">{f.tokens_aprox}</td>
              <td>
                <Enlace url={f.url} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function PestanaCorpus() {
  const [texto, setTexto] = useState("");
  const [busqueda, setBusqueda] = useState("");
  const [seccion, setSeccion] = useState("");
  const [pagina, setPagina] = useState(1);
  const [elegido, setElegido] = useState<Fragmento | null>(null);

  // La búsqueda se pide tras una pausa al escribir, no en cada tecla.
  useEffect(() => {
    const t = setTimeout(() => {
      setBusqueda(texto.trim());
      setPagina(1);
    }, ESPERA_BUSQUEDA_MS);
    return () => clearTimeout(t);
  }, [texto]);

  const pedir = useCallback(
    () => api.fragmentos({ q: busqueda || undefined, seccion: seccion || undefined, pagina, tamano: POR_PAGINA }),
    [busqueda, seccion, pagina],
  );
  const fragmentos = useCarga(pedir);
  const estadisticas = useCarga(api.estadisticasBase);
  const secciones =
    estadisticas.estado.tipo === "listo" ? Object.keys(estadisticas.estado.datos.secciones).sort((a, b) => a.localeCompare(b, "es")) : [];

  return (
    <section className="ig-pestana" aria-labelledby="titulo-corpus">
      <header className="ig-pestana-cab">
        <span className="ig-pestana-icono" aria-hidden="true">
          <Icono nombre="corpus" tamano={22} />
        </span>
        <h1 id="titulo-corpus">Corpus</h1>
      </header>
      <p className="ig-vacio-motivo">Fragmentos del corpus Gold con su URL y su origen. Solo lectura.</p>

      <div className="ig-sesion-datos">
        <div>
          <label className="ig-sesion-etiqueta" htmlFor="ig-corpus-busqueda">
            Buscar
          </label>
          <input
            id="ig-corpus-busqueda"
            className="ignis-input"
            type="search"
            value={texto}
            onChange={(e) => setTexto(e.target.value)}
            placeholder="Texto del fragmento"
            autoComplete="off"
          />
        </div>
        <div>
          <label className="ig-sesion-etiqueta" htmlFor="ig-corpus-seccion">
            Sección
          </label>
          <select
            id="ig-corpus-seccion"
            className="ignis-select"
            value={seccion}
            onChange={(e) => {
              setSeccion(e.target.value);
              setPagina(1);
            }}
          >
            <option value="">Todas</option>
            {secciones.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </div>
      </div>

      {elegido ? <Detalle f={elegido} cerrar={() => setElegido(null)} /> : null}

      <Bloque
        titulo="fragmentos del corpus"
        carga={fragmentos.estado}
        reintentar={fragmentos.cargar}
        vacio={(p) => (p.total === 0 ? "Ningún fragmento coincide con la búsqueda" : null)}
      >
        {(p) => {
          const paginas = Math.max(1, Math.ceil(p.total / POR_PAGINA));
          return (
            <>
              <p className="ig-vacio-motivo" role="status" aria-live="polite">
                {p.total} fragmentos · Página {p.pagina} de {paginas}
              </p>
              <Tabla pagina={p} elegido={elegido?.id ?? null} elegir={setElegido} />
              <div className="ig-corpus-paginacion">
                <button type="button" className="ignis-btn" disabled={p.pagina <= 1} onClick={() => setPagina(p.pagina - 1)}>
                  Anterior
                </button>{" "}
                <button
                  type="button"
                  className="ignis-btn"
                  disabled={p.pagina >= paginas}
                  onClick={() => setPagina(p.pagina + 1)}
                >
                  Siguiente
                </button>
              </div>
            </>
          );
        }}
      </Bloque>
    </section>
  );
}
