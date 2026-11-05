/**
 * Escena 3D del freno de disco (React Three Fiber). Carga el GLB generado por
 * `uv run fabrica simulador generar` y aplica, en cada fotograma:
 *   posición = base + despiece_i · Δdespiece_i + k · Δarticulaciones_i     (Δ calculados por la API)
 *   giro     = Rz(θ) para el conjunto giratorio (j_rueda, eje z por el origen)
 * El estado mutable vive en una referencia para no re-renderizar React a 60 Hz.
 */
import { OrbitControls, useGLTF } from "@react-three/drei";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { useEffect, useMemo, useRef } from "react";
import * as THREE from "three";
import type { OrbitControls as OrbitControlsImpl } from "three-stdlib";
import { prefiereMovimientoReducido } from "../componentes/anatomia";
import { colocarEtiquetas, puntoBorde, type Rect } from "../modelos/etiquetas";

export const URL_MODELO = `${import.meta.env.BASE_URL}modelos/freno_disco.glb`;
export const GIRATORIAS = new Set(["cubo", "disco", "esparrago_1", "esparrago_2", "esparrago_3", "esparrago_4"]);

export interface EstadoEscena {
  despiece: Record<string, number>; // 0..1 por pieza
  apriete: number; // 0..1 (fracción de la holgura cerrada)
  ampliacion: number; // factor visual de holguras
  angulo: number; // rad, conjunto giratorio
  seleccion: string | null;
  ocultas: Set<string>;
  aislada: string | null;
  transparencia: number;
  seccion: boolean;
  autoGiro: boolean;
  /** Contador: al incrementarse se vuelve al encuadre automático (botón «Cámara»). */
  reencuadrar: number;
}

/** Etiquetas HTML con línea guía: el punto cae sobre su pieza y la caja se coloca cerca, sin solaparse. */
export const ANCLAS: Record<string, { pieza: string; desfase: [number, number, number]; pref: [number, number] }> = {
  piston: { pieza: "piston", desfase: [0.0, 0.0, 0.0], pref: [95, -70] },
  disco: { pieza: "disco", desfase: [0.0, -0.1, 0.0], pref: [105, 60] },
  rueda: { pieza: "cubo", desfase: [0.0, 0.0, 0.03], pref: [-110, -60] },
};

export interface GeometriaDespiece {
  delta: Record<string, THREE.Vector3>; // despiece completo − ensamblado
  deltaApriete: Record<string, THREE.Vector3>; // pinza cerrada − abierta
}

export interface LecturaLocal {
  posicion: [number, number, number];
  angulo_z_grados: number;
}

interface Props {
  estado: React.MutableRefObject<EstadoEscena>;
  geometria: GeometriaDespiece | null;
  alSeleccionar: (id: string | null) => void;
  alFotograma: (lectura: LecturaLocal | null) => void;
  etiquetas: React.MutableRefObject<Record<string, HTMLDivElement | null>>;
  lineas: React.MutableRefObject<Record<string, { linea: SVGLineElement | null; punto: SVGCircleElement | null }>>;
  controles: React.MutableRefObject<OrbitControlsImpl | null>;
}

const MARGEN_ENCUADRE = 0.92; // la esfera envolvente de la caja es holgada: el factor < 1 deja un margen visual de ~10 %
const DIRECCION_INICIAL = new THREE.Vector3(0.52, 0.33, 0.72).multiplyScalar(0.9);
const PLANO = new THREE.Plane(new THREE.Vector3(-1, 0, 0), 0);
const EJE_Z = new THREE.Vector3(0, 0, 1);

