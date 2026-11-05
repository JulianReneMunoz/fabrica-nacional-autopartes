/**
 * Escena 3D de la motocicleta de referencia (React Three Fiber). Carga `moto_honda.glb`
 * (`uv run fabrica simulador generar`) y, en cada fotograma, aplica a cada pieza:
 *   posición = base + despiece_i · Δdespiece_i  (+ movimientos del mecanismo atenuados por el despiece)
 * Movimientos del mecanismo (todos desde `modelos/moto.ts`, sin números propios):
 *   pistón  y = x(θ) − x(0)                 biela  rota φ = asin(r·sin θ / L) y cuelga entre munequillaequilla y bulón
 *   válvulas: levante senoidal en su fase    chispa: en el PMS de la compresión (θ720 = 360°)
 *   piñón / corona / ruedas: ángulos acumulados por la página (ya divididos por el factor de cámara lenta)
 *   cadena: marcas que avanzan sobre el lazo a la velocidad lineal v = ω·r
 * El estado mutable vive en una referencia para no re-renderizar React a 60 Hz.
 */
import { OrbitControls, useGLTF } from "@react-three/drei";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { useEffect, useMemo, useRef } from "react";
import * as THREE from "three";
import type { OrbitControls as OrbitControlsImpl } from "three-stdlib";
import {
  anguloBielaRad,
  FASES_INFO,
  faseCiclo,
  GEOMETRIA_MOTOR,
  chispaPermitida,
  intensidadChispaMotor,
  levanteAdmision,
  levanteEscape,
  posicionPistonM,
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
  enfoque: Set<string> | null; // piezas que se mantienen opacas; el resto pasa a fantasma
  transparencia: number;
  autoGiro: boolean;
  camara: PeticionCamara | null;
}

export interface Ancla {
  pieza: string;
  desfase: Vec3;
  px: [number, number]; // desplazamiento en pantalla (px) para evitar solapes
}
/** Etiquetas HTML superpuestas: se proyectan en cada fotograma desde un punto de anclaje 3D. */
export const ANCLAS: Record<string, Ancla> = {
  motor: { pieza: "cilindro", desfase: [0, 0.55, 0], px: [-20, -6] },
  cilindrada: { pieza: "ciguenal", desfase: [0, -0.3, 0], px: [40, 28] },
  transmision: { pieza: "cadena", desfase: [-0.1, -0.1, 0.07], px: [-10, 40] },
  rueda: { pieza: "rin_trasero", desfase: [-0.1, -0.33, 0.07], px: [-40, 22] },
  disco_del: { pieza: "disco_delantero", desfase: [0, 0.35, 0.05], px: [-34, -8] },
  disco_tras: { pieza: "disco_trasero", desfase: [-0.1, 0.4, -0.05], px: [-40, -10] },
};

export interface GeometriaDespieceMoto {
  delta: Record<string, THREE.Vector3>; // despiece completo − ensamblado
}

interface Props {
  estado: React.MutableRefObject<EstadoMoto>;
  geometria: GeometriaDespieceMoto | null;
  alSeleccionar: (id: string | null) => void;
  etiquetas: React.MutableRefObject<Record<string, HTMLDivElement | null>>;
  etiquetasVisibles: React.MutableRefObject<boolean>;
  controles: React.MutableRefObject<OrbitControlsImpl | null>;
}

const EJE_Z = new THREE.Vector3(0, 0, 1);
const EJE_HORQUILLA = new THREE.Vector3(-0.45399, 0.891007, 0);
const GRUPO_DELANTERO = new Set([
  "botella_izquierda",
  "botella_derecha",
  "rin_delantero",
  "llanta_delantera",
  "disco_delantero",
  "caliper_delantero",
  "cubo_delantero",
]);
const GIRA_TRASERA = new Set(["rin_trasero", "llanta_trasera", "disco_trasero", "cubo_trasero", "corona"]);
const GIRA_DELANTERA = new Set(["rin_delantero", "llanta_delantera", "disco_delantero", "cubo_delantero"]);
const OPACIDAD_FANTASMA = 0.1;
const N_MARCAS = 24;
const Z_CADENA = 0.065;

