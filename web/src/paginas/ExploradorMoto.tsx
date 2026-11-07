/**
 * Vista «Explorador de la motocicleta» (fase 14) — #/maquina/moto_honda/explorador (alias #/explorador).
 * Misma plantilla y tokens de la 7b; mismo GLB genérico `moto_honda` y los mismos ids de pieza. No calcula nada:
 * selecciona sistemas (clic en 3D, etiquetas, franja inferior o buscador), encuadra la cámara, atenúa el resto
 * y muestra la función de cada pieza, los datos de la ficha con fuente y estado y la pregunta sobre la pieza.
 */
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import * as THREE from "three";
import type { OrbitControls as OrbitControlsImpl } from "three-stdlib";
import { apiMoto, type FichaMotoApi, type Pieza, type SistemaApi } from "../api";
import { prefiereMovimientoReducido, useMaquina } from "../componentes/anatomia";
import { BuscadorPiezas, encuadrePiezas, FranjaSistemas, ListaPartes, PanelSistema, camposRelacionados } from "../componentes/explorador";
import { piezasDeCampo } from "../componentes/panelesMoto";
import { ChipDato } from "../componentes/plantilla/ChipDato";
import { EtiquetasPieza } from "../componentes/plantilla/EtiquetaPieza";
import { armarExperimentos } from "../componentes/plantilla/ModoExperimento";
import { PlantillaMaquina } from "../componentes/plantilla/PlantillaMaquina";
import { EXPLORADOR_MOTO, ETIQUETAS_SISTEMA } from "../maquinas/explorador_moto";
import EscenaMoto, { type Ancla, GEOMETRIA_MOVIL_DEFECTO, type EstadoMoto, type GeometriaDespieceMoto, type PeticionCamara } from "./EscenaMoto";

const ID_FICHA = "cb160f"; // única ficha curada del catálogo (data/catalogo/motos_honda.yaml)
type Vista = "interactiva" | "explosion" | "partes";
const VISTAS: { id: Vista; texto: string }[] = [
  { id: "interactiva", texto: "Interactiva" },
  { id: "explosion", texto: "Explosión" },
  { id: "partes", texto: "Partes" },
];
const GENERAL: PeticionCamara["encuadre"] = { centro: [0.01, 0.45, 0], radio: 0.8, direccion: [0.9, 0.75, 2.25] };
const ANCLAS_EXPLORADOR: Record<string, Ancla> = Object.fromEntries(ETIQUETAS_SISTEMA.map((e) => [e.clave, e.ancla]));

