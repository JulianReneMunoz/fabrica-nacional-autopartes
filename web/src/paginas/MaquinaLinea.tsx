/**
 * Máquina 3 — Línea de ensamble de chasises (SVG 2D). La demanda por defecto es la capacidad anual que la API
 * extrae de la base de conocimiento (p. ej. 24.000 chasises/año, planta Bogotá). Texto, pasos, controles y
 * pestañas salen de `maquinas/linea.ts`; la estructura, de `PlantillaMaquina`.
 */
import { useEffect, useMemo, useState } from "react";
import { fmt, hashRecorrido, useMaquina, useReloj, useTour } from "../componentes/anatomia";
import { ChipDato } from "../componentes/plantilla/ChipDato";
import { ControlesDeclarados } from "../componentes/plantilla/controles";
import { InsigniaFuente } from "../componentes/plantilla/InsigniaFuente";
import { ListaComponentes } from "../componentes/plantilla/ListaComponentes";
import { armarExperimentos } from "../componentes/plantilla/ModoExperimento";
import { PlantillaMaquina } from "../componentes/plantilla/PlantillaMaquina";
import { LINEA } from "../maquinas";
import { calcularLinea, colaAcumulada, ENTRADA_LINEA_DEFECTO } from "../modelos/linea";
import { C } from "../tema/colores";

