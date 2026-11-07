/**
 * Componentes del «Explorador de la motocicleta» (fase 14). Texto informativo: definición del ensamblaje
 * (sistemas y piezas), ficha técnica con fuente y estado, o base de conocimiento con cita. Lo que no existe
 * se muestra como «No publicado». Sin marcas, referencias de repuesto, disponibilidad ni precios.
 */
import { useMemo, useState, type KeyboardEvent } from "react";
import * as THREE from "three";
import { apiMoto, type FichaMotoApi, type Pieza, type RespuestaPieza, type SistemaApi } from "../api";
import { ICONOS_SISTEMA, type IdSistema, LECCIONES, ORDEN_SISTEMAS } from "../maquinas/explorador_moto";
import type { CampoFichaApi } from "../modelos/moto";
import type { EncuadreCamara, GeometriaDespieceMoto } from "../paginas/EscenaMoto";
import { CAMPOS, FilaFicha, FRASE_RECHAZO, GRUPOS, NO_PUBLICADO, piezasDeCampo } from "./panelesMoto";
import { InsigniaFuente } from "./plantilla/InsigniaFuente";

/* ---------- lógica pura (probada en Vitest) ---------- */

const sinTildes = (s: string) => s.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();

/** Piezas cuyo nombre (o id) contiene todas las palabras de la consulta, sin distinguir tildes ni mayúsculas. */
export function buscarPiezas(piezas: Pieza[], consulta: string, maximo = 8): Pieza[] {
  const palabras = sinTildes(consulta).split(/\s+/).filter(Boolean);
  if (palabras.length === 0) return [];
  return piezas.filter((p) => palabras.every((w) => sinTildes(`${p.nombre} ${p.id.replace(/_/g, " ")}`).includes(w))).slice(0, maximo);
}

export interface CampoRelacionado {
  ruta: string;
  etiqueta: string;
  campo: CampoFichaApi;
}
/** Campos de la ficha cuyas piezas pertenecen al sistema (por grupo y, en frenos, por versión). */
export function camposRelacionados(ficha: FichaMotoApi | null, piezasSistema: Iterable<string>): CampoRelacionado[] {
  if (!ficha) return [];
  const ids = new Set(piezasSistema);
  const salida: CampoRelacionado[] = [];
  for (const [g, campos] of Object.entries(ficha.grupos)) {
    for (const [k, c] of Object.entries(campos)) {
      const ruta = `${g}.${k}`;
      if (piezasDeCampo(ruta).some((p) => ids.has(p))) salida.push({ ruta, etiqueta: `${GRUPOS[g] ?? g} · ${CAMPOS[k] ?? k}`, campo: c });
    }
  }
  for (const [ver, campos] of Object.entries(ficha.por_version)) {
    for (const [k, c] of Object.entries(campos)) {
      const ruta = `frenos.${ver}.${k}`;
      if (piezasDeCampo(ruta).some((p) => ids.has(p))) salida.push({ ruta, etiqueta: `Frenos ${ver} · ${CAMPOS[k] ?? k}`, campo: c });
    }
  }
  return salida;
}

/** Un dato de ficha solo se muestra si trae su estado y, si está publicado, su fuente. */
export const campoMostrable = (c: CampoFichaApi) => c.estado === "no_publicado" || c.estado === "supuesto" || Boolean(c.fuente);

/** Esfera que contiene las piezas (posición ensamblada + fracción `f` del despiece) y dirección de cámara. */
export function encuadrePiezas(ids: string[], g: GeometriaDespieceMoto | null, f: number): EncuadreCamara | null {
  if (!g?.base) return null;
  const caja = new THREE.Box3();
  const p = new THREE.Vector3();
  let n = 0;
  for (const id of ids) {
    const b = g.base[id];
    if (!b) continue;
    p.copy(b);
    const d = g.delta[id];
    if (d) p.addScaledVector(d, f);
    caja.expandByPoint(p);
    n++;
  }
  if (n === 0) return null;
  const esfera = caja.getBoundingSphere(new THREE.Sphere());
  return { centro: [esfera.center.x, esfera.center.y, esfera.center.z], radio: Math.max(esfera.radius + 0.12, 0.22), direccion: [0.45, 0.32, 1] };
}

/* ---------- iconos y franja de sistemas ---------- */

export function IconoSistema({ id }: { id: IdSistema }) {
  return (
    <svg className="icono-sistema" viewBox="0 0 24 24" aria-hidden="true" focusable="false">
      {ICONOS_SISTEMA[id].map((d) => (
        <path key={d} d={d} />
      ))}
    </svg>
  );
}

