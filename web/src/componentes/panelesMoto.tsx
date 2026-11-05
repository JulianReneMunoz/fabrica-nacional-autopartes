/**
 * Paneles de la máquina «moto»: pestañas plegables, diagrama del ciclo de 4 tiempos, ficha técnica
 * con fuente y estado por campo, FAQ de modelos (deterministas) y FAQ de Fanalca (precalculadas con citas).
 * Todo número muestra su procedencia: «supuesto didáctico», ficha publicada o «No publicado».
 */
import { useState } from "react";
import type { FaqVisor, FichaMotoApi, ItemFaqVisor, RespuestaModeloApi, RespuestaQa } from "../api";
import { InsigniaFuente } from "./plantilla/InsigniaFuente";
import { ETIQUETA_SUPUESTO, FASES_CICLO, type FaseCiclo, FASES_INFO, faseCiclo, type CampoFichaApi } from "../modelos/moto";

export const fmt = (v: number, d = 0) => v.toLocaleString("es-CO", { minimumFractionDigits: d, maximumFractionDigits: d });
export const NO_PUBLICADO = "No publicado";
export const FRASE_RECHAZO = "La información solicitada no se encuentra en la base de conocimiento de Fanalca.";

/* ---------- insignias (una sola implementación: plantilla/InsigniaFuente) ---------- */
export function InsigniaSupuesto({ texto = ETIQUETA_SUPUESTO }: { texto?: string }) {
  return <InsigniaFuente fuente="supuesto" texto={texto} />;
}
export function InsigniaEstado({ estado }: { estado: CampoFichaApi["estado"] }) {
  return estado === "publicado" ? (
    <InsigniaFuente fuente="ficha" texto="publicado" />
  ) : estado === "supuesto" ? (
    <InsigniaFuente fuente="supuesto" texto={ETIQUETA_SUPUESTO} />
  ) : (
    <InsigniaFuente fuente="no_publicado" texto={NO_PUBLICADO.toLowerCase()} />
  );
}

/** Nombre de la fase con una muestra de su color (el texto va en tinta: el color solo acompaña). */
export function NombreFase({ fase }: { fase: FaseCiclo }) {
  return (
    <span className="nombre-fase">
      <span className="muestra-fase" style={{ background: FASES_INFO[fase].color }} aria-hidden="true" />
      <b>{FASES_INFO[fase].nombre}</b>
    </span>
  );
}

/* ---------- diagrama del ciclo de 4 tiempos ---------- */
export function DiagramaCiclo({ theta720 }: { theta720: number }) {
  const cx = 70;
  const cy = 70;
  const R = 58;
  const r = 34;
  const punto = (grados: number, rad: number) => {
    const a = ((grados - 90) * Math.PI) / 180; // 0° arriba, sentido horario
    return [cx + rad * Math.cos(a), cy + rad * Math.sin(a)];
  };
  const sector = (desde: number, hasta: number) => {
    const [x1, y1] = punto(desde, R);
    const [x2, y2] = punto(hasta, R);
    const [x3, y3] = punto(hasta, r);
    const [x4, y4] = punto(desde, r);
    return `M${x1.toFixed(2)} ${y1.toFixed(2)} A${R} ${R} 0 0 1 ${x2.toFixed(2)} ${y2.toFixed(2)} L${x3.toFixed(2)} ${y3.toFixed(2)} A${r} ${r} 0 0 0 ${x4.toFixed(2)} ${y4.toFixed(2)}Z`;
  };
  const t = ((theta720 % 720) + 720) % 720;
  const fase = faseCiclo(t);
  const [ax, ay] = punto((t / 720) * 360, R + 6);
  const [bx, by] = punto((t / 720) * 360, r - 4);
  return (
    <figure className="diagrama-ciclo" aria-label="Diagrama del ciclo de cuatro tiempos">
      <svg viewBox="0 0 140 140" role="img" aria-label={`Ciclo 4T: ${FASES_INFO[fase].nombre}, ${fmt(t)} grados de 720`}>
        {FASES_CICLO.map((f, i) => (
          <path key={f} d={sector(i * 90, (i + 1) * 90)} fill={FASES_INFO[f].color} opacity={f === fase ? 1 : 0.42} stroke="var(--papel)" strokeWidth="1.5" />
        ))}
        {FASES_CICLO.map((f, i) => {
          const [x, y] = punto(i * 90 + 45, (R + r) / 2);
          return (
            <text key={f} x={x} y={y + 3} textAnchor="middle" fontSize="9" fontWeight="700" className="texto-sector">
              {["ADM", "COM", "EXP", "ESC"][i]}
            </text>
          );
        })}
        <line x1={bx} y1={by} x2={ax} y2={ay} stroke="var(--tinta)" strokeWidth="2.4" />
        <circle cx={ax} cy={ay} r="3.2" fill="var(--tinta)" />
        <text x={cx} y={cy - 2} textAnchor="middle" fontSize="13" fontWeight="700">{fmt(t)}°</text>
        <text x={cx} y={cy + 11} textAnchor="middle" fontSize="8" fill="var(--tinta-2)">de 720°</text>
      </svg>
      <figcaption>
        <NombreFase fase={fase} />: pistón {FASES_INFO[fase].pistón}. {FASES_INFO[fase].detalle}
      </figcaption>
    </figure>
  );
}

