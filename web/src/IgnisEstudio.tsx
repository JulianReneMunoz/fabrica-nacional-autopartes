/**
 * Estudio de presentación de IGNIS (Fase 6, opción A): fondo, piso, plataforma, luces, reflejos y posprocesado.
 *
 * Criterio visual: el auto es oscuro, así que el fondo NO puede ser negro. Se usa un estudio de ciclorama con
 * horizonte gris grafito más claro justo detrás del sujeto, luces de recorte (rim) que dibujan la silueta y
 * franjas de luz en el entorno que trazan reflejos largos sobre la pintura con laca (clearcoat). El rojo queda
 * como acento (contraluz, aro de la plataforma y escáner frontal) y no tiñe toda la escena.
 *
 * Todo es procedural: no se descargan HDRI ni texturas externas.
 */
import { useEffect, useMemo } from "react";
import { useThree } from "@react-three/fiber";
import { ContactShadows, Environment, Lightformer, MeshReflectorMaterial } from "@react-three/drei";
import { Bloom, EffectComposer, N8AO, SMAA, ToneMapping, Vignette } from "@react-three/postprocessing";
import { ToneMappingMode } from "postprocessing";
import * as THREE from "three";
import { CONFIG_CALIDAD, type NivelCalidad } from "./ignisCalidad";

const PI = Math.PI;
/** Color del horizonte: la niebla usa el mismo para que el piso se funda con el fondo (ciclorama infinito). */
export const COLOR_HORIZONTE = "#1c1f26";
/** Altura de la plataforma giratoria sobre el piso. */
export const ALTURA_PLATAFORMA = 0.06;

/* ------------------------------------------------------------------ cúpula de fondo con degradado */
const VERTICE_CUPULA = /* glsl */ `
  varying vec3 vDir;
  void main() {
    vDir = normalize(position);
    gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
  }
`;
const FRAGMENTO_CUPULA = /* glsl */ `
  uniform vec3 uHorizonte;
  uniform vec3 uCenit;
  uniform vec3 uAcento;
  varying vec3 vDir;
  void main() {
    float h = clamp(vDir.y, 0.0, 1.0);
    // Banda clara en el horizonte que se oscurece hacia el techo.
    vec3 color = mix(uHorizonte, uCenit, smoothstep(0.0, 0.55, h));
    // Halo detrás del sujeto (dirección -z) para separar la silueta negra del fondo.
    float detras = pow(max(dot(normalize(vec3(vDir.x, 0.0, vDir.z)), vec3(0.0, 0.0, -1.0)), 0.0), 3.0);
    color += vec3(0.05, 0.055, 0.065) * detras * (1.0 - smoothstep(0.0, 0.45, h));
    // Acento rojo muy tenue al fondo a la derecha (eco del contraluz).
    float derecha = pow(max(dot(normalize(vec3(vDir.x, 0.0, vDir.z)), normalize(vec3(0.8, 0.0, -0.6))), 0.0), 6.0);
    color += uAcento * derecha * 0.35 * (1.0 - smoothstep(0.0, 0.35, h));
    gl_FragColor = vec4(color, 1.0);
    #include <colorspace_fragment>
  }
`;

function Cupula() {
  const material = useMemo(
    () =>
      new THREE.ShaderMaterial({
        vertexShader: VERTICE_CUPULA,
        fragmentShader: FRAGMENTO_CUPULA,
        side: THREE.BackSide,
        depthWrite: false,
        fog: false,
        uniforms: {
          uHorizonte: { value: new THREE.Color(COLOR_HORIZONTE) },
          uCenit: { value: new THREE.Color("#07080b") },
          uAcento: { value: new THREE.Color("#5a1208") },
        },
      }),
    [],
  );
  return (
    <mesh material={material} renderOrder={-1}>
      <sphereGeometry args={[45, 48, 24]} />
    </mesh>
  );
}

