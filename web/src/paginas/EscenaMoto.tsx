/**
 * Escena 3D de la motocicleta de referencia (React Three Fiber). Carga `moto_honda.glb`
 * (`uv run fabrica simulador generar`, 79 piezas) y, en cada fotograma, aplica a cada pieza:
 *   posición = base + despiece_i · Δdespiece_i  (+ movimientos del mecanismo atenuados por el despiece)
 * Los ejes y orígenes de las articulaciones (cilindro inclinado, horquilla, cadena) se leen de la API del
 * simulador (`GeometriaMovil`); no hay verticales fijos. Movimientos del mecanismo (todos desde `modelos/moto.ts`):
 *   pistón  s = x(θ) − x(0) a lo largo del EJE DEL CILINDRO   biela: cuelga entre muñequilla y bulón, φ = asin(r·sin θ / L)
 *   válvulas: levante senoidal a lo largo del eje             chispa: en el PMS de la compresión (θ720 = 360°)
 *   piñón / corona / ruedas: ángulos acumulados por la página (ya divididos por el factor de cámara lenta)
 *   cadena: eslabones (InstancedMesh) que avanzan sobre el lazo a la velocidad v = ω·r
 * Presentación: materiales PBR por tipo de pieza, entorno de estudio con Lightformers locales (sin HDR externo),
 * sombras de contacto, tone mapping ACES y selección por CONTORNO (casco invertido) sin recolorear la pieza.
 * El estado mutable vive en una referencia para no re-renderizar React a 60 Hz.
 */
import { ContactShadows, Environment, Lightformer, OrbitControls, useGLTF } from "@react-three/drei";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { useEffect, useMemo, useRef } from "react";
import * as THREE from "three";
import { EffectComposer } from "three/examples/jsm/postprocessing/EffectComposer.js";
import { SSAOPass } from "three/examples/jsm/postprocessing/SSAOPass.js";
import { OutputPass } from "three/examples/jsm/postprocessing/OutputPass.js";
import { RenderPass } from "three/examples/jsm/postprocessing/RenderPass.js";
import { mergeVertices } from "three/examples/jsm/utils/BufferGeometryUtils.js";
import type { OrbitControls as OrbitControlsImpl } from "three-stdlib";
import type { ArticulacionApi } from "../api";
import { colocarEtiquetas, puntoBorde, type Rect } from "../modelos/etiquetas";
import { mecanismoMotor } from "../modelos/mecanismo";
import {
  chispaPermitida,
  EJE_CORONA,
  EJE_PINON,
  FASES_INFO,
  faseCiclo,
  GEOMETRIA_MOTOR,
  intensidadChispaMotor,
  levanteAdmision,
  levanteEscape,
  RADIO_CORONA_M,
  RADIO_PINON_M,
  trazadoCadena,
  type EstadoMotor,
} from "../modelos/moto";

export const URL_MODELO_MOTO = `${import.meta.env.BASE_URL}modelos/moto_honda.glb`;

export type Vec3 = [number, number, number];
export interface PeticionCamara {
  id: number;
  pos: Vec3;
  objetivo: Vec3;
}

/** Ejes y centros del mecanismo, leídos de las articulaciones del simulador (con valores por omisión). */
export interface GeometriaMovil {
  ejeCilindro: [number, number]; // unitario: de la muñequilla hacia la culata (j_piston)
  centroCiguenal: [number, number];
  ejeHorquilla: [number, number]; // unitario: sentido en que sube la botella al comprimirse
  cadena: { pinon: [number, number]; corona: [number, number]; rp: number; rc: number; z: number };
}
const GRAD = Math.PI / 180;
export const GEOMETRIA_MOVIL_DEFECTO: GeometriaMovil = {
  ejeCilindro: [Math.sin(15 * GRAD), Math.cos(15 * GRAD)],
  centroCiguenal: [0.1, 0.33],
  ejeHorquilla: [-Math.sin(26 * GRAD), Math.cos(26 * GRAD)],
  cadena: { pinon: [EJE_PINON[0], EJE_PINON[1]], corona: [EJE_CORONA[0], EJE_CORONA[1]], rp: RADIO_PINON_M, rc: RADIO_CORONA_M, z: 0.075 },
};

export function geometriaMovil(arts: ArticulacionApi[] | null, params: Record<string, number> | null): GeometriaMovil {
  const d = GEOMETRIA_MOVIL_DEFECTO;
  const j = (id: string) => arts?.find((a) => a.id === id);
  const unit = (v: number[] | undefined, def: [number, number]): [number, number] => {
    if (!v) return def;
    const n = Math.hypot(v[0], v[1]);
    return n > 1e-9 ? [v[0] / n, v[1] / n] : def;
  };
  const p = (c: string, def: number) => params?.[c] ?? def;
  return {
    ejeCilindro: unit(j("j_piston")?.eje, d.ejeCilindro),
    centroCiguenal: j("j_ciguenal") ? [j("j_ciguenal")!.origen[0], j("j_ciguenal")!.origen[1]] : d.centroCiguenal,
    ejeHorquilla: unit(j("j_botella_izquierda")?.eje, d.ejeHorquilla),
    cadena: {
      pinon: [p("cadena_pinon_x_m", d.cadena.pinon[0]), p("cadena_pinon_y_m", d.cadena.pinon[1])],
      corona: [p("cadena_corona_x_m", d.cadena.corona[0]), p("cadena_corona_y_m", d.cadena.corona[1])],
      rp: p("cadena_radio_paso_pinon_m", d.cadena.rp),
      rc: p("cadena_radio_paso_corona_m", d.cadena.rc),
      z: p("cadena_z_m", d.cadena.z),
    },
  };
}

