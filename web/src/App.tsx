/**
 * Aplicación IGNIS v2 (prompt v2, sección 1): barra lateral agrupada, encabezado global y pestañas con carga
 * diferida. Enrutador por hash: funciona servido como estático desde FastAPI en /app.
 *
 * Las rutas del M1 retiradas (biblioteca, máquinas, prensa, línea, moto, explorador, simulador, robot) y las
 * desconocidas redirigen a Atención (ver `resolverRuta`).
 */
import { lazy, Suspense, useCallback, useEffect, useRef, useState, type KeyboardEvent, type ReactNode } from "react";
import { ProveedorIgnis, useIgnis, type EstadoServicio } from "./ignisContexto";
import { Icono } from "./IgnisIconos";
import { GRUPOS, hashDe, pestanaPorId, PESTANAS_PIE, resolverRuta, type IdPestana, type Pestana } from "./ignisRutas";
import "./ignis.css";

// El canvas 3D (three.js) solo se descarga y se monta en Atención; al salir de la pestaña se desmonta.
const IgnisAtencionView = lazy(() => import("./IgnisAtencionView"));
const PestanaPendiente = lazy(() => import("./PestanaPendiente"));

/** Pestañas que ya tienen implementación propia; el resto muestra su estado vacío con el PR que la trae. */
const IMPLEMENTADAS: Partial<Record<IdPestana, () => ReactNode>> = {
  atencion: () => <IgnisAtencionView />,
};

function useRuta(): IdPestana {
  const leer = () => {
    const r = resolverRuta(window.location.hash);
    if (r.redirigirA) window.history.replaceState(null, "", r.redirigirA);
    return r.id;
  };
  const [id, setId] = useState<IdPestana>(leer);
  useEffect(() => {
    const alCambiar = () => setId(leer());
    window.addEventListener("hashchange", alCambiar);
    return () => window.removeEventListener("hashchange", alCambiar);
  }, []);
  return id;
}

/* ------------------------------------------------------------------ barra lateral */
function EnlaceNav({ p, activa, alNavegar }: { p: Pestana; activa: boolean; alNavegar: () => void }) {
  return (
    <a className={`ig-nav-item${activa ? " activo" : ""}`} href={hashDe(p.id)} aria-current={activa ? "page" : undefined} onClick={alNavegar}>
      <Icono nombre={p.icono} />
      <span className="ig-nav-etiqueta">{p.etiqueta}</span>
    </a>
  );
}

/** Flechas arriba/abajo, Inicio y Fin mueven el foco entre los enlaces de la barra lateral. */
function moverFoco(e: KeyboardEvent<HTMLElement>) {
  if (!["ArrowDown", "ArrowUp", "Home", "End"].includes(e.key)) return;
  const items = Array.from(e.currentTarget.querySelectorAll<HTMLElement>(".ig-nav-item"));
  const i = items.indexOf(document.activeElement as HTMLElement);
  if (i < 0) return;
  e.preventDefault();
  const destino = e.key === "Home" ? 0 : e.key === "End" ? items.length - 1 : (i + (e.key === "ArrowDown" ? 1 : -1) + items.length) % items.length;
  items[destino].focus();
}

function BarraLateral({ activa, expandida, alternar, menuAbierto, cerrarMenu }: { activa: IdPestana; expandida: boolean; alternar: () => void; menuAbierto: boolean; cerrarMenu: () => void }) {
  return (
    <nav
      id="ig-navegacion"
      className={`ig-lateral${expandida ? " expandida" : ""}${menuAbierto ? " abierta" : ""}`}
      aria-label="Principal"
      onKeyDown={moverFoco}
    >
      <button className="ig-nav-alternar" onClick={alternar} aria-expanded={expandida} aria-controls="ig-navegacion" title={expandida ? "Contraer la barra lateral" : "Expandir la barra lateral"}>
        <Icono nombre={expandida ? "contraer" : "expandir"} />
        <span className="sr">{expandida ? "Contraer la barra lateral" : "Expandir la barra lateral"}</span>
      </button>
      <div className="ig-nav-grupos">
        {GRUPOS.map((g) => (
          <div key={g.titulo} className="ig-nav-grupo" role="group" aria-label={g.titulo}>
            <span className="ig-nav-titulo" aria-hidden="true">
              {g.titulo}
            </span>
            {g.pestanas.map((p) => (
              <EnlaceNav key={p.id} p={p} activa={p.id === activa} alNavegar={cerrarMenu} />
            ))}
          </div>
        ))}
      </div>
      <div className="ig-nav-pie" role="group" aria-label="Cuenta y ayuda">
        {PESTANAS_PIE.map((p) => (
          <EnlaceNav key={p.id} p={p} activa={p.id === activa} alNavegar={cerrarMenu} />
        ))}
        <a className="ig-nav-item" href="/docs" target="_blank" rel="noreferrer">
          <Icono nombre="ayuda" />
          <span className="ig-nav-etiqueta">Ayuda (API)</span>
        </a>
        {/* Sin sesiones todavía (#44): el enlace lleva a «Mi sesión», que explica el estado. */}
        <a className="ig-nav-item" href={hashDe("sesion")} onClick={cerrarMenu}>
          <Icono nombre="salir" />
          <span className="ig-nav-etiqueta">Cerrar sesión</span>
        </a>
      </div>
    </nav>
  );
}