export default function ExploradorMoto() {
  const def = EXPLORADOR_MOTO;
  const { maquina, error } = useMaquina("moto_honda");

  /* ---------- datos: definición del ensamblaje y ficha ---------- */
  const [piezas, setPiezas] = useState<Pieza[]>([]);
  const [sistemas, setSistemas] = useState<SistemaApi[]>([]);
  const [geometria, setGeometria] = useState<GeometriaDespieceMoto | null>(null);
  const geometriaRef = useRef<GeometriaDespieceMoto | null>(null);
  geometriaRef.current = geometria;
  const [errorSim, setErrorSim] = useState<string | null>(null);
  const [ficha, setFicha] = useState<FichaMotoApi | null>(null);
  const [errorFicha, setErrorFicha] = useState<string | null>(null);

  useEffect(() => {
    const v3 = (a: number[]) => new THREE.Vector3(a[0], a[1], a[2]);
    Promise.all([apiMoto.piezas(), apiMoto.sistemas(), apiMoto.despiece(0), apiMoto.despiece(1)]).then(
      ([p, s, d0, d1]) => {
        setPiezas(p);
        setSistemas(s);
        const delta: GeometriaDespieceMoto["delta"] = {};
        const base: NonNullable<GeometriaDespieceMoto["base"]> = {};
        for (const id of Object.keys(d0)) {
          delta[id] = v3(d1[id]).sub(v3(d0[id]));
          base[id] = v3(d0[id]);
        }
        setGeometria({ delta, base });
      },
      (e: Error) => setErrorSim(e.message),
    );
    apiMoto.fichaMoto(ID_FICHA).then(setFicha, (e: Error) => setErrorFicha(e.message));
  }, []);

  const sistemaDe = useMemo(() => {
    const m: Record<string, string> = {};
    for (const s of sistemas) for (const p of s.piezas) m[p] = s.id;
    return m;
  }, [sistemas]);
  const porIdSistema = useMemo(() => new Map(sistemas.map((s) => [s.id, s])), [sistemas]);

  /* ---------- selección ---------- */
  const [vista, setVista] = useState<Vista>("interactiva");
  const [sistemaSel, setSistemaSel] = useState<string | null>(null);
  const [piezaSel, setPiezaSel] = useState<string | null>(null);
  const [campoSel, setCampoSel] = useState<string | null>(null);
  const [pasando, setPasando] = useState<string | null>(null);
  const fDespiece = useRef(0); // 0 = ensamblada, 1 = explosión completa (radial, del backend)

  const escena = useRef<EstadoMoto>({
    despiece: {},
    theta720: 0,
    ciclo: 0,
    angRuedaTras: 0,
    angRuedaDel: 0,
    angPinon: 0,
    cadenaS: 0,
    compresionHorquilla: 0,
    escalaLlantaTrasera: 1,
    elevacionTrasera: 0,
    motorEnMarcha: false, // el explorador no anima el mecanismo: la moto está detenida
    estadoMotor: "neutro",
    seleccion: null,
    resaltadas: new Set(),
    alerta: new Set(),
    ocultas: new Set(),
    subconjuntoAislado: null,
    subconjuntoDe: {},
    tipoDe: {},
    enfoque: null,
    transparencia: 0,
    autoGiro: false,
    camara: null,
    geom: GEOMETRIA_MOVIL_DEFECTO,
    giraTrasera: new Set(),
    giraDelantera: new Set(),
    grupoHorquilla: new Set(),
    pasando: new Set(),
    rotularTodo: true, // las etiquetas de sistema siguen visibles para saltar de un sistema a otro
  });
  const divsEtiqueta = useRef<Record<string, HTMLDivElement | null>>({});
  const lineas = useRef<Record<string, { linea: SVGLineElement | null; punto: SVGCircleElement | null }>>({});
  const etiquetasVisibles = useRef(true);
  etiquetasVisibles.current = vista !== "partes";
  const controles = useRef<OrbitControlsImpl | null>(null);

  const subconjuntoDe = useMemo(() => Object.fromEntries(piezas.map((p) => [p.id, p.subconjunto])), [piezas]);
  const tipoDe = useMemo(() => Object.fromEntries(piezas.map((p) => [p.id, p.tipo])), [piezas]);
  const piezasSistema = useMemo(() => new Set(sistemaSel ? porIdSistema.get(sistemaSel)?.piezas ?? [] : []), [sistemaSel, porIdSistema]);
  const resaltadas = useMemo(() => (campoSel ? new Set(piezasDeCampo(campoSel)) : piezasSistema), [campoSel, piezasSistema]);
  Object.assign(escena.current, {
    subconjuntoDe,
    tipoDe,
    seleccion: piezaSel,
    resaltadas,
    enfoque: sistemaSel ? piezasSistema : null,
    pasando: new Set(pasando ? [pasando] : []),
  });

  const encuadrar = useCallback((ids: string[] | null) => {
    const enc = ids ? encuadrePiezas(ids, geometriaRef.current, fDespiece.current) : null;
    escena.current.camara = { id: Date.now() + Math.random(), pos: [0.9, 0.75, 2.25], objetivo: [0.01, 0.43, 0], encuadre: enc ?? GENERAL };
  }, []);
  useEffect(() => encuadrar(null), [encuadrar]);

  /** Selecciona un sistema (franja, etiqueta o clic en 3D): contorno, encuadre del sistema y el resto atenuado. */
  const elegirSistema = useCallback(
    (id: string | null, pieza: string | null = null) => {
      setSistemaSel(id);
      setPiezaSel(pieza);
      setCampoSel(null);
      encuadrar(id ? porIdSistema.get(id)?.piezas ?? null : null);
    },
    [encuadrar, porIdSistema],
  );
  /** Selecciona una pieza (buscador, lista o panel): su sistema queda activo y la cámara encuadra la pieza. */
  const elegirPieza = useCallback(
    (id: string) => {
      setSistemaSel(sistemaDe[id] ?? null);
      setPiezaSel(id);
      setCampoSel(null);
      if (vista === "partes") setVista("interactiva");
      encuadrar([id]);
    },
    [encuadrar, sistemaDe, vista],
  );
  const alSeleccionar3d = useCallback((id: string | null) => (id ? elegirSistema(sistemaDe[id] ?? null, id) : elegirSistema(null)), [elegirSistema, sistemaDe]);
  const alCampo = useCallback((ruta: string) => setCampoSel((c) => (c === ruta ? null : ruta)), []);

  useEffect(() => {
    const alTecla = (e: KeyboardEvent) => e.key === "Escape" && elegirSistema(null);
    window.addEventListener("keydown", alTecla);
    return () => window.removeEventListener("keydown", alTecla);
  }, [elegirSistema]);

  /* ---------- vista: interactiva, explosión (despiece radial existente) o lista de partes ---------- */
  useEffect(() => {
    const objetivo = vista === "explosion" ? 1 : 0;
    const desde = fDespiece.current;
    const aplicar = (f: number) => {
      fDespiece.current = f;
      const d: Record<string, number> = {};
      for (const p of piezas) d[p.id] = f;
      escena.current.despiece = d;
    };
    const reencuadrar = () => (vista === "explosion" && geometriaRef.current ? encuadrar(Object.keys(geometriaRef.current.delta)) : encuadrar(sistemaSel ? porIdSistema.get(sistemaSel)?.piezas ?? null : null));
    if (prefiereMovimientoReducido() || desde === objetivo) {
      aplicar(objetivo);
      reencuadrar();
      return;
    }
    let raf = 0;
    const t0 = performance.now();
    const paso = (t: number) => {
      const k = Math.min((t - t0) / 700, 1);
      const s = k * k * (3 - 2 * k);
      aplicar(desde + (objetivo - desde) * s);
      if (k < 1) raf = requestAnimationFrame(paso);
      else reencuadrar();
    };
    raf = requestAnimationFrame(paso);
    return () => cancelAnimationFrame(raf);
    // Solo al cambiar de vista o al llegar las piezas.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [vista, piezas]);

  /* ---------- chips y experimentos ---------- */
  const sistema = sistemaSel ? porIdSistema.get(sistemaSel) ?? null : null;
  const relacionados = useMemo(() => (sistema ? camposRelacionados(ficha, sistema.piezas) : []), [ficha, sistema]);
  const publicados = relacionados.filter((c) => c.campo.estado === "publicado").length;
  const experimentos = armarExperimentos(def.experimentos, [
    { explicacion: "Los cálipers aprietan las pastillas contra los discos: la presión hidráulica se convierte en fricción.", aplicar: () => elegirSistema("frenos") },
    { explicacion: "La transmisión final es el piñón de salida, la cadena y la corona de la rueda trasera.", aplicar: () => elegirSistema("transmision") },
  ]);
  const nombrePasando = pasando ? piezas.find((p) => p.id === pasando)?.nombre : null;

  return (
    <PlantillaMaquina
      def={def}
      maquina={maquina}
      errorApi={error}
      raizProps={{ "data-testid": "explorador-moto", "data-vista": vista, "data-sistema": sistemaSel ?? "" }}
      avisos={errorSim && <p className="aviso error">No se pudo cargar el ensamblaje ({errorSim}).</p>}
      barra={{
        // La vista (Interactiva · Explosión · Partes) se elige en «Controles»; la barra solo reencuadra.
        camara: { alPulsar: () => elegirSistema(null), titulo: "Encuadre general y deseleccionar (Esc)" },
      }}
      lienzo={
        <EscenaMoto
          estado={escena}
          geometria={geometria}
          alSeleccionar={alSeleccionar3d}
          alPasar={setPasando}
          anclas={ANCLAS_EXPLORADOR}
          etiquetas={divsEtiqueta}
          lineas={lineas}
          etiquetasVisibles={etiquetasVisibles}
          controles={controles}
          ssao={false}
        />
      }
      capas={
        <>
          <EtiquetasPieza
            divs={divsEtiqueta}
            lineas={lineas}
            etiquetas={ETIQUETAS_SISTEMA.map((e) => ({
              clave: e.clave,
              clase: `etiqueta-sistema${sistemaSel === e.sistema ? " activa" : ""}`,
              contenido: (
                <button className="boton-etiqueta" aria-pressed={sistemaSel === e.sistema} aria-label={`${e.texto}: seleccionar el sistema`} onClick={() => elegirSistema(e.sistema, e.ancla.pieza)}>
                  {e.texto}
                </button>
              ),
            }))}
          />
          {vista === "partes" && <ListaPartes sistemas={sistemas} piezas={piezas} alElegir={elegirPieza} />}
        </>
      }
      leyenda={nombrePasando ? `Bajo el cursor: ${nombrePasando}` : "Pasar el cursor para ver el contorno; pulsar para seleccionar el sistema · Esc deselecciona"}
      banda={{ texto: null, transcurrido: 0, duracion: 0 }}
      escenarioProps={{ "data-testid": "escenario-explorador" }}
      controles={
        <>
          <div className="selector-vista" role="radiogroup" aria-label="Vista">
            {VISTAS.map((v) => (
              <button key={v.id} role="radio" aria-checked={vista === v.id} className={`chip-boton${vista === v.id ? " activo" : ""}`} data-vista={v.id} onClick={() => setVista(v.id)}>
                {v.texto}
              </button>
            ))}
          </div>
          <BuscadorPiezas piezas={piezas} alElegir={elegirPieza} />
        </>
      }
      contenidoPestanas={{
        sistema: (
          <PanelSistema sistema={sistema} piezas={piezas} piezaActual={piezaSel} alElegirPieza={elegirPieza} ficha={ficha} errorFicha={errorFicha} campoActivo={campoSel} alCampo={alCampo} />
        ),
      }}
      pestanaInicial="sistema"
      chips={
        <>
          <ChipDato etiqueta="sistemas" valor={sistemas.length} />
          <ChipDato etiqueta="piezas del ensamblaje" valor={piezas.length} />
          {sistema && <ChipDato etiqueta={`piezas · ${sistema.nombre}`} valor={sistema.piezas.length} variante="dato" />}
          {sistema && <ChipDato etiqueta="datos de ficha publicados" valor={`${publicados} de ${relacionados.length}`} variante="dato" />}
        </>
      }
      detalle={<FranjaSistemas sistemas={sistemas} activo={sistemaSel} alElegir={(id) => elegirSistema(sistemaSel === id ? null : id)} />}
      pasoActual={-1}
      experimentos={experimentos}
    />
  );
}