export function FranjaSistemas(props: { sistemas: SistemaApi[]; activo: string | null; alElegir: (id: string) => void }) {
  const porId = new Map(props.sistemas.map((s) => [s.id, s]));
  return (
    <section className="panel franja-sistemas" aria-label="Sistemas de la motocicleta">
      <h3>Sistemas de la motocicleta</h3>
      <div className="franja-botones">
        {ORDEN_SISTEMAS.filter((id) => porId.has(id)).map((id) => {
          const s = porId.get(id)!;
          return (
            <button
              key={id}
              className={`boton-sistema${props.activo === id ? " activo" : ""}`}
              aria-pressed={props.activo === id}
              aria-label={`Seleccionar el sistema ${s.nombre}`}
              data-sistema={id}
              onClick={() => props.alElegir(id)}
            >
              <IconoSistema id={id} />
              <span>{s.nombre}</span>
            </button>
          );
        })}
      </div>
    </section>
  );
}

/* ---------- buscador de piezas ---------- */

export function BuscadorPiezas(props: { piezas: Pieza[]; alElegir: (id: string) => void }) {
  const [consulta, setConsulta] = useState("");
  const resultados = useMemo(() => buscarPiezas(props.piezas, consulta), [props.piezas, consulta]);
  const elegir = (id: string) => {
    props.alElegir(id);
    setConsulta("");
  };
  const alTeclear = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" && resultados[0]) {
      e.preventDefault();
      elegir(resultados[0].id);
    } else if (e.key === "Escape") setConsulta("");
  };
  return (
    <div className="buscador-piezas" role="search">
      <label htmlFor="buscador-piezas">Buscar pieza por nombre</label>
      <input
        id="buscador-piezas"
        type="search"
        value={consulta}
        placeholder="p. ej. cadena, cáliper, bujía"
        autoComplete="off"
        aria-describedby="buscador-ayuda"
        aria-controls="buscador-resultados"
        onChange={(e) => setConsulta(e.target.value)}
        onKeyDown={alTeclear}
      />
      <span id="buscador-ayuda" className="fecha">Enter selecciona el primer resultado.</span>
      {consulta.trim() && (
        <ul id="buscador-resultados" className="buscador-resultados" aria-live="polite">
          {resultados.length === 0 ? (
            <li className="fecha">Sin piezas con ese nombre en el ensamblaje.</li>
          ) : (
            resultados.map((p) => (
              <li key={p.id}>
                <button className="fila-dato" data-pieza={p.id} onClick={() => elegir(p.id)}>{p.nombre}</button>
              </li>
            ))
          )}
        </ul>
      )}
    </div>
  );
}

/* ---------- lista de partes (vista «Partes») ---------- */

export function ListaPartes(props: { sistemas: SistemaApi[]; piezas: Pieza[]; alElegir: (id: string) => void }) {
  const porId = new Map(props.piezas.map((p) => [p.id, p]));
  return (
    <div className="lista-partes" data-testid="lista-partes" aria-label="Lista de partes por sistema">
      {props.sistemas.map((s) => (
        <section key={s.id} aria-labelledby={`partes-${s.id}`}>
          <h4 id={`partes-${s.id}`}>
            <IconoSistema id={s.id as IdSistema} /> {s.nombre}
          </h4>
          <ul>
            {s.piezas.map((pid) => {
              const p = porId.get(pid);
              if (!p) return null;
              return (
                <li key={pid}>
                  <button className="fila-dato" data-pieza={pid} onClick={() => props.alElegir(pid)}>{p.nombre}</button>
                  <span className="funcion-pieza">{p.funcion}</span>
                </li>
              );
            })}
          </ul>
        </section>
      ))}
    </div>
  );
}

/* ---------- pregunta sobre una pieza (POST …/moto_honda/preguntar) ---------- */

