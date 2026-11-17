/**
 * Escenario 3D de IGNIS (prompt v2, sección 2.1): solo el auto `ignis_auto.glb` sobre el estudio de
 * `IgnisEstudio.tsx`. Lo único que se anima al conversar es el escáner rojo del frente (`seg_00 … seg_11`).
 *
 * - El GLB viene con meshopt y texturas WebP; `useGLTF` de drei decodifica meshopt sin configuración extra.
 * - Encuadre automático por la esfera envolvente del auto (ignisEncuadre.ts); giro lento en reposo, sin giro con
 *   `prefers-reduced-motion`.
 * - La amplitud del escáner se lee en cada cuadro de un objeto mutable (sin estado de React).
 */
import { useEffect, useLayoutEffect, useMemo, useRef, useState, type MutableRefObject } from "react";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { OrbitControls, PerformanceMonitor, useGLTF } from "@react-three/drei";
import * as THREE from "three";
import IgnisEstudio, { ALTURA_PLATAFORMA } from "./IgnisEstudio";
import { bajarNivel, CONFIG_CALIDAD, nivelDesdeUrl, nivelInicial, subirNivel, type NivelCalidad } from "./ignisCalidad";
import { avanzarAmplitud, modoDesdeConversacion, type AmplitudCompartida, type ModoEscaner } from "./escanerIgnis";
import { limitesZoom, posicionEncuadre } from "./ignisEncuadre";
import type { EstadoAvatarIgnis } from "./ignisStateMachine";
import { useEscanerIgnis } from "./useEscanerIgnis";

/** Ruta pública del modelo: FastAPI sirve el build en /app (vite `base`). */
export const URL_MODELO_AUTO = `${import.meta.env.BASE_URL}models/ignis_auto.glb`;

export interface AccionCamara {
  tipo: "restablecer" | "acercar" | "alejar" | "ninguna";
  n: number;
}

interface Props {
  estado: EstadoAvatarIgnis;
  amplitud: AmplitudCompartida;
  autoGiro: boolean;
  accionCamara: AccionCamara;
  movimientoReducido: boolean;
}

/** Esfera envolvente del auto ya colocado sobre la plataforma. */
interface Envolvente {
  centro: [number, number, number];
  radio: number;
}

const FOV = 34;

/* ------------------------------------------------------------------ auto */
function AutoIgnis({
  modo,
  amplitud,
  alMedir,
}: {
  modo: MutableRefObject<ModoEscaner>;
  amplitud: AmplitudCompartida;
  alMedir: (e: Envolvente) => void;
}) {
  const { scene } = useGLTF(URL_MODELO_AUTO);
  const grupo = useRef<THREE.Group>(null);
  const nivelAmplitud = useRef(0);

  // Sombras en todas las mallas, salvo el escáner (emisivo) y los cristales.
  useMemo(() => {
    scene.traverse((o) => {
      const m = o as THREE.Mesh;
      if (!m.isMesh) return;
      const escaner = /^seg_\d{2}$/.test(m.name);
      m.castShadow = !escaner && m.name !== "parabrisas";
      m.receiveShadow = !escaner;
    });
  }, [scene]);

  // Apoya las ruedas en la plataforma y centra el auto en X/Z; informa la esfera envolvente para el encuadre.
  useLayoutEffect(() => {
    const g = grupo.current;
    if (!g) return;
    g.position.set(0, 0, 0);
    g.updateWorldMatrix(true, true);
    const caja = new THREE.Box3().setFromObject(scene);
    const centro = caja.getCenter(new THREE.Vector3());
    g.position.set(-centro.x, ALTURA_PLATAFORMA - caja.min.y, -centro.z);
    g.updateWorldMatrix(true, true);
    const esfera = new THREE.Box3().setFromObject(scene).getBoundingSphere(new THREE.Sphere());
    alMedir({ centro: [esfera.center.x, esfera.center.y, esfera.center.z], radio: esfera.radius });
  }, [scene, alMedir]);

  // La amplitud se avanza antes de que el hook del escáner lea `nivelAmplitud` en el mismo cuadro.
  useFrame((_, dt) => {
    nivelAmplitud.current = avanzarAmplitud(amplitud, Math.min(dt, 0.1));
  });
  useEscanerIgnis(scene, modo, nivelAmplitud);

  return (
    <group ref={grupo}>
      <primitive object={scene} />
    </group>
  );
}

/* ------------------------------------------------------------------ cámara */
interface ControlesOrbita {
  target: THREE.Vector3;
  update: () => void;
  minDistance: number;
  maxDistance: number;
}

