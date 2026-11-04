/**
 * Máquina 2 — Prensa excéntrica de estampado (SVG 2D).
 * Pregunta: ¿cómo convierte una prensa una lámina de acero en un panel estampado?
 * Relación: F = L · t · τ ; cinemática biela-manivela s(θ).
 */
import { useMemo, useState } from "react";
import {
  BandaTour,
  CabeceraMaquina,
  Chip,
  Deslizador,
  ModoExperimento,
  PanelEmpresa,
  Pasos,
  Reproduccion,
  RevisionCritica,
  useMaquina,
  useReloj,
  useTour,
  type Experimento,
} from "../componentes/anatomia";
import { carrera, ENTRADA_PRENSA_DEFECTO, fuerzaCorte, MATERIALES, ventanaCorte } from "../modelos/prensa";

const OMEGA = Math.PI; // rad/s → 30 golpes/min (demostrativo)
const PASOS = [
  "El volante y la manivela giran y almacenan energía",
  "La biela convierte el giro en carrera vertical del carro",
  "El punzón toca la lámina sobre la matriz",
  "Corte: la prensa debe entregar F = L · t · τ",
  "El carro sube y la pieza estampada queda libre",
];
const fmt = (v: number, d = 0) => v.toLocaleString("es-CO", { minimumFractionDigits: d, maximumFractionDigits: d });

