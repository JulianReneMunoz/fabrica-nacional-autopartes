import { useEffect, useState } from "react";
import { api, type Maquina } from "../api";
import { TarjetaMaquina } from "../componentes/plantilla/TarjetaMaquina";
import { MAQUINAS } from "../maquinas";

/** La biblioteca sale de `maquinas/*.ts`; la API aporta los datos de la empresa (con su URL y origen). */
export default function Biblioteca() {
  const [maquinas, setMaquinas] = useState<Maquina[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    api.maquinas().then(setMaquinas, (e: Error) => setError(e.message));
  }, []);
  const origenes = new Set(maquinas?.flatMap((m) => m.datos_empresa.map((d) => d.origen)) ?? []);
  return (
    <>
      <p className="relacion" style={{ display: "inline-block" }}>biblioteca · método anatomy</p>
      <h1 className="titular">¿Cómo funcionan las máquinas detrás de una autoparte?</h1>
      <p className="bajada">
        Cada tarjeta responde una pregunta con una relación medible. Los datos de la empresa se extraen de la base de
        conocimiento construida con web scraping de autopartesfanalca.com.co y fanalca.com, y se muestran con su URL.
        Las geometrías y cifras de las máquinas son demostrativas.
      </p>
      {error && <p className="aviso error">No se pudo consultar la API ({error}). Iniciar el backend con <code>.\scripts\ejecutar_api.ps1</code>.</p>}
      {origenes.size > 0 && !origenes.has("scraping") && (
        <p className="aviso">
          La base actual proviene de la semilla o de lectura web. Ejecutar <code>uv run fabrica pipeline</code> para
          reemplazarla por el resultado del scraping.
        </p>
      )}
      <div className="rejilla">
        {MAQUINAS.map((def) => (
          <TarjetaMaquina key={def.id} def={def} datos={maquinas?.find((m) => m.id === def.id) ?? null} />
        ))}
      </div>
    </>
  );
}
