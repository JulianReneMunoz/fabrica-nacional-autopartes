/** Tarjeta de la biblioteca: se construye a partir de `maquinas/<id>.ts` y, si hay API, de los datos de la empresa. */
import type { Maquina } from "../../api";
import type { DefinicionMaquina } from "../../maquinas/tipos";
import { C } from "../../tema/colores";
import { InsigniaFuente } from "./InsigniaFuente";
import { TextoEnLinea } from "./TextoEnLinea";

/** Láminas esquemáticas propias (no reproducen productos reales). */
function Lamina({ id }: { id: DefinicionMaquina["lamina"] }) {
  const trazo = { stroke: C.tinta, strokeWidth: 1.5, fill: "none" } as const;
  if (id === "freno")
    return (
      <svg viewBox="0 0 340 150" className="lamina" role="img" aria-label="Esquema de disco y pinza">
        <circle cx="150" cy="78" r="58" {...trazo} />
        <circle cx="150" cy="78" r="20" {...trazo} />
        {[0, 1, 2, 3].map((i) => (
          <circle key={i} cx={150 + 11 * Math.cos((i * Math.PI) / 2 + 0.78)} cy={78 + 11 * Math.sin((i * Math.PI) / 2 + 0.78)} r="2.5" fill={C.tinta} />
        ))}
        <rect x="128" y="10" width="44" height="34" rx="5" fill={C.acento} stroke={C.tinta} strokeWidth="1.5" />
        <path d="M200 28 h60" stroke={C.acento} strokeWidth="2" markerEnd="url(#fl)" />
        <text x="205" y="22" fontSize="11" fill={C.tinta}>F = p·A</text>
        <text x="215" y="100" fontSize="11" fill={C.tinta}>T = 2μF·r</text>
        <defs>
          <marker id="fl" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="7" markerHeight="7" orient="auto">
            <path d="M0 0 L8 4 L0 8 z" fill={C.acento} />
          </marker>
        </defs>
      </svg>
    );
  if (id === "moto_honda")
    return (
      <svg viewBox="0 0 340 150" className="lamina" role="img" aria-label="Esquema de motocicleta con piñón, cadena y corona">
        <circle cx="85" cy="92" r="40" {...trazo} />
        <circle cx="255" cy="92" r="38" {...trazo} />
        <circle cx="85" cy="92" r="9" fill={C.tinta} />
        <circle cx="255" cy="92" r="9" fill={C.tinta} />
        <path d="M85 92 L135 60 L200 60 L255 92 M135 60 L120 40 L170 36 L205 60" {...trazo} />
        <circle cx="150" cy="86" r="7" fill={C.acento} stroke={C.tinta} strokeWidth="1.5" />
        <path d="M85 78 L150 80 M85 106 L150 92" stroke={C.dato} strokeWidth="2" strokeDasharray="4 3" />
        <rect x="165" y="30" width="38" height="12" rx="3" fill={C.acento} stroke={C.tinta} strokeWidth="1.5" />
        <text x="14" y="18" fontSize="11" fill={C.tinta}>v = rpm·2πR / i</text>
        <text x="222" y="146" fontSize="11" fill={C.tinta}>T = 2μFr</text>
      </svg>
    );
  if (id === "prensa")
    return (
      <svg viewBox="0 0 340 150" className="lamina" role="img" aria-label="Esquema de prensa excéntrica">
        <rect x="110" y="10" width="120" height="14" {...trazo} />
        <circle cx="170" cy="36" r="12" {...trazo} />
        <line x1="170" y1="36" x2="176" y2="78" {...trazo} />
        <rect x="140" y="78" width="60" height="18" fill={C.dato} stroke={C.tinta} strokeWidth="1.5" />
        <rect x="120" y="112" width="100" height="5" fill={C.acento} />
        <rect x="110" y="118" width="120" height="18" {...trazo} />
        <text x="240" y="105" fontSize="11" fill={C.tinta}>F = L·t·τ</text>
      </svg>
    );
  return (
    <svg viewBox="0 0 340 150" className="lamina" role="img" aria-label="Esquema de línea de ensamble">
      <line x1="20" y1="100" x2="320" y2="100" {...trazo} />
      {[0, 1, 2, 3, 4].map((i) => (
        <g key={i}>
          <rect x={30 + i * 60} y={60} width={40} height={30} {...trazo} />
          <rect x={36 + i * 60} y={92} width={28} height={6} fill={i === 2 ? C.acento : C.dato} />
        </g>
      ))}
      <text x="20" y="130" fontSize="11" fill={C.tinta}>takt = disponible / demanda</text>
    </svg>
  );
}

export function TarjetaMaquina({ def, datos }: { def: DefinicionMaquina; datos: Maquina | null }) {
  return (
    <article className="tarjeta" data-maquina={def.id}>
      <Lamina id={def.lamina} />
      <div className="cuerpo">
        <h2>{def.pregunta}</h2>
        <p className="linea">{datos ? <TextoEnLinea texto={datos.una_linea} /> : def.contexto}</p>
        <span className="relacion">{def.formula}</span>
        <ul className="datos">
          {(datos?.datos_empresa ?? []).slice(0, 2).map((d) => (
            <li key={d.fragmento_id}>
              <InsigniaFuente fuente={d.origen} />
              <TextoEnLinea texto={d.texto.length > 170 ? d.texto.slice(0, 167) + "…" : d.texto} />
              <br />
              <a href={d.url} target="_blank" rel="noreferrer">{d.url}</a>
            </li>
          ))}
        </ul>
        <div className="pie barra">
          <a className="boton" href={def.ruta}>Abrir máquina →</a>
          <a className="boton secundario" href={`${def.ruta}?tour=1&inicio=manual`}>Recorrido 30 s</a>
        </div>
      </div>
    </article>
  );
}