export default function MaquinaPrensa({ tour }: { tour: boolean }) {
  const { maquina, error } = useMaquina("prensa");
  const [escala, setEscala] = useState(1);
  const reloj = useReloj(escala);
  const [espesor, setEspesor] = useState(ENTRADA_PRENSA_DEFECTO.espesor_mm);
  const [perimetro, setPerimetro] = useState(ENTRADA_PRENSA_DEFECTO.perimetro_mm);
  const [material, setMaterial] = useState(MATERIALES[0].id);
  const tau = MATERIALES.find((m) => m.id === material)!.tau_mpa;
  const entrada = useMemo(
    () => ({ ...ENTRADA_PRENSA_DEFECTO, espesor_mm: espesor, perimetro_mm: perimetro, tau_mpa: tau }),
    [espesor, perimetro, tau],
  );
  const f = fuerzaCorte(entrada);
  const ventana = ventanaCorte(entrada);

  // Ángulo de manivela: si la fuerza excede la capacidad, el carro se detiene al tocar la lámina.
  const giro = OMEGA * reloj.t;
  const vuelta = Math.floor(giro / (2 * Math.PI));
  let theta = giro % (2 * Math.PI);
  const atascada = f.excede && theta >= ventana.inicio;
  if (atascada) theta = ventana.inicio;
  if (atascada && reloj.corriendo) queueMicrotask(() => reloj.setCorriendo(false));
  const golpes = f.excede ? 0 : vuelta + (theta > ventana.fin ? 1 : 0);
  const s = carrera(entrada, theta);
  const cortando = !f.excede && theta >= ventana.inicio && theta <= ventana.fin;
  const cortada = !f.excede && theta > ventana.fin;
  const paso =
    !reloj.corriendo && reloj.t === 0
      ? -1
      : theta < 0.6
        ? 0
        : theta < ventana.inicio - 0.12
          ? 1
          : theta < ventana.inicio
            ? 2
            : theta <= ventana.fin || atascada
              ? 3
              : 4;

  // Geometría SVG (mm → px). El espesor se dibuja ampliado para que sea visible.
  const k = 0.3;
  const cx = 380;
  const cy = 120;
  const r = entrada.radio_manivela_mm * k;
  const l = entrada.longitud_biela_mm * k;
  const px = cx + r * Math.sin(theta);
  const py = cy - r * Math.cos(theta);
  const yCarro = cy - r + l + s * k; // pasador del carro
  const yPunzon = yCarro + 34;
  const baseCarro = cy - r + l + 34 + 40; // borde inferior del punzón en el punto muerto superior
  const contactoMm = 2 * entrada.radio_manivela_mm - espesor - 4;
  const yLamina = baseCarro + contactoMm * k; // cara superior de la lámina
  const espPx = espesor * 1.2 + 2;
  const yMatriz = yLamina + espPx;

  const tourPasos = [
    { en: 0, texto: "La manivela gira: la biela convierte el giro en carrera del carro", accion: () => {
      setEspesor(2); setPerimetro(1200); setMaterial("dc04"); setEscala(1); reloj.reiniciar(); reloj.setCorriendo(true);
    } },
    { en: 5, texto: "Cámara lenta: el corte ocurre en pocos grados cerca del punto muerto inferior", accion: () => setEscala(0.25) },
    { en: 11, texto: "Duplicar el espesor duplica la fuerza: F = L·t·τ", accion: () => { setEscala(1); setEspesor(4); } },
    { en: 15, texto: "Acero HSLA a 4 mm: 220 t superan la capacidad de 200 t y el ciclo se detiene", accion: () => {
      setMaterial("hsla"); reloj.reiniciar(); reloj.setCorriendo(true);
    } },
    { en: 20, texto: "Menor perímetro de corte: la fuerza vuelve a estar dentro de la capacidad", accion: () => {
      setPerimetro(800); reloj.reiniciar(); reloj.setCorriendo(true);
    } },
    { en: 25, texto: "Cifras demostrativas; los datos de la planta provienen del sitio oficial" },
  ];
  const banda = useTour(tour, tourPasos, 28);

  const f4 = fuerzaCorte({ ...ENTRADA_PRENSA_DEFECTO, espesor_mm: 4 });
  const fH = fuerzaCorte({ ...ENTRADA_PRENSA_DEFECTO, espesor_mm: 4, tau_mpa: 450 });
  const experimentos: Experimento[] = [
    {
      pregunta: "Si el espesor de la lámina pasa de 2 a 4 mm, ¿qué ocurre con la fuerza de corte?",
      opciones: [
        { texto: "Se duplica", correcta: true },
        { texto: "Se cuadruplica", correcta: false },
        { texto: "Se reduce porque la lámina es más rígida", correcta: false },
      ],
      explicacion: `F = L·t·τ es lineal en t: ${fmt(fuerzaCorte(ENTRADA_PRENSA_DEFECTO).toneladas)} t → ${fmt(f4.toneladas)} t.`,
      aplicar: () => { setEspesor(4); setMaterial("dc04"); setPerimetro(1200); reloj.reiniciar(); reloj.setCorriendo(true); },
    },
    {
      pregunta: "Con acero HSLA 420 de 4 mm y 1.200 mm de perímetro, ¿completa la prensa de 200 t el corte?",
      opciones: [
        { texto: "Sí, con margen", correcta: false },
        { texto: "No: la fuerza supera la capacidad", correcta: true },
      ],
      explicacion: `F = 1.200 · 4 · 450 = ${fmt(fH.fuerza_kn)} kN ≈ ${fmt(fH.toneladas)} t > 200 t: el carro se detiene al tocar la lámina.`,
      aplicar: () => { setEspesor(4); setMaterial("hsla"); setPerimetro(1200); reloj.reiniciar(); reloj.setCorriendo(true); },
    },
    {
      pregunta: "¿En qué punto de la carrera es mínima la velocidad del carro?",
      opciones: [
        { texto: "A mitad de carrera", correcta: false },
        { texto: "En los puntos muertos superior e inferior", correcta: true },
        { texto: "Es constante", correcta: false },
      ],
      explicacion: "ds/dθ = 0 en θ = 0° y 180°: el corte ocurre cerca del punto muerto inferior, donde el carro casi se detiene.",
      aplicar: () => { setEspesor(2); setMaterial("dc04"); setPerimetro(1200); setEscala(0.1); reloj.reiniciar(); reloj.setCorriendo(true); },
    },
  ];

  return (
    <>
      <CabeceraMaquina
        maquina={maquina}
        respaldo={{
          pregunta: "¿Cómo convierte una prensa una lámina de acero en un panel estampado?",
          relacion: "F = L · t · τ",
          idea: "La fuerza para cortar crece con el perímetro, el espesor y la resistencia del acero.",
        }}
      />
      <div className="maquina">
        <div>
          <div className="escenario" data-testid="escenario-prensa" style={{ height: 560 }}>
            <svg viewBox="0 0 760 560" width="100%" height="100%" role="img" aria-label="Prensa excéntrica animada">
              <defs>
                <pattern id="rayado" width="8" height="8" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
                  <line x1="0" y1="0" x2="0" y2="8" stroke="#8a8984" strokeWidth="1.5" />
                </pattern>
              </defs>
              {/* bastidor */}
              <rect x="230" y="30" width="300" height="20" fill="url(#rayado)" stroke="#0b0b0b" />
              <rect x="230" y="470" width="300" height="40" fill="url(#rayado)" stroke="#0b0b0b" />
              <line x1="250" y1="50" x2="250" y2="470" stroke="#0b0b0b" strokeWidth="2" />
              <line x1="510" y1="50" x2="510" y2="470" stroke="#0b0b0b" strokeWidth="2" />
              {/* volante y manivela */}
              <circle cx={cx} cy={cy} r={r + 18} fill="none" stroke="#0b0b0b" strokeDasharray="4 4" />
              <circle cx={cx} cy={cy} r={6} fill="#0b0b0b" />
              <line x1={cx} y1={cy} x2={px} y2={py} stroke="#2a78d6" strokeWidth="6" strokeLinecap="round" />
              {/* biela */}
              <line x1={px} y1={py} x2={cx} y2={yCarro} stroke="#0b0b0b" strokeWidth="5" strokeLinecap="round" />
              <circle cx={px} cy={py} r={5} fill="#fcfcfb" stroke="#0b0b0b" strokeWidth="2" />
              {/* carro y punzón */}
              <rect x={cx - 80} y={yCarro - 6} width="160" height="40" fill="#2a78d6" stroke="#0b0b0b" />
              <rect x={cx - 50} y={yPunzon} width="100" height="40" fill="#cfd8e3" stroke="#0b0b0b" />
              {/* matriz con abertura y lámina */}
              <rect x="270" y={yMatriz} width={cx - 52 - 270} height={470 - yMatriz} fill="#e6e5e1" stroke="#0b0b0b" />
              <rect x={cx + 52} y={yMatriz} width={490 - cx - 52} height={470 - yMatriz} fill="#e6e5e1" stroke="#0b0b0b" />
              {cortada ? (
                <>
                  <rect x="270" y={yLamina} width={cx - 52 - 270} height={espPx} fill="#eb6834" />
                  <rect x={cx + 52} y={yLamina} width={490 - cx - 52} height={espPx} fill="#eb6834" />
                  <rect x={cx - 50} y={Math.min(yMatriz + 30, 455)} width="100" height={espPx} fill="#1baf7a" stroke="#0b0b0b" />
                  <text x={cx - 46} y={Math.min(yMatriz + 30, 455) - 6} fontSize="11" fill="#0b0b0b">pieza estampada</text>
                </>
              ) : (
                <rect x="270" y={yLamina} width="220" height={espPx} fill="#eb6834" stroke={cortando || atascada ? "#0b0b0b" : "none"} />
              )}
              {/* cifras junto a las piezas */}
              <text x={530} y={cy - 4} fontSize="13" fill="#0b0b0b">θ = {fmt((theta * 180) / Math.PI)}°</text>
              <text x={530} y={cy + 14} fontSize="12" fill="#52514e">r = {entrada.radio_manivela_mm} mm · l = {entrada.longitud_biela_mm} mm</text>
              <line x1={cx + 80} y1={yCarro + 14} x2={526} y2={yCarro + 14} stroke="#2a78d6" strokeDasharray="2 3" />
              <text x={530} y={yCarro + 18} fontSize="13" fill="#0b0b0b">s = {fmt(s)} mm</text>
              <g transform={`translate(530, ${yLamina - 40})`}>
                <rect x="-4" y="-16" width="232" height="44" rx="3" fill={f.excede ? "#c2410c" : "#eb6834"} />
                <text x="4" y="0" fontSize="14" fill="#0b0b0b" fontWeight="700">F = {fmt(f.fuerza_kn)} kN ({fmt(f.toneladas)} t)</text>
                <text x="4" y="18" fontSize="12" fill="#0b0b0b">{fmt(perimetro)} mm · {fmt(espesor, 1)} mm · {tau} MPa</text>
              </g>
              <text x="40" y="500" fontSize="12" fill="#52514e">Capacidad: {entrada.capacidad_t} t</text>
              <rect x="40" y="508" width="160" height="10" fill="#e6e5e1" />
              <rect x="40" y="508" width={Math.min(f.uso, 1.25) * 128} height="10" fill={f.excede ? "#c2410c" : "#1baf7a"} />
              <line x1="168" y1="504" x2="168" y2="522" stroke="#0b0b0b" />
              <text x="40" y="538" fontSize="12" fill="#0b0b0b">Uso {fmt(f.uso * 100)} %</text>
              <text x="40" y="60" fontSize="12" fill="#52514e">Golpes completos: {golpes}</text>
              {atascada && (
                <text x="40" y="440" fontSize="14" fill="#c2410c" fontWeight="700">
                  <tspan x="40" dy="0">Sobrecarga: la prensa</tspan>
                  <tspan x="40" dy="18">no completa el ciclo</tspan>
                </text>
              )}
            </svg>
            <span className="leyenda-escena">esquema 2D demostrativo · 30 golpes/min · no representa una prensa específica</span>
            <BandaTour {...banda} />
          </div>
          <div className="lecturas">
            <Chip etiqueta="F" valor={`${fmt(f.fuerza_kn)} kN`} tono="fuerza" />
            <Chip etiqueta="Toneladas" valor={`${fmt(f.toneladas)} t`} tono="fuerza" />
            <Chip etiqueta="Uso de capacidad" valor={`${fmt(f.uso * 100)} %`} tono={f.excede ? "alerta" : "correcto"} />
            <Chip etiqueta="Ventana de corte" valor={`${fmt((ventana.inicio * 180) / Math.PI, 1)}°–${fmt((ventana.fin * 180) / Math.PI, 1)}°`} tono="movimiento" />
            <Chip etiqueta="s(θ)" valor={`${fmt(s)} mm`} tono="movimiento" />
          </div>
          <div className="maquina" style={{ gridTemplateColumns: "1fr 1fr" }}>
            <section className="panel">
              <h3>Mecanismo paso a paso</h3>
              <Pasos pasos={PASOS} actual={paso} />
            </section>
            <ModoExperimento experimentos={experimentos} />
          </div>
        </div>
        <aside>
          <section className="panel">
            <h3>Controles</h3>
            <Deslizador etiqueta="Espesor de lámina" valor={espesor} min={0.5} max={6} paso={0.1} unidad="mm" alCambiar={setEspesor} formato={(v) => fmt(v, 1)} />
            <Deslizador etiqueta="Perímetro de corte" valor={perimetro} min={200} max={3000} paso={50} unidad="mm" alCambiar={setPerimetro} />
            <div className="control">
              <label htmlFor="material">Material (τ)</label>
              <output>{tau} MPa</output>
              <select id="material" value={material} onChange={(e) => setMaterial(e.target.value)} style={{ gridColumn: "1 / -1" }}>
                {MATERIALES.map((m) => (
                  <option key={m.id} value={m.id}>{m.nombre}</option>
                ))}
              </select>
            </div>
            <Reproduccion
              corriendo={reloj.corriendo}
              alCorrer={() => (atascada ? (reloj.reiniciar(), reloj.setCorriendo(true)) : reloj.setCorriendo(true))}
              alPausar={() => reloj.setCorriendo(false)}
              alReiniciar={reloj.reiniciar}
              escala={escala}
              alEscala={setEscala}
            />
          </section>
          <div style={{ marginTop: 12 }}>
            <PanelEmpresa maquina={maquina} error={error} />
          </div>
          <div style={{ marginTop: 12 }}>
            <RevisionCritica extra={["τ por material declarado como rango típico publicado (demostrativo)"]} />
          </div>
        </aside>
      </div>
    </>
  );
}