/* ------------------------------------------------------------------ piso */
/** Mapa de rugosidad procedural de concreto pulido: manchas lisas (charcos) que reflejan y zonas mate que no. */
function crearRugosidadConcreto(tamano = 512): THREE.CanvasTexture {
  const lienzo = document.createElement("canvas");
  lienzo.width = tamano;
  lienzo.height = tamano;
  const textura = new THREE.CanvasTexture(lienzo);
  const ctx = lienzo.getContext("2d");
  if (!ctx) return textura;
  ctx.fillStyle = "rgb(150,150,150)";
  ctx.fillRect(0, 0, tamano, tamano);
  let semilla = 7;
  const rnd = () => {
    semilla = (semilla * 16807) % 2147483647;
    return semilla / 2147483647;
  };
  for (let i = 0; i < 70; i++) {
    const x = rnd() * tamano;
    const y = rnd() * tamano;
    const r = tamano * (0.04 + rnd() * 0.12);
    const g = ctx.createRadialGradient(x, y, 0, x, y, r);
    const v = Math.round(40 + rnd() * 60);
    g.addColorStop(0, `rgba(${v},${v},${v},0.9)`);
    g.addColorStop(1, `rgba(${v},${v},${v},0)`);
    ctx.fillStyle = g;
    ctx.fillRect(x - r, y - r, r * 2, r * 2);
  }
  for (let i = 0; i < 9000; i++) {
    const v = Math.round(110 + rnd() * 90);
    ctx.fillStyle = `rgba(${v},${v},${v},0.35)`;
    ctx.fillRect(rnd() * tamano, rnd() * tamano, 1.5, 1.5);
  }
  textura.wrapS = THREE.RepeatWrapping;
  textura.wrapT = THREE.RepeatWrapping;
  textura.repeat.set(6, 6);
  return textura;
}

function Piso({ reflector }: { reflector: number }) {
  const rugosidad = useMemo(() => crearRugosidadConcreto(), []);
  useEffect(() => () => rugosidad.dispose(), [rugosidad]);
  return (
    <mesh rotation={[-PI / 2, 0, 0]} receiveShadow>
      <circleGeometry args={[40, 64]} />
      {reflector > 0 ? (
        <MeshReflectorMaterial
          resolution={reflector}
          blur={[400, 120]}
          mixBlur={1}
          mixStrength={8}
          mixContrast={1}
          roughness={1}
          roughnessMap={rugosidad}
          depthScale={1.1}
          minDepthThreshold={0.4}
          maxDepthThreshold={1.4}
          color="#121419"
          metalness={0.35}
          mirror={0}
        />
      ) : (
        <meshStandardMaterial color="#14161b" roughness={0.6} metalness={0.3} roughnessMap={rugosidad} />
      )}
    </mesh>
  );
}

/** Plataforma giratoria de exhibición con aro LED rojo (lo capta el bloom). */
function Plataforma() {
  return (
    <group>
      <mesh position={[0, ALTURA_PLATAFORMA / 2, 0]} receiveShadow castShadow>
        <cylinderGeometry args={[2.95, 3.0, ALTURA_PLATAFORMA, 96]} />
        <meshPhysicalMaterial color="#17191e" metalness={0.8} roughness={0.32} clearcoat={0.6} clearcoatRoughness={0.2} />
      </mesh>
      <mesh position={[0, ALTURA_PLATAFORMA + 0.001, 0]} rotation={[-PI / 2, 0, 0]} receiveShadow>
        <ringGeometry args={[2.55, 2.6, 96]} />
        <meshStandardMaterial color="#2a2d34" metalness={0.9} roughness={0.25} />
      </mesh>
      <mesh position={[0, 0.012, 0]} rotation={[-PI / 2, 0, 0]}>
        <ringGeometry args={[3.0, 3.05, 128]} />
        <meshStandardMaterial color="#ff2a14" emissive="#ff1a0a" emissiveIntensity={2.4} toneMapped={false} />
      </mesh>
    </group>
  );
}

/* ------------------------------------------------------------------ luces */
function Luces({ sombra }: { sombra: number }) {
  return (
    <group>
      <ambientLight intensity={0.06} />
      {/* Principal: caja de luz fría desde arriba al frente, con sombra suave. */}
      <spotLight
        position={[4, 11, 6]}
        angle={0.4}
        penumbra={1}
        intensity={95}
        color="#eef2ff"
        castShadow
        shadow-mapSize={[sombra, sombra]}
        shadow-bias={-0.0004}
        shadow-normalBias={0.02}
      />
      {/* Relleno lateral tenue para no perder el lado en sombra. */}
      <spotLight position={[-7, 4, 5]} angle={0.5} penumbra={1} intensity={45} color="#cfd8ff" />
      {/* Contraluz rojo bajo y lateral. El recorte blanco lo dan las franjas del entorno (solo reflejo, sin
          punto especular): una luz puntual detrás deja una mancha blanca en la laca y en el piso. */}
      <spotLight position={[7, 3.2, -7]} angle={0.5} penumbra={0.9} intensity={60} color="#ff3b1f" />
    </group>
  );
}