/* ---------- ficha técnica ---------- */
const GRUPOS: Record<string, string> = {
  motor: "Motor",
  transmision: "Transmisión",
  suspension: "Suspensión",
  llantas: "Llantas",
  capacidades: "Capacidades",
  electrico: "Eléctrico",
  chasis: "Chasis y carrocería",
};
const CAMPOS: Record<string, string> = {
  tipo: "Tipo de motor",
  cilindrada: "Cilindrada",
  diametro_x_carrera: "Diámetro × carrera",
  potencia: "Potencia",
  regimen_potencia: "Régimen de potencia",
  torque: "Torque",
  regimen_torque: "Régimen de torque",
  relacion_compresion: "Relación de compresión",
  corte_encendido: "Corte de encendido",
  marchas: "Número de marchas",
  relacion_primaria: "Relación primaria",
  relaciones_por_marcha: "Relaciones por marcha",
  transmision_final: "Transmisión final",
  delantera: "Delantera",
  trasera: "Trasera",
  tanque: "Tanque",
  peso: "Peso",
  arranque: "Arranque",
  iluminacion_delantera: "Iluminación delantera",
  iluminacion_trasera: "Iluminación trasera",
  instrumentos: "Instrumentos",
  sillin: "Sillín",
  tanque_descripcion: "Tanque (descripción)",
  delantero: "Freno delantero",
  cbs: "CBS",
  reparto_cbs: "Reparto del CBS",
};

/** Pieza(s) del modelo 3D que cada dato de la ficha o de la FAQ resalta al pulsarlo. */
export const PIEZAS_POR_CAMPO: Record<string, string[]> = {
  "motor.tipo": ["cilindro", "piston", "biela", "ciguenal"],
  "motor.cilindrada": ["cilindro", "piston"],
  "motor.diametro_x_carrera": ["cilindro", "piston"],
  "motor.potencia": ["ciguenal", "piston"],
  "motor.regimen_potencia": ["ciguenal"],
  "motor.torque": ["ciguenal"],
  "motor.regimen_torque": ["ciguenal"],
  "motor.relacion_compresion": ["cilindro", "piston"],
  "motor.corte_encendido": ["bujia"],
  "transmision.marchas": ["caja_cambios"],
  "transmision.relacion_primaria": ["caja_cambios"],
  "transmision.relaciones_por_marcha": ["caja_cambios"],
  "transmision.transmision_final": ["pinon", "cadena", "corona"],
  "suspension.delantera": ["tubo_izquierdo", "tubo_derecho", "botella_izquierda", "botella_derecha", "puente_horquilla"],
  "suspension.trasera": ["monoamortiguador", "basculante"],
  "llantas.delantera": ["llanta_delantera", "rin_delantero"],
  "llantas.trasera": ["llanta_trasera", "rin_trasero"],
  "capacidades.tanque": ["tanque"],
  "capacidades.peso": ["chasis", "cuna_chasis"],
  "electrico.arranque": ["ciguenal", "caja_cambios"],
  "electrico.iluminacion_delantera": ["farola"],
  "electrico.iluminacion_trasera": ["stop"],
  "electrico.instrumentos": ["velocimetro"],
  "chasis.sillin": ["sillin"],
  "chasis.tanque_descripcion": ["tanque"],
};
const PIEZAS_FRENO: Record<string, string[]> = {
  delantero: ["disco_delantero", "caliper_delantero"],
  trasero: ["disco_trasero", "caliper_trasero"],
  cbs: ["unidad_cbs"],
  reparto_cbs: ["unidad_cbs"],
};
/** Normaliza `frenos.STD.trasero` o `grupo.campo` a la clave de `PIEZAS_POR_CAMPO`. */
export function piezasDeCampo(ruta: string): string[] {
  const m = /^frenos\.(?:STD|DLX)\.(.+)$/.exec(ruta);
  if (m) return PIEZAS_FRENO[m[1]] ?? [];
  return PIEZAS_POR_CAMPO[ruta] ?? [];
}

