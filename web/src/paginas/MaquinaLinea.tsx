/**
 * Máquina 3 — Línea de ensamble de chasises (SVG 2D).
 * Pregunta: ¿cada cuánto debe salir un chasis de la línea?
 * Relación: takt = tiempo disponible / demanda. La demanda por defecto es la capacidad anual
 * que la API extrae de la base de conocimiento (p. ej. 24.000 chasises/año, planta Bogotá).
 */
import { useEffect, useMemo, useState } from "react";
import {
  BandaTour,
  CabeceraMaquina,
  Chip,
  Deslizador,
  Insignia,
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
import { calcularLinea, colaAcumulada, ENTRADA_LINEA_DEFECTO } from "../modelos/linea";

const MIN_POR_SEGUNDO = 10; // a 1×, un segundo real equivale a 10 min de operación
const PASOS = [
  "La demanda anual y el tiempo disponible fijan el takt",
  "El contenido de trabajo se reparte entre las estaciones",
  "Cada estación trabaja un ciclo c = contenido / estaciones",
  "Si c ≤ takt sale un chasis a tiempo; si no, la cola crece",
];
const fmt = (v: number, d = 0) => v.toLocaleString("es-CO", { minimumFractionDigits: d, maximumFractionDigits: d });

export default function MaquinaLinea({ tour }: { tour: boolean }) {
  const { maquina, error } = useMaquina("linea");
  const capacidadKb = maquina?.parametros.find((p) => p.nombre === "capacidad_anual");
  const [escala, setEscala] = useState(1);
  const reloj = useReloj(escala);
  const [demanda, setDemanda] = useState(ENTRADA_LINEA_DEFECTO.demanda_anual);
  const [contenido, setContenido] = useState(ENTRADA_LINEA_DEFECTO.contenido_min);
  const [estaciones, setEstaciones] = useState(ENTRADA_LINEA_DEFECTO.estaciones);
  const [turnos, setTurnos] = useState(ENTRADA_LINEA_DEFECTO.turnos_dia);
  useEffect(() => {
    if (capacidadKb) setDemanda(capacidadKb.valor);
  }, [capacidadKb]);

  const entrada = useMemo(
    () => ({ ...ENTRADA_LINEA_DEFECTO, demanda_anual: demanda, contenido_min: contenido, estaciones, turnos_dia: turnos }),
    [demanda, contenido, estaciones, turnos],
  );
  const r = calcularLinea(entrada);
  const tMin = reloj.t * MIN_POR_SEGUNDO;
  const producidos = Math.floor(tMin / r.ciclo_min);
  const demandados = Math.floor(tMin / r.takt_min);
  const cola = colaAcumulada(entrada, tMin);
  const fase = (tMin % r.ciclo_min) / r.ciclo_min; // avance dentro del ciclo actual
  const paso = reloj.t === 0 && !reloj.corriendo ? -1 : Math.min(Math.floor(reloj.t / 1.5), 3);

  // Dibujo: hasta 30 estaciones en una fila
  const n = Math.min(estaciones, 30);
  const x0 = 70;
  const ancho = 620;
  const w = ancho / n;
  const yLinea = 270;

  const base = { demanda: capacidadKb?.valor ?? 24000 };
  const tourPasos = [
    { en: 0, texto: `Demanda ${fmt(base.demanda)} chasises/año: el takt marca cada cuánto debe salir uno`, accion: () => {
      setDemanda(base.demanda); setContenido(240); setEstaciones(22); setTurnos(2); setEscala(1); reloj.reiniciar(); reloj.setCorriendo(true);
    } },
    { en: 6, texto: "Con 22 estaciones el ciclo queda por debajo del takt: la línea cumple" },
    { en: 10, texto: "Demanda +25 %: el takt baja y el ciclo ya no alcanza; la cola crece", accion: () => {
      setDemanda(Math.round(base.demanda * 1.25)); reloj.reiniciar(); reloj.setCorriendo(true);
    } },
    { en: 16, texto: "Balancear con más estaciones: N = ⌈contenido / takt⌉", accion: () => {
      setEstaciones(calcularLinea({ ...ENTRADA_LINEA_DEFECTO, demanda_anual: Math.round(base.demanda * 1.25), contenido_min: 240 }).estaciones_min);
      reloj.reiniciar(); reloj.setCorriendo(true);
    } },
    { en: 22, texto: "Capacidad tomada de la base de conocimiento; turnos y contenido son demostrativos" },
  ];
  const banda = useTour(tour, tourPasos, 26);

  const d30 = { ...entrada, demanda_anual: 30000, contenido_min: 240, estaciones: 22, turnos_dia: 2 };
  const r30 = calcularLinea(d30);
  const r30t3 = calcularLinea({ ...d30, turnos_dia: 3 });
  const experimentos: Experimento[] = [
    {
      pregunta: "Si la demanda sube a 30.000 chasises/año con 22 estaciones y 240 min de contenido, ¿se cumple el takt?",
      opciones: [
        { texto: "Sí, sobra capacidad", correcta: false },
        { texto: "No: el ciclo supera el takt y la cola crece", correcta: true },
      ],
      explicacion: `takt = ${fmt(r30.takt_min, 2)} min y c = ${fmt(r30.ciclo_min, 2)} min > takt: faltan ${fmt(r30.deficit_anual)} chasises/año.`,
      aplicar: () => { setDemanda(30000); setContenido(240); setEstaciones(22); setTurnos(2); reloj.reiniciar(); reloj.setCorriendo(true); },
    },
    {
      pregunta: "¿Cuántas estaciones como mínimo se necesitan para 30.000 chasises/año?",
      opciones: [
        { texto: "22", correcta: false },
        { texto: String(r30.estaciones_min), correcta: true },
        { texto: "35", correcta: false },
      ],
      explicacion: `N = ⌈240 / ${fmt(r30.takt_min, 2)}⌉ = ${r30.estaciones_min} estaciones (balanceo ideal, sin pérdidas).`,
      aplicar: () => { setDemanda(30000); setContenido(240); setEstaciones(r30.estaciones_min); setTurnos(2); reloj.reiniciar(); reloj.setCorriendo(true); },
    },
    {
      pregunta: "Con 30.000 chasises/año, si se pasa de 2 a 3 turnos, ¿qué ocurre con el takt?",
      opciones: [
        { texto: "Disminuye", correcta: false },
        { texto: "Aumenta un 50 %", correcta: true },
        { texto: "No cambia", correcta: false },
      ],
      explicacion: `El tiempo disponible crece 50 %: takt ${fmt(r30.takt_min, 2)} → ${fmt(r30t3.takt_min, 2)} min; con 22 estaciones la línea vuelve a cumplir.`,
      aplicar: () => { setDemanda(30000); setContenido(240); setEstaciones(22); setTurnos(3); reloj.reiniciar(); reloj.setCorriendo(true); },
    },
  ];

  return (
    <>
      <CabeceraMaquina
        maquina={maquina}
        respaldo={{
          pregunta: "¿Cada cuánto debe salir un chasis de la línea de ensamble?",
          relacion: "takt = tiempo disponible / demanda",
          idea: "La demanda fija el ritmo: si una estación tarda más que el takt, la cola crece.",
        }}
      />
      <div className="maquina">
        <div>
          <div className="escenario" data-testid="escenario-linea" style={{ height: 460 }}>
            <svg viewBox="0 0 760 460" width="100%" height="100%" role="img" aria-label="Línea de ensamble animada">
              <text x={x0} y="60" fontSize="13" fill="#0b0b0b">Demanda: {fmt(demanda)} chasises/año · {turnos} turno(s) · {entrada.dias_anio} días</text>
              <text x={x0} y="80" fontSize="12" fill="#52514e">Tiempo disponible = {fmt(r.disponible_min)} min/año</text>
              {/* cola de entrada */}
              <g transform={`translate(18, ${yLinea - 60})`}>
                <rect width="40" height="60" fill="none" stroke={cola > 0 ? "#c2410c" : "#8a8984"} strokeDasharray="3 3" />
                <text x="20" y="36" textAnchor="middle" fontSize="16" fill={cola > 0 ? "#c2410c" : "#52514e"} fontWeight="700">{cola}</text>
                <text x="20" y="78" textAnchor="middle" fontSize="11" fill="#52514e">cola</text>
              </g>
              {/* transportador y estaciones */}
              <line x1={x0} y1={yLinea + 6} x2={x0 + ancho} y2={yLinea + 6} stroke="#0b0b0b" strokeWidth="3" />
              {Array.from({ length: n }, (_, i) => (
                <g key={i}>
                  <rect x={x0 + i * w + 2} y={yLinea - 70} width={w - 4} height="40" fill="none" stroke="#0b0b0b" />
                  <rect x={x0 + i * w + 2} y={yLinea - 30} width={(w - 4) * fase} height="3" fill="#2a78d6" />
                  {/* chasis en cada estación (línea llena) */}
                  <rect x={x0 + i * w + 4 + fase * 2} y={yLinea - 12} width={w - 8} height="14" rx="2" fill={r.cumple ? "#2a78d6" : "#eb6834"} />
                </g>
              ))}
              {estaciones > 30 && <text x={x0 + ancho} y={yLinea - 80} textAnchor="end" fontSize="11" fill="#52514e">se dibujan 30 de {estaciones}</text>}
              {/* cifras junto a las piezas */}
              <text x={x0} y={yLinea - 84} fontSize="13" fill="#0b0b0b">c = {fmt(contenido)} / {estaciones} = {fmt(r.ciclo_min, 2)} min por estación</text>
              <g transform={`translate(${x0 + ancho + 6}, ${yLinea - 40})`}>
                <path d="M0 30 h30" stroke="#0b0b0b" strokeWidth="2" />
                <text x="0" y="60" fontSize="12" fill="#0b0b0b">salida</text>
                <text x="0" y="76" fontSize="13" fill="#0b0b0b" fontWeight="700">{producidos}</text>
              </g>
              <g transform={`translate(${x0}, ${yLinea + 60})`}>
                <rect width="330" height="52" rx="3" fill={r.cumple ? "#1baf7a" : "#c2410c"} />
                <text x="10" y="22" fontSize="15" fill="#0b0b0b" fontWeight="700">takt = {fmt(r.takt_min, 2)} min/chasis</text>
                <text x="10" y="42" fontSize="12" fill="#0b0b0b">{r.cumple ? "c ≤ takt: la línea cumple la demanda" : "c > takt: la línea no alcanza la demanda"}</text>
              </g>
              <g transform={`translate(${x0 + 360}, ${yLinea + 60})`}>
                <text x="0" y="16" fontSize="12" fill="#52514e">Estaciones mínimas N = ⌈{fmt(contenido)} / {fmt(r.takt_min, 2)}⌉ = {r.estaciones_min}</text>
                <text x="0" y="36" fontSize="12" fill="#52514e">Capacidad máxima = {fmt(r.capacidad_maxima_anual)} chasises/año</text>
              </g>
              <text x={x0} y="430" fontSize="12" fill="#52514e">
                Tiempo de operación simulado: {fmt(tMin)} min · demandados {demandados} · producidos {producidos}
              </text>
            </svg>
            <span className="leyenda-escena">1 s = {MIN_POR_SEGUNDO} min a 1× · balanceo ideal sin pérdidas · cifras demostrativas</span>
            <BandaTour {...banda} />
          </div>
          <div className="lecturas">
            <Chip etiqueta="takt" valor={`${fmt(r.takt_min, 2)} min`} tono="movimiento" />
            <Chip etiqueta="c" valor={`${fmt(r.ciclo_min, 2)} min`} tono={r.cumple ? "correcto" : "alerta"} />
            <Chip etiqueta="N mínimo" valor={r.estaciones_min} />
            <Chip etiqueta="Capacidad" valor={`${fmt(r.capacidad_maxima_anual)} /año`} />
            <Chip etiqueta="Déficit" valor={`${fmt(r.deficit_anual)} /año`} tono={r.deficit_anual > 0 ? "alerta" : "correcto"} />
            <Chip etiqueta="Cola" valor={cola} tono={cola > 0 ? "alerta" : undefined} />
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
            <Deslizador etiqueta="Demanda anual" valor={demanda} min={6000} max={40000} paso={500} unidad="chasises" alCambiar={setDemanda} />
            {capacidadKb && (
              <p style={{ margin: "-6px 0 10px", fontSize: 12 }}>
                <Insignia tipo={capacidadKb.procedencia} /> valor inicial {fmt(capacidadKb.valor)} {capacidadKb.unidad}
              </p>
            )}
            <Deslizador etiqueta="Contenido de trabajo" valor={contenido} min={60} max={480} paso={10} unidad="min/chasis" alCambiar={setContenido} />
            <Deslizador etiqueta="Estaciones" valor={estaciones} min={4} max={40} paso={1} unidad="" alCambiar={setEstaciones} />
            <Deslizador etiqueta="Turnos por día" valor={turnos} min={1} max={3} paso={1} unidad="" alCambiar={setTurnos} />
            <Reproduccion
              corriendo={reloj.corriendo}
              alCorrer={() => reloj.setCorriendo(true)}
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
            <RevisionCritica extra={["Demanda inicial tomada de la base de conocimiento con su URL"]} />
          </div>
        </aside>
      </div>
    </>
  );
}