export interface EstadoMoto {
  despiece: Record<string, number>; // 0..1 por pieza
  theta720: number; // grados de cigüeñal (0..720) para el ciclo 4T
  ciclo: number; // ciclos completos de 720° (el limitador suprime la chispa en ciclos alternos)
  angRuedaTras: number; // rad, acumulado (negativo = avanza hacia +X)
  angRuedaDel: number;
  angPinon: number;
  cadenaS: number; // m recorridos sobre el lazo de la cadena
  compresionHorquilla: number; // m
  escalaLlantaTrasera: number; // radio de la llanta de la ficha / radio genérico (plano de la rueda)
  elevacionTrasera: number; // m: aumento del radio trasero; la moto cabecea sobre el contacto delantero
  motorEnMarcha: boolean;
  estadoMotor: EstadoMotor;
  seleccion: string | null;
  resaltadas: Set<string>;
  alerta: Set<string>;
  ocultas: Set<string>;
  subconjuntoAislado: string | null;
  subconjuntoDe: Record<string, string>;
  tipoDe: Record<string, string>;
  enfoque: Set<string> | null; // piezas que se mantienen opacas; el resto pasa a fantasma
  transparencia: number;
  autoGiro: boolean;
  camara: PeticionCamara | null;
  geom: GeometriaMovil;
  giraTrasera: Set<string>; // piezas solidarias a la rueda trasera (de las articulaciones)
  giraDelantera: Set<string>;
  grupoHorquilla: Set<string>; // botellas y todo lo montado en ellas: se comprimen con la horquilla
}

export interface Ancla {
  pieza: string;
  desfase: Vec3; // punto de anclaje respecto al origen de la pieza (m): debe caer sobre la pieza
  pref: [number, number]; // desplazamiento preferido de la etiqueta en pantalla (px)
}
/** Etiquetas HTML con línea guía: el punto cae sobre su pieza y la caja se coloca cerca, sin solaparse. */
export const ANCLAS: Record<string, Ancla> = {
  motor: { pieza: "cilindro", desfase: [0.02, 0.02, 0.04], pref: [-110, -105] },
  cilindrada: { pieza: "culata", desfase: [0.03, 0.02, 0.04], pref: [120, -100] },
  transmision: { pieza: "cadena", desfase: [-0.02, -0.07, 0.075], pref: [-20, 95] },
  rueda: { pieza: "llanta_trasera", desfase: [-0.2, -0.2, 0.05], pref: [-85, 45] },
  disco_del: { pieza: "disco_delantero", desfase: [0.07, 0.05, 0.05], pref: [95, -85] },
  disco_tras: { pieza: "disco_trasero", desfase: [-0.07, 0.07, -0.05], pref: [-95, -70] },
};

export interface GeometriaDespieceMoto {
  delta: Record<string, THREE.Vector3>; // despiece completo − ensamblado
}

interface Props {
  estado: React.MutableRefObject<EstadoMoto>;
  geometria: GeometriaDespieceMoto | null;
  alSeleccionar: (id: string | null) => void;
  etiquetas: React.MutableRefObject<Record<string, HTMLDivElement | null>>;
  lineas: React.MutableRefObject<Record<string, { linea: SVGLineElement | null; punto: SVGCircleElement | null }>>;
  etiquetasVisibles: React.MutableRefObject<boolean>;
  controles: React.MutableRefObject<OrbitControlsImpl | null>;
  /** Oclusión ambiental (SSAO/GTAO); solo con calidad «alta». */
  ssao?: boolean;
  alCalidad?: (c: Calidad) => void;
}

/** «alta»: entorno de estudio con Lightformers (IBL) y SSAO en GPU; «ligera»: luces analíticas para render por software. */
export type Calidad = "alta" | "ligera";

const EJE_Z = new THREE.Vector3(0, 0, 1);
const OPACIDAD_FANTASMA = 0.1;
const PASO_ESLABON = 0.0127; // paso de cadena 428 (12,7 mm), demostrativo