function Modelo({ estado, geometria, alSeleccionar, etiquetas: etq, etiquetasVisibles }: Omit<Props, "controles">) {
  const { scene } = useGLTF(URL_MODELO_MOTO);
  const camara = useThree((t) => t.camera);
  const tamano = useThree((t) => t.size);
  const controles = useThree((t) => t.controls) as OrbitControlsImpl | null;

  // Copia profunda con materiales propios para poder resaltar y aplicar transparencia por pieza.
  const raiz = useMemo(() => {
    const copia = scene.clone(true);
    copia.traverse((o) => {
      const m = o as THREE.Mesh;
      if (m.isMesh) {
        const mat = (m.material as THREE.MeshStandardMaterial).clone();
        m.material = mat;
      }
    });
    return copia;
  }, [scene]);

  const nodos = useMemo(() => {
    const mapa = new Map<string, { obj: THREE.Object3D; base: THREE.Vector3; mallas: THREE.Mesh[] }>();
    raiz.traverse((o) => {
      if (o.name && !mapa.has(o.name) && o !== raiz) {
        const mallas: THREE.Mesh[] = [];
        o.traverse((h) => (h as THREE.Mesh).isMesh && mallas.push(h as THREE.Mesh));
        if (mallas.length) mapa.set(o.name, { obj: o, base: o.position.clone(), mallas });
      }
    });
    return mapa;
  }, [raiz]);

  const cadena = useMemo(() => trazadoCadena(), []);
  const marcas = useMemo(() => {
    const im = new THREE.InstancedMesh(
      new THREE.BoxGeometry(0.016, 0.016, 0.02),
      new THREE.MeshStandardMaterial({ color: "#2a78d6", emissive: "#2a78d6", emissiveIntensity: 0.35 }),
      N_MARCAS,
    );
    im.frustumCulled = false;
    return im;
  }, []);
  const gas = useMemo(
    () =>
      new THREE.Mesh(
        new THREE.CylinderGeometry(0.0245, 0.0245, 1, 24, 1, false),
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
  const q = useMemo(() => new THREE.Quaternion(), []);
  const m4 = useMemo(() => new THREE.Matrix4(), []);
  const color = useMemo(() => new THREE.Color(), []);
  const camaraObjetivo = useMemo(() => ({ id: -1, pos: new THREE.Vector3(), objetivo: new THREE.Vector3(), activa: false }), []);

  useEffect(
    () => () => {
      marcas.geometry.dispose();
      (marcas.material as THREE.Material).dispose();
      gas.geometry.dispose();
      (gas.material as THREE.Material).dispose();
      chispa.geometry.dispose();
      (chispa.material as THREE.Material).dispose();
    },
    [marcas, gas, chispa],
  );

  useFrame((_, dtReal) => {
    const s = estado.current;
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

    // Con una llanta trasera mayor, la moto cabecea sobre el contacto delantero: la rueda trasera sigue apoyada.
    if (grupo.current) {
      const apoyo = nodos.get("llanta_delantera")?.base.x ?? 0.71;
      const largo = apoyo - (nodos.get("llanta_trasera")?.base.x ?? -0.63);
      const ang = -s.elevacionTrasera / largo;
      grupo.current.rotation.z = ang;
      grupo.current.position.set(apoyo * (1 - Math.cos(ang)), -apoyo * Math.sin(ang), 0);
    }

    /* ---- mecanismo del motor, desde moto.ts ---- */
    const carrera = GEOMETRIA_MOTOR.carreraM;
    const longBiela = GEOMETRIA_MOTOR.bielaM;
    const r = carrera / 2;
    const th720 = s.theta720;
    const th = (th720 * Math.PI) / 180; // θ de cigüeñal (el ciclo completo ocupa 2 vueltas)
    const xPms = posicionPistonM(0, carrera, longBiela);
    const dyPiston = posicionPistonM(th, carrera, longBiela) - xPms;
    const phi = anguloBielaRad(th, carrera, longBiela);
    const base = nodos.get("ciguenal")?.base;
    const cx = base?.x ?? 0;
    const cy = base?.y ?? 0.33;
    // El cigüeñal gira en sentido horario (visto desde +Z): la munequillaequilla está en (r·sin θ, r·cos θ).
    const munequilla = { x: cx + r * Math.sin(th), y: cy + r * Math.cos(th) };
    const bulon = { x: cx, y: cy + posicionPistonM(th, carrera, longBiela) };

    for (const [id, n] of nodos) {
      const f = s.despiece[id] ?? 0;
      const atenuar = 1 - Math.min(f * 4, 1); // el mecanismo vuelve a su pose nominal al separarse
      tmp.copy(n.base);
      const d = geometria?.delta[id];
      let rotZ = 0;
      let giro = false;
      switch (id) {
        case "piston":
          tmp.y += dyPiston * atenuar;
          break;
        case "biela": {
          const mx = (munequilla.x + bulon.x) / 2;
          const my = (munequilla.y + bulon.y) / 2;
          tmp.x = n.base.x + (mx - n.base.x) * atenuar;
          tmp.y = n.base.y + (my - n.base.y) * atenuar;
          rotZ = phi * atenuar;
          giro = true;
          break;
        }
        case "ciguenal":
          rotZ = -th;
          giro = true;
          break;
        case "valvula_admision":
          tmp.y -= levanteAdmision(th720) * atenuar;
          break;
        case "valvula_escape":
          tmp.y -= levanteEscape(th720) * atenuar;
          break;
        case "pinon":
          rotZ = s.angPinon;
          giro = true;
          break;
        default:
          if (GIRA_TRASERA.has(id)) {
            rotZ = s.angRuedaTras;
            giro = true;
          } else if (GIRA_DELANTERA.has(id)) {
            rotZ = s.angRuedaDel;
            giro = true;
          }
      }
      if (d) tmp.addScaledVector(d, f);
      if (GRUPO_DELANTERO.has(id)) tmp.addScaledVector(EJE_HORQUILLA, s.compresionHorquilla * (1 - f));
      if (giro) {
        q.setFromAxisAngle(EJE_Z, rotZ);
        n.obj.quaternion.copy(q);
      }
      n.obj.position.copy(tmp);
      if (id === "llanta_trasera") n.obj.scale.set(s.escalaLlantaTrasera, s.escalaLlantaTrasera, 1);
      const sub = s.subconjuntoDe[id];
      n.obj.visible = !s.ocultas.has(id) && (s.subconjuntoAislado === null || s.subconjuntoAislado === sub);

      const sel = s.seleccion === id || s.resaltadas.has(id);
      const alerta = s.alerta.has(id);
      const fantasma = s.enfoque !== null && !s.enfoque.has(id) && !sel;
      for (let i = 0; i < n.mallas.length; i++) {
        const mat = n.mallas[i].material as THREE.MeshStandardMaterial;
        if (sel) color.set("#eb6834");
        else if (alerta) color.set("#c2410c");
        else color.set("#000000");
        mat.emissive.copy(color);
        mat.emissiveIntensity = sel ? 0.6 : alerta ? 0.5 : 0;
        const op = sel ? 1 : fantasma ? OPACIDAD_FANTASMA : 1 - s.transparencia;
        if (mat.transparent !== op < 1) {
          mat.transparent = op < 1;
          mat.needsUpdate = true; // el programa del shader cambia entre opaco y transparente
        }
        mat.opacity = op;
        mat.depthWrite = op >= 1;
      }
    }

    /* ---- gas en la cámara de combustión y chispa ---- */
    const cil = nodos.get("cilindro");
    const pis = nodos.get("piston");
    const dCil = geometria?.delta["cilindro"];
    const visibleMotor = Boolean(cil?.obj.visible && pis?.obj.visible) && (s.despiece["cilindro"] ?? 0) < 0.02 && (s.despiece["piston"] ?? 0) < 0.02;
    if (cil && pis) {
      const techo = cil.base.y + 0.06 + (dCil ? dCil.y * (s.despiece["cilindro"] ?? 0) : 0); // culata del cilindro (largo 0,12 m)
      const cima = pis.obj.position.y + 0.025;
      const h = Math.max(techo - cima, 0.002);
      gas.visible = visibleMotor && s.motorEnMarcha;
      gas.scale.set(1, h, 1);
      gas.rotation.set(0, 0, 0);
      gas.position.set(0, cima + h / 2, 0);
      const fase = faseCiclo(th720);
      const gm = gas.material as THREE.MeshBasicMaterial;
      gm.color.set(FASES_INFO[fase].color);
      // Con el limitador, en el ciclo sin chispa la expansión no tiene combustión: el gas se atenúa.
      gm.opacity = fase === "expansion" && !chispaPermitida(s.estadoMotor, s.ciclo) ? 0.1 : 0.38;
      const k = intensidadChispaMotor(th720, s.ciclo, s.estadoMotor);
      chispa.visible = visibleMotor && s.motorEnMarcha && k > 0;
      chispa.position.set(0, techo - 0.012, 0);
      chispa.scale.setScalar(0.6 + 1.6 * k);
    }

    /* ---- marcas de la cadena: avanzan sobre el lazo a la velocidad v = ω·r ---- */
    const dCad = geometria?.delta["cadena"];
    const fCad = s.despiece["cadena"] ?? 0;
    const cad = nodos.get("cadena");
    marcas.visible = Boolean(cad?.obj.visible) && (s.enfoque === null || s.enfoque.has("cadena"));
    const pasoMarca = cadena.longitud / N_MARCAS;
    for (let i = 0; i < N_MARCAS; i++) {
      const p = cadena.punto(s.cadenaS + i * pasoMarca);
      const p2 = cadena.punto(s.cadenaS + i * pasoMarca + 0.004);
      q.setFromAxisAngle(EJE_Z, Math.atan2(p2.y - p.y, p2.x - p.x));
      tmp2.set(p.x + (dCad ? dCad.x * fCad : 0), p.y + (dCad ? dCad.y * fCad : 0), Z_CADENA + (dCad ? dCad.z * fCad : 0));
      m4.compose(tmp2, q, tmp.set(1, 1, 1));
      marcas.setMatrixAt(i, m4);
    }
    marcas.instanceMatrix.needsUpdate = true;

    /* ---- etiquetas DOM proyectadas ---- */
    for (const [clave, ancla] of Object.entries(ANCLAS)) {
      const div = etq.current[clave];
      const n = nodos.get(ancla.pieza);
      if (!div || !n) continue;
      if (!etiquetasVisibles.current) {
        div.style.visibility = "hidden";
        continue;
      }
      n.obj.getWorldPosition(tmp);
      tmp.add(tmp2.set(...ancla.desfase)).project(camara);
      const x = (tmp.x * 0.5 + 0.5) * tamano.width + ancla.px[0];
      const y = (-tmp.y * 0.5 + 0.5) * tamano.height + ancla.px[1];
      div.style.visibility = tmp.z < 1 ? "visible" : "hidden";
      div.style.transform = `translate(${x.toFixed(1)}px, ${y.toFixed(1)}px) translate(-50%, -100%)`;
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
      <primitive object={marcas} />
      <primitive object={gas} />
      <primitive object={chispa} renderOrder={10} />
    </group>
  );
}

export default function EscenaMoto(props: Props) {
  return (
    <Canvas
      dpr={[1, 2]}
      camera={{ position: [0.75, 0.75, 2.3], fov: 40, near: 0.02, far: 30 }}
      gl={{ preserveDrawingBuffer: true, antialias: true }}
      onCreated={({ gl }) => gl.setClearColor("#fcfcfb")}
      data-testid="lienzo-3d"
    >
      <hemisphereLight args={["#ffffff", "#c9c7c0", 1.0]} />
      <directionalLight position={[1.5, 2.2, 2.0]} intensity={2.2} />
      <directionalLight position={[-1.5, 0.8, -1.2]} intensity={0.7} />
      <gridHelper args={[3.2, 32, "#d4d2cb", "#e6e5e1"]} position={[0.05, -0.002, 0]} />
      <Modelo
        estado={props.estado}
        geometria={props.geometria}
        alSeleccionar={props.alSeleccionar}
        etiquetas={props.etiquetas}
        etiquetasVisibles={props.etiquetasVisibles}
      />
      <OrbitControls ref={props.controles} makeDefault enableDamping minDistance={0.2} maxDistance={7} target={[0.05, 0.45, 0]} />
    </Canvas>
  );
}

useGLTF.preload(URL_MODELO_MOTO);