function valorLegible(c: CampoFichaApi): string {
  if (c.estado === "no_publicado" || c.valor === null || c.valor === undefined) return NO_PUBLICADO;
  if (typeof c.valor === "boolean") return c.valor ? "Sí" : "No";
  const unidad = c.unidad && !["ancho/perfil-rin", "piñón/corona (dientes)"].includes(c.unidad) ? ` ${c.unidad}` : "";
  return `${String(c.valor)}${unidad}`;
}

function FilaFicha(props: { ruta: string; etiqueta: string; campo: CampoFichaApi; activa: boolean; alPulsar: (ruta: string) => void }) {
  const { campo: c } = props;
  const sinDato = c.estado === "no_publicado";
  return (
    <tr className={props.activa ? "activa" : ""}>
      <th scope="row">
        <button className="fila-dato" aria-pressed={props.activa} onClick={() => props.alPulsar(props.ruta)} data-campo={props.ruta} title="Resaltar la pieza en el modelo 3D">
          {props.etiqueta}
        </button>
      </th>
      <td className={sinDato ? "sin-dato" : "num"}>{valorLegible(c)}</td>
      <td>
        <InsigniaEstado estado={c.estado} />
      </td>
      <td className="fuente-ficha">
        {c.fuente ? (
          <>
            {c.fuente}
            {c.fecha_consulta && <span className="fecha"> · consulta {c.fecha_consulta}</span>}
          </>
        ) : (
          <span className="fecha">sin fuente verificable</span>
        )}
        {c.observacion && <span className="obs">{c.observacion}</span>}
      </td>
    </tr>
  );
}