function Modelo({ estado, geometria, alSeleccionar, alFotograma, etiquetas: etq, lineas }: Omit<Props, "controles">) {
  const { scene } = useGLTF(URL_MODELO);
  const gl = useThree((t) => t.gl);
  const camara = useThree((t) => t.camera);
  const tamano = useThree((t) => t.size);
  const controles = useThree((t) => t.controls) as OrbitControlsImpl | null;
  // Copia profunda con materiales propios para poder resaltar y aplicar transparencia por pieza.
  const raiz = useMemo(() => {
    const copia = scene.clone(true);
    copia.traverse((o) => {
      const m = o as THREE.Mesh;
      if (m.isMesh) {
        m.material = (m.material as THREE.MeshStandardMaterial).clone();
        m.castShadow = true;
        m.receiveShadow = true;
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

  useEffect(() => {
    gl.localClippingEnabled = true;
  }, [gl]);

  /* ---------- encuadre automático (fit to bounds): solo la cámara; el GLB no cambia ---------- */
  const encuadre = useMemo(() => {
    raiz.updateMatrixWorld(true);
    const caja = new THREE.Box3();
    const cajaDespiece = new THREE.Box3();
    const tmpCaja = new THREE.Box3();
    for (const [id, n] of nodos) {
      tmpCaja.setFromObject(n.obj);
      caja.union(tmpCaja);
      cajaDespiece.union(tmpCaja);
      const d = geometria?.delta[id];
      if (d) cajaDespiece.union(tmpCaja.translate(d));
    }
    const esfera = (c: THREE.Box3) => c.getBoundingSphere(new THREE.Sphere());
    return { ens: esfera(caja), des: esfera(cajaDespiece), manual: false, vistos: -1, inicializado: false };
  }, [raiz, nodos, geometria]);
  useEffect(() => {
    if (!controles) return;
    const alInteractuar = () => {
      encuadre.manual = true;
    };
    controles.addEventListener("start", alInteractuar);
    return () => controles.removeEventListener("start", alInteractuar);
  }, [controles, encuadre]);
  const reservadas = useRef<{ t: number; r: Rect[] }>({ t: -1e9, r: [] });
  const medidas = useRef<Record<string, { w: number; h: number; t: number }>>({});

  const ultimoAviso = useRef(0);
  const tmp = useMemo(() => new THREE.Vector3(), []);
  const q = useMemo(() => new THREE.Quaternion(), []);

  useFrame((_, dtFotograma) => {
    const s = estado.current;
    if (controles) {
      controles.autoRotate = s.autoGiro;
      controles.autoRotateSpeed = 1.6;
    }
    if (controles && (s.reencuadrar !== encuadre.vistos || !encuadre.inicializado)) {
      if (encuadre.vistos !== -1 || !encuadre.inicializado) {
        controles.target.copy(encuadre.ens.center);
        camara.position.copy(encuadre.ens.center).add(DIRECCION_INICIAL);
      }
      encuadre.manual = false;
      encuadre.vistos = s.reencuadrar;
      encuadre.inicializado = true;
    }
    if (controles && !encuadre.manual) {
      let fMax = 0;
      for (const v of Object.values(s.despiece)) fMax = Math.max(fMax, v);
      const centro = tmp.copy(encuadre.ens.center).lerp(encuadre.des.center, fMax);
      const radio = THREE.MathUtils.lerp(encuadre.ens.radius, encuadre.des.radius, fMax);
      const persp = camara as THREE.PerspectiveCamera;
      const semiV = THREE.MathUtils.degToRad(persp.fov) / 2;
      const semiH = Math.atan(Math.tan(semiV) * persp.aspect);
      const distancia = (radio * MARGEN_ENCUADRE) / Math.sin(Math.min(semiV, semiH));
      const k = prefiereMovimientoReducido() ? 1 : 1 - Math.exp(-dtFotograma * 4);
      controles.target.lerp(centro, k);
      const dir = camara.position.clone().sub(controles.target).normalize();
      const actual = camara.position.distanceTo(controles.target);
      camara.position.copy(controles.target).addScaledVector(dir, THREE.MathUtils.lerp(actual, distancia, k));
      controles.update();
    }
    q.setFromAxisAngle(EJE_Z, s.angulo);
    for (const [id, n] of nodos) {
      tmp.copy(n.base);
      const d = geometria?.delta[id];
      if (d) tmp.addScaledVector(d, s.despiece[id] ?? 0);
      const a = geometria?.deltaApriete[id];
      if (a) tmp.addScaledVector(a, s.apriete * s.ampliacion);
      if (GIRATORIAS.has(id)) {
        tmp.applyQuaternion(q);
        n.obj.quaternion.copy(q);
      }
      n.obj.position.copy(tmp);
      n.obj.visible = !s.ocultas.has(id) && (s.aislada === null || s.aislada === id);
      for (const m of n.mallas) {
        const mat = m.material as THREE.MeshStandardMaterial;
        const sel = s.seleccion === id;
        mat.emissive.set(sel ? "#eb6834" : "#000000");
        mat.emissiveIntensity = sel ? 0.55 : 0;
        const op = sel ? 1 : 1 - s.transparencia;
        mat.transparent = op < 1;
        mat.opacity = op;
        mat.depthWrite = op >= 1;
        mat.clippingPlanes = s.seccion ? [PLANO] : [];
        mat.side = s.seccion ? THREE.DoubleSide : THREE.FrontSide;
      }
    }
    const ahora0 = performance.now();
    const escenario = gl.domElement.closest("[data-testid=escenario-freno]") as HTMLElement | null;
    if (escenario && ahora0 - reservadas.current.t > 400) {
      const er = escenario.getBoundingClientRect();
      reservadas.current = {
        t: ahora0,
        r: Array.from(escenario.querySelectorAll<HTMLElement>(".leyenda-escena, .tour-banda")).map((e) => {
          const bb = e.getBoundingClientRect();
          return { x: bb.left - er.left, y: bb.top - er.top, w: bb.width, h: bb.height };
        }),
      };
    }
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
      if (!div || !n || div.style.display === "none" || !n.obj.visible) {
        ocultar();
        continue;
      }
      n.obj.localToWorld(tmp.set(...ancla.desfase));
      tmp.project(camara);
      if (tmp.z >= 1) {
        ocultar();
        continue;
      }
      let med = medidas.current[clave];
      if (!med || ahora0 - med.t > 200) {
        med = { w: div.offsetWidth, h: div.offsetHeight, t: ahora0 };
        medidas.current[clave] = med;
      }
      entradas.push({ clave, px: (tmp.x * 0.5 + 0.5) * tamano.width, py: (-tmp.y * 0.5 + 0.5) * tamano.height, pref: ancla.pref, w: med.w, h: med.h });
    }
    for (const c of colocarEtiquetas(entradas, tamano.width, tamano.height, reservadas.current.r, 0)) {
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
    const ahora = performance.now();
    if (ahora - ultimoAviso.current > 120) {
      ultimoAviso.current = ahora;
      const n = s.seleccion ? nodos.get(s.seleccion) : undefined;
      if (n) {
        const p = new THREE.Vector3();
        n.obj.getWorldPosition(p);
        const e = new THREE.Euler().setFromQuaternion(n.obj.quaternion, "XYZ");
        alFotograma({ posicion: [p.x, p.y, p.z], angulo_z_grados: THREE.MathUtils.radToDeg(e.z) });
      } else alFotograma(null);
    }
  });

  return (
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
  );
}

export default function EscenaFreno(props: Props) {
  return (
    <Canvas
      shadows
      dpr={[1, 2]}
      camera={{ position: [0.52, 0.36, 0.72], fov: 40, near: 0.01, far: 20 }}
      gl={{ preserveDrawingBuffer: true, antialias: true }}
      onCreated={({ gl }) => gl.setClearColor("#fcfcfb")}
      data-testid="lienzo-3d"
    >
      <hemisphereLight args={["#ffffff", "#c9c7c0", 0.9]} />
      <directionalLight position={[0.6, 0.9, 0.7]} intensity={2.2} castShadow />
      <directionalLight position={[-0.6, 0.3, -0.5]} intensity={0.6} />
      <gridHelper args={[1.2, 24, "#d4d2cb", "#e6e5e1"]} position={[0, -0.2, 0]} />
      <Modelo
        estado={props.estado}
        geometria={props.geometria}
        alSeleccionar={props.alSeleccionar}
        alFotograma={props.alFotograma}
        etiquetas={props.etiquetas}
        lineas={props.lineas}
      />
      <OrbitControls
        ref={props.controles}
        makeDefault
        minDistance={0.15}
        maxDistance={2.5}
        enableDamping={!prefiereMovimientoReducido()}
        target={[0, 0.03, 0]}
      />
    </Canvas>
  );
}

useGLTF.preload(URL_MODELO);