const MIN_POR_SEGUNDO = 10; // a 1×, un segundo real equivale a 10 min de operación

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
  const banda = useTour(tour, tourPasos, LINEA.duracionRecorrido);

  const d30 = { ...entrada, demanda_anual: 30000, contenido_min: 240, estaciones: 22, turnos_dia: 2 };
  const r30 = calcularLinea(d30);
  const r30t3 = calcularLinea({ ...d30, turnos_dia: 3 });
  const experimentos = armarExperimentos(LINEA.experimentos, [
    {
      explicacion: `takt = ${fmt(r30.takt_min, 2)} min y c = ${fmt(r30.ciclo_min, 2)} min > takt: faltan ${fmt(r30.deficit_anual)} chasises/año.`,
      aplicar: () => { setDemanda(30000); setContenido(240); setEstaciones(22); setTurnos(2); reloj.reiniciar(); reloj.setCorriendo(true); },
    },
    {
      explicacion: `N = ⌈240 / ${fmt(r30.takt_min, 2)}⌉ = ${r30.estaciones_min} estaciones (balanceo ideal, sin pérdidas).`,
      aplicar: () => { setDemanda(30000); setContenido(240); setEstaciones(r30.estaciones_min); setTurnos(2); reloj.reiniciar(); reloj.setCorriendo(true); },
    },
    {
      explicacion: `El tiempo disponible crece 50 %: takt ${fmt(r30.takt_min, 2)} → ${fmt(r30t3.takt_min, 2)} min; con 22 estaciones la línea vuelve a cumplir.`,
      aplicar: () => { setDemanda(30000); setContenido(240); setEstaciones(22); setTurnos(3); reloj.reiniciar(); reloj.setCorriendo(true); },
    },
  ]);

  const lienzo = (
    <svg viewBox="0 0 760 460" width="100%" height="100%" role="img" aria-label="Línea de ensamble animada">
      <text x={x0} y="60" fontSize="13" className="svg-texto">Demanda: {fmt(demanda)} chasises/año · {turnos} turno(s) · {entrada.dias_anio} días</text>
      <text x={x0} y="80" fontSize="12" className="svg-texto-2">Tiempo disponible = {fmt(r.disponible_min)} min/año</text>
      {/* cola de entrada */}
      <g transform={`translate(18, ${yLinea - 60})`}>
        <rect width="40" height="60" fill="none" stroke={cola > 0 ? C.alerta : C.tinta3} strokeDasharray="3 3" />
        <text x="20" y="36" textAnchor="middle" fontSize="16" fill={cola > 0 ? C.alerta : C.tinta2} fontWeight="700">{cola}</text>
        <text x="20" y="78" textAnchor="middle" fontSize="11" className="svg-texto-2">cola</text>
      </g>
      {/* transportador y estaciones */}
      <line x1={x0} y1={yLinea + 6} x2={x0 + ancho} y2={yLinea + 6} stroke={C.tinta} strokeWidth="3" />
      {Array.from({ length: n }, (_, i) => (
        <g key={i}>
          <rect x={x0 + i * w + 2} y={yLinea - 70} width={w - 4} height="40" fill="none" stroke={C.tinta} />
          <rect x={x0 + i * w + 2} y={yLinea - 30} width={(w - 4) * fase} height="3" fill={C.dato} />
          {/* chasis en cada estación (línea llena) */}
          <rect x={x0 + i * w + 4 + fase * 2} y={yLinea - 12} width={w - 8} height="14" rx="2" fill={r.cumple ? C.dato : C.acento} />
        </g>
      ))}
      {estaciones > 30 && <text x={x0 + ancho} y={yLinea - 80} textAnchor="end" fontSize="11" className="svg-texto-2">se dibujan 30 de {estaciones}</text>}
      {/* cifras junto a las piezas */}
      <text x={x0} y={yLinea - 84} fontSize="13" className="svg-texto">c = {fmt(contenido)} / {estaciones} = {fmt(r.ciclo_min, 2)} min por estación</text>
      <g transform={`translate(${x0 + ancho + 6}, ${yLinea - 40})`}>
        <path d="M0 30 h30" stroke={C.tinta} strokeWidth="2" />
        <text x="0" y="60" fontSize="12" className="svg-texto">salida</text>
        <text x="0" y="76" fontSize="13" className="svg-texto" fontWeight="700">{producidos}</text>
      </g>
      <g transform={`translate(${x0}, ${yLinea + 60})`}>
        <rect width="330" height="52" rx="3" fill={r.cumple ? C.ok : C.alerta} />
        <text x="10" y="22" fontSize="15" fill={C.papel} fontWeight="700">takt = {fmt(r.takt_min, 2)} min/chasis</text>
        <text x="10" y="42" fontSize="12" fill={C.papel}>{r.cumple ? "c ≤ takt: la línea cumple la demanda" : "c > takt: la línea no alcanza la demanda"}</text>
      </g>
      <g transform={`translate(${x0 + 360}, ${yLinea + 60})`}>
        <text x="0" y="16" fontSize="12" className="svg-texto-2">Estaciones mínimas N = ⌈{fmt(contenido)} / {fmt(r.takt_min, 2)}⌉ = {r.estaciones_min}</text>
        <text x="0" y="36" fontSize="12" className="svg-texto-2">Capacidad máxima = {fmt(r.capacidad_maxima_anual)} chasises/año</text>
      </g>
      <text x={x0} y="430" fontSize="12" className="svg-texto-2">
        Tiempo de operación simulado: {fmt(tMin)} min · demandados {demandados} · producidos {producidos}
      </text>
    </svg>
  );

  const valores = { demanda, contenido, estaciones, turnos };
  const setters: Record<string, (v: number) => void> = { demanda: setDemanda, contenido: setContenido, estaciones: setEstaciones, turnos: setTurnos };
  const cambiar = (id: string, v: number) => setters[id]?.(v);

  return (
    <PlantillaMaquina
      def={LINEA}
      maquina={maquina}
      errorApi={error}
      barra={{ recorrido: { alPulsar: () => { window.location.hash = hashRecorrido(LINEA.ruta); }, deshabilitado: tour } }}
      lienzo={lienzo}
      leyenda={`1 s = ${MIN_POR_SEGUNDO} min a 1× · balanceo ideal sin pérdidas · cifras demostrativas`}
      banda={banda}
      escenarioProps={{ "data-testid": "escenario-linea" }}
      controles={
        <>
          <ControlesDeclarados defs={LINEA.controles.slice(0, 1)} valores={valores} alCambiar={cambiar} />
          {capacidadKb && (
            <p className="marcas-rpm">
              <InsigniaFuente fuente={capacidadKb.procedencia} /> valor inicial {fmt(capacidadKb.valor)} {capacidadKb.unidad}
            </p>
          )}
          <ControlesDeclarados defs={LINEA.controles.slice(1)} valores={valores} alCambiar={cambiar} />
        </>
      }
      reproduccion={{
        corriendo: reloj.corriendo,
        alCorrer: () => reloj.setCorriendo(true),
        alPausar: () => reloj.setCorriendo(false),
        alReiniciar: reloj.reiniciar,
        escala,
        alEscala: setEscala,
      }}
      contenidoPestanas={{ componentes: <ListaComponentes lista={LINEA.componentes ?? []} /> }}
      chips={
        <>
          <ChipDato etiqueta="takt" valor={`${fmt(r.takt_min, 2)} min`} variante="dato" />
          <ChipDato etiqueta="c" valor={`${fmt(r.ciclo_min, 2)} min`} variante="estado" ok={r.cumple} />
          <ChipDato etiqueta="N mínimo" valor={r.estaciones_min} />
          <ChipDato etiqueta="Capacidad" valor={`${fmt(r.capacidad_maxima_anual)} /año`} />
          <ChipDato etiqueta="Déficit" valor={`${fmt(r.deficit_anual)} /año`} variante="estado" ok={r.deficit_anual <= 0} />
          <ChipDato etiqueta="Cola" valor={cola} variante="estado" ok={cola <= 0} />
        </>
      }
      pasoActual={paso}
      experimentos={experimentos}
    />
  );
}