function Camara({ envolvente, accionCamara }: { envolvente: Envolvente | null; accionCamara: AccionCamara }) {
  const camera = useThree((s) => s.camera) as THREE.PerspectiveCamera;
  const ancho = useThree((s) => s.size.width);
  const alto = useThree((s) => s.size.height);
  const controles = useThree((s) => s.controls) as unknown as ControlesOrbita | null;
  const aspecto = alto > 0 ? ancho / alto : 1;
  const objetivo = useRef(new THREE.Vector3(0, 0.6, 0));
  const deseada = useRef<THREE.Vector3 | null>(null);

  const encuadrar = () => {
    if (!envolvente) return;
    objetivo.current.set(...envolvente.centro);
    deseada.current = new THREE.Vector3(...posicionEncuadre(envolvente.centro, envolvente.radio, camera.fov, aspecto));
  };

  // Al cargar el auto o cambiar el tamaño del lienzo, la cámara encuadra el auto completo.
  useEffect(() => {
    encuadrar();
    if (envolvente && controles) {
      const { min, max } = limitesZoom(envolvente.radio, camera.fov, aspecto);
      controles.minDistance = min;
      controles.maxDistance = max;
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [envolvente, aspecto, camera, controles]);

  useEffect(() => {
    if (!controles || accionCamara.tipo === "ninguna") return;
    if (accionCamara.tipo === "restablecer") {
      encuadrar();
      return;
    }
    deseada.current = null;
    const desde = camera.position.clone().sub(controles.target);
    desde.multiplyScalar(accionCamara.tipo === "acercar" ? 0.85 : 1.18);
    const d = THREE.MathUtils.clamp(desde.length(), controles.minDistance, controles.maxDistance);
    camera.position.copy(controles.target).add(desde.setLength(d));
    controles.update();
    // Solo reacciona al contador de la acción.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [accionCamara.n]);

  // Suavizado por tiempo (no por cuadro): converge igual a 20 o a 120 fps.
  useFrame((_, delta) => {
    if (!controles) return;
    const paso = 1 - Math.exp(-delta * 4);
    controles.target.lerp(objetivo.current, paso);
    const d = deseada.current;
    if (d) {
      camera.position.lerp(d, paso);
      if (camera.position.distanceTo(d) < 0.02) deseada.current = null;
    }
  });
  return null;
}

/* ------------------------------------------------------------------ escena */
function nivelDeArranque(): { nivel: NivelCalidad; fijo: boolean } {
  if (typeof window === "undefined") return { nivel: "alto", fijo: false };
  const forzado = nivelDesdeUrl(window.location.search, window.location.hash);
  return { nivel: forzado ?? nivelInicial(window.location.search, window.location.hash), fijo: forzado !== null };
}

export default function IgnisCanvas3D({ estado, amplitud, autoGiro, accionCamara, movimientoReducido }: Props) {
  const arranque = useMemo(nivelDeArranque, []);
  const [nivel, setNivel] = useState<NivelCalidad>(arranque.nivel);
  const [envolvente, setEnvolvente] = useState<Envolvente | null>(null);
  const modo = useRef<ModoEscaner>(modoDesdeConversacion(estado));
  modo.current = modoDesdeConversacion(estado);

  // Con ?calidad= en la URL el nivel queda fijo (capturas, depuración); si no, se adapta a los fps medidos.
  const ajustar = (cambio: (n: NivelCalidad) => NivelCalidad) => {
    if (!arranque.fijo) setNivel(cambio);
  };
  // El giro lento solo corre en reposo: al conversar el auto queda quieto para que se vea el escáner.
  const girar = autoGiro && !movimientoReducido && (estado === "auto" || estado === "escribiendo");

  return (
    <Canvas
      shadows
      dpr={CONFIG_CALIDAD[nivel].dpr}
      gl={{ antialias: true, powerPreference: "high-performance" }}
      camera={{ position: [5.4, 2.3, 4.6], fov: FOV, near: 0.1, far: 120 }}
      aria-label="Auto IGNIS en 3D"
      data-calidad={nivel}
      data-modelo={envolvente ? "cargado" : "cargando"}
    >
      <PerformanceMonitor flipflops={3} onDecline={() => ajustar(bajarNivel)} onIncline={() => ajustar(subirNivel)} onFallback={() => ajustar(() => "bajo")} />
      <IgnisEstudio nivel={nivel} />
      <AutoIgnis modo={modo} amplitud={amplitud} alMedir={setEnvolvente} />
      <OrbitControls makeDefault enablePan={false} enableDamping maxPolarAngle={1.5} autoRotate={girar} autoRotateSpeed={0.5} target={[0, 0.6, 0]} />
      <Camara envolvente={envolvente} accionCamara={accionCamara} />
    </Canvas>
  );
}

useGLTF.preload(URL_MODELO_AUTO);