/* ------------------------------------------------------------------ encabezado global */
const ETIQUETA_SERVICIO: Record<EstadoServicio, string> = {
  comprobando: "comprobando…",
  en_linea: "en línea",
  reconectando: "reconectando",
  sin_conexion: "sin conexión",
  sin_datos: "sin uso aún",
  respaldo: "respaldo Q&A",
};

function ChipServicio({ nombre, estado, detalle }: { nombre: string; estado: EstadoServicio | "pendiente"; detalle?: string }) {
  const texto = estado === "pendiente" ? (detalle ?? "no disponible todavía") : ETIQUETA_SERVICIO[estado];
  return (
    <span className={`ig-chip-servicio ${estado}`} role="status" title={`${nombre}: ${texto}`}>
      <span className="punto" aria-hidden="true" />
      <span className="ig-chip-nombre">{nombre}</span>
      <span className="ig-chip-texto">{texto}</span>
    </span>
  );
}

function EncabezadoGlobal({ menuAbierto, alternarMenu }: { menuAbierto: boolean; alternarMenu: () => void }) {
  const { hilo, nuevoHilo, api, sse } = useIgnis();
  return (
    <header className="ig-encabezado">
      <button className="ig-boton-menu" onClick={alternarMenu} aria-expanded={menuAbierto} aria-controls="ig-navegacion">
        <Icono nombre={menuAbierto ? "cerrar" : "menu"} />
        <span className="sr">{menuAbierto ? "Cerrar menú" : "Abrir menú"}</span>
      </button>
      <span className="ig-marca">
        <b>IGNIS</b>
        <span className="ig-marca-sub"> · Fanalca · TAAML 2026-2S</span>
      </span>
      <div className="ig-encabezado-datos">
        <span className="ig-campo" title="Las sesiones de usuario llegan con el PR #44">
          <Icono nombre="usuario" tamano={16} /> <span className="ig-vacio">Sin sesión (#44)</span>
        </span>
        <span className="ig-campo ig-hilo">
          <Icono nombre="historial" tamano={16} />
          <code title={`thread_id: ${hilo}`}>{hilo}</code>
          <button className="ignis-btn" onClick={() => nuevoHilo()}>
            <Icono nombre="mas" tamano={14} /> Nuevo hilo
          </button>
        </span>
        <span className="ig-campo" title="Proveedor, modelo y modo de contexto por usuario llegan con el PR #38b">
          <Icono nombre="deslizadores" tamano={16} /> <span className="ig-vacio">Modelo y contexto: no disponible todavía (#38b)</span>
        </span>
      </div>
      <div className="ig-chips" aria-label="Estado de los servicios">
        <ChipServicio nombre="API" estado={api} />
        <ChipServicio nombre="SSE" estado={sse} />
        <ChipServicio nombre="Qdrant" estado="pendiente" detalle="no disponible todavía (#34)" />
      </div>
    </header>
  );
}

/* ------------------------------------------------------------------ contenido */
function EsqueletoPestana() {
  return (
    <div className="ig-esqueleto" aria-busy="true" aria-label="Cargando la pestaña">
      <span className="ig-esqueleto-linea ancha" />
      <span className="ig-esqueleto-linea" />
      <span className="ig-esqueleto-bloque" />
    </div>
  );
}

function Contenido({ id }: { id: IdPestana }) {
  const propia = IMPLEMENTADAS[id];
  return <Suspense fallback={<EsqueletoPestana />}>{propia ? propia() : <PestanaPendiente pestana={pestanaPorId(id)} />}</Suspense>;
}

function Shell() {
  const id = useRuta();
  const [expandida, setExpandida] = useState(false);
  const [menuAbierto, setMenuAbierto] = useState(false);
  const principal = useRef<HTMLElement>(null);
  const cerrarMenu = useCallback(() => setMenuAbierto(false), []);

  // Al cambiar de pestaña se cierra el menú móvil y el título de la página refleja la pestaña.
  useEffect(() => {
    setMenuAbierto(false);
    document.title = `${pestanaPorId(id).etiqueta} · IGNIS`;
  }, [id]);

  return (
    <div className={`ig-shell${expandida ? " lateral-expandida" : ""}`}>
      <a className="ig-saltar" href="#ig-principal" onClick={(e) => (e.preventDefault(), principal.current?.focus())}>
        Saltar al contenido
      </a>
      <BarraLateral activa={id} expandida={expandida} alternar={() => setExpandida((v) => !v)} menuAbierto={menuAbierto} cerrarMenu={cerrarMenu} />
      {menuAbierto ? <div className="ig-velo" onClick={cerrarMenu} aria-hidden="true" /> : null}
      <EncabezadoGlobal menuAbierto={menuAbierto} alternarMenu={() => setMenuAbierto((v) => !v)} />
      <main id="ig-principal" ref={principal} tabIndex={-1} className={`ig-principal pestana-${id}`}>
        <Contenido key={id} id={id} />
      </main>
    </div>
  );
}

export default function App() {
  return (
    <ProveedorIgnis>
      <Shell />
    </ProveedorIgnis>
  );
}
