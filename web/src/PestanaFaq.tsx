/**
 * «Preguntas frecuentes» (solo lectura): FAQ precalculada del corpus (`GET /api/v1/faq-visor`) con búsqueda por texto,
 * filtro por categoría y preguntas desplegables con su confianza y sus fuentes. Sin datos simulados: con el backend
 * caído no se muestra ninguna pregunta. Las preguntas sin respaldo (`rechazo`) se marcan como tales.
 */
import { useMemo, useState } from "react";
import { api, type FaqVisor, type ItemFaqVisor } from "./api";
import { Icono } from "./IgnisIconos";
import { Bloque, useCarga } from "./PestanaBase";
import { ListaFuentes } from "./origenFuentes";

const TODAS = "";

/** Texto sin acentos y en minúsculas para comparar la búsqueda. */
export function normalizar(texto: string): string {
  return texto.normalize("NFD").replace(/\p{M}/gu, "").toLowerCase();
}

function Pregunta({ item }: { item: ItemFaqVisor }) {
  // El origen de las fuentes se pide al desplegar la pregunta, no para las 19 a la vez.
  const [abierta, setAbierta] = useState(false);
  return (
    <details className="ig-faq-item" onToggle={(e) => setAbierta(e.currentTarget.open)}>
      <summary>
        {item.pregunta}
        {item.rechazo ? <span className="ignis-insignia">Sin respaldo en la base</span> : null}
      </summary>
      {/* Con rechazo, `respuesta` trae la frase de rechazo fija; la insignia la distingue de una respuesta válida. */}
      <p className={item.rechazo ? "ig-vacio-motivo" : undefined}>{item.respuesta}</p>
      <p>
        <span className="ig-sesion-etiqueta">Confianza</span> {item.confianza || "—"}
      </p>
      {item.fuentes.length ? <ListaFuentes fuentes={item.fuentes} className="ig-faq-fuentes" activo={abierta} /> : null}
    </details>
  );
}

function ListaFaq({ faq }: { faq: FaqVisor }) {
  const [busqueda, setBusqueda] = useState("");
  const [categoria, setCategoria] = useState(TODAS);

  const conteos = useMemo(() => {
    const c = new Map<string, number>();
    for (const i of faq.items) c.set(i.categoria, (c.get(i.categoria) ?? 0) + 1);
    return [...c.entries()].sort(([a], [b]) => a.localeCompare(b, "es"));
  }, [faq.items]);

  const visibles = useMemo(() => {
    const q = normalizar(busqueda.trim());
    return faq.items.filter(
      (i) =>
        (categoria === TODAS || i.categoria === categoria) &&
        (!q || normalizar(i.pregunta).includes(q) || normalizar(i.respuesta).includes(q)),
    );
  }, [faq.items, busqueda, categoria]);

  return (
    <>
      <div className="ig-sesion-datos ig-faq-filtros">
        <div>
          <label className="ig-sesion-etiqueta" htmlFor="ig-faq-busqueda">
            Buscar
          </label>
          <input
            id="ig-faq-busqueda"
            className="ignis-input"
            type="search"
            value={busqueda}
            onChange={(e) => setBusqueda(e.target.value)}
            placeholder="Texto en la pregunta o la respuesta"
            autoComplete="off"
          />
        </div>
        <div>
          <label className="ig-sesion-etiqueta" htmlFor="ig-faq-categoria">
            Categoría
          </label>
          <select id="ig-faq-categoria" className="ignis-select" value={categoria} onChange={(e) => setCategoria(e.target.value)}>
            <option value={TODAS}>Todas ({faq.items.length})</option>
            {conteos.map(([c, n]) => (
              <option key={c} value={c}>
                {c} ({n})
              </option>
            ))}
          </select>
        </div>
      </div>

      <p className="ig-vacio-motivo" role="status" aria-live="polite">
        {visibles.length === 1 ? "1 pregunta" : `${visibles.length} preguntas`}
      </p>
      {visibles.length === 0 ? (
        <div className="ig-vacio-tarjeta">
          <strong>Ninguna pregunta coincide con la búsqueda</strong>
        </div>
      ) : (
        <div className="ig-faq-lista">
          {visibles.map((i) => (
            <Pregunta key={i.id} item={i} />
          ))}
        </div>
      )}

      <footer className="ig-vacio-motivo ig-faq-pie">
        {faq.advertencia ? <p>{faq.advertencia}</p> : null}
        <p>
          Modelo: {faq.proveedor ? `${faq.proveedor} / ` : ""}
          {faq.modelo || "—"} · Prompt: {faq.version_prompt || "—"} · Generado: {faq.generado || "—"}
        </p>
      </footer>
    </>
  );
}

export default function PestanaFaq() {
  const faq = useCarga(api.faqVisor);
  return (
    <section className="ig-pestana" aria-labelledby="titulo-faq">
      <header className="ig-pestana-cab">
        <span className="ig-pestana-icono" aria-hidden="true">
          <Icono nombre="faq" tamano={22} />
        </span>
        <h1 id="titulo-faq">Preguntas frecuentes</h1>
      </header>
      <p className="ig-vacio-motivo">Preguntas frecuentes generadas a partir del corpus, con sus fuentes. Solo lectura.</p>
      <Bloque
        titulo="preguntas frecuentes"
        carga={faq.estado}
        reintentar={faq.cargar}
        vacio={(f) => (f.items.length === 0 ? "Aún no hay preguntas frecuentes generadas" : null)}
      >
        {(f) => <ListaFaq faq={f} />}
      </Bloque>
    </section>
  );
}
