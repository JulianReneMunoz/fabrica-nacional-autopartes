/**
 * Origen real de cada fuente citada (scraping, lectura_web, semilla…), leído de `GET /api/v1/base/fragmentos/{id}`.
 * La regla del proyecto exige mostrar la URL y el origen de cada fuente; el origen nunca se deduce del id ni de la URL:
 * si el backend no lo entrega, se muestra «origen no disponible». Las peticiones se guardan en una caché del módulo
 * para no repetirlas; un fallo no se guarda, así se reintenta la próxima vez.
 */
import { useEffect, useState } from "react";
import { api } from "./api";
import { urlSegura } from "./PestanaBase";

const cache = new Map<string, Promise<string | null>>();

/** Origen de un fragmento o `null` si no está disponible. */
export function pedirOrigen(id: string): Promise<string | null> {
  let promesa = cache.get(id);
  if (!promesa) {
    promesa = api
      .fragmento(id)
      .then((f) => (typeof f.origen === "string" && f.origen ? f.origen : null))
      .catch(() => {
        cache.delete(id);
        return null;
      });
    cache.set(id, promesa);
  }
  return promesa;
}

/** Vacía la caché (solo para pruebas). */
export function vaciarCacheOrigenes(): void {
  cache.clear();
}

/**
 * Orígenes de una lista de fragmentos: `undefined` mientras carga, `null` si no está disponible. Con `activo` en falso no
 * se pide nada (la FAQ solo pide los de la pregunta desplegada). Un resultado de una lista anterior se descarta.
 */
export function useOrigenes(ids: readonly string[], activo = true): Record<string, string | null> {
  const clave = JSON.stringify(ids);
  const [origenes, setOrigenes] = useState<Record<string, string | null>>({});
  useEffect(() => {
    const lista = JSON.parse(clave) as string[];
    if (!activo || lista.length === 0) return;
    let vigente = true;
    void Promise.all(lista.map(async (id) => [id, await pedirOrigen(id)] as const)).then((pares) => {
      if (vigente) setOrigenes(Object.fromEntries(pares));
    });
    return () => {
      vigente = false;
    };
  }, [clave, activo]);
  return origenes;
}

function textoOrigen(origen: string | null | undefined): string {
  if (origen === undefined) return "origen: cargando…";
  if (origen === null) return "origen no disponible";
  return `origen: ${origen}`;
}

export interface FuenteCitada {
  fragmento_id: string;
  url: string;
  titulo?: string;
}

/** Lista de fuentes con su URL (solo http(s) se enlaza) y su origen real. */
export function ListaFuentes({
  fuentes,
  className,
  activo = true,
}: {
  fuentes: readonly FuenteCitada[];
  className: string;
  activo?: boolean;
}) {
  const origenes = useOrigenes(
    fuentes.map((f) => f.fragmento_id),
    activo,
  );
  return (
    <ul className={className} aria-label="Fuentes">
      {fuentes.map((f) => {
        const texto = f.titulo || f.fragmento_id;
        return (
          <li key={f.fragmento_id}>
            {urlSegura(f.url) ? (
              <a href={f.url} target="_blank" rel="noopener noreferrer">
                {texto}
              </a>
            ) : (
              <span>{texto}</span>
            )}{" "}
            <small className="ig-fuente-origen">({textoOrigen(origenes[f.fragmento_id])})</small>
          </li>
        );
      })}
    </ul>
  );
}