/* ---------- materiales PBR por tipo de pieza ---------- */
interface Pbr {
  color: string;
  metalness: number;
  roughness: number;
  emissive?: string;
  emissiveIntensity?: number;
}
const ACERO_PULIDO: Pbr = { color: "#c7cbd1", metalness: 1, roughness: 0.22 };
const ALUMINIO: Pbr = { color: "#b4b9c0", metalness: 0.9, roughness: 0.42 };
const ALUMINIO_FUNDIDO: Pbr = { color: "#8d9298", metalness: 0.8, roughness: 0.58 };
const CAUCHO: Pbr = { color: "#17181a", metalness: 0, roughness: 0.95 };
const PINTURA: Pbr = { color: "#1d5a8f", metalness: 0.15, roughness: 0.32 };
const NEGRO_ESTRUCTURA: Pbr = { color: "#26282c", metalness: 0.55, roughness: 0.48 };
const PBR_POR_TIPO: Record<string, Pbr> = {
  llanta: CAUCHO,
  rin: { color: "#c3c7cd", metalness: 0.95, roughness: 0.3 },
  cubo: ALUMINIO,
  disco: { color: "#aeb3ba", metalness: 1, roughness: 0.28 },
  pinza: { color: "#4a4f57", metalness: 0.7, roughness: 0.4 },
  engranaje: { color: "#b9bdc4", metalness: 0.95, roughness: 0.35 },
  cadena: { color: "#9aa0a8", metalness: 0.95, roughness: 0.4 },
  carcasa: ALUMINIO_FUNDIDO,
  cilindro_motor: ALUMINIO_FUNDIDO,
  piston: { color: "#d4d8dd", metalness: 1, roughness: 0.2 },
  biela: ACERO_PULIDO,
  ciguenal: { color: "#b3b8bf", metalness: 1, roughness: 0.3 },
  valvula: ACERO_PULIDO,
  bujia: { color: "#e6e2d6", metalness: 0.2, roughness: 0.4 },
  escape: { color: "#cfd3d8", metalness: 1, roughness: 0.18 },
  tanque: PINTURA,
  sillin: { color: "#141416", metalness: 0, roughness: 0.85 },
  agarre: CAUCHO,
  tubo_suspension: { color: "#d2d6db", metalness: 1, roughness: 0.2 },
  botella: ALUMINIO,
  amortiguador: { color: "#2c2f34", metalness: 0.6, roughness: 0.4 },
  basculante: NEGRO_ESTRUCTURA,
  instrumento: { color: "#101113", metalness: 0.2, roughness: 0.3 },
  luz: { color: "#e9eef4", metalness: 0, roughness: 0.12, emissive: "#ffe9b0", emissiveIntensity: 0.12 },
  manguera: { color: "#0f1012", metalness: 0, roughness: 0.7 },
  unidad_hidraulica: { color: "#34373c", metalness: 0.55, roughness: 0.5 },
  electrico: { color: "#1a1c20", metalness: 0.3, roughness: 0.6 },
  estructura: NEGRO_ESTRUCTURA,
};
export function pbrDe(tipo: string | undefined, subconjunto: string | undefined, id: string): Pbr {
  if (subconjunto === "carroceria" && tipo !== "luz") return id === "porta_placa" ? NEGRO_ESTRUCTURA : { ...PINTURA, roughness: 0.34 };
  if (id === "filtro_aire") return { ...PINTURA, color: "#17446b", roughness: 0.4 }; // caja del filtro: pintura de carrocería, integrada con el tanque
  if (id === "monoamortiguador") return { color: "#c8362d", metalness: 0.4, roughness: 0.35 }; // resorte/depósito
  return (tipo && PBR_POR_TIPO[tipo]) || NEGRO_ESTRUCTURA;
}

/** Geometría suavizada (vértices soldados) para el casco del contorno: evita huecos en las aristas. */
function geometriaContorno(g: THREE.BufferGeometry): THREE.BufferGeometry {
  const c = new THREE.BufferGeometry();
  c.setAttribute("position", g.getAttribute("position").clone());
  if (g.index) c.setIndex(g.index.clone());
  const m = mergeVertices(c, 1e-4);
  m.computeVertexNormals();
  return m;
}
const materialContorno = (color: string, grosor: number) =>
  new THREE.ShaderMaterial({
    uniforms: { color: { value: new THREE.Color(color) }, grosor: { value: grosor } },
    vertexShader: "uniform float grosor; void main(){ vec3 p = position + normalize(normal) * grosor; gl_Position = projectionMatrix * modelViewMatrix * vec4(p, 1.0); }",
    fragmentShader: "uniform vec3 color;\nvoid main() {\n  gl_FragColor = vec4(color, 1.0);\n#include <colorspace_fragment>\n}",
    side: THREE.BackSide,
    toneMapped: false,
  });