function PreguntaPieza({ pieza }: { pieza: Pieza }) {
  const [pregunta, setPregunta] = useState("¿Para qué sirve?");
  const [r, setR] = useState<RespuestaPieza | null>(null);
  const [cargando, setCargando] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [de, setDe] = useState<string | null>(null);
  const preguntar = () => {
    setCargando(true);
    setError(null);
    apiMoto.preguntar(pieza.id, pregunta.trim() || "¿Para qué sirve?").then(
      (x) => {
        setR(x);
        setDe(pieza.id);
        setCargando(false);
      },
      (e: Error) => {
        setError(e.message);
        setCargando(false);
      },
    );
  };
  const vigente = r && de === pieza.id ? r : null;
  return (
    <section className="pregunta-pieza" aria-label="Preguntar sobre esta pieza">
      <h4>Preguntar sobre {pieza.nombre}</h4>
      <div className="fila-pregunta">
        <input aria-label={`Pregunta sobre ${pieza.nombre}`} value={pregunta} onChange={(e) => setPregunta(e.target.value)} onKeyDown={(e) => e.key === "Enter" && preguntar()} maxLength={300} />
        <button className="boton" onClick={preguntar} disabled={cargando} data-testid="preguntar-pieza">
          {cargando ? "Consultando…" : "Preguntar sobre esta pieza"}
        </button>
      </div>
      {error && <p className="aviso error">No se pudo consultar ({error}).</p>}
      {vigente && (
        <div className="respuesta-pieza" aria-live="polite" data-testid="respuesta-pieza">
          <p>
            <InsigniaFuente fuente="supuesto" texto="modelo genérico" /> {vigente.respuesta_modelo}
          </p>
          <h5>Base de conocimiento de Fanalca</h5>
          {vigente.documentado.length === 0 ? (
            <p className="rechazo" data-testid="rechazo">{FRASE_RECHAZO}</p>
          ) : (
            <ul className="datos">
              {vigente.documentado.map((d) => (
                <li key={d.fragmento_id}>
                  <InsigniaFuente fuente={d.origen} /> <code>{d.fragmento_id}</code> {d.texto.length > 220 ? d.texto.slice(0, 217) + "…" : d.texto}
                  <br />
                  <a href={d.url} target="_blank" rel="noreferrer">{d.url}</a>
                </li>
              ))}
            </ul>
          )}
          <p className="fecha">Los fragmentos provienen de los sitios oficiales y pueden no referirse a esta pieza en particular.</p>
        </div>
      )}
    </section>
  );
}

/* ---------- panel de detalle del sistema ---------- */

export function PanelSistema(props: {
  sistema: SistemaApi | null;
  piezas: Pieza[];
  piezaActual: string | null;
  alElegirPieza: (id: string) => void;
  ficha: FichaMotoApi | null;
  errorFicha: string | null;
  campoActivo: string | null;
  alCampo: (ruta: string) => void;
}) {
  const { sistema } = props;
  const porId = useMemo(() => new Map(props.piezas.map((p) => [p.id, p])), [props.piezas]);
  const campos = useMemo(() => (sistema ? camposRelacionados(props.ficha, sistema.piezas).filter((c) => campoMostrable(c.campo)) : []), [props.ficha, sistema]);
  if (!sistema)
    return (
      <p className="aviso" data-testid="panel-sistema-vacio">
        Pulsar una pieza, una etiqueta o un sistema de la franja inferior para ver su función, sus piezas y sus datos.
      </p>
    );
  const pieza = (props.piezaActual && porId.get(props.piezaActual)) || porId.get(sistema.piezas[0]) || null;
  const leccion = LECCIONES[sistema.id as IdSistema];
  return (
    <div className="panel-sistema" data-testid="panel-sistema" data-sistema={sistema.id}>
      <h4 className="nombre-sistema">
        <IconoSistema id={sistema.id as IdSistema} /> {sistema.nombre}
      </h4>
      <p>{sistema.funcion}</p>
      <p className="fecha">Texto de la definición del ensamblaje genérico moto_honda.</p>

      <h5>Piezas del sistema ({sistema.piezas.length})</h5>
      <ul className="piezas-sistema">
        {sistema.piezas.map((pid) => {
          const p = porId.get(pid);
          if (!p) return null;
          return (
            <li key={pid} className={pid === pieza?.id ? "activa" : undefined}>
              <button className="fila-dato" aria-pressed={pid === pieza?.id} data-pieza={pid} onClick={() => props.alElegirPieza(pid)}>{p.nombre}</button>
              <span className="funcion-pieza">{p.funcion}</span>
            </li>
          );
        })}
      </ul>

      <h5>Ficha técnica relacionada</h5>
      {props.errorFicha ? (
        <p className="aviso error">Sin ficha: {props.errorFicha}</p>
      ) : !props.ficha ? (
        <p className="aviso">Consultando la ficha técnica…</p>
      ) : campos.length === 0 ? (
        <p className="sin-dato" data-testid="ficha-no-publicada">{NO_PUBLICADO}: la ficha {props.ficha.nombre} no incluye datos de este sistema.</p>
      ) : (
        <div className="ficha-tecnica">
          <table>
            <tbody>
              {campos.map((c) => (
                <FilaFicha key={c.ruta} ruta={c.ruta} etiqueta={c.etiqueta} campo={c.campo} activa={props.campoActivo === c.ruta} alPulsar={props.alCampo} />
              ))}
            </tbody>
          </table>
        </div>
      )}

      {pieza && <PreguntaPieza pieza={pieza} />}

      {leccion && (
        <p>
          <a className="boton" href={leccion.ruta} data-testid="ver-leccion">Ver la lección: {leccion.titulo} →</a>
        </p>
      )}
    </div>
  );
}
