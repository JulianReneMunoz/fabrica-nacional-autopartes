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
}

/** Etiquetas HTML superpuestas: se proyectan en cada fotograma desde el punto de anclaje 3D. */
export const ANCLAS: Record<string, { pieza: string; desfase: [number, number, number] }> = {
  piston: { pieza: "piston", desfase: [0.09, 0.02, -0.03] },
  disco: { pieza: "disco", desfase: [0.13, -0.1, 0.02] },
  rueda: { pieza: "cubo", desfase: [-0.06, -0.05, 0.05] },
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
  controles: React.MutableRefObject<OrbitControlsImpl | null>;
}

const PLANO = new THREE.Plane(new THREE.Vector3(-1, 0, 0), 0);
const EJE_Z = new THREE.Vector3(0, 0, 1);

function Modelo({ estado, geometria, alSeleccionar, alFotograma, etiquetas: etq }: Omit<Props, "controles">) {
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

  const ultimoAviso = useRef(0);
  const tmp = useMemo(() => new THREE.Vector3(), []);
  const q = useMemo(() => new THREE.Quaternion(), []);

  useFrame(() => {
    const s = estado.current;
    if (controles) {
      controles.autoRotate = s.autoGiro;
      controles.autoRotateSpeed = 1.6;
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
    for (const [clave, ancla] of Object.entries(ANCLAS)) {
      const div = etq.current[clave];
      const n = nodos.get(ancla.pieza);
      if (!div || !n) continue;
      n.obj.getWorldPosition(tmp);
      tmp.add(new THREE.Vector3(...ancla.desfase)).project(camara);
      const x = (tmp.x * 0.5 + 0.5) * tamano.width;
      const y = (-tmp.y * 0.5 + 0.5) * tamano.height;
      div.style.transform = `translate(${x.toFixed(1)}px, ${y.toFixed(1)}px) translate(-50%, -100%)`;
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
      />
      <OrbitControls
        ref={props.controles}
        makeDefault
        enableDamping
        minDistance={0.15}
        maxDistance={2.5}
        target={[0, 0.03, 0]}
      />
    </Canvas>
  );
}

useGLTF.preload(URL_MODELO);