function Modelo({ estado, geometria, alSeleccionar, etiquetas: etq, lineas, etiquetasVisibles, calidad }: Omit<Props, "controles" | "ssao" | "alCalidad"> & { calidad: Calidad }) {
  const { scene } = useGLTF(URL_MODELO_MOTO);
  const camara = useThree((t) => t.camera);
  const tamano = useThree((t) => t.size);
  const gl = useThree((t) => t.gl);
  const controles = useThree((t) => t.controls) as OrbitControlsImpl | null;

  // Copia profunda con materiales PBR propios (por tipo de pieza); el contorno se crea al seleccionar.
  const raiz = useMemo(() => {
    const copia = scene.clone(true);
    copia.traverse((o) => {
      const m = o as THREE.Mesh;
      if (m.isMesh) m.material = (m.material as THREE.Material).clone();
    });
    return copia;
  }, [scene]);

  const nodos = useMemo(() => {
    const mapa = new Map<string, { obj: THREE.Object3D; base: THREE.Vector3; qBase: THREE.Quaternion; mallas: THREE.Mesh[] }>();
    raiz.traverse((o) => {
      if (o.name && !mapa.has(o.name) && o !== raiz) {
        const mallas: THREE.Mesh[] = [];
        o.traverse((h) => (h as THREE.Mesh).isMesh && mallas.push(h as THREE.Mesh));
        if (mallas.length) mapa.set(o.name, { obj: o, base: o.position.clone(), qBase: o.quaternion.clone(), mallas });
      }
    });
    return mapa;
  }, [raiz]);

  // La pieza `cadena` del GLB es solo una guía: los eslabones son un InstancedMesh que avanza sobre el lazo.
  useEffect(() => {
    nodos.get("cadena")?.mallas.forEach((m) => (m.visible = false));
  }, [nodos]);

  const contornos = useMemo(() => new Map<THREE.Mesh, THREE.Mesh>(), []);
  const matSel = useMemo(() => materialContorno("#eb6834", 0.0055), []);
  const matAlerta = useMemo(() => materialContorno("#c2410c", 0.0055), []);
  const tipoAplicado = useRef<Record<string, string>>({});

  const eslabones = useMemo(() => {
    const geo = estado.current.geom.cadena;
    const trazado = trazadoCadena(geo.pinon, geo.corona, geo.rp, geo.rc);
    const n = Math.max(Math.round(trazado.longitud / PASO_ESLABON), 12);
    const im = new THREE.InstancedMesh(
      new THREE.BoxGeometry(0.0105, 0.0055, 0.0105),
      new THREE.MeshStandardMaterial({ color: "#aab0b8", metalness: 0.95, roughness: 0.38 }),
      n,
    );
    im.frustumCulled = false;
    im.instanceColor = new THREE.InstancedBufferAttribute(new Float32Array(n * 3), 3);
    const marca = new THREE.Color("#2a78d6");
    const normal = new THREE.Color("#aab0b8");
    for (let i = 0; i < n; i++) im.setColorAt(i, i % 9 === 0 ? marca : normal);
    return { im, n, trazado, paso: trazado.longitud / n };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  const gas = useMemo(
    () =>
      new THREE.Mesh(
        new THREE.CylinderGeometry(1, 1, 1, 24, 1, false),
        new THREE.MeshBasicMaterial({ color: "#0072b2", transparent: true, opacity: 0.38, depthWrite: false }),
      ),
    [],
  );
  const chispa = useMemo(
    () =>
      new THREE.Mesh(
        new THREE.SphereGeometry(0.012, 16, 12),
        new THREE.MeshBasicMaterial({ color: "#ffe14d", transparent: true, opacity: 0.95, depthTest: false }),
      ),
    [],
  );

  const grupo = useRef<THREE.Group>(null);
  const tmp = useMemo(() => new THREE.Vector3(), []);
  const tmp2 = useMemo(() => new THREE.Vector3(), []);
  const escalaTmp = useMemo(() => new THREE.Vector3(), []);
  const q = useMemo(() => new THREE.Quaternion(), []);
  const q2 = useMemo(() => new THREE.Quaternion(), []);
  const m4 = useMemo(() => new THREE.Matrix4(), []);
  const camaraObjetivo = useMemo(() => ({ id: -1, pos: new THREE.Vector3(), objetivo: new THREE.Vector3(), activa: false }), []);
  const reservadas = useRef<{ t: number; r: Rect[] }>({ t: -1e9, r: [] });
  const medidas = useRef<Record<string, { w: number; h: number; t: number }>>({});
  const mecanico = useRef({ crown: 0.1657, deck: 0.1748, listo: false });

  // Gancho de pruebas (e2e): posición mundial, color y contorno de cada pieza, y la geometría móvil vigente.
  useEffect(() => {
    const w = window as unknown as { __moto3d?: unknown };
    w.__moto3d = {
      mundo: (id: string) => {
        const n = nodos.get(id);
        if (!n) return null;
        const v = n.obj.getWorldPosition(new THREE.Vector3());
        return [v.x, v.y, v.z];
      },
      color: (id: string) => {
        const m = nodos.get(id)?.mallas[0]?.material as THREE.MeshStandardMaterial | undefined;
        return m ? { hex: m.color.getHexString(), emisivo: m.emissiveIntensity } : null;
      },
      contorno: (id: string) => Boolean(nodos.get(id)?.mallas.some((m) => contornos.get(m)?.visible)),
      geom: () => estado.current.geom,
      piezas: () => nodos.size,
    };
    return () => {
      delete w.__moto3d;
    };
  }, [nodos, contornos, estado]);

  useEffect(
    () => () => {
      eslabones.im.geometry.dispose();
      (eslabones.im.material as THREE.Material).dispose();
      gas.geometry.dispose();
      (gas.material as THREE.Material).dispose();
      chispa.geometry.dispose();
      (chispa.material as THREE.Material).dispose();
      matSel.dispose();
      matAlerta.dispose();
      contornos.forEach((c) => c.geometry.dispose());
    },
    [eslabones, gas, chispa, matSel, matAlerta, contornos],
  );

  useFrame((_, dtReal) => {
    const s = estado.current;
    const geom = s.geom;
    const dt = Math.min(dtReal, 0.1);
    if (controles) {
      controles.autoRotate = s.autoGiro;
      controles.autoRotateSpeed = 1.6;
    }
    // Transición suave de cámara solicitada por la página.
    if (s.camara && s.camara.id !== camaraObjetivo.id) {
      camaraObjetivo.id = s.camara.id;
      camaraObjetivo.pos.set(...s.camara.pos);
      camaraObjetivo.objetivo.set(...s.camara.objetivo);
      camaraObjetivo.activa = true;
    }
    if (camaraObjetivo.activa && controles) {
      const k = 1 - Math.exp(-dt * 5);
      camara.position.lerp(camaraObjetivo.pos, k);
      controles.target.lerp(camaraObjetivo.objetivo, k);
      controles.update();
      if (camara.position.distanceTo(camaraObjetivo.pos) < 0.005 && controles.target.distanceTo(camaraObjetivo.objetivo) < 0.005) camaraObjetivo.activa = false;
    }

    // Materiales PBR: se asignan una vez por pieza cuando llegan sus tipos desde la API.
    for (const [id, n] of nodos) {
      const tipo = s.tipoDe[id];
      const clave = `${tipo}|${s.subconjuntoDe[id]}|${calidad}`;
      if (tipo !== undefined && tipoAplicado.current[id] !== clave) {
        tipoAplicado.current[id] = clave;
        const p = pbrDe(tipo, s.subconjuntoDe[id], id);
        for (const m of n.mallas) {
          const viejo = m.material as THREE.Material;
          const mat = new THREE.MeshStandardMaterial({
            color: p.color,
            // Sin entorno (calidad ligera) un metal puro se ve negro: se atenúa para conservar volumen.
            metalness: calidad === "alta" ? p.metalness : Math.min(p.metalness, 0.5),
            roughness: p.roughness,
            emissive: p.emissive ?? "#000000",
            emissiveIntensity: p.emissiveIntensity ?? 0,
            side: THREE.DoubleSide, // las piezas de corte (cilindro, culata) y las extrusiones abiertas se ven por dentro
          });
          m.material = mat;
          viejo.dispose();
        }
      }
    }

    // Con una llanta trasera mayor, la moto cabecea sobre el contacto delantero: la rueda trasera sigue apoyada.
    if (grupo.current) {
      const apoyo = nodos.get("llanta_delantera")?.base.x ?? 0.66;
      const largo = apoyo - (nodos.get("llanta_trasera")?.base.x ?? -0.64);
      const ang = -s.elevacionTrasera / largo;
      grupo.current.rotation.z = ang;
      grupo.current.position.set(apoyo * (1 - Math.cos(ang)), -apoyo * Math.sin(ang), 0);
    }

    /* ---- mecanismo del motor sobre el EJE INCLINADO del cilindro, desde moto.ts ---- */
    const carrera = GEOMETRIA_MOTOR.carreraM;
    const longBiela = GEOMETRIA_MOTOR.bielaM;
    const th720 = s.theta720;
    const th = (th720 * Math.PI) / 180;
    const [ux, uy] = geom.ejeCilindro;
    const [cx, cy] = geom.centroCiguenal;
    const mec = mecanismoMotor(th, geom.ejeCilindro, geom.centroCiguenal, carrera, longBiela);
    const desplPiston = mec.desplazamiento;
    const phi = mec.phi;
    const munX = mec.muneca.x;
    const munY = mec.muneca.y;
    const bulX = mec.bulon.x;
    const bulY = mec.bulon.y;

    for (const [id, n] of nodos) {
      const f = s.despiece[id] ?? 0;
      const atenuar = 1 - Math.min(f * 4, 1); // el mecanismo vuelve a su pose nominal al separarse
      tmp.copy(n.base);
      const d = geometria?.delta[id];
      let rotZ = 0;
      let giro = false;
      switch (id) {
        case "piston":
          tmp.x += ux * desplPiston * atenuar;
          tmp.y += uy * desplPiston * atenuar;
          break;
        case "biela": {
          tmp.x = n.base.x + ((munX + bulX) / 2 - n.base.x) * atenuar;
          tmp.y = n.base.y + ((munY + bulY) / 2 - n.base.y) * atenuar;
          rotZ = phi * atenuar;
          giro = true;
          break;
        }
        case "ciguenal":
          rotZ = -th;
          giro = true;
          break;
        case "valvula_admision": {
          const l = levanteAdmision(th720) * atenuar;
          tmp.x -= ux * l;
          tmp.y -= uy * l;
          break;
        }
        case "valvula_escape": {
          const l = levanteEscape(th720) * atenuar;
          tmp.x -= ux * l;
          tmp.y -= uy * l;
          break;
        }
        case "pinon":
          rotZ = s.angPinon;
          giro = true;
          break;
        default:
          if (s.giraTrasera.has(id)) {
            rotZ = s.angRuedaTras;
            giro = true;
          } else if (s.giraDelantera.has(id)) {
            rotZ = s.angRuedaDel;
            giro = true;
          }
      }
      if (d) tmp.addScaledVector(d, f);
      if (s.grupoHorquilla.has(id)) {
        const k = s.compresionHorquilla * (1 - f);
        tmp.x += geom.ejeHorquilla[0] * k;
        tmp.y += geom.ejeHorquilla[1] * k;
      }
      if (giro) n.obj.quaternion.copy(q.setFromAxisAngle(EJE_Z, rotZ)).multiply(n.qBase);
      n.obj.position.copy(tmp);
      if (id === "llanta_trasera") n.obj.scale.set(s.escalaLlantaTrasera, s.escalaLlantaTrasera, 1);
      const sub = s.subconjuntoDe[id];
      n.obj.visible = !s.ocultas.has(id) && (s.subconjuntoAislado === null || s.subconjuntoAislado === sub);

      const sel = s.seleccion === id || s.resaltadas.has(id);
      const alerta = s.alerta.has(id);
      const fantasma = s.enfoque !== null && !s.enfoque.has(id) && !sel;
      const op = fantasma ? OPACIDAD_FANTASMA : 1 - s.transparencia;
      for (let i = 0; i < n.mallas.length; i++) {
        const malla = n.mallas[i];
        if (id === "cadena") continue;
        const mat = malla.material as THREE.MeshStandardMaterial;
        if (mat.transparent !== op < 1) {
          mat.transparent = op < 1;
          mat.needsUpdate = true; // el programa del shader cambia entre opaco y transparente
        }
        mat.opacity = op;
        mat.depthWrite = op >= 1;
        // Contorno (casco invertido): la pieza seleccionada conserva su material.
        let c = contornos.get(malla);
        if ((sel || alerta) && !c) {
          c = new THREE.Mesh(geometriaContorno(malla.geometry), matSel);
          c.renderOrder = -1;
          malla.add(c);
          contornos.set(malla, c);
        }
        if (c) {
          c.visible = sel || alerta;
          c.material = sel ? matSel : matAlerta;
        }
      }
    }

    /* ---- gas en la cámara de combustión y chispa, a lo largo del eje del cilindro ---- */
    const cil = nodos.get("cilindro");
    const pis = nodos.get("piston");
    const cul = nodos.get("culata");
    const meca = mecanico.current;
    if (!meca.listo && pis && cul) {
      // Corona del pistón y cubierta del cilindro (a lo largo de u) a partir de la caja local de sus mallas.
      const proy = (n: { base: THREE.Vector3 }) => (n.base.x - cx) * ux + (n.base.y - cy) * uy;
      const zLocal = (n: { qBase: THREE.Quaternion }) => tmp.set(0, 0, 1).applyQuaternion(n.qBase).dot(tmp2.set(ux, uy, 0)) >= 0;
      const caja = (m: THREE.Mesh) => {
        m.geometry.computeBoundingBox();
        return m.geometry.boundingBox!;
      };
      const cp = caja(pis.mallas[0]);
      const cu = caja(cul.mallas[0]);
      meca.crown = proy(pis) + (zLocal(pis) ? cp.max.z : -cp.min.z);
      meca.deck = proy(cul) + (zLocal(cul) ? cu.min.z : -cu.max.z);
      meca.listo = true;
    }
    const visibleMotor = Boolean(cil?.obj.visible && pis?.obj.visible) && (s.despiece["cilindro"] ?? 0) < 0.02 && (s.despiece["piston"] ?? 0) < 0.02;
    const cima = meca.crown + desplPiston;
    const h = Math.max(meca.deck - cima, 0.002);
    gas.visible = visibleMotor && s.motorEnMarcha;
    gas.scale.set(0.0262, h, 0.0262);
    gas.quaternion.setFromUnitVectors(tmp.set(0, 1, 0), tmp2.set(ux, uy, 0));
    gas.position.set(cx + (cima + h / 2) * ux, cy + (cima + h / 2) * uy, 0);
    const fase = faseCiclo(th720);
    const gm = gas.material as THREE.MeshBasicMaterial;
    gm.color.set(FASES_INFO[fase].color);
    // Con el limitador, en el ciclo sin chispa la expansión no tiene combustión: el gas se atenúa.
    gm.opacity = fase === "expansion" && !chispaPermitida(s.estadoMotor, s.ciclo) ? 0.1 : 0.38;
    const kChispa = intensidadChispaMotor(th720, s.ciclo, s.estadoMotor);
    chispa.visible = visibleMotor && s.motorEnMarcha && kChispa > 0;
    chispa.position.set(cx + (meca.deck - 0.008) * ux, cy + (meca.deck - 0.008) * uy, 0);
    chispa.scale.setScalar(0.6 + 1.6 * kChispa);

    /* ---- eslabones de la cadena: avanzan sobre el lazo a la velocidad v = ω·r ---- */
    const dCad = geometria?.delta["cadena"];
    const fCad = s.despiece["cadena"] ?? 0;
    const cad = nodos.get("cadena");
    eslabones.im.visible = Boolean(cad?.obj.visible) && (s.enfoque === null || s.enfoque.has("cadena"));
    const zc = geom.cadena.z;
    for (let i = 0; i < eslabones.n; i++) {
      const sA = s.cadenaS + i * eslabones.paso;
      const p = eslabones.trazado.punto(sA);
      const p2 = eslabones.trazado.punto(sA + 0.004);
      q2.setFromAxisAngle(EJE_Z, Math.atan2(p2.y - p.y, p2.x - p.x));
      tmp2.set(p.x + (dCad ? dCad.x * fCad : 0), p.y + (dCad ? dCad.y * fCad : 0), zc + (dCad ? dCad.z * fCad : 0));
      const marca = i % 9 === 0;
      const interior = i % 2 === 0;
      escalaTmp.set(marca ? 1.35 : 1, marca ? 1.5 : interior ? 1 : 0.8, interior ? 0.85 : 1.15);
      m4.compose(tmp2, q2, escalaTmp);
      eslabones.im.setMatrixAt(i, m4);
    }
    eslabones.im.instanceMatrix.needsUpdate = true;

    /* ---- etiquetas DOM con línea guía: punto sobre la pieza, caja cercana y sin solapes ---- */
    const escenario = gl.domElement.closest(".escenario") as HTMLElement | null;
    const ahora = performance.now();
    if (escenario && ahora - reservadas.current.t > 400) {
      const er = escenario.getBoundingClientRect();
      reservadas.current = {
        t: ahora,
        r: Array.from(escenario.querySelectorAll<HTMLElement>(".superpuesto, .lento, .leyenda-escena, .tour-banda")).map((e) => {
          const b = e.getBoundingClientRect();
          return { x: b.left - er.left, y: b.top - er.top, w: b.width, h: b.height };
        }),
      };
    }
    const visibles = etiquetasVisibles.current;
    const entradas: { clave: string; px: number; py: number; pref: [number, number]; w: number; h: number }[] = [];
    for (const [clave, ancla] of Object.entries(ANCLAS)) {
      const div = etq.current[clave];
      const g = lineas.current[clave];
      const n = nodos.get(ancla.pieza);
      const ocultar = () => {
        if (div) div.style.visibility = "hidden";
        if (g?.linea) g.linea.style.visibility = "hidden";
        if (g?.punto) g.punto.style.visibility = "hidden";
      };
      // En el corte del motor solo se rotulan las piezas que se mantienen opacas.
      const fueraDeEnfoque = s.enfoque !== null && !s.enfoque.has(ancla.pieza);
      if (!div || !n || !visibles || !n.obj.visible || fueraDeEnfoque) {
        ocultar();
        continue;
      }
      n.obj.localToWorld(tmp.set(...ancla.desfase));
      grupo.current?.localToWorld(tmp); // cabeceo del conjunto
      tmp.project(camara);
      if (tmp.z >= 1) {
        ocultar();
        continue;
      }
      let med = medidas.current[clave];
      if (!med || ahora - med.t > 200) {
        med = { w: div.offsetWidth, h: div.offsetHeight, t: ahora };
        medidas.current[clave] = med;
      }
      entradas.push({ clave, px: (tmp.x * 0.5 + 0.5) * tamano.width, py: (-tmp.y * 0.5 + 0.5) * tamano.height, pref: ancla.pref, w: med.w, h: med.h });
    }
    const colocadas = colocarEtiquetas(entradas, tamano.width, tamano.height, reservadas.current.r, 40);
    for (const c of colocadas) {
      const div = etq.current[c.clave]!;
      div.style.visibility = "visible";
      div.style.transform = `translate(${(c.cx - c.w / 2).toFixed(1)}px, ${(c.cy - c.h / 2).toFixed(1)}px)`;
      const g = lineas.current[c.clave];
      const [bx, by] = puntoBorde(c);
      if (g?.linea) {
        g.linea.setAttribute("x1", c.px.toFixed(1));
        g.linea.setAttribute("y1", c.py.toFixed(1));
        g.linea.setAttribute("x2", bx.toFixed(1));
        g.linea.setAttribute("y2", by.toFixed(1));
        g.linea.style.visibility = "visible";
      }
      if (g?.punto) {
        g.punto.setAttribute("cx", c.px.toFixed(1));
        g.punto.setAttribute("cy", c.py.toFixed(1));
        g.punto.style.visibility = "visible";
      }
    }
  });

  return (
    <group ref={grupo}>
      <primitive
        object={raiz}
        onClick={(e: { stopPropagation: () => void; object: THREE.Object3D }) => {
          e.stopPropagation();
          let o: THREE.Object3D | null = e.object;
          while (o && !nodos.has(o.name)) o = o.parent;
          alSeleccionar(o ? o.name : null);
        }}
        onPointerMissed={() => alSeleccionar(null)}
      />
      <primitive object={eslabones.im} />
      <primitive object={gas} />
      <primitive object={chispa} renderOrder={10} />
    </group>
  );
}

/** Detecta (una vez, con un contexto desechable) si WebGL corre por software (SwiftShader, llvmpipe…). */
let softwareCache: boolean | null = null;
function esRenderPorSoftware(): boolean {
  if (softwareCache !== null) return softwareCache;
  try {
    const ctx = document.createElement("canvas").getContext("webgl");
    const ext = ctx?.getExtension("WEBGL_debug_renderer_info");
    const nombre = ctx ? String(ctx.getParameter(ext ? ext.UNMASKED_RENDERER_WEBGL : ctx.RENDERER)) : "";
    softwareCache = /swiftshader|llvmpipe|software|basic render/i.test(nombre);
    ctx?.getExtension("WEBGL_lose_context")?.loseContext();
  } catch {
    softwareCache = false;
  }
  return softwareCache;
}
const calidadInicial = (): Calidad => (/[?&]calidad=(alta|ligera)/.exec(window.location.hash)?.[1] as Calidad | undefined) ?? (esRenderPorSoftware() ? "ligera" : "alta");

/** SSAO con el compositor de three: sustituye al render por defecto mientras está activo. */
function PostProceso() {
  const { gl, scene, camera, size } = useThree();
  const composer = useMemo(() => {
    const rt = new THREE.WebGLRenderTarget(size.width, size.height, { type: THREE.HalfFloatType, samples: 0 });
    const c = new EffectComposer(gl, rt);
    c.addPass(new RenderPass(scene, camera));
    const ao = new SSAOPass(scene, camera, size.width, size.height);
    ao.kernelRadius = 0.08;
    ao.minDistance = 0.0005;
    ao.maxDistance = 0.03;
    c.addPass(ao);
    c.addPass(new OutputPass());
    return c;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [gl, scene, camera]);
  useEffect(() => composer.setSize(size.width, size.height), [composer, size]);
  useEffect(() => () => composer.dispose(), [composer]);
  useFrame(() => composer.render(), 1);
  return null;
}

function Contenido(props: Props & { calidad: Calidad }) {
  const { calidad } = props;
  useEffect(() => {
    props.alCalidad?.(calidad);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [calidad]);
  return (
    <>
      {calidad === "alta" ? (
        /* Entorno de estudio local: Lightformers dentro de un cubemap generado en el cliente (sin HDR externo). */
        <Environment resolution={256} environmentIntensity={0.85}>
          <Lightformer form="rect" intensity={2.4} color="#ffffff" position={[0, 5, 0]} rotation-x={Math.PI / 2} scale={[9, 6, 1]} />
          <Lightformer form="rect" intensity={1.6} color="#fff4e6" position={[-5, 2, 3]} rotation-y={Math.PI / 2} scale={[6, 3, 1]} />
          <Lightformer form="rect" intensity={1.2} color="#e8f0ff" position={[5, 1.5, -2]} rotation-y={-Math.PI / 2} scale={[6, 3, 1]} />
          <Lightformer form="ring" intensity={1.0} color="#ffffff" position={[0, 2, -6]} scale={4} />
          <Lightformer form="rect" intensity={0.5} color="#ffffff" position={[0, -1, 4]} scale={[8, 1, 1]} />
        </Environment>
      ) : (
        <>
          <hemisphereLight args={["#ffffff", "#bdbbb3", 1.1]} />
          <directionalLight position={[-2, 1.2, 2.5]} intensity={1.2} color="#fff1e0" />
          <directionalLight position={[2.5, 1.0, -1.5]} intensity={0.8} color="#e6efff" />
        </>
      )}
      <hemisphereLight args={["#ffffff", "#c9c7c0", calidad === "alta" ? 0.35 : 0.2]} />
      <directionalLight position={[1.5, 2.2, 2.0]} intensity={calidad === "alta" ? 1.1 : 1.6} />
      <gridHelper args={[3.2, 32, "#d4d2cb", "#e6e5e1"]} position={[0.01, -0.002, 0]} />
      <ContactShadows position={[0.01, 0.001, 0]} opacity={0.5} scale={3.6} blur={2.2} far={1.1} resolution={512} frames={2} color="#1b1b1b" />
      <Modelo
        estado={props.estado}
        geometria={props.geometria}
        alSeleccionar={props.alSeleccionar}
        etiquetas={props.etiquetas}
        lineas={props.lineas}
        etiquetasVisibles={props.etiquetasVisibles}
        calidad={calidad}
      />
      {calidad === "alta" && props.ssao !== false && <PostProceso />}
    </>
  );
}

export default function EscenaMoto(props: Props) {
  const calidad = useMemo(calidadInicial, []);
  return (
    <Canvas
      dpr={[1, 2]}
      camera={{ position: [1.0, 0.8, 2.5], fov: 40, near: 0.02, far: 30 }}
      gl={{ preserveDrawingBuffer: true, antialias: calidad === "alta", toneMapping: THREE.ACESFilmicToneMapping, toneMappingExposure: 1.05 }}
      onCreated={({ gl }) => gl.setClearColor("#fcfcfb")}
      data-testid="lienzo-3d"
    >
      <Contenido {...props} calidad={calidad} />
      <OrbitControls ref={props.controles} makeDefault enableDamping minDistance={0.2} maxDistance={7} target={[0.01, 0.45, 0]} />
    </Canvas>
  );
}

useGLTF.preload(URL_MODELO_MOTO);