/** Entorno de estudio hecho con franjas de luz: da reflejos largos y limpios sobre la laca sin depender de un HDRI. */
function Ambiente() {
  return (
    <Environment resolution={512} environmentIntensity={0.9} frames={1}>
      <color attach="background" args={["#050507"]} />
      {/* Franjas de techo (softbox) */}
      {[-3, 0, 3].map((z) => (
        <Lightformer key={z} form="rect" intensity={3} position={[0, 7, z]} rotation-x={PI / 2} scale={[12, 0.8, 1]} />
      ))}
      {/* Paneles laterales blancos: el reflejo horizontal largo típico de una foto de auto de estudio. */}
      <Lightformer form="rect" intensity={1.6} position={[0, 1.6, 9]} scale={[16, 0.5, 1]} />
      <Lightformer form="rect" intensity={1.8} position={[-9, 2, 0]} rotation-y={PI / 2} scale={[14, 1.2, 1]} />
      <Lightformer form="rect" intensity={1.4} position={[-6, 3, -7]} rotation-y={PI / 4} scale={[8, 1, 1]} />
      <Lightformer form="rect" intensity={1.2} position={[9, 2, 0]} rotation-y={-PI / 2} scale={[14, 1.2, 1]} />
      {/* Acento rojo detrás. */}
      <Lightformer form="rect" intensity={2.2} color="#ff3b1f" position={[4, 2, -9]} scale={[6, 2, 1]} />
      {/* Aro superior: brillo especular redondo en techos y hombros. */}
      <Lightformer form="ring" intensity={1.4} position={[0, 6, -2]} scale={2.5} rotation-x={PI / 2} />
    </Environment>
  );
}

/* ------------------------------------------------------------------ posprocesado y control de calidad */
function Posprocesado({ oclusion }: { oclusion: boolean }) {
  return (
    <EffectComposer multisampling={0} enableNormalPass={false}>
      {oclusion ? <N8AO halfRes aoRadius={0.6} intensity={1.6} distanceFalloff={0.6} /> : <></>}
      {/* Umbral ≈ 0,9: solo brillan los emisivos con intensidad > 1 (escáner, faros y aro de la plataforma). */}
      <Bloom mipmapBlur luminanceThreshold={0.9} luminanceSmoothing={0.2} intensity={0.8} radius={0.7} />
      <ToneMapping mode={ToneMappingMode.AGX} />
      <Vignette offset={0.32} darkness={0.62} />
      <SMAA />
    </EffectComposer>
  );
}

/**
 * Aplica el nivel al renderer: dpr y tone mapping. El tone mapping se hace UNA sola vez: en el efecto AgX cuando
 * hay posprocesado y en el renderer cuando no lo hay.
 */
function AjusteRenderer({ nivel }: { nivel: NivelCalidad }) {
  const gl = useThree((s) => s.gl);
  const setDpr = useThree((s) => s.setDpr);
  useEffect(() => {
    const cfg = CONFIG_CALIDAD[nivel];
    setDpr(cfg.dpr);
    gl.toneMapping = cfg.posprocesado ? THREE.NoToneMapping : THREE.AgXToneMapping;
    gl.toneMappingExposure = 1;
    gl.shadowMap.type = THREE.PCFShadowMap;
  }, [gl, nivel, setDpr]);
  return null;
}

interface PropsEstudio {
  nivel: NivelCalidad;
}

export default function IgnisEstudio({ nivel }: PropsEstudio) {
  const cfg = CONFIG_CALIDAD[nivel];
  return (
    <>
      <AjusteRenderer nivel={nivel} />
      <color attach="background" args={[COLOR_HORIZONTE]} />
      <fog attach="fog" args={[COLOR_HORIZONTE, 10, 28]} />
      <Cupula />
      <Ambiente />
      <Luces sombra={cfg.sombra} />
      <Piso reflector={cfg.reflector} />
      <Plataforma />
      {cfg.reflector === 0 ? <ContactShadows position={[0, ALTURA_PLATAFORMA + 0.004, 0]} opacity={0.75} scale={8} blur={2.2} far={4} /> : null}
      {cfg.posprocesado ? <Posprocesado oclusion={cfg.oclusion} /> : null}
    </>
  );
}