export function FichaTecnica(props: {
  ficha: FichaMotoApi | null;
  error: string | null;
  seleccion: string | null;
  alSeleccionar: (ruta: string) => void;
}) {
  const { ficha } = props;
  if (props.error) return <p className="aviso error">Sin ficha: {props.error}</p>;
  if (!ficha) return <p className="aviso">Consultando la ficha técnica…</p>;
  return (
    <div className="ficha-tecnica">
      <p className="aviso">
        Ficha curada de <b>{ficha.nombre}</b> ({ficha.categoria}). Cada valor lleva fuente y fecha de consulta; un dato sin fuente se muestra como «{NO_PUBLICADO}». Pulsar un dato resalta la pieza en 3D.
      </p>
      {Object.entries(GRUPOS).map(([g, titulo]) => {
        const campos = ficha.grupos[g];
        if (!campos) return null;
        return (
          <section key={g} aria-label={titulo}>
            <h4>{titulo}</h4>
            <table>
              <tbody>
                {Object.entries(campos).map(([k, c]) => (
                  <FilaFicha key={`${g}.${k}`} ruta={`${g}.${k}`} etiqueta={CAMPOS[k] ?? k} campo={c} activa={props.seleccion === `${g}.${k}`} alPulsar={props.alSeleccionar} />
                ))}
              </tbody>
            </table>
          </section>
        );
      })}
      {Object.entries(ficha.por_version).map(([ver, campos]) => (
        <section key={ver} aria-label={`Frenos ${ver}`}>
          <h4>Frenos · versión {ver}</h4>
          <table>
            <tbody>
              {Object.entries(campos).map(([k, c]) => (
                <FilaFicha key={`frenos.${ver}.${k}`} ruta={`frenos.${ver}.${k}`} etiqueta={CAMPOS[k] ?? k} campo={c} activa={props.seleccion === `frenos.${ver}.${k}`} alPulsar={props.alSeleccionar} />
              ))}
            </tbody>
          </table>
        </section>
      ))}
      {ficha.pendientes_de_confirmar.length > 0 && (
        <section aria-label="Pendientes de confirmar">
          <h4>Pendientes de confirmar</h4>
          <ul className="datos">
            {ficha.pendientes_de_confirmar.map((p) => (
              <li key={p.campo}>
                <code>{p.campo}</code>: {p.detalle}
              </li>
            ))}
          </ul>
        </section>
      )}
      <section aria-label="Fuentes de la ficha">
        <h4>Fuentes</h4>
        <ul className="datos">
          {ficha.fuentes.map((f) => (
            <li key={f.id}>
              <b>{f.id}</b> · consulta {f.fecha_consulta ?? "—"}
              {f.url ? (
                <>
                  {" "}
                  <a href={f.url} target="_blank" rel="noreferrer">{f.url}</a>
                </>
              ) : (
                " · documento aportado por el usuario (no se muestra en la aplicación)"
              )}
              <br />
              <span className="fecha">{f.descripcion}</span>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}

/* ---------- FAQ de modelos (deterministas) ---------- */
export function FaqModelos(props: { items: RespuestaModeloApi[] | null; error: string | null; alAbrir: (campos: string[] | null) => void }) {
  if (props.error) return <p className="aviso error">Sin preguntas de modelo: {props.error}</p>;
  if (!props.items) return <p className="aviso">Consultando las preguntas del modelo…</p>;
  return (
    <div className="faq">
      <p className="aviso">Respuestas deterministas desde la ficha curada: cada una cita el campo y la fuente que la sustentan.</p>
      {props.items.map((it) => (
        <details key={it.id} data-faq-modelo={it.id} onToggle={(e) => props.alAbrir((e.currentTarget as HTMLDetailsElement).open ? it.campos : null)}>
          <summary>{it.pregunta}</summary>
          <p className="respuesta">{it.respuesta}</p>
          <p className="citas">
            <InsigniaEstado estado={it.estado} /> campos: <code>{it.campos.join(", ")}</code>
            <br />
            fuente: {it.fuentes.length ? it.fuentes.join("; ") : <span className="fecha">sin fuente verificable</span>}
          </p>
        </details>
      ))}
    </div>
  );
}

/* ---------- FAQ de Fanalca (precalculadas + pregunta en vivo) ---------- */
function CitasFanalca({ fuentes }: { fuentes: { fragmento_id: string; url: string; titulo?: string }[] }) {
  if (fuentes.length === 0) return <p className="citas">Sin citas: la base de conocimiento no contiene la respuesta.</p>;
  return (
    <ul className="citas">
      {fuentes.map((f) => (
        <li key={f.fragmento_id}>
          <code>{f.fragmento_id}</code> {f.titulo ? `· ${f.titulo} ` : ""}
          <a href={f.url} target="_blank" rel="noreferrer">{f.url}</a>
        </li>
      ))}
    </ul>
  );
}

export function FaqFanalca(props: {
  datos: FaqVisor | null;
  error: string | null;
  faltaArchivo: boolean;
  enVivo: { respuesta: RespuestaQa | null; error: string | null; consultando: boolean };
  alPreguntar: (pregunta: string) => void;
}) {
  const [texto, setTexto] = useState("");
  const { datos } = props;
  return (
    <div className="faq">
      {props.faltaArchivo && (
        <p className="aviso" role="status" data-testid="faq-sin-archivo">
          Aún no hay respuestas precalculadas. Ejecutar <code>uv run fabrica faq-visor</code> para generarlas (guarda <code>data/gold/faq_visor.json</code> con sus citas).
        </p>
      )}
      {props.error && !props.faltaArchivo && <p className="aviso error">No se pudo leer la FAQ de Fanalca: {props.error}</p>}
      {!datos && !props.error && !props.faltaArchivo && <p className="aviso">Consultando la FAQ de Fanalca…</p>}
      {datos && (
        <>
          <p className="aviso">
            {datos.advertencia} Proveedor {datos.proveedor} · modelo {datos.modelo} · prompt {datos.version_prompt} · generado {datos.generado}.
          </p>
          {datos.items.map((it: ItemFaqVisor) => (
            <details key={it.id} data-faq-fanalca={it.id}>
              <summary>{it.pregunta}</summary>
              <p className="respuesta">{it.rechazo ? FRASE_RECHAZO : it.respuesta}</p>
              <p className="citas">
                <InsigniaFuente fuente="base_conocimiento" /> confianza {it.confianza}
                {it.rechazo && " · sin respuesta en la base"}
              </p>
              <CitasFanalca fuentes={it.fuentes} />
            </details>
          ))}
        </>
      )}
      <form
        className="en-vivo"
        onSubmit={(e) => {
          e.preventDefault();
          if (texto.trim().length >= 3) props.alPreguntar(texto.trim());
        }}
      >
        <label htmlFor="pregunta-en-vivo">Pregunta sobre Fanalca</label>
        <input id="pregunta-en-vivo" value={texto} maxLength={500} onChange={(e) => setTexto(e.target.value)} placeholder="¿Dónde queda la sede principal?" />
        <button className="boton" disabled={texto.trim().length < 3 || props.enVivo.consultando}>
          {props.enVivo.consultando ? "Consultando…" : "Preguntar en vivo"}
        </button>
      </form>
      {props.enVivo.error && <p className="aviso error">Pregunta en vivo: {props.enVivo.error}</p>}
      {props.enVivo.respuesta && (
        <div data-testid="respuesta-en-vivo">
          <p className="respuesta">{props.enVivo.respuesta.respuesta}</p>
          <p className="citas">
            en vivo · {props.enVivo.respuesta.proveedor} / {props.enVivo.respuesta.modelo} · confianza {props.enVivo.respuesta.confianza}
          </p>
          <CitasFanalca fuentes={props.enVivo.respuesta.fuentes} />
        </div>
      )}
    </div>
  );
}
