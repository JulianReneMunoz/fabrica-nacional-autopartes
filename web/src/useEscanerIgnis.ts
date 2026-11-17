/**
 * Hook de React Three Fiber que anima el escáner del GLB del auto IGNIS (ignis_auto.glb).
 * Se buscan los nodos seg_00 … seg_11 (dentro de escaner_frontal), se asigna a cada uno un material propio
 * y se actualiza el brillo emisivo en cada cuadro.
 *
 * Uso:
 *   const { scene } = useGLTF('/app/models/ignis_auto.glb');
 *   const modo = useRef<ModoEscaner>('reposo');
 *   const amplitud = useRef(0);           // 0..1, desde el AnalyserNode del TTS o del micrófono
 *   useEscanerIgnis(scene, modo, amplitud);
 */
import { useEffect, useMemo, useRef, type MutableRefObject } from 'react';
import { useFrame } from '@react-three/fiber';
import * as THREE from 'three';
import {
  crearEstado,
  nivelesSinMovimiento,
  pasoEscaner,
  OPCIONES_POR_DEFECTO,
  type ModoEscaner,
} from './escanerIgnis';

const ROJO = new THREE.Color(1.0, 0.005, 0.003);
const INTENSIDAD_MAX = 7;    // con bloom; sin posprocesado, 3–4 es suficiente
const INTENSIDAD_MIN = 0.04; // lente apagado pero visible

export function useEscanerIgnis(
  escena: THREE.Object3D | null,
  modo: MutableRefObject<ModoEscaner>,
  amplitud: MutableRefObject<number>,
) {
  const materiales = useMemo(() => {
    if (!escena) return [] as THREE.MeshStandardMaterial[];
    const lista: THREE.MeshStandardMaterial[] = [];
    for (let i = 0; i < OPCIONES_POR_DEFECTO.segmentos; i++) {
      const nodo = escena.getObjectByName(`seg_${String(i).padStart(2, "0")}`);
      const malla = nodo as THREE.Mesh | undefined;
      if (!malla?.isMesh) continue;
      const mat = (malla.material as THREE.MeshStandardMaterial).clone();
      mat.color.setRGB(0.02, 0.004, 0.004); // base casi negra: el rojo lo pone solo el emisivo
      mat.emissive = ROJO.clone();
      mat.emissiveIntensity = INTENSIDAD_MIN;
      mat.toneMapped = false; // rojo saturado aunque esté muy brillante
      malla.material = mat;
      lista.push(mat);
    }
    return lista;
  }, [escena]);

  const estado = useRef(crearEstado());
  const reducido = useRef(false);

  useEffect(() => {
    const mq = window.matchMedia('(prefers-reduced-motion: reduce)');
    reducido.current = mq.matches;
    const cambio = (e: MediaQueryListEvent) => (reducido.current = e.matches);
    mq.addEventListener('change', cambio);
    return () => {
      mq.removeEventListener('change', cambio);
      materiales.forEach((m) => m.dispose());
    };
  }, [materiales]);

  useFrame((_, dt) => {
    if (!materiales.length) return;
    const niveles = reducido.current
      ? nivelesSinMovimiento(modo.current)
      : (estado.current = pasoEscaner(estado.current, Math.min(dt, 0.1), modo.current, amplitud.current)).niveles;
    materiales.forEach((m, i) => {
      m.emissiveIntensity = INTENSIDAD_MIN + niveles[i] * INTENSIDAD_MAX;
    });
  });
}

/** Se reexporta desde el módulo puro para que la voz y el micrófono no dependan de Three.js. */
export { leerAmplitud } from './escanerIgnis';
