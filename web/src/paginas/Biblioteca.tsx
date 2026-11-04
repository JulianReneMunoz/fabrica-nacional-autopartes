import { useEffect, useState } from "react";
import { api, type Maquina } from "../api";
import { Insignia } from "../componentes/anatomia";

/** Láminas esquemáticas propias (no reproducen productos reales). */
function Lamina({ id }: { id: string }) {
  const trazo = { stroke: "#0b0b0b", strokeWidth: 1.5, fill: "none" } as const;
  if (id === "freno")
    return (
      <svg viewBox="0 0 340 150" className="lamina" role="img" aria-label="Esquema de disco y pinza">
        <circle cx="150" cy="78" r="58" {...trazo} />
        <circle cx="150" cy="78" r="20" {...trazo} />
        {[0, 1, 2, 3].map((i) => (
          <circle key={i} cx={150 + 11 * Math.cos((i * Math.PI) / 2 + 0.78)} cy={78 + 11 * Math.sin((i * Math.PI) / 2 + 0.78)} r="2.5" fill="#0b0b0b" />
        ))}
        <rect x="128" y="10" width="44" height="34" rx="5" fill="#eb6834" stroke="#0b0b0b" strokeWidth="1.5" />
        <path d="M200 28 h60" stroke="#eb6834" strokeWidth="2" markerEnd="url(#fl)" />
        <text x="205" y="22" fontSize="11">F = p·A</text>
        <text x="215" y="100" fontSize="11">T = 2μF·r</text>
        <defs>
          <marker id="fl" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="7" markerHeight="7" orient="auto">
            <path d="M0 0 L8 4 L0 8 z" fill="#eb6834" />
          </marker>
        </defs>
      </svg>
    );
  if (id === "prensa")
    return (
      <svg viewBox="0 0 340 150" className="lamina" role="img" aria-label="Esquema de prensa excéntrica">
        <rect x="110" y="10" width="120" height="14" {...trazo} />
        <circle cx="170" cy="36" r="12" {...trazo} />
        <line x1="170" y1="36" x2="176" y2="78" {...trazo} />
        <rect x="140" y="78" width="60" height="18" fill="#2a78d6" stroke="#0b0b0b" strokeWidth="1.5" />
        <rect x="120" y="112" width="100" height="5" fill="#eb6834" />
        <rect x="110" y="118" width="120" height="18" {...trazo} />
        <text x="240" y="105" fontSize="11">F = L·t·τ</text>
      </svg>
    );
  return (
    <svg viewBox="0 0 340 150" className="lamina" role="img" aria-label="Esquema de línea de ensamble">
      <line x1="20" y1="100" x2="320" y2="100" {...trazo} />
      {[0, 1, 2, 3, 4].map((i) => (
        <g key={i}>
          <rect x={30 + i * 60} y={60} width={40} height={30} {...trazo} />
          <rect x={36 + i * 60} y={92} width={28} height={6} fill={i === 2 ? "#eb6834" : "#2a78d6"} />
        </g>
      ))}
      <text x="20" y="130" fontSize="11">takt = disponible / demanda</text>
    </svg>
  );
}

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
        <p className="aviso" style={{ marginBottom: 16 }}>
          La base actual proviene de la semilla o de lectura web. Ejecutar <code>uv run fabrica pipeline</code> para
          reemplazarla por el resultado del scraping.
        </p>
      )}
      <div className="rejilla">
        {(maquinas ?? []).map((m) => (
          <article className="tarjeta" key={m.id} data-maquina={m.id}>
            <Lamina id={m.id} />
            <div className="cuerpo">
              <h2>{m.pregunta}</h2>
              <p className="linea">{m.una_linea}</p>
              <span className="relacion">{m.relacion}</span>
              <ul className="datos">
                {m.datos_empresa.slice(0, 2).map((d) => (
                  <li key={d.fragmento_id}>
                    <Insignia tipo={d.origen} />
                    {d.texto.length > 170 ? d.texto.slice(0, 167) + "…" : d.texto}
                    <br />
                    <a href={d.url} target="_blank" rel="noreferrer">{d.url}</a>
                  </li>
                ))}
              </ul>
              <div className="pie barra">
                <a className="boton" href={m.ruta}>Abrir máquina →</a>
                <a className="boton secundario" href={`${m.ruta}?tour=1`}>Recorrido 30 s</a>
              </div>
            </div>
          </article>
        ))}
      </div>
    </>
  );
}
